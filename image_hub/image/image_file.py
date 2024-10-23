import os
from io import BytesIO

import aiofiles
from fastapi import UploadFile
from PIL import Image

from image_hub.config import get_settings
from image_hub.utils import delete_directory


THUMBNAIL_FILE_NAME = 'thumbnail.jpg'


def _get_original_image_save_directory(image_id: int):
    return os.path.join(
        get_settings().image_path,
        str(image_id),
    )

def _get_thumbnail_save_directory(image_id: int):
    return os.path.join(
        _get_original_image_save_directory(image_id),
        'thumbnail'
    )


async def upload_file(file: UploadFile, save_path: str) -> str:
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, file.filename)
    async with aiofiles.open(file_path, mode='wb') as save_file:
        await  save_file.write(await file.read())

    return file_path


async def save_image_async(
    image: Image.Image,
    save_path: str,
    file_name: str,
    image_format: str = 'JPEG'
):
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, file_name)

    img_bytes = BytesIO()
    image.save(img_bytes, format=image_format)
    img_bytes.seek(0)

    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(img_bytes.getvalue())


def delete_image_files(image_id: int):
    image_file_directory = _get_original_image_save_directory(image_id)
    delete_directory(image_file_directory)


async def upload_image_files(image_id:int, image_file: UploadFile):
    file_path = await upload_file(
        image_file,
        _get_original_image_save_directory(image_id)
    )

    thumbnail_directory = _get_thumbnail_save_directory(image_id)

    with Image.open(file_path) as img:
        settings = get_settings()
        img = img.convert('RGB')
        img.thumbnail((settings.thumbnail_size, settings.thumbnail_size))
        await save_image_async(
            img,
            thumbnail_directory,
            THUMBNAIL_FILE_NAME,
        )


def get_original_image_file_url(image_id: int, image_file_name: str) -> str:
    return f'/image/{image_id}/file/{image_file_name}'


def get_thumbnail_image_file_url(image_id: int) -> str:
    return f'/image/{image_id}/thumbnail/{THUMBNAIL_FILE_NAME}'


def get_original_image_file_path(image_id: int, image_file_name: str) -> str:
    return os.path.join(
        _get_original_image_save_directory(image_id),
        image_file_name
    )


def get_thumbnail_image_file_path(image_id: int) -> str:
    return os.path.join(
        _get_thumbnail_save_directory(image_id),
        THUMBNAIL_FILE_NAME
    )