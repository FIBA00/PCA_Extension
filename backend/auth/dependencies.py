from jwt.exceptions import PyJWTError as JWTError
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from typing import Optional

from utility.logger import get_logger
from core.config import settings
from core.schemas import TokenData
from core.custom_error_handlers import (
    InvalidToken,
    AccessTokenRequired,
    RefreshTokenRequired,
)
from db.redis import token_in_blocklist
from auth.oauth2 import decode_access_token

lg = get_logger(__file__)

security = HTTPBearer(auto_error=True)
optional_security = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = creds.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception

        token_data = TokenData(
            user_id=user_id,
            is_admin=payload.get("is_admin", False),
            is_verified=payload.get("is_verified", False),
        )
        return token_data
    except JWTError:
        raise credentials_exception


def get_optional_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[TokenData]:
    if creds is None:
        return None
    try:
        payload = decode_access_token(creds.credentials)
        user_id: str = payload.get("user_id")
        if user_id is None:
            return None

        token_data = TokenData(
            user_id=user_id,
            is_admin=payload.get("is_admin", False),
            is_verified=payload.get("is_verified", False),
        )
        return token_data
    except JWTError:
        return None


def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is not verified"
        )
    return current_user


def get_current_admin_user(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User is not an admin"
        )
    return current_user


async def get_access_token(
    creds: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> str:
    lg.debug(f"Extracted credentials scheme: {creds.scheme}")

    token = creds.credentials
    lg.debug(f"Validating access token: {token[:10]}...")
    token_data = decode_access_token(token)
    if token_data is None:
        lg.debug("Token data invalid")
        raise InvalidToken()

    jti = token_data.get("jti")
    if jti and await token_in_blocklist(jti):
        lg.debug(f"Token JTI {jti} is in blocklist.")
        raise InvalidToken()

    if token_data.get("refresh", False):
        lg.error("Refresh token used where access token expected.")
        raise AccessTokenRequired()
    lg.debug("Access token validated successfully")
    return token


async def get_refresh_token(
    creds: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> str:
    lg.debug(f"Extracted credentials scheme: {creds.scheme}")

    token = creds.credentials

    token_data = decode_access_token(token)
    if token_data is None:
        lg.debug("Token data invalid")
        raise InvalidToken()

    jti = token_data.get("jti")
    if jti and await token_in_blocklist(jti):
        lg.debug(f"Token JTI {jti} is in blocklist.")
        raise InvalidToken()

    lg.debug("Token is valid")
    if not token_data.get("refresh", False):
        lg.error("Access token used where refresh token expected!")
        raise RefreshTokenRequired()

    lg.debug("Refresh token validated successfully")
    return token
