import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import AsyncIterator
from html.parser import HTMLParser

from app.infra.db.session import Session
from app.infra.gateway.minio import MinioGateway, input_key, utc_timestamp, version_key, work_key
from app.infra.gateway.modal import ModalGateway, SandboxMissingError
from app.services.session_service import check_owner, check_thread_id, snapshot_session

MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_SCRIPT_BYTES = 1024 * 1024
RESOURCE_ATTRS = {
    "script": ("src",),
    "link": ("href",),
    "img": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "source": ("src",),
}
INPUT_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".txt", ".md", ".json", ".csv"}
MAX_INPUT_BYTES = 5 * 1024 * 1024
FILENAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]{0,127}$")
VERSION_RE = re.compile(r"^\d{14}(?:_\d+)?$")
ESM_RE = re.compile(r"^\s*(import|export)\b", re.MULTILINE)
VERSION_ATTEMPTS = 100
STREAM_CHUNK = 1024 * 64


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
        for attr in RESOURCE_ATTRS.get(name, ()):
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
    return ref.strip().lower().startswith(("data:", "blob:", "#"))


def validate_index_html(html: bytes) -> list[str]:
    if not html:
        raise ValueError("index.html 为空，无法发布")
    if len(html) > MAX_HTML_BYTES:
        raise ValueError("index.html 超过 2MB，无法发布")
    try:
        text = html.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("index.html 不是合法 UTF-8 编码") from None
    lowered = text.lower()
    if "<html" not in lowered or "</html>" not in lowered:
        raise ValueError("index.html 缺少 <html> 结构")
    collector = _RefCollector()
    try:
        collector.feed(text)
    except Exception as e:
        raise ValueError(f"index.html 解析失败：{e}") from e
    if not collector.has_html:
        raise ValueError("index.html 缺少 <html> 结构")
    if collector.bad_refs:
        raise ValueError(
            "index.html 引用了外部文件，单文件发布不允许：" + "；".join(collector.bad_refs[:5])
        )
    if not collector.has_script:
        raise ValueError("index.html 缺少 <script>，不是可玩游戏")
    scripts = [s for s in (b.strip() for b in collector.scripts) if s]
    if not scripts:
        raise ValueError("index.html 没有内联游戏代码")
    if sum(len(s) for s in scripts) > MAX_SCRIPT_BYTES:
        raise ValueError("内联脚本超过 1MB，无法发布")
    return scripts


def check_scripts_with_node(scripts: list[str]) -> None:
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("校验环境缺 node，无法发布")
    for i, script in enumerate(scripts):
        suffix = ".mjs" if ESM_RE.search(script) else ".js"
        handle, path = tempfile.mkstemp(suffix=suffix)
        os.close(handle)
        try:
            with open(path, "w") as tmp:
                tmp.write(script)
            proc = subprocess.run(
                [node, "--check", path], capture_output=True, text=True, timeout=60
            )
        finally:
            os.unlink(path)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip().splitlines()
            raise ValueError(f"第 {i + 1} 段内联脚本语法错误：" + (detail[0] if detail else "未知"))


def check_input_file(filename: str, size: int) -> None:
    if not FILENAME_RE.match(filename):
        raise ValueError("文件名非法：只允许字母数字及 _.-，且不能以点开头")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in INPUT_EXTS:
        raise ValueError("素材只支持图片与文本：png/jpg/gif/webp/svg/txt/md/json/csv")
    if size > MAX_INPUT_BYTES:
        raise ValueError("素材超过 5MB")


def check_version(version: str) -> None:
    if version != "latest" and not VERSION_RE.match(version):
        raise ValueError(f"版本非法：{version}")


async def _claim_version(minio: MinioGateway, thread_id: str, html: bytes) -> str:
    base = utc_timestamp()
    for n in range(VERSION_ATTEMPTS):
        version = base if n == 0 else f"{base}_{n + 1}"
        claimed = await asyncio.to_thread(
            minio.put_bytes_if_absent,
            version_key(thread_id, version),
            html,
            "text/html; charset=utf-8",
        )
        if claimed:
            return version
    raise RuntimeError("版本并发冲突过多，请重试")


async def publish_version(
    *,
    thread_id: str,
    owner: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    await check_owner(session, thread_id, owner, must_exist=True)
    async with modal.locked(thread_id):
        try:
            await snapshot_session(
                thread_id=thread_id, owner=owner, session=session, modal=modal, minio=minio
            )
        except SandboxMissingError:
            raise ValueError("会话环境不存在，请先创建会话再发布") from None
        html = await asyncio.to_thread(minio.get_bytes, work_key(thread_id, "index.html"))
        if html is None:
            raise ValueError("工作区还没有 /workspace/work/index.html，生成完成后再发布")
        scripts = validate_index_html(html)
        await asyncio.to_thread(check_scripts_with_node, scripts)
        version = await _claim_version(minio, thread_id, html)
    return {"thread_id": thread_id, "version": version, "size": len(html)}


async def list_versions(
    *, thread_id: str, owner: str, session: Session, minio: MinioGateway
) -> list[dict]:
    check_thread_id(thread_id)
    await check_owner(session, thread_id, owner, must_exist=True)
    items = await asyncio.to_thread(minio.list_versions, thread_id)
    return [{"n": i + 1, **v} for i, v in enumerate(items)]


async def resolve_version(
    *, thread_id: str, owner: str, version: str, session: Session, minio: MinioGateway
) -> str:
    check_thread_id(thread_id)
    check_version(version)
    await check_owner(session, thread_id, owner, must_exist=True)
    if version == "latest":
        items = await asyncio.to_thread(minio.list_versions, thread_id)
        if not items:
            raise ValueError("该会话还没有已发布版本")
        return items[-1]["version"]
    return version


async def get_version_bytes(
    *, thread_id: str, owner: str, version: str, session: Session, minio: MinioGateway
) -> bytes:
    resolved = await resolve_version(
        thread_id=thread_id, owner=owner, version=version, session=session, minio=minio
    )
    html = await asyncio.to_thread(minio.get_bytes, version_key(thread_id, resolved))
    if html is None:
        raise ValueError(f"版本 {resolved} 不存在")
    return html


async def _stream_body(body) -> AsyncIterator[bytes]:
    try:
        chunks = body.iter_chunks(chunk_size=STREAM_CHUNK)
        while True:
            chunk = await asyncio.to_thread(next, chunks, None)
            if chunk is None:
                break
            yield chunk
    finally:
        await asyncio.to_thread(body.close)


async def open_version_stream(
    *, minio: MinioGateway, thread_id: str, version: str
) -> AsyncIterator[bytes]:
    body = await asyncio.to_thread(minio.open_stream, version_key(thread_id, version))
    if body is None:
        raise ValueError(f"版本 {version} 不存在")
    return _stream_body(body)


async def store_input(
    *,
    thread_id: str,
    owner: str,
    filename: str,
    data: bytes,
    content_type: str,
    session: Session,
    minio: MinioGateway,
) -> dict:
    check_thread_id(thread_id)
    await check_owner(session, thread_id, owner, must_exist=True)
    check_input_file(filename, len(data))
    await asyncio.to_thread(minio.put_bytes, input_key(thread_id, filename), data, content_type)
    return {"filename": filename, "size": len(data)}
