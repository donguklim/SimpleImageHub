from pydantic import BaseModel, Field


class CategoryUpdateDto(BaseModel):
    name: str = Field(min_length=4, max_length=63)


class CategoryInfoDto(BaseModel):
    id: int
    name: str

class CategoryListDto(BaseModel):
    next_search_key: str | None
    categories: list[CategoryInfoDto]
