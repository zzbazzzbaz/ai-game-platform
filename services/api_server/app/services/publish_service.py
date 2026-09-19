import os
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from html.parser import HTMLParser

from sqlalchemy.orm import Session

from app.core.constants import (
    ESM_PATTERN,
    FILENAME_PATTERN,
    HTML_MEDIA_TYPE,
    INLINE_REF_PREFIXES,
    INLINE_RESOURCE_ATTRS,
    INPUT_EXTENSIONS,
    MAX_HTML_BYTES,
    MAX_INPUT_BYTES,
    MAX_SCRIPT_BYTES,
    NODE_CHECK_TIMEOUT_SECONDS,
    NODE_CONCURRENCY,
    STREAM_CHUNK_SIZE,
    VERSION_LATEST,
    VERSION_MAX_ATTEMPTS,
    VERSION_PATTERN,
    WORK_INDEX_FILE,
)
from app.core.exceptions import NotFoundError, UpstreamError, ValidationError
from app.gateways.minio import (
    MinioGateway,
    input_key,
    utc_timestamp,
    version_key,
    work_key,
)
from app.gateways.modal import ModalGateway, SandboxMissingError
from app.services.session_service import check_owner, check_thread_id, snapshot_session

_NODE_SEMAPHORE = threading.Semaphore(NODE_CONCURRENCY)


class _RefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_html = False
        self.has_script = False
        self.in_inline_script = False
        self.scripts: list[str] = []
        self.bad_refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name == "html":
            self.has_html = True
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if name == "script":
            self.has_script = True
            src = attr_map.get("src", "")
            if src:
                if not _is_inlineable_ref(src):
                    self.bad_refs.append(f"script src={src}")
            else:
                self.in_inline_script = True
                self.scripts.append("")
        for attr in INLINE_RESOURCE_ATTRS.get(name, ()):
            if name == "script" and attr == "src":
                continue
            ref = attr_map.get(attr, "")
            if ref and not _is_inlineable_ref(ref):
                self.bad_refs.append(f"{name} {attr}={ref}")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self.in_inline_script = False

    def handle_data(self, data: str) -> None:
        if self.in_inline_script and self.scripts:
            self.scripts[-1] += data


def _is_inlineable_ref(ref: str) -> bool:
    return ref.strip().lower().startswith(INLINE_REF_PREFIXES)


def validate_index_html(html: bytes) -> list[str]:
    if not html:
        raise ValidationError("index.html 为空，无法发布")
    if len(html) > MAX_HTML_BYTES:
        raise ValidationError("index.html 超过 2MB，无法发布")
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError("index.html 不是合法 UTF-8 编码") from None
    lowered = text.lower()
    if "<html" not in lowered or "</html>" not in lowered:
        raise ValidationError("index.html 缺少 <html> 结构")
    collector = _RefCollector()
    try:
        collector.feed(text)
    except Exception as e:
        raise ValidationError(f"index.html 解析失败：{e}") from e
    if not collector.has_html:
        raise ValidationError("index.html 缺少 <html> 结构")
    if collector.bad_refs:
        raise ValidationError(
            "index.html 引用了外部文件，单文件发布不允许：" + "；".join(collector.bad_refs[:5])
        )
    if not collector.has_script:
        raise ValidationError("index.html 缺少 <script>，不是可玩游戏")
    scripts = [s for s in (b.strip() for b in collector.scripts) if s]
    if not scripts:
        raise ValidationError("index.html 没有内联游戏代码")
    if sum(len(s) for s in scripts) > MAX_SCRIPT_BYTES:
        raise ValidationError("内联脚本超过 1MB，无法发布")
    return scripts


def check_scripts_with_node(scripts: list[str]) -> None:
    node = shutil.which("node")
    if node is None:
        raise UpstreamError("校验环境缺 node，无法发布")
    for i, script in enumerate(scripts):
        suffix = ".mjs" if ESM_PATTERN.search(script) else ".js"
        handle, path = tempfile.mkstemp(suffix=suffix)
        os.close(handle)
        try:
            with open(path, "w") as tmp:
                tmp.write(script)
            proc = subprocess.run(
                [node, "--check", path],
                capture_output=True,
                text=True,
                timeout=NODE_CHECK_TIMEOUT_SECONDS,
            )
        finally:
            os.unlink(path)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            raise ValidationError(f"第 {i + 1} 段内联脚本语法错误：" + (detail[0] if detail else "未知"))


def check_input_file(filename: str, size: int) -> None:
    if not FILENAME_PATTERN.match(filename):
        raise ValidationError("文件名非法：只允许字母数字及 _.-，且不能以点开头")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in INPUT_EXTENSIONS:
        raise ValidationError("素材只支持图片与文本：png/jpg/gif/webp/svg/txt/md/json/csv")
    if size > MAX_INPUT_BYTES:
        raise ValidationError("素材超过 5MB")


def check_version(version: str) -> None:
    if version != VERSION_LATEST and not VERSION_PATTERN.match(version):
        raise ValidationError(f"版本非法：{version}")


def _claim_version(minio: MinioGateway, thread_id: str, html: bytes) -> str:
    base = utc_timestamp()
    for n in range(VERSION_MAX_ATTEMPTS):
        version = base if n == 0 else f"{base}_{n + 1}"
        claimed = minio.put_bytes_if_absent(
            version_key(thread_id, version),
            html,
            HTML_MEDIA_TYPE,
        )
        if claimed:
            return version
    raise UpstreamError("版本并发冲突过多，请重试")


def publish_version(
    *,
    thread_id: str,
    user_id: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    check_owner(session, thread_id, user_id, must_exist=True)
    with modal.locked(thread_id):
        try:
            snapshot_session(
                thread_id=thread_id, user_id=user_id, session=session, modal=modal, minio=minio
            )
        except SandboxMissingError:
            raise ValidationError("会话环境不存在，请先创建会话再发布") from None
        html = minio.get_bytes(work_key(thread_id, WORK_INDEX_FILE))
        if html is None:
            raise ValidationError("工作区还没有 /workspace/work/index.html，生成完成后再发布")
        scripts = validate_index_html(html)
        with _NODE_SEMAPHORE:
            check_scripts_with_node(scripts)
        version = _claim_version(minio, thread_id, html)
    return {"thread_id": thread_id, "version": version, "size": len(html)}


def list_versions(
    *, thread_id: str, user_id: str, session: Session, minio: MinioGateway
) -> list[dict]:
    check_thread_id(thread_id)
    check_owner(session, thread_id, user_id, must_exist=True)
    items = minio.list_versions(thread_id)
    return [{"n": i + 1, **v} for i, v in enumerate(items)]


def resolve_version(*, thread_id: str, version: str, minio: MinioGateway) -> str:
    check_thread_id(thread_id)
    check_version(version)
    if version == VERSION_LATEST:
        items = minio.list_versions(thread_id)
        if not items:
            raise NotFoundError("该会话还没有已发布版本")
        return items[-1]["version"]
    return version


def get_version_bytes(*, thread_id: str, version: str, minio: MinioGateway) -> bytes:
    resolved = resolve_version(thread_id=thread_id, version=version, minio=minio)
    html = minio.get_bytes(version_key(thread_id, resolved))
    if html is None:
        raise NotFoundError(f"版本 {resolved} 不存在")
    return html


def _stream_body(body) -> Iterator[bytes]:
    try:
        yield from body.iter_chunks(chunk_size=STREAM_CHUNK_SIZE)
    finally:
        body.close()


def open_version_stream(*, minio: MinioGateway, thread_id: str, version: str) -> Iterator[bytes]:
    body = minio.open_stream(version_key(thread_id, version))
    if body is None:
        raise NotFoundError(f"版本 {version} 不存在")
    return _stream_body(body)


def store_input(
    *,
    thread_id: str,
    user_id: str,
    filename: str,
    data: bytes,
    content_type: str,
    session: Session,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    check_owner(session, thread_id, user_id, must_exist=True)
    check_input_file(filename, len(data))
    minio.put_bytes(input_key(thread_id, filename), data, content_type)
    return {"filename": filename, "size": len(data)}
