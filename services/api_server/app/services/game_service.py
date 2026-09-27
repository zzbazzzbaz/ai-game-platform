import tempfile

from sqlalchemy.orm import Session

from app.core.constants import HTML_MEDIA_TYPE, WORK_DIST_INDEX, WORK_INDEX_FILE, WORK_ROOT
from app.core.exceptions import ValidationError
from app.gateways.minio import MinioGateway, game_key
from app.gateways.modal import ModalGateway, SandboxMissingError
from app.services.publish_service import validate_index_html
from app.services.session_service import check_thread_id


def publish_game(
    *,
    thread_id: str,
    user_id: str,
    session: Session,
    modal: ModalGateway,
    minio: MinioGateway,
    public_base_url: str,
) -> dict:
    """把沙箱内 dist/index.html 发布为公网可玩的单文件游戏。

    简化版：构建由 Agent 在工作区执行 `npm run build` 完成，平台只校验产物形状并落桶。
    user_id 暂仅为接口预留（用户体系未落地，越权校验已临时关闭）。
    """
    check_thread_id(thread_id)
    # TODO(用户体系): 恢复 check_owner(session, thread_id, user_id, must_exist=True) 越权校验
    remote = f"{WORK_ROOT}/{WORK_DIST_INDEX}"
    with modal.locked(thread_id):
        with tempfile.TemporaryDirectory(prefix="publish-") as tmpdir:
            try:
                paths = modal.download_to_local(thread_id, [remote], tmpdir)
            except SandboxMissingError:
                raise ValidationError("会话环境不存在，请先创建会话并生成游戏") from None
            local = paths[0]
        if local is None:
            raise ValidationError("还没有构建产物 dist/index.html，请先执行 npm run build")
        with open(local, "rb") as handle:
            html = handle.read()
        validate_index_html(html)
        minio.put_bytes(game_key(thread_id), html, HTML_MEDIA_TYPE)
    base = public_base_url.rstrip("/")
    return {
        "thread_id": thread_id,
        "size": len(html),
        "url": f"{base}/{thread_id}/{WORK_INDEX_FILE}",
    }
