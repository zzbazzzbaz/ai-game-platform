import secrets

from fastapi import APIRouter, HTTPException

from app.api.schemas.auth import LoginBody, LoginResponse
from app.services.auth_service import USER_ID_RE, sign_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginBody) -> LoginResponse:
    user_id = body.user_id.strip() or f"guest-{secrets.token_hex(4)}"
    if not USER_ID_RE.match(user_id):
        raise HTTPException(status_code=400, detail="user_id 非法：只允许字母数字及 -_，长度 1-32")
    token, ttl = sign_token(user_id)
    return LoginResponse(token=token, expires_in=ttl)
