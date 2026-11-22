
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt
from pwdlib import PasswordHash
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_SESSION_EXPIRE_HOURS: int = 12

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = SecuritySettings()
password_hasher = PasswordHash.recommended()


# =====================================
# 1. PASSWORD HASHING
# =====================================

def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hasher.verify(
        plain_password,
        hashed_password
    )


# =====================================
# 2. CREATE JWT ACCESS TOKEN
# =====================================

def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)

    expire = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": expire
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


# =====================================
# 3. GENERATE REFRESH TOKEN
# =====================================

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


# =====================================
# 4. HASH REFRESH TOKEN
# =====================================

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
