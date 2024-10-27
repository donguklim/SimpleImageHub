import argparse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine

from image_hub.auth.services import get_password_hash
from image_hub.database.models import User
from image_hub.config import get_settings


def create_admin(user_name: str, password: str):

    if len(user_name) > 31:
        print('user name must be less than 31 characters. The admin user is not created')

    engine = create_engine(get_settings().database_sync_url, echo=True)

    if not password:
        print('Password is empty. The admin user is not created')


    with Session(engine) as session:
        session.add(
            User(
                user_name=user_name,
                password=get_password_hash(password),
                is_admin=True
            )
        )
        try:
            session.commit()
        except IntegrityError:
            print(f'user {user_name} already exists. The admin user is not created')
            return

        print(f'admin user named {user_name} is created')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', type=str, required=True, help='Your name')
    parser.add_argument('--password', type=str, required=True, help='Your city')

    args = parser.parse_args()
    create_admin(args.name, args.password)


if __name__ == '__main__':
    main()