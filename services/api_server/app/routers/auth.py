import hmac
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.auth_service import USER_ID_RE, sign_token, verify_token
from app.settings import get_settings

router = APIRouter()


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def require_user(request: Request) -> str:
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


def require_user_flexible(request: Request, token: str = Query(default="")) -> str:
    user_id = verify_token(_bearer(request) or token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


UserDep = Annotated[str, Depends(require_user)]
FlexibleUserDep = Annotated[str, Depends(require_user_flexible)]


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
