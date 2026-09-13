import asyncio
import hashlib
import json
import os
import posixpath
import re
import tempfile
import time

from sqlalchemy.orm import Session

from app.infra.db.models import claim_owner, get_owner
from app.infra.gateway.minio import (
    MinioGateway,
    input_prefix,
    manifest_key,
    utc_timestamp,
    work_key,
    work_prefix,
)
from app.infra.gateway.modal import ModalGateway

THREAD_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
WORK_ROOT = "/workspace/work"
INPUT_ROOT = "/workspace/input"
RESTORE_CONCURRENCY = 8
READ_CHUNK = 1024 * 256


def check_thread_id(thread_id: str) -> None:
    if not THREAD_ID_RE.match(thread_id):
        raise ValueError("thread_id 非法：须为 UUID")


async def check_owner(session: Session, thread_id: str, owner: str, *, must_exist: bool) -> None:
    current = await get_owner(session, thread_id)
    if current is None:
        if must_exist:
            raise ValueError(f"会话 {thread_id} 不存在")
        return
    if current != owner:
        raise PermissionError("无权操作他人会话")


def sanitize_rel(rel: str) -> str:
    cleaned = posixpath.normpath(rel.replace("\\", "/"))
    if (
        cleaned != rel.replace("\\", "/")
        or cleaned.startswith("/")
        or any(s in ("", ".", "..") for s in cleaned.split("/"))
    ):
        raise ValueError(f"快照路径非法：{rel}")
    return cleaned


def _parse_manifest_files(raw: object) -> dict[str, str | None]:
    if not isinstance(raw, list):
        raise ValueError("快照 manifest 损坏，无法恢复")
    parsed: dict[str, str | None] = {}
    for entry in raw:
        if isinstance(entry, str):
            parsed[sanitize_rel(entry)] = None
            continue
        if not isinstance(entry, dict):
            raise ValueError("快照 manifest 损坏，无法恢复")
        sha = entry.get("sha256")
        parsed[sanitize_rel(entry["path"])] = sha if isinstance(sha, str) else None
    return parsed


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_local(local_path: str) -> tuple[bool, int]:
    if not os.path.isfile(local_path) or os.path.islink(local_path):
        return False, 0
    return True, os.path.getsize(local_path)


async def _snapshot_to_minio(
    *, thread_id: str, modal: ModalGateway, minio: MinioGateway
) -> tuple[str, list[dict], list[dict]]:
    remote, skipped = await modal.list_files(thread_id, WORK_ROOT)
    checkpoint = utc_timestamp()
    entries: list[dict] = []
    if not remote:
        return checkpoint, entries, skipped
    with tempfile.TemporaryDirectory(prefix="snapshot-") as tmpdir:
        local_paths = await modal.download_to_local(thread_id, remote, tmpdir)
        for remote_path, local_path in zip(remote, local_paths, strict=True):
            if local_path is None:
                skipped.append({"path": remote_path, "reason": "下载失败或非普通文件"})
                continue
            ok, size = await asyncio.to_thread(_inspect_local, local_path)
            if not ok:
                skipped.append({"path": remote_path, "reason": "下载失败或非普通文件"})
                continue
            rel = sanitize_rel(remote_path[len(WORK_ROOT) + 1 :])
            await asyncio.to_thread(
                minio.put_file, work_key(thread_id, rel), local_path, "application/octet-stream"
            )
            entries.append(
                {
                    "path": rel,
                    "size": size,
                    "sha256": await asyncio.to_thread(sha256_file, local_path),
                }
            )
    return checkpoint, entries, skipped


async def _write_manifest(
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
    await asyncio.to_thread(
        minio.put_bytes, manifest_key(thread_id), json.dumps(manifest).encode(), "application/json"
    )


async def snapshot_session(
    *,
    thread_id: str,
    owner: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    await check_owner(session, thread_id, owner, must_exist=True)
    checkpoint, entries, skipped = await _snapshot_to_minio(
        thread_id=thread_id, modal=modal, minio=minio
    )
    await _write_manifest(
        thread_id=thread_id,
        checkpoint=checkpoint,
        entries=entries,
        skipped=skipped,
        minio=minio,
        closed=False,
    )
    return {"thread_id": thread_id, "checkpoint": checkpoint, "files": len(entries)}


async def ensure_session(
    *,
    thread_id: str,
    owner: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    await claim_owner(session, thread_id, owner)
    sandbox_id = await modal.ensure(thread_id)
    prefix, in_prefix = work_prefix(thread_id), input_prefix(thread_id)
    manifest_raw = await asyncio.to_thread(minio.get_bytes, manifest_key(thread_id))
    manifest_files: dict[str, str | None] | None = None
    if manifest_raw is not None:
        try:
            manifest_files = _parse_manifest_files(json.loads(manifest_raw).get("files"))
        except (ValueError, KeyError, AttributeError, TypeError) as e:
            raise ValueError("快照 manifest 损坏，无法恢复") from e
    if manifest_files is None:
        keys = await asyncio.to_thread(minio.list_keys, prefix)
        manifest_path = manifest_key(thread_id)
        wanted = {sanitize_rel(k["key"][len(prefix) :]) for k in keys if k["key"] != manifest_path}
        expected: dict[str, str | None] = dict.fromkeys(wanted)
    else:
        expected = dict(manifest_files)
    semaphore = asyncio.Semaphore(RESTORE_CONCURRENCY)

    async def _fetch(rel: str) -> tuple[str, bytes]:
        async with semaphore:
            data = await asyncio.to_thread(minio.get_bytes, work_key(thread_id, rel))
        if data is None:
            raise ValueError(f"快照缺文件无法恢复：{rel}")
        if expected[rel] is not None:
            digest = await asyncio.to_thread(hashlib.sha256, data)
            if digest.hexdigest() != expected[rel]:
                raise ValueError(f"快照校验不一致无法恢复：{rel}")
        return rel, data

    files: dict[str, bytes] = {}
    if expected:
        for rel, data in await asyncio.gather(*(_fetch(r) for r in expected)):
            files[f"{WORK_ROOT}/{rel}"] = data
    inputs = await asyncio.to_thread(minio.list_keys, in_prefix)

    async def _fetch_input(key: str) -> tuple[str, bytes | None]:
        async with semaphore:
            return key, await asyncio.to_thread(minio.get_bytes, key)

    for key, data in await asyncio.gather(*(_fetch_input(i["key"]) for i in inputs)):
        if data is not None:
            files[f"{INPUT_ROOT}/{key[len(in_prefix) :]}"] = data
    if files:
        await modal.upload(thread_id, files)
    return {
        "thread_id": thread_id,
        "sandbox_id": sandbox_id,
        "restored_files": len(files),
        "manifest_match": manifest_files is not None,
    }


async def close_session(
    *,
    thread_id: str,
    owner: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    await check_owner(session, thread_id, owner, must_exist=True)
    checkpoint, entries, skipped = await _snapshot_to_minio(
        thread_id=thread_id, modal=modal, minio=minio
    )
    await _write_manifest(
        thread_id=thread_id,
        checkpoint=checkpoint,
        entries=entries,
        skipped=skipped,
        minio=minio,
        closed=True,
    )
    await modal.terminate(thread_id)
    return {"thread_id": thread_id, "checkpoint": checkpoint, "files": len(entries)}
