"""Acceso a MongoDB para las rutas. Las pruebas sustituyen `get_db` con app.dependency_overrides."""
from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from backend.app.config import get_settings


@lru_cache
def _client() -> MongoClient:
    return MongoClient(get_settings().mongodb_uri, serverSelectionTimeoutMS=2500, appname="demand-forecasting-api")


def get_db() -> Database:
    return _client()[get_settings().mongodb_database]
