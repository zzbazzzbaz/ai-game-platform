import asyncio
import os
import posixpath
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import modal
from modal.exception import SandboxFilesystemError

SANDBOX_NAME_PREFIX = "game-"
SANDBOX_TAG_THREAD = "aigame-thread"
LIST_ROOT = "/workspace/work"
READY_RETRIES = 10


class SandboxMissingError(RuntimeError):
    pass


class ModalGateway:
    def __init__(self, *, app_name: str, idle_timeout: int, timeout: int) -> None:
        self._app_name = app_name
        self._idle_timeout = idle_timeout
        self._timeout = timeout
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = asyncio.Lock()
        self._app_id: str | None = None
        self._app_lock = threading.Lock()

    async def _lock_for(self, thread_id: str) -> asyncio.Lock:
        async with self._locks_guard:
            return self._locks.setdefault(thread_id, asyncio.Lock())

    @asynccontextmanager
    async def locked(self, thread_id: str) -> AsyncIterator[None]:
        async with await self._lock_for(thread_id):
            yield

    async def _drop_lock(self, thread_id: str) -> None:
        async with self._locks_guard:
            self._locks.pop(thread_id, None)

    def _app_id_sync(self) -> str:
        with self._app_lock:
            if self._app_id is None:
                self._app_id = modal.App.lookup(self._app_name, create_if_missing=True).app_id
            return self._app_id

    def _find(self, thread_id: str) -> modal.Sandbox | None:
        app_id = self._app_id_sync()
        for sandbox in modal.Sandbox.list(app_id=app_id, tags={SANDBOX_TAG_THREAD: thread_id}):
            return sandbox
        return None

    def _create(self, thread_id: str) -> modal.Sandbox:
        app = modal.App.lookup(self._app_name, create_if_missing=True)
        self._app_id = app.app_id
        sandbox = modal.Sandbox.create(
            app=app,
            name=f"{SANDBOX_NAME_PREFIX}{thread_id}",
            tags={SANDBOX_TAG_THREAD: thread_id},
            idle_timeout=self._idle_timeout,
            timeout=self._timeout,
        )
        last_error = "创建后无响应"
        for _ in range(READY_RETRIES):
            try:
                code, _, err = self._exec(sandbox, "mkdir -p /workspace/work /workspace/input")
                if code == 0:
                    return sandbox
                last_error = err or f"退出码 {code}"
            except Exception as e:
                last_error = str(e)
            time.sleep(3)
        raise RuntimeError(f"sandbox 创建后未就绪：{last_error}")

    def _exec(self, sandbox: modal.Sandbox, command: str) -> tuple[int, str, str]:
        process = sandbox.exec("bash", "-c", command, timeout=60)
        process.wait()
        return process.returncode, process.stdout.read(), process.stderr.read()

    def _require(self, thread_id: str) -> modal.Sandbox:
        sandbox = self._find(thread_id)
        if sandbox is None:
            raise SandboxMissingError(
                f"thread {thread_id} 的 sandbox 不存在，请先调 /sessions/ensure"
            )
        return sandbox

    async def ensure(self, thread_id: str) -> str:
        lock = await self._lock_for(thread_id)
        async with lock:
            found = await asyncio.to_thread(self._find, thread_id)
            if found is not None:
                return found.object_id
            return (await asyncio.to_thread(self._create, thread_id)).object_id

    def _resolve_link(self, entry) -> str | None:
        target = entry.symlink_target
        if not target:
            return None
        if not target.startswith("/"):
            target = posixpath.join(posixpath.dirname(entry.path), target)
        resolved = posixpath.normpath(target)
        if resolved == entry.path:
            return None
        if resolved != LIST_ROOT and not resolved.startswith(LIST_ROOT + "/"):
            return None
        return resolved

    def _is_file(self, sandbox: modal.Sandbox, path: str) -> bool:
        try:
            entries = sandbox.filesystem.list_files(posixpath.dirname(path))
        except SandboxFilesystemError:
            return False
        return any(e.path == path and e.is_file() for e in entries)

    def _walk(
        self, sandbox: modal.Sandbox, root: str, files: list[str], skipped: list[dict]
    ) -> None:
        try:
            entries = sandbox.filesystem.list_files(root)
        except SandboxFilesystemError:
            skipped.append({"path": root, "reason": "列举失败"})
            return
        for entry in entries:
            if entry.is_dir():
                self._walk(sandbox, entry.path, files, skipped)
            elif entry.is_file():
                files.append(entry.path)
            elif entry.is_symlink():
                resolved = self._resolve_link(entry)
                if resolved is not None and self._is_file(sandbox, resolved):
                    files.append(entry.path)
                else:
                    skipped.append({"path": entry.path, "reason": "软链越界或目标非文件"})

    def _list_files(self, thread_id: str, root: str) -> tuple[list[str], list[dict]]:
        if posixpath.normpath(root) != LIST_ROOT:
            raise ValueError(f"只允许列举 {LIST_ROOT}")
        sandbox = self._require(thread_id)
        try:
            files: list[str] = []
            skipped: list[dict] = []
            self._walk(sandbox, LIST_ROOT, files, skipped)
            return sorted(files), skipped
        except SandboxFilesystemError:
            return [], [{"path": LIST_ROOT, "reason": "列举失败"}]

    async def list_files(self, thread_id: str, root: str) -> tuple[list[str], list[dict]]:
        return await asyncio.to_thread(self._list_files, thread_id, root)

    async def download_to_local(
        self, thread_id: str, paths: list[str], dest_dir: str
    ) -> list[str | None]:
        def _run() -> list[str | None]:
            sandbox = self._require(thread_id)
            local_paths: list[str | None] = []
            for index, path in enumerate(paths):
                local_path = os.path.join(dest_dir, f"f{index}")
                try:
                    sandbox.filesystem.copy_to_local(path, local_path)
                except SandboxFilesystemError:
                    local_paths.append(None)
                else:
                    local_paths.append(local_path)
            return local_paths

        return await asyncio.to_thread(_run)

    async def upload(self, thread_id: str, files: dict[str, bytes]) -> None:
        def _run() -> None:
            sandbox = self._require(thread_id)
            for path, content in files.items():
                sandbox.filesystem.write_bytes(bytes(content), path)

        lock = await self._lock_for(thread_id)
        async with lock:
            await asyncio.to_thread(_run)

    async def terminate(self, thread_id: str) -> bool:
        lock = await self._lock_for(thread_id)
        async with lock:
            found = await asyncio.to_thread(self._find, thread_id)
            if found is None:
                return False
            await asyncio.to_thread(found.terminate)
            await self._drop_lock(thread_id)
            return True
