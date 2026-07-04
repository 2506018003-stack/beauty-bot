from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from bot.config import settings

_engine_kwargs = {"echo": False}
if "sqlite" not in str(settings.DATABASE_URL):
    _engine_kwargs.update(pool_size=20, max_overflow=0, pool_pre_ping=True, pool_recycle=3600)

engine = create_async_engine(str(settings.DATABASE_URL), **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
