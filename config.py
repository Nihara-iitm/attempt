from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: str
    DUCKDB_PATH: str = "data/db.duckdb"

    class Config:
        env_file = ".env"


settings = Settings()
