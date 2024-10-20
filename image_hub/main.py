from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    FastAPI,
    Response,
    status,
)
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError

from image_hub.auth.bearer import TokenAuthScheme
from image_hub.auth.dto import Token, UserAuthDto, UserDto
from image_hub.auth.errors import AuthTokenError
from image_hub.auth.services import (
    get_token,
    get_user_instance,
    get_user_id_and_is_admin_from_token,
    verify_password
)
from image_hub.database.models import User
from image_hub.database.session import get_session


oauth2_scheme = TokenAuthScheme()
app = FastAPI()


def get_user_auth(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UserAuthDto:
    try:
        user_id, is_admin =  get_user_id_and_is_admin_from_token(token)
    except AuthTokenError as error:
        raise HTTPException(400, detail=str(error))

    return UserAuthDto(user_id=user_id, is_admin=is_admin)


def get_admin_user(
        token: Annotated[str, Depends(oauth2_scheme)],
) -> int:
    try:
        user_id, is_admin = get_user_id_and_is_admin_from_token(token)
    except AuthTokenError as error:
        raise HTTPException(400, detail=str(error))

    if not is_admin:
        raise HTTPException(404, detail='Only admins are allowed')

    return user_id


@app.post('/signup', status_code=status.HTTP_201_CREATED)
async def signup(user_info:UserDto, response: Response, session: AsyncSession = Depends(get_session)) -> dict:
    user = get_user_instance(user_info)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return dict(message=f'user {user_info.user_name} already exists')

    return dict(message=f'user {user_info.user_name} is created')


@app.post('/login')
async def login(
    user_info:UserDto,
    session: AsyncSession = Depends(get_session)
) -> Token:
    result = await session.exec(
        select(User).where(User.user_name == user_info.user_name)
    )
    user = result.first()
    if not user:
        raise HTTPException(status_code=400, detail='user does not exist')

    if not verify_password(user_info.password, user.password):
        raise HTTPException(status_code=400, detail='wrong password')

    return get_token(user.id)


@app.get('/hello_user')
async def hello_user(user_auth: Annotated[UserAuthDto, Depends(get_user_auth)]):
    """
    Hello message api for testing if a user is logged in.
    """
    return dict(message=f'Hello {user_auth.user_id}', is_admin=user_auth.is_admin)
