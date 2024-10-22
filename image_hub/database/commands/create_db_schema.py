from image_hub.database.db_schema  import create_db_schema
from image_hub.database.models import User, ImageInfo, ImageCategory, ImageCategoryMapping   # noqa: F401


if __name__ == '__main__':
    create_db_schema()
