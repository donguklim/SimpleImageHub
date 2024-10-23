
from fastapi import HTTPException, status

from sqlmodel import select, and_, or_, asc, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.operators import is_


from image_hub.auth.dto import UserAuthDto
from image_hub.database.models import ImageInfo



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


def get_admin_base_image_query(
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


def get_user_base_image_query(user_id: int, next_key: str | None = None):
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
