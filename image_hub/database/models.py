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
    image_id: int = Field(foreign_key='image.id', primary_key=True)
    category_id: int = Field(foreign_key='image_category.id', primary_key=True)


class ImageCategory(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=63)
    created_at: datetime = Field(
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
            default=time_now
        )
    )

    images: list['Image'] = Relationship(back_populates='categories', link_model=ImageCategoryMapping)


class Image(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    file_name: str = Field(index=True, max_length=255)
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
    description: str = Field(max_length=511)
    uploader_id: int = Field(foreign_key='user.id')

    categories: list['ImageCategory'] = Relationship(back_populates='images', link_model=ImageCategoryMapping)
