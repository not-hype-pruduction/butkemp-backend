from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    registration_date = Column(DateTime, default=datetime.utcnow)

    # Отношения
    mascots = relationship("Mascot", back_populates="user")
    rating = relationship("UserRating", uselist=False, back_populates="user")


class Mascot(Base):
    __tablename__ = "mascots"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    hat_name = Column(String, nullable=False)
    hat_rarity = Column(String, nullable=False)
    hat_color = Column(String, nullable=False)
    body_rarity = Column(String, nullable=False)
    body_color = Column(String, nullable=False)
    stroke_rarity = Column(String, nullable=False)
    stroke_color = Column(String, nullable=False)

    # Индекс редкости - числовое значение для сортировки
    rarity_index = Column(Float, nullable=False)
    # Полная информация о маскоте в JSON
    mascot_data = Column(JSON, nullable=False)

    # Отношения
    user = relationship("User", back_populates="mascots")


class UserRating(Base):
    __tablename__ = "user_ratings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), unique=True)
    total_mascots = Column(Integer, default=0)
    legendary_count = Column(Integer, default=0)
    epic_count = Column(Integer, default=0)
    rare_count = Column(Integer, default=0)
    uncommon_count = Column(Integer, default=0)
    common_count = Column(Integer, default=0)
    rating_score = Column(Float, default=0.0)

    # Новые поля для отслеживания самого редкого маскота
    max_rarity_score = Column(Float, default=0.0)  # Максимальный скор редкости отдельного маскота
    rarest_mascot_id = Column(Integer, ForeignKey("mascots.id"), nullable=True)  # ID самого редкого маскота

    last_updated = Column(DateTime, default=datetime.utcnow)

    # Отношения
    user = relationship("User", back_populates="rating")
    rarest_mascot = relationship("Mascot", foreign_keys=[rarest_mascot_id])