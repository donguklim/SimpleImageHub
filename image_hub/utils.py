import shutil
from datetime import datetime, timezone


def time_now():
    return datetime.now(timezone.utc)


def delete_directory(directory_path):
    shutil.rmtree(directory_path, ignore_errors=True)
