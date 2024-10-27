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
from sqlmodel import asc, desc, select, delete, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.operators import is_, in_op
from sqlalchemy.orm import selectinload

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
from image_hub.image.dto import (
    ImageDetailDto,
    ImageCreationResultDto,
    ImageInfoDto,
    ImageInfoListDto,
    ImageUpdateDto
)
from image_hub.image_category.dto import CategoryUpdateDto, CategoryInfoDto, CategoryListDto
from image_hub.image.image_file import (
    upload_image_files,
    delete_image_files,
    get_original_image_file_path,
    get_original_image_file_url,
    get_thumbnail_image_file_path,
    get_thumbnail_image_file_url,
)
from image_hub.image.query import (
    check_image_access,
    get_admin_base_image_query,
    get_user_base_image_query
)


oauth2_scheme = TokenAuthScheme()

tags_metadata = [
    dict(name='auth'),
    dict(name='category'),
    dict(name='image_info'),
]

app = FastAPI(openapi_tags=tags_metadata)


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


@app.post('/signup', status_code=status.HTTP_201_CREATED, tags=['auth'])
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


@app.post('/login', tags=['auth'])
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


@app.delete('/categories/{category_id}', tags=['category'])
async def delete_category_by_id(
    category_id: int,
    admin_id: Annotated[int, Depends(get_admin_user_id)],
    session: AsyncSession = Depends(get_session)
) -> dict:
    await session.exec(
        delete(ImageCategory).where(ImageCategory.id == category_id)
    )
    await session.commit()
    return dict(message=f'Category with id {category_id} is deleted')


@app.get('/categories/{category_id}', tags=['category'])
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

@app.delete('/categories/', tags=['category'])
async def delete_category_by_name(
    category: CategoryUpdateDto,
    admin_id: Annotated[int, Depends(get_admin_user_id)],
    session: AsyncSession = Depends(get_session)
) -> dict:
    name = category.name.upper()
    await session.exec(
        delete(ImageCategory).where(ImageCategory.name == name)
    )
    await session.commit()
    return dict(message=f'Category {name} is deleted')


@app.post('/categories/', tags=['category'])
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


@app.get('/categories/', tags=['category'])
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


@app.get('/images/{image_id}/file/{file_name}', tags=['image_info'])
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


@app.get('/images/{image_id}/thumbnail/thumbnail.jpg', tags=['image_info'])
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


@app.delete('/images/{image_id}', tags=['image_info'])
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


@app.get('/images/{image_id}', tags=['image_info'])
async def get_image_info(
    image_id: int,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> ImageDetailDto:
    if user_auth.is_admin:
        query = select(ImageInfo).options(selectinload(ImageInfo.categories)).where(
            ImageInfo.id == image_id
        ).where(
            or_(
                ImageInfo.uploader_admin_id == user_auth.user_id,
                is_(ImageInfo.uploader_admin_id, None)
            )
        ).options(selectinload(ImageInfo.categories))
    else:
        query = select(ImageInfo).options(selectinload(ImageInfo.categories)).where(
            ImageInfo.id == image_id
        ).where(
            ImageInfo.uploader_id == user_auth.user_id
        )

    result = await session.exec(query)
    image_info = result.one_or_none()

    if not image_info:
        raise HTTPException(
            status_code=404,
            detail=f'You do not have access to image {image_id}, or the image does not exist.'
        )

    return ImageDetailDto(
        id=image_info.id,
        file_name=image_info.file_name,
        image_url=get_original_image_file_url(image_info.id, image_info.file_name),
        thumbnail_url=get_thumbnail_image_file_url(image_info.id),
        description=image_info.description,
        uploader_id=image_info.uploader_id or image_info.uploader_admin_id,
        created_at=image_info.created_at.isoformat(),
        categories=[
            CategoryInfoDto(
                name=category.name,
                id=category.id
            ) for category in image_info.categories
        ]
    )


@app.post('/images/{image_id}', tags=['image_info'])
async def update_image_info(
    image_id: int,
    update_dto: ImageUpdateDto,
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    if user_auth.is_admin:
        query = select(ImageInfo).options(selectinload(ImageInfo.categories)).where(
            ImageInfo.id == image_id
        ).where(
            or_(
                ImageInfo.uploader_admin_id == user_auth.user_id,
                is_(ImageInfo.uploader_admin_id, None)
            )
        ).options(selectinload(ImageInfo.categories))
    else:
        query = select(ImageInfo).options(selectinload(ImageInfo.categories)).where(
            ImageInfo.id == image_id
        ).where(
            ImageInfo.uploader_id == user_auth.user_id
        )

    result = await session.exec(query)
    image_info = result.one_or_none()
    if not image_info:
        raise HTTPException(
            status_code=404,
            detail=f'You do not have access to image {image_id}, or the image does not exist.'
        )

    if update_dto.description is not None:
        description = update_dto.description.strip()
        if description == '':
            image_info.description = None
        else:
            image_info.description = description


    deleting_ids = set(update_dto.deleting_categories or [])
    adding_ids = set(update_dto.adding_categories or [])

    interseting_ids = deleting_ids & adding_ids

    # ignore interseting ids
    deleting_ids = deleting_ids - interseting_ids
    adding_ids = adding_ids - interseting_ids

    category_ids = set([category.id for category in image_info.categories])
    if deleting_ids:
        deleting_ids = deleting_ids & category_ids
        category_ids = category_ids - deleting_ids

    num_updated_categories = len(category_ids | adding_ids)
    settings = get_settings()
    if num_updated_categories > settings.max_num_categories_per_image:
        raise HTTPException(
            status_code=400,
            detail=f'Image {image_id} will have {num_updated_categories} categories, '
                   f'exceeding the limit {settings.max_num_categories_per_image}'
        )

    await session.exec(
        delete(ImageCategoryMapping).where(
            ImageCategoryMapping.image_info_id == image_info.id,
            in_op(ImageCategoryMapping.category_id, deleting_ids)
        )
    )

    adding_ids = adding_ids - category_ids

    for category_id in adding_ids:
        session.add(
            ImageCategoryMapping(
                image_info_id=image_info.id,
                category_id=category_id,
            )
        )

    try:
        await session.commit()
    except IntegrityError as error:
        if 'is not present in table "image_category"' in str(error):
            raise HTTPException(
                status_code=400,
                detail=f'Some of the adding category ids({adding_ids}) do not exist!'
            )

    await session.commit()

    return dict(message=f'image {image_id} updated')


@app.get('/images/', tags=['image_info'])
async def list_images(
    user_auth: Annotated[UserAuthDto, Depends(get_user_auth)],
    session: AsyncSession = Depends(get_session),
    next_key: str | None = None,
    size: int = 100,
):
    if user_auth.is_admin:
        base_query = get_admin_base_image_query(user_auth.user_id, next_key)
    else:
        base_query = get_user_base_image_query(user_auth.user_id, next_key)

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


@app.post('/images/', tags=['image_info'])
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
