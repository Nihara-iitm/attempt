from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DUCKDB_PATH: str = "data/db.duckdb"

    class Config:
        env_file = ".env"


settings = Settings()
