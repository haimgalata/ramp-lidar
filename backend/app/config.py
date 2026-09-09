"""Application configuration, loaded from environment variables (.env)."""
import os
from functools import lru_cache

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can also be set directly.
    pass


class Settings:
    viz_max_points: int = int(os.getenv("VIZ_MAX_POINTS", "150000"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "300"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    return Settings()
