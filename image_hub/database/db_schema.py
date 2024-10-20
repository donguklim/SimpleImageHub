from sqlmodel import SQLModel, create_engine
from image_hub.config import get_settings


def create_db_schema():
    engine = create_engine(get_settings().database_sync_url, echo=True)
    SQLModel.metadata.create_all(engine)


def destroy_db_schema():
    engine = create_engine(get_settings().database_sync_url, echo=True)
    SQLModel.metadata.drop_all(engine)
