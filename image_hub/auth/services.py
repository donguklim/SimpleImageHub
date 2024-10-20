from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from image_hub.auth.dto import Token, UserDto
from image_hub.auth.errors import InvalidToken, InvalidDecodedToken, ExpiredToken
from image_hub.config import get_settings
from image_hub.database.models import User


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_byte_enc = plain_password.encode('utf-8')
    return bcrypt.checkpw(
        password=password_byte_enc,
        hashed_password=hashed_password.encode('utf-8')
    )


def create_access_token(
    user_id: int,
    is_admin: bool,
    secret_key: str,
    expire_seconds: int = 15 * 60
) -> str:
    to_encode = dict(
        sub=user_id,
        is_admin=is_admin,
        exp=datetime.now(timezone.utc) + timedelta(seconds=expire_seconds)
    )
    encoded_jwt = jwt.encode(
        to_encode,
        secret_key,
        algorithm=ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str, secret_key: str) -> dict:
    return jwt.decode(token, secret_key, algorithms=[ALGORITHM])


def get_user_instance(user_info: UserDto) -> User:
    user = User(
        password=get_password_hash(user_info.password),
        user_name=user_info.user_name,
        is_admin=user_info.is_admin,
    )

    return user


def get_token(user_id: int, is_admin: bool) -> Token:
    token = create_access_token(
        user_id=user_id,
        is_admin=is_admin,
        secret_key=get_settings().auth_secret_key
    )

    return Token(access_token=token, token_type='bearer')


def get_user_id_and_is_admin_from_token(token: str) -> tuple[int, bool]:
    try:
        decoded_token = decode_access_token(token, get_settings().auth_secret_key)
    except ExpiredSignatureError as error:
        raise ExpiredToken() from error
    except InvalidTokenError as error:
        raise InvalidToken(token) from error

    if 'sub' not in decoded_token:
        raise InvalidDecodedToken(
            f'key `sub` missing in the decoded token: {decoded_token}'
        )

    if not isinstance(decoded_token['sub'], int):
        raise InvalidDecodedToken(
            f'key `sub` in decoded token data does not contain user_id: {decoded_token}'
        )

    if 'is_admin' not in decoded_token:
        raise InvalidDecodedToken(
            f'key `is_admin` missing in the decoded token: {decoded_token}'
        )

    if not isinstance(decoded_token['is_admin'], int):
        raise InvalidDecodedToken(
            f'key `is_admin` in decoded token data does not contain user_id: {decoded_token}'
        )

    return decoded_token['sub'], decoded_token['is_admin']
