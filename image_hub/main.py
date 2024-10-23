import os
from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    FastAPI,
    Form,
    Response,
    status,
    UploadFile
)
from fastapi.responses import FileResponse
from markdown_it.rules_inline import image
from sqlmodel import asc, desc, select, delete, or_, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.operators import is_

from image_hub.auth.auth_scheme import TokenAuthScheme
from image_hub.auth.dto import Token, UserAuthDto, UserDto
from image_hub.auth.errors import AuthTokenError
from image_hub.auth.services import (
    get_token,
    get_user_instance,
    get_user_id_and_is_admin_from_token,
    verify_password
)
from image_hub.config import get_settings
from image_hub.database.models import ImageCategory, ImageCategoryMapping, ImageInfo, User
from image_hub.database.session import get_session
from image_hub.image.dto import ImageCreationResultDto, ImageInfoDto, ImageInfoListDto
from image_hub.image_category.dto import CategoryUpdateDto, CategoryInfoDto, CategoryListDto
from image_hub.image.image_file import (
    upload_image_files,
    delete_image_files,
    get_original_image_file_path,
    get_original_image_file_url,
    get_thumbnail_image_file_path,
    get_thumbnail_image_file_url,
)


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


async def check_image_access(
    image_id: int,
    user_auth: UserAuthDto,
    session: AsyncSession
):

    if user_auth.is_admin:
        query = select(ImageInfo.id).where(
            ImageInfo.id == image_id
        ).where(
            or_(
                ImageInfo.uploader_admin_id == user_auth.user_id,
                is_(ImageInfo.uploader_admin_id, None)
            )
        )
    else:
        query = select(ImageInfo.id).where(
            ImageInfo.id == image_id
        ).where(
            ImageInfo.uploader_id == user_auth.user_id
        )

    result = await session.exec(query)
    returned_image_id = result.one_or_none()

    if not returned_image_id:
        raise HTTPException(
            status_code=404,
            detail=f'You do not have access to image {image_id}, or the image does not exist.'
        )



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


@app.get('/images/{image_id}/{file_name}')
async def get_image_file(
    image_id: int,
    file_name: str,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    await check_image_access(image_id, user_auth, session)

    file_path = get_original_image_file_path(image_id, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type='image/png')


@app.get('/images/{image_id}/thumbnail/thumbnail.jpg')
async def get_thumbnail_image_file(
    image_id: int,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> FileResponse:
    await check_image_access(image_id, user_auth, session)

    file_path = get_thumbnail_image_file_path(image_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type='image/png')


@app.delete('/images/{image_id}')
async def delete_image(
    image_id: int,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    await check_image_access(image_id, user_auth, session)

    delete_image_files(image_id)
    await session.exec(
        delete(ImageInfo).where(ImageInfo.id == image_id)
    )
    await session.commit()
    return dict(message=f'Image id {image_id} is deleted')


def _get_admin_base_image_query(
    admin_id: int,
    next_key: str | None = None,
):
    if next_key:
        try:
            is_fetch_owning_image, image_id_str = next_key.split('-')
            image_id = int(image_id_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'next_key={next_key} not valid'
            )

        if is_fetch_owning_image:
            query = select(ImageInfo).where(
                or_(
                    and_(
                        ImageInfo.uploader_admin_id == admin_id,
                        ImageInfo.id < image_id
                    ),
                    is_(ImageInfo.uploader_admin_id, None)
                )
            )
        else:
            query = select(ImageInfo).where(
                is_(ImageInfo.uploader_admin_id, None),
                ImageInfo.id < image_id

            )
    else:
        query = select(ImageInfo).where(
            or_(
                ImageInfo.uploader_admin_id == admin_id,
                is_(ImageInfo.uploader_admin_id, None)
            )
        )

    return query.order_by(
        asc(ImageInfo.uploader_admin_id),
        desc(ImageInfo.id)
    )


def _get_user_base_image_query(user_id: int, next_key: str | None = None):
    if next_key:
        try:
            image_id = int(next_key)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'next_key={next_key} not valid'
            )

        query = select(ImageInfo).where(
            ImageInfo.uploader_id == user_id,
            ImageInfo.id < image_id
        )
    else:
        query = select(ImageInfo).where(
            ImageInfo.uploader_id == user_id
        )

    return query.order_by(
        desc(ImageInfo.id)
    )

@app.get('/images/')
async def list_images(
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session),
    next_key: str | None = None,
    size: int = 100,
):
    if user_auth.is_admin:
        base_query = _get_admin_base_image_query(user_auth.user_id, next_key)
    else:
        base_query = _get_user_base_image_query(user_auth.user_id, next_key)

    result = await session.exec(
        base_query.limit(size)
    )

    images = [
        ImageInfoDto(
            id=image_info.id,
            file_name=image_info.file_name,
            image_url=get_original_image_file_url(image_info.id, image_info.file_name),
            thumbnail_url=get_thumbnail_image_file_url(image_info.id),
            description=image_info.description,
            uploader_id=image_info.uploader_id or image_info.uploader_admin_id,
            created_at=image_info.created_at.isoformat()
        )
        for image_info in result
    ]

    if len(images) < size:
        next_key = None
    elif user_auth.is_admin:
        if images[-1].uploader_id == user_auth.user_id:
            next_key = f'a-{images[-1].id}'
        else:
            next_key = f'-{images[-1].id}'

    else:
        next_key = str(images[-1].id)

    return ImageInfoListDto(
        images=images,
        next_key=next_key
    )


@app.post('/images/')
async def upload_image(
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    image: UploadFile,
    categories: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form(max_length=511)] = None,
    session: AsyncSession = Depends(get_session)
) -> ImageCreationResultDto:

    try:
        category_ids = list(
            set([int(item) for item in categories.split(',')])
        ) if categories else []
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail=f'categories must be either null or '
                   f'a comma separated integer strings, but the received input is "{categories}"'
        )

    if len(category_ids) > 5:
        raise HTTPException(
            status_code=500,
            detail=f'number of categories must not exceed 5, '
                   f'but {len(category_ids)} categories are received: {category_ids} '
        )

    settings = get_settings()
    if image.size > settings.image_file_size_limit_mb * 1024 * 1024:
        raise HTTPException(
            status_code=500,
            detail=f'Image exceeds size limit of {settings.image_file_size_limit_mb}MB'
        )

    if user_auth.is_admin:
        uploader_id = None
        uploader_admin_id = user_auth.user_id
    else:
        uploader_id = user_auth.user_id
        uploader_admin_id = None

    image_info = ImageInfo(
        file_name=image.filename,
        description=description,
        uploader_id=uploader_id,
        uploader_admin_id=uploader_admin_id
    )
    session.add(image_info)

    await session.flush()

    image_id = image_info.id
    for category_id in category_ids:
        session.add(
            ImageCategoryMapping(
                category_id=category_id,
                image_info_id=image_info.id
            )
        )

    try:
        await upload_image_files(image_id, image)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

    try:
        await session.commit()
    except IntegrityError as error:
        delete_image_files(image_id)
        if 'is not present in table "image_category"' in str(error):
            raise HTTPException(
                status_code=400,
                detail=f'Some of the input category ids({category_ids}) do not exist!'
            )

    return ImageCreationResultDto(
        id=image_id,
        file_name=image.filename,
        description=description,
        image_url=get_original_image_file_url(image_id, image.filename),
        thumbnail_url=get_thumbnail_image_file_url(image_id),
        categories=category_ids,
    )
