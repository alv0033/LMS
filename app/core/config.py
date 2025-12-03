from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    LOG_LEVEL: str = "INFO"
    SLOW_REQUEST_THRESHOLD_MS: int = 1000  # 1 segundo

    class Config:
        env_file = ".env"


settings = Settings()
