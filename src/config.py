from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    REDIS_PORT: str
    REDIS_HOST: str

    SECRET: str
    SECRET_MANAGER: str

    TG_BOT_TOKEN: str
    TG_STAFF_CHAT_ID: str
    TG_CHAT_ID: str

    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    ADMIN_NAME: str
    ADMIN_ROLE: str

    MANAGER_EMAIL: str
    MANAGER_PASSWORD: str
    MANAGER_NAME: str
    MANAGER_ROLE: str

    WAREHOUSE_EMAIL: str
    WAREHOUSE_PASSWORD: str
    WAREHOUSE_NAME: str
    WAREHOUSE_ROLE: str

    CSRF_TOKEN_EXPIRY: int

    CELERY_BACHUP_RATE: int 

    OAUTH_GOOGLE_CLIENT_ID: str
    OAUTH_GOOGLE_CLIENT_SECRET: str
    OAUTH_GOOGLE_REDIRECT_URI: str

    NP_API_KEY: str
    MIN_ORDER_AMOUNT: int

    DEBUG: bool = False

    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_ENDPOINT_URL: str
    S3_BUCKET_NAME: str
    S3_REGION: str
    S3_PUBLIC_URL: str

    URL: str = "http://localhost:8000"


settings = Settings()
