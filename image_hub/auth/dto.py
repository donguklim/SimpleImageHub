from pydantic import BaseModel, Field


class UserDto(BaseModel):
    user_name: str = Field(min_length=4, max_length=31)
    password: str = Field(min_length=4, max_length=63)
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class UserAuthDto(BaseModel):
    user_id: int
    is_admin: bool
