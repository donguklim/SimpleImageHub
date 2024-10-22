from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    FastAPI,
    Response,
    status,
)
from sqlmodel import asc, desc, select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError

from image_hub.auth.auth_scheme import TokenAuthScheme
from image_hub.auth.dto import Token, UserAuthDto, UserDto
from image_hub.auth.errors import AuthTokenError
from image_hub.auth.services import (
    get_token,
    get_user_instance,
    get_user_id_and_is_admin_from_token,
    verify_password
)
from image_hub.database.models import ImageCategory, User
from image_hub.database.session import get_session
from image_hub.image.dto import CategoryUpdateDto, CategoryInfoDto, CategoryListDto


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


def get_admin_user_id(
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
async def signup(
        user_info:UserDto,
        response: Response,
        session: AsyncSession = Depends(get_session)
) -> dict:
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

    return get_token(user.id, is_admin=user.is_admin)


@app.get('/hello_user')
async def hello_user(user_auth: Annotated[UserAuthDto, Depends(get_user_auth)]) -> dict:
    """
    Hello message api for testing if a user is logged in.
    """
    return dict(message=f'Hello {user_auth.user_id}', is_admin=user_auth.is_admin)


@app.delete('/categories/{category_id}')
async def delete_category_by_id(
    category_id: int,
    admin_id: Annotated[int, Depends(get_admin_user_id)],
    response: Response,
    session: AsyncSession = Depends(get_session)
) -> dict:
    await session.exec(
        delete(ImageCategory).where(ImageCategory.id == category_id)
    )
    await session.commit()
    return dict(message=f'Category with id {category_id} is deleted')


@app.get('/categories/{category_id}')
async def get_category_by_id(
    category_id: int,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> CategoryInfoDto:
    result = await session.exec(
        select(ImageCategory).where(
            ImageCategory.id == category_id,
        )
    )
    category = result.first()
    if not category:
        raise HTTPException(status_code=404, detail=f'category {category_id} not found')

    return CategoryInfoDto(
        name=category.name,
        id=category.id
    )

@app.delete('/categories/')
async def delete_category_by_name(
    category: CategoryUpdateDto,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> dict:
    name = category.name.upper()
    await session.exec(
        delete(ImageCategory).where(ImageCategory.name == name)
    )
    await session.commit()
    return dict(message=f'Category {name} is deleted')


@app.post('/categories/')
async def create_category(
    category: CategoryUpdateDto,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    response: Response,
    session: AsyncSession = Depends(get_session)
) -> dict:
    name = category.name.upper()
    session.add(ImageCategory(name=name))
    try:
        await session.commit()
    except IntegrityError:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return dict(message=f'Category {name} already exists')

    return dict(message=f'Category {name} is created')


@app.get('/categories/')
async def list_category(
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session),
    is_ascending: bool = True,
    search_key: str | None = None,
    size: int = 100,
) -> CategoryListDto:
    if size > 1000:
        raise HTTPException(status_code=400, detail=f'size {size} exceeds 1000')

    if is_ascending:
        order = asc(ImageCategory.name)
    else:
        order = desc(ImageCategory.name)

    query = select(ImageCategory)

    if search_key and is_ascending:
        query = query.where(
            ImageCategory.name > search_key.upper()
        )
    elif search_key and not is_ascending:
        query = query.where(
            ImageCategory.name < search_key.upper()
        )

    result = await session.exec(
        query.order_by(order).limit(size)
    )

    categories = [
        CategoryInfoDto(
            name=category.name,
            id=category.id
        ) for category in result
    ]

    if len(categories) < size:
        next_search_key = None
    else:
        next_search_key = categories[-1].name

    return CategoryListDto(next_search_key=next_search_key, categories=categories)
