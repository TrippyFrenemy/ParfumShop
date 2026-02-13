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
    REDIS_CACHE_DB: int = 2

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

    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 900  # 15 minutes

    # Auth token lifetimes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate limiting
    MAX_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_BLOCK_SECONDS: int = 600  # 10 minutes

    # OAuth
    OAUTH_STATE_TTL: int = 600  # 10 minutes

    # Upload limits
    MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # Logging configuration (LOG_* env variables)
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # json/text/colored
    LOG_ENVIRONMENT: str = "development"  # development/staging/production
    LOG_FILE_ENABLED: bool = True
    LOG_FILE_PATH: str = ""  # Auto-detect if empty
    LOG_FILE_MAX_BYTES: int = 10_485_760  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    LOG_CONSOLE_ENABLED: bool = True
    LOG_CONSOLE_LEVEL: str = "DEBUG"
    LOG_DB_ENABLED: bool = True  # Audit trail
    LOG_DB_LEVEL: str = "INFO"
    LOG_PII_MASKING_ENABLED: bool = True
    LOG_CORRELATION_ID_ENABLED: bool = True


settings = Settings()
