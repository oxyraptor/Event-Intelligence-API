from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite:///./assignment.db", alias="DATABASE_URL")
    chroma_persist_directory: str = Field(default="./chroma_data", alias="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="events", alias="CHROMA_COLLECTION_NAME")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_NAME",
    )
    search_min_score: float = Field(default=0.35, alias="SEARCH_MIN_SCORE")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
