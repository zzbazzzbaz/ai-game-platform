import hmac
import secrets

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.routers.deps import _bearer
from app.services.auth_service import USER_ID_RE, sign_token, verify_token
from app.settings import get_settings

router = APIRouter()


class LoginBody(BaseModel):
    user_id: str = ""


@router.post("/auth/login")
def login(body: LoginBody) -> dict:
    user_id = body.user_id.strip() or f"guest-{secrets.token_hex(4)}"
    if not USER_ID_RE.match(user_id):
        raise HTTPException(status_code=400, detail="user_id 非法：只允许字母数字及 -_，长度 1-32")
    token, ttl = sign_token(user_id)
    return {"token": token, "expires_in": ttl}


@router.get("/internal/verify")
def internal_verify(request: Request, x_internal_token: str = Header(default="")) -> dict:
    if not hmac.compare_digest(x_internal_token, get_settings().auth_internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="token 无效")
    return {"user_id": user_id}
