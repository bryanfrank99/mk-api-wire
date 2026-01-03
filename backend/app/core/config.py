import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "WireGuard Account Manager"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_dev_key_change_me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./wireguard_manager.db")
    
settings = Settings()
