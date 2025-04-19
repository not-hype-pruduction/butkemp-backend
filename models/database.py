import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/blindb")

# Create the database engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session factory
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncSession:
    """Custom implementation to create and yield a database session."""
    async with async_session() as session:
        yield session

async def get_session_ctx() -> AsyncSession:
    """Returns a session that can be used with async with."""
    return async_session()

async def init_db():
    """Custom implementation to initialize the database."""
    from .models import Base  # Import models dynamically to avoid circular imports
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)