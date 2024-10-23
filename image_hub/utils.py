import os
import shutil
from datetime import datetime, timezone

import aiofiles
from fastapi import UploadFile


def time_now():
    return datetime.now(timezone.utc)


async def upload_file(file: UploadFile, save_path):
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, file.filename)
    async with aiofiles.open(file_path, mode='wb') as save_file:
        await  save_file.write(await file.read())


def delete_directory(directory_path):
    shutil.rmtree(directory_path, ignore_errors=True)
