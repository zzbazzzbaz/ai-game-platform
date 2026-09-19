import secrets

from app.core.security import USER_ID_RE, sign_token


def login(user_id: str) -> tuple[str, int]:
    resolved = user_id.strip() or f"guest-{secrets.token_hex(4)}"
    if not USER_ID_RE.match(resolved):
        raise ValueError("user_id 非法：只允许字母数字及 -_，长度 1-32")
    return sign_token(resolved)
