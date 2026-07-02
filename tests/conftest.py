import os

from app.core.config import get_settings

os.environ["REASONING_PROVIDER"] = "mock"
get_settings.cache_clear()
