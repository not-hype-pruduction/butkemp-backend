from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import User, Mascot, UserRating

# Вес для расчёта рейтинга
RARITY_WEIGHTS = {
    "легендарный": 100,
    "эпический": 40,
    "редкий": 15,
    "необычный": 5,
    "обычный": 1
}


async def get_or_create_user(session: AsyncSession, user_id: int, username: str = None,
                             first_name: str = None, last_name: str = None) -> User:
    """Получает или создаёт пользователя в БД"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()

    if not user:
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        await session.flush()

        # Создаем запись рейтинга для нового пользователя
        user_rating = UserRating(user_id=user_id)
        session.add(user_rating)
        await session.flush()

    return user


async def add_mascot(session: AsyncSession, user_id: int, mascot_info: Dict[str, Any]) -> Mascot:
    """Добавляет маскота в БД и обновляет рейтинг пользователя"""
    # Получаем пользователя
    user = await get_or_create_user(session, user_id)

    # Расчитываем индекс редкости для сортировки
    rarity_values = [
        RARITY_WEIGHTS[mascot_info["hat"]["rarity"]],
        RARITY_WEIGHTS[mascot_info["body"]["rarity"]],
        RARITY_WEIGHTS[mascot_info["stroke"]["rarity"]]
    ]
    rarity_index = sum(rarity_values)

    # Создаем запись о маскоте
    mascot = Mascot(
        user_id=user_id,
        hat_name=mascot_info["hat"]["name"],
        hat_rarity=mascot_info["hat"]["rarity"],
        hat_color=mascot_info["hat"]["color"],
        body_rarity=mascot_info["body"]["rarity"],
        body_color=mascot_info["body"]["color"],
        stroke_rarity=mascot_info["stroke"]["rarity"],
        stroke_color=mascot_info["stroke"]["color"],
        rarity_index=rarity_index,
        mascot_data=mascot_info
    )
    session.add(mascot)
    await session.flush()

    # Обновляем рейтинг пользователя
    await update_user_rating(session, user_id)

    return mascot


async def update_user_rating(session: AsyncSession, user_id: int) -> None:
    """Обновляет рейтинг пользователя на основе всех его маскотов"""
    # Получаем все маскоты пользователя
    mascots_query = await session.execute(select(Mascot).filter(Mascot.user_id == user_id))
    mascots = mascots_query.scalars().all()

    # Считаем количество маскотов каждой редкости
    rarity_counts = {
        "легендарный": 0,
        "эпический": 0,
        "редкий": 0,
        "необычный": 0,
        "обычный": 0
    }

    for mascot in mascots:
        rarity_counts[mascot.hat_rarity] += 1
        rarity_counts[mascot.body_rarity] += 1
        rarity_counts[mascot.stroke_rarity] += 1

    # Рассчитываем рейтинг
    rating_score = (
            rarity_counts["легендарный"] * RARITY_WEIGHTS["легендарный"] +
            rarity_counts["эпический"] * RARITY_WEIGHTS["эпический"] +
            rarity_counts["редкий"] * RARITY_WEIGHTS["редкий"] +
            rarity_counts["необычный"] * RARITY_WEIGHTS["необычный"] +
            rarity_counts["обычный"] * RARITY_WEIGHTS["обычный"]
    )

    # Обновляем рейтинг в БД
    await session.execute(
        update(UserRating)
        .where(UserRating.user_id == user_id)
        .values(
            total_mascots=len(mascots),
            legendary_count=rarity_counts["легендарный"],
            epic_count=rarity_counts["эпический"],
            rare_count=rarity_counts["редкий"],
            uncommon_count=rarity_counts["необычный"],
            common_count=rarity_counts["обычный"],
            rating_score=rating_score,
            last_updated=datetime.utcnow()
        )
    )
    await session.flush()


async def get_top_users(session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """Получает топ пользователей по рейтингу"""
    query = (
        select(User, UserRating)
        .join(UserRating, User.user_id == UserRating.user_id)
        .order_by(desc(UserRating.rating_score))
        .limit(limit)
    )

    result = await session.execute(query)
    top_users = []

    for user, rating in result:
        top_users.append({
            "user_id": user.user_id,
            "username": user.username,
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "total_mascots": rating.total_mascots,
            "legendary_count": rating.legendary_count,
            "epic_count": rating.epic_count,
            "rare_count": rating.rare_count,
            "uncommon_count": rating.uncommon_count,
            "common_count": rating.common_count,
            "rating_score": rating.rating_score
        })

    return top_users


async def get_user_rating(session: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    """Получает рейтинг конкретного пользователя"""
    query = (
        select(User, UserRating)
        .join(UserRating, User.user_id == UserRating.user_id)
        .where(User.user_id == user_id)
    )

    result = await session.execute(query)
    row = result.first()

    if row:
        user, rating = row
        return {
            "user_id": user.user_id,
            "username": user.username,
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "total_mascots": rating.total_mascots,
            "legendary_count": rating.legendary_count,
            "epic_count": rating.epic_count,
            "rare_count": rating.rare_count,
            "uncommon_count": rating.uncommon_count,
            "common_count": rating.common_count,
            "rating_score": rating.rating_score,
            "rating_position": await get_user_position(session, user_id)
        }

    return None


async def get_user_position(session: AsyncSession, user_id: int) -> int:
    """Определяет текущую позицию пользователя в общем рейтинге"""
    # Получаем рейтинг пользователя
    user_rating_query = await session.execute(
        select(UserRating.rating_score).where(UserRating.user_id == user_id)
    )
    user_rating = user_rating_query.scalar()

    if not user_rating:
        return 0

    # Определяем позицию среди всех пользователей
    position_query = await session.execute(
        select(func.count()).where(UserRating.rating_score > user_rating)
    )
    position = position_query.scalar() + 1

    return position


async def get_user_mascots(session: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """Получает все маскоты пользователя, отсортированные по редкости"""
    query = (
        select(Mascot)
        .filter(Mascot.user_id == user_id)
        .order_by(desc(Mascot.rarity_index), desc(Mascot.created_at))
    )

    result = await session.execute(query)
    mascots = result.scalars().all()

    return [
        {
            "id": mascot.id,
            "created_at": mascot.created_at,
            "hat_name": mascot.hat_name,
            "hat_rarity": mascot.hat_rarity,
            "body_rarity": mascot.body_rarity,
            "stroke_rarity": mascot.stroke_rarity,
            "rarity_index": mascot.rarity_index,
            "mascot_data": mascot.mascot_data
        }
        for mascot in mascots
    ]