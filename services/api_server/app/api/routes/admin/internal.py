import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.api.dependencies import _bearer
from app.services.auth_service import verify_token
from app.settings import Settings

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/verify")
def internal_verify(request: Request, x_internal_token: str = Header(default="")) -> dict:
    settings: Settings = request.app.state.settings
    if not hmac.compare_digest(x_internal_token, settings.auth_internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="token 无效")
    return {"user_id": user_id}
