from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import db_session

DbSession = Annotated[AsyncSession, Depends(db_session)]
