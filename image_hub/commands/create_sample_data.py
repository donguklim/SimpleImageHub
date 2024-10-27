import os
from random import randint, sample

from PIL import Image
from sqlmodel import Session, create_engine

from image_hub.auth.services import get_password_hash
from image_hub.image.image_file import (
    get_original_image_save_directory,
    get_thumbnail_save_directory,
    THUMBNAIL_FILE_NAME
)
from image_hub.database.models import User, ImageCategory, ImageCategoryMapping, ImageInfo
from image_hub.config import get_settings


def create_categories(session: Session) -> list[int]:
    categories = [
        ImageCategory(name=f'CATEGORY_{i}')
        for i in range(1, 51)
    ]

    session.add_all(categories)
    session.commit()

    return [category.id for category in categories]

def create_admin_users(session: Session) -> list[int]:
    users = [
        User(user_name=f'admin{i}', password=get_password_hash('asdf'), is_admin=True)
        for i in range(1, 11)
    ]

    session.add_all(users)
    session.commit()
    print('created admin users: [admin1, admin2, ... admin10]')
    print('all created admin user passwords is set to asdf')
    return [user.id for user in users]

def create_user(session: Session) -> list[int]:
    users = [
        User(user_name=f'user{i}', password=get_password_hash('asdf'), is_admin=False)
        for i in range(1, 11)
    ]

    session.add_all(users)
    session.commit()

    print('created users: [user1, user2, ... user10]')
    print('all created user passwords is set to asdf')
    return [user.id for user in users]

def create_images_for_user(
        user_id: int,
        is_admin: bool,
        category_ids:list[int],
        session: Session
) -> list[int]:
    num_images = randint(1, 12)

    images = []
    image_category_mappings = []
    image_file_names = []
    for i in range(num_images):
        file_name = f'image_{i}.jpg'
        images.append(
            ImageInfo(
                file_name=file_name,
                uploader_id=user_id if not is_admin else None,
                uploader_admin_id=user_id if is_admin else None,
                description=f'Image {i} of user {user_id}',
            )
        )
        image_file_names.append(file_name)

    session.add_all(images)
    session.commit()
    image_ids = [image.id for image in images]

    for image_id in image_ids:
        num_categories = randint(0, 5)
        image_category_ids = sample(category_ids, num_categories)

        for category_id in image_category_ids:
            image_category_mappings.append(
                ImageCategoryMapping(
                    category_id=category_id,
                    image_info_id=image_id
                )
            )

    session.add_all(image_category_mappings)
    session.commit()

    image_size = (256, 256)
    thumbnail_size = (128, 128)
    for image_id, file_name in zip(image_ids, image_file_names):
        save_directory = get_original_image_save_directory(image_id)
        os.makedirs(save_directory, exist_ok=True)
        file_path = os.path.join(save_directory, file_name)

        color = (randint(0, 255), randint(0, 255), randint(0, 255))
        image = Image.new('RGB', image_size, color)
        image.save(file_path)

        thumbnail_save_directory = get_thumbnail_save_directory(image_id)
        os.makedirs(thumbnail_save_directory, exist_ok=True)
        thumbnail_path = os.path.join(thumbnail_save_directory, THUMBNAIL_FILE_NAME)

        image.resize(thumbnail_size)
        image.save(thumbnail_path)


def create_sample_data():
    engine = create_engine(get_settings().database_sync_url, echo=True)

    with Session(engine) as session:
        num_categories = create_categories(session)
        admin_users = create_admin_users(session)
        users = create_user(session)

        for admin_user_id in admin_users:
            create_images_for_user(admin_user_id, is_admin=True, category_ids=num_categories, session=session)

        for user_id in users:
            create_images_for_user(user_id, is_admin=False, category_ids=num_categories, session=session)


if __name__ == '__main__':
    create_sample_data()
