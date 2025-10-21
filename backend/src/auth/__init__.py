# Ensure SQLAlchemy models are registered with metadata
from . import models  # noqa: F401
from .router import router

__all__ = ["router"]
