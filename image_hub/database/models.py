from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field, SQLModel, Relationship

from image_hub.utils import time_now


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_name: str = Field(index=True, max_length=31, unique=True)
    password: str
    is_admin: bool = Field(default=False)


class ImageCategoryMapping(SQLModel, table=True):
    __tablename__ = 'image_category_mapping'

    image_info_id: int = Field(foreign_key='image_info.id', primary_key=True, ondelete='CASCADE')
    category_id: int = Field(foreign_key='image_category.id', primary_key=True, ondelete='CASCADE')


class ImageCategory(SQLModel, table=True):
    __tablename__ = 'image_category'

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=63)
    created_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            default=time_now
        )
    )

    images: list['ImageInfo'] = Relationship(
        back_populates='categories',
        link_model=ImageCategoryMapping
    )


class ImageInfo(SQLModel, table=True):
    __tablename__ = 'image_info'
    id: int | None = Field(default=None, primary_key=True)
    file_name: str = Field(index=True, max_length=511)
    created_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            default=time_now
        )
    )
    updated_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            onupdate=time_now,
            nullable=False,
            default=time_now
        )
    )
    description: str | None = Field(max_length=511, nullable=True)
    uploader_id: int | None = Field(foreign_key='user.id', nullable=True)
    uploader_admin_id: int | None = Field(foreign_key='user.id', nullable=True)

    categories: list['ImageCategory'] = Relationship(
        back_populates='images',
        link_model=ImageCategoryMapping
    )
