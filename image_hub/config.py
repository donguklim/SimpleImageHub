from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='hub_')

    database_url: str
    auth_secret_key: str
    max_num_categories_per_image: int = 5


@lru_cache
def get_settings(env_file_name: str = '.env'):
    return Settings(_env_file='.env', _env_file_encoding='utf-8')
