import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.dependencies import UserIdDep
from app.settings import Settings

router = APIRouter(tags=["callback"])


@router.get("/verify")
def internal_verify(
    request: Request,
    user_id: UserIdDep,
    x_internal_token: str = Header(default=""),
) -> dict:
    settings: Settings = request.app.state.settings
    if not hmac.compare_digest(x_internal_token, settings.auth_internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")
    return {"user_id": user_id}
