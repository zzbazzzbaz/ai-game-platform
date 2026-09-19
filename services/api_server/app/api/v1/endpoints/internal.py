import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.dependencies import UserIdDep
from app.api.schemas.auth import VerifyResponse
from app.core.config import Settings

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/verify", response_model=VerifyResponse)
def internal_verify(
    request: Request,
    user_id: UserIdDep,
    x_internal_token: str = Header(default=""),
) -> VerifyResponse:
    settings: Settings = request.app.state.settings
    if not hmac.compare_digest(x_internal_token, settings.auth_internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")
    return VerifyResponse(user_id=user_id)
