import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Получаем параметры подключения из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/blindb")

# Создаем движок базы данных
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    """Создаёт сессию соединения с БД"""
    async with async_session() as session:
        yield session

async def init_db():
    """Инициализирует БД при запуске приложения"""
    from .models import Base
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # Для сброса БД (только для разработки)
        await conn.run_sync(Base.metadata.create_all)