from image_hub.database.db_schema  import destroy_db_schema
from image_hub.database.models import User, Image, ImageCategory, ImageCategoryMapping   # noqa: F401


if __name__ == '__main__':
    destroy_db_schema()
