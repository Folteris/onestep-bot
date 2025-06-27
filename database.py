import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String

# 📦 Получение URL базы данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# 🔌 Создание асинхронного движка и сессии
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# 🧱 Базовый класс моделей
Base = declarative_base()

# 📂 Функция получения сессии
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# 👤 Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String)
    age = Column(Integer)
    country = Column(String)
    city = Column(String)
    goal = Column(String)
    bio = Column(String)
    photo = Column(String)
