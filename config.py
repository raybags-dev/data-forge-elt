from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "DataForge"

    DEBUG: bool = True

    LOG_LEVEL: str = "INFO"

    DATA_LAKE: str = "./datalake"

    DUCKDB_PATH: str = "./warehouse/data.duckdb"

    class Config:
        env_file = ".env"


settings = Settings()