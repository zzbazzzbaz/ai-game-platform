from fastapi import APIRouter, HTTPException

from app.schemas.auth import LoginBody, LoginResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginBody) -> LoginResponse:
    try:
        token, ttl = auth_service.login(body.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return LoginResponse(token=token, expires_in=ttl)
