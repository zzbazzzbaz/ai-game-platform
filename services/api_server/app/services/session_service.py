import hashlib
import json
import os
import posixpath
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.core.constants import (
    BINARY_MEDIA_TYPE,
    FILE_CHUNK_SIZE,
    INPUT_ROOT,
    JSON_MEDIA_TYPE,
    RESTORE_CONCURRENCY,
    THREAD_ID_PATTERN,
    WORK_ROOT,
)
from app.core.exceptions import ForbiddenError, ValidationError
from app.gateways.minio import (
    MinioGateway,
    input_prefix,
    manifest_key,
    utc_timestamp,
    work_key,
    work_prefix,
)
from app.gateways.modal import ModalGateway
from app.repositories.thread_owner_repository import thread_owner_repository


def check_thread_id(thread_id: str) -> None:
    if not THREAD_ID_PATTERN.match(thread_id):
        raise ValidationError("thread_id 非法：须为 UUID")


def get_owner(session: Session, thread_id: str) -> str | None:
    row = thread_owner_repository.get(session, thread_id)
    return row.user_id if row else None


def claim_owner(session: Session, thread_id: str, user_id: str) -> None:
    thread_owner_repository.claim(session, thread_id, user_id)
    current = get_owner(session, thread_id)
    if current != user_id:
        if current is None:
            raise ValidationError(f"会话 {thread_id} 不存在")
        raise ForbiddenError("无权操作他人会话")


def check_owner(session: Session, thread_id: str, user_id: str, *, must_exist: bool) -> None:
    current = get_owner(session, thread_id)
    if current is None:
        if must_exist:
            raise ValidationError(f"会话 {thread_id} 不存在")
        return
    if current != user_id:
        raise ForbiddenError("无权操作他人会话")


def sanitize_rel(rel: str) -> str:
    cleaned = posixpath.normpath(rel.replace("\\", "/"))
    if (
        cleaned != rel.replace("\\", "/")
        or cleaned.startswith("/")
        or any(s in ("", ".", "..") for s in cleaned.split("/"))
    ):
        raise ValidationError(f"快照路径非法：{rel}")
    return cleaned


def _parse_manifest_files(raw: object) -> dict[str, str | None]:
    if not isinstance(raw, list):
        raise ValidationError("快照 manifest 损坏，无法恢复")
    parsed: dict[str, str | None] = {}
    for entry in raw:
        if isinstance(entry, str):
            parsed[sanitize_rel(entry)] = None
            continue
        if not isinstance(entry, dict):
            raise ValidationError("快照 manifest 损坏，无法恢复")
        sha = entry.get("sha256")
        parsed[sanitize_rel(entry["path"])] = sha if isinstance(sha, str) else None
    return parsed


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(FILE_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_local(local_path: str) -> tuple[bool, int]:
    if not os.path.isfile(local_path) or os.path.islink(local_path):
        return False, 0
    return True, os.path.getsize(local_path)


def _snapshot_to_minio(
    *, thread_id: str, modal: ModalGateway, minio: MinioGateway
) -> tuple[str, list[dict], list[dict]]:
    remote, skipped = modal.list_files(thread_id, WORK_ROOT)
    checkpoint = utc_timestamp()
    entries: list[dict] = []
    if not remote:
        return checkpoint, entries, skipped
    with tempfile.TemporaryDirectory(prefix="snapshot-") as tmpdir:
        local_paths = modal.download_to_local(thread_id, remote, tmpdir)
        for remote_path, local_path in zip(remote, local_paths, strict=True):
            if local_path is None:
                skipped.append({"path": remote_path, "reason": "下载失败或非普通文件"})
                continue
            ok, size = _inspect_local(local_path)
            if not ok:
                skipped.append({"path": remote_path, "reason": "下载失败或非普通文件"})
                continue
            rel = sanitize_rel(remote_path[len(WORK_ROOT) + 1 :])
            minio.put_file(work_key(thread_id, rel), local_path, BINARY_MEDIA_TYPE)
            entries.append(
                {
                    "path": rel,
                    "size": size,
                    "sha256": sha256_file(local_path),
                }
            )
    return checkpoint, entries, skipped


def _write_manifest(
    *,
    thread_id: str,
    checkpoint: str,
    entries: list[dict],
    skipped: list[dict],
    minio: MinioGateway,
    closed: bool,
) -> None:
    manifest = {
        "thread_id": thread_id,
        "checkpoint": checkpoint,
        "closed_at": int(time.time()) if closed else None,
        "files": sorted(entries, key=lambda e: e["path"]),
        "skipped": skipped,
    }
    minio.put_bytes(manifest_key(thread_id), json.dumps(manifest).encode(), JSON_MEDIA_TYPE)


def snapshot_session(
    *,
    thread_id: str,
    user_id: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    check_owner(session, thread_id, user_id, must_exist=True)
    checkpoint, entries, skipped = _snapshot_to_minio(thread_id=thread_id, modal=modal, minio=minio)
    _write_manifest(
        thread_id=thread_id,
        checkpoint=checkpoint,
        entries=entries,
        skipped=skipped,
        minio=minio,
        closed=False,
    )
    return {"thread_id": thread_id, "checkpoint": checkpoint, "files": len(entries)}


def ensure_session(
    *,
    thread_id: str,
    user_id: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    claim_owner(session, thread_id, user_id)
    sandbox_id = modal.ensure(thread_id)
    prefix, in_prefix = work_prefix(thread_id), input_prefix(thread_id)
    manifest_raw = minio.get_bytes(manifest_key(thread_id))
    manifest_files: dict[str, str | None] | None = None
    if manifest_raw is not None:
        try:
            manifest_files = _parse_manifest_files(json.loads(manifest_raw).get("files"))
        except (ValueError, ValidationError, KeyError, AttributeError, TypeError) as e:
            raise ValidationError("快照 manifest 损坏，无法恢复") from e
    if manifest_files is None:
        keys = minio.list_keys(prefix)
        manifest_path = manifest_key(thread_id)
        wanted = {sanitize_rel(k["key"][len(prefix) :]) for k in keys if k["key"] != manifest_path}
        expected: dict[str, str | None] = dict.fromkeys(wanted)
    else:
        expected = dict(manifest_files)

    def _fetch(rel: str) -> tuple[str, bytes]:
        data = minio.get_bytes(work_key(thread_id, rel))
        if data is None:
            raise ValidationError(f"快照缺文件无法恢复：{rel}")
        if expected[rel] is not None and hashlib.sha256(data).hexdigest() != expected[rel]:
            raise ValidationError(f"快照校验不一致无法恢复：{rel}")
        return rel, data

    files: dict[str, bytes] = {}
    if expected:
        with ThreadPoolExecutor(max_workers=RESTORE_CONCURRENCY) as pool:
            for rel, data in pool.map(_fetch, expected):
                files[f"{WORK_ROOT}/{rel}"] = data
    inputs = minio.list_keys(in_prefix)

    def _fetch_input(key: str) -> tuple[str, bytes | None]:
        return key, minio.get_bytes(key)

    with ThreadPoolExecutor(max_workers=RESTORE_CONCURRENCY) as pool:
        for key, data in pool.map(_fetch_input, (i["key"] for i in inputs)):
            if data is not None:
                files[f"{INPUT_ROOT}/{key[len(in_prefix) :]}"] = data
    if files:
        modal.upload(thread_id, files)
    return {
        "thread_id": thread_id,
        "sandbox_id": sandbox_id,
        "restored_files": len(files),
        "manifest_match": manifest_files is not None,
    }


def close_session(
    *,
    thread_id: str,
    user_id: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    check_owner(session, thread_id, user_id, must_exist=True)
    checkpoint, entries, skipped = _snapshot_to_minio(thread_id=thread_id, modal=modal, minio=minio)
    _write_manifest(
        thread_id=thread_id,
        checkpoint=checkpoint,
        entries=entries,
        skipped=skipped,
        minio=minio,
        closed=True,
    )
    modal.terminate(thread_id)
    return {"thread_id": thread_id, "checkpoint": checkpoint, "files": len(entries)}
