from typing import AsyncGenerator
from app.core.database import SessionLocal

async def get_db() -> AsyncGenerator:
    async with SessionLocal() as session:
        yield session
