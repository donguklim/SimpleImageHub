from fastapi import UploadFile
from pydantic import BaseModel, conlist, Field

from image_hub.image_category.dto import CategoryInfoDto


class ImageUploadForm(BaseModel):
    image: UploadFile
    categories: conlist(int, max_length=5)
    description: str | None = Field(max_length=511)


class ImageUploadResponse(BaseModel):
    id: int
    file_name: str
    image_url: str
    thumbnail_url: str
    description: str
    categories: list[int]


class ImageCreationResultDto(BaseModel):
    id: int
    file_name: str
    image_url: str
    thumbnail_url: str
    description: str | None
    categories: list[int]


class ImageInfoDto(BaseModel):
    id: int
    file_name: str
    image_url: str
    thumbnail_url: str
    description: str | None
    uploader_id: int
    created_at: str


class ImageInfoListDto(BaseModel):
    images: list[ImageInfoDto]
    next_key: str | None
