import base64
import hashlib
import hmac
import json
import re
import secrets
import time

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

from app.settings import get_settings

router = APIRouter()
USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_token(user_id: str) -> tuple[str, int]:
    settings = get_settings()
    exp = int(time.time()) + settings.auth_token_ttl_seconds
    payload = _b64(json.dumps({"sub": user_id, "exp": exp, "nonce": secrets.token_hex(8)}).encode())
    sig = _b64(hmac.new(settings.auth_secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}", settings.auth_token_ttl_seconds


def verify_token(token: str) -> str | None:
    try:
        payload, _, sig = token.partition(".")
        expect = _b64(
            hmac.new(get_settings().auth_secret.encode(), payload.encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expect):
            return None
        body = json.loads(_unb64(payload))
        if not isinstance(body, dict):
            return None
        exp = body.get("exp", 0)
        if not isinstance(exp, (int, float)) or exp < time.time():
            return None
        user_id = body.get("sub", "")
        if not isinstance(user_id, str):
            return None
        return user_id if USER_ID_RE.match(user_id) else None
    except ValueError, KeyError:
        return None


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


async def require_user(request: Request) -> str:
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


async def require_user_flexible(request: Request, token: str = Query(default="")) -> str:
    user_id = verify_token(_bearer(request) or token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user_id


class LoginBody(BaseModel):
    user_id: str = ""


@router.post("/auth/login")
async def login(body: LoginBody) -> dict:
    user_id = body.user_id.strip() or f"guest-{secrets.token_hex(4)}"
    if not USER_ID_RE.match(user_id):
        raise HTTPException(status_code=400, detail="user_id 非法：只允许字母数字及 -_，长度 1-32")
    token, ttl = sign_token(user_id)
    return {"token": token, "expires_in": ttl}


@router.get("/internal/verify")
async def internal_verify(request: Request, x_internal_token: str = Header(default="")) -> dict:
    if not hmac.compare_digest(x_internal_token, get_settings().auth_internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")
    user_id = verify_token(_bearer(request) or "")
    if user_id is None:
        raise HTTPException(status_code=401, detail="token 无效")
    return {"user_id": user_id}
