from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DISCORD_TOKEN: str = "your_super_secret_bot_token"
    POSTGRES_USER: str = "voicemaster"
    POSTGRES_PASSWORD: str = "your_secure_password"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "voicemaster_db"
    DB_ECHO: bool = False
    DATABASE_URL: str = ""
    MAX_LOCKS: int = 10000
    VIEW_TIMEOUT: int = 180

    @model_validator(mode='before')
    def assemble_db_connection(cls, v):
        if 'DATABASE_URL' not in v:
            v['DATABASE_URL'] = f"postgresql+asyncpg://{v.get('POSTGRES_USER')}:{v.get('POSTGRES_PASSWORD')}@{v.get('POSTGRES_HOST')}:{v.get('POSTGRES_PORT')}/{v.get('POSTGRES_DB')}"
        return v


settings = Settings()
