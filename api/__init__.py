"""
api – AIRINDEX Backend & REST API Package
==========================================
Member 3: Backend + Database Engineer  |  Project SIH26056
"""

from .main import app
from .database import init_sqlite_db

__all__ = ["app", "init_sqlite_db"]
