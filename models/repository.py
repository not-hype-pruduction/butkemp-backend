from sqlalchemy import select, func, desc, update, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import User, Mascot, UserRating
from .database import async_session

# Weight for calculating ratings
RARITY_WEIGHTS = {
    "легендарный": 100,
    "эпический": 40,
    "редкий": 15,
    "необычный": 5,
    "обычный": 1
}


async def add_mascot(session: AsyncSession, user_id: int, mascot_data: Dict[str, Any]) -> Mascot:
    """Adds a new mascot to user's collection and updates their rating"""

    # Check if user exists, create if not
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalars().first()

    if not user:
        # Create new user
        user = User(user_id=user_id)
        session.add(user)
        await session.flush()

    # Create mascot
    mascot = Mascot(
        user_id=user_id,
        hat_name=mascot_data.get("hat", {}).get("name", ""),
        hat_rarity=mascot_data.get("hat", {}).get("rarity", "обычный"),
        hat_color=mascot_data.get("hat", {}).get("color", "#FFFFFF"),
        body_rarity=mascot_data.get("body", {}).get("rarity", "обычный"),
        body_color=mascot_data.get("body", {}).get("color", "#FFFFFF"),
        stroke_rarity=mascot_data.get("stroke", {}).get("rarity", "обычный"),
        stroke_color=mascot_data.get("stroke", {}).get("color", "#FFFFFF"),
        rarity_index=mascot_data.get("rarity_index", 0.0),
        mascot_data=mascot_data
    )
    session.add(mascot)
    await session.flush()  # Чтобы получить ID маскота

    # Рассчитываем общий score редкости для этого маскота
    rarities = [
        mascot_data.get("hat", {}).get("rarity", "обычный"),
        mascot_data.get("body", {}).get("rarity", "обычный"),
        mascot_data.get("stroke", {}).get("rarity", "обычный")
    ]

    current_mascot_score = sum(RARITY_WEIGHTS.get(rarity, 0) for rarity in rarities)

    # Update user's rating
    rating_result = await session.execute(select(UserRating).where(UserRating.user_id == user_id))
    rating = rating_result.scalars().first()

    if not rating:
        # Create new rating for user
        rating = UserRating(
            user_id=user_id,
            total_mascots=0,
            legendary_count=0,
            epic_count=0,
            rare_count=0,
            uncommon_count=0,
            common_count=0,
            rating_score=0.0,
            max_rarity_score=0.0
        )
        session.add(rating)

    # Update mascot counts
    rating.total_mascots += 1

    # Count mascot rarities and update counts
    for rarity in rarities:
        if rarity == "легендарный":
            rating.legendary_count += 1
        elif rarity == "эпический":
            rating.epic_count += 1
        elif rarity == "редкий":
            rating.rare_count += 1
        elif rarity == "необычный":
            rating.uncommon_count += 1
        elif rarity == "обычный":
            rating.common_count += 1

    # Обновляем максимальный скор редкости, только если текущий маскот более редкий
    if current_mascot_score > rating.max_rarity_score:
        rating.max_rarity_score = current_mascot_score
        rating.rarest_mascot_id = mascot.id

        # Важно: рейтинг теперь равен максимальному скору редкости
        rating.rating_score = current_mascot_score

    rating.last_updated = datetime.utcnow()

    await session.commit()
    return mascot

async def get_user_mascots(session: AsyncSession, user_id: int) -> List[Mascot]:
    """Gets all mascots for a user"""
    result = await session.execute(select(Mascot).where(Mascot.user_id == user_id))
    return result.scalars().all()


async def get_user_rating(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    """Gets rating info for a user"""
    # Get user information
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalars().first()

    # Get rating information
    result = await session.execute(
        select(UserRating).where(UserRating.user_id == user_id)
    )
    rating = result.scalars().first()

    # Get position in ranking
    position_result = await get_user_position(session, user_id)

    if not rating:
        return None

    # Формирование полного имени с проверкой значений
    full_name = ""
    if user and user.first_name:
        full_name += user.first_name
    if user and user.last_name:
        full_name += f" {user.last_name}" if full_name else user.last_name

    # Если полное имя пустое, используем username или ID
    if not full_name and user and user.username:
        full_name = user.username
    elif not full_name:
        full_name = f"Игрок {user_id}"

    return {
        "user_id": user_id,
        "username": user.username if user else None,
        "full_name": full_name,
        "total_mascots": rating.total_mascots,
        "legendary_count": rating.legendary_count,
        "epic_count": rating.epic_count,
        "rare_count": rating.rare_count,
        "uncommon_count": rating.uncommon_count,
        "common_count": rating.common_count,
        "rating_score": rating.rating_score,
        "rating_position": position_result
    }
async def get_top_users(session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
    """Gets top users by rating score"""
    result = await session.execute(
        select(
            UserRating,
            User.username,
            User.first_name,
            User.last_name
        )
        .join(User, UserRating.user_id == User.user_id)
        .order_by(desc(UserRating.rating_score))
        .limit(limit)
    )

    top_users = []
    for row in result:
        rating = row.UserRating
        username = row.username
        first_name = row.first_name
        last_name = row.last_name

        # Формирование полного имени с проверкой значений
        full_name = ""
        if first_name:
            full_name += first_name
        if last_name:
            full_name += f" {last_name}" if full_name else last_name

        # Если полное имя пустое, используем username или ID
        if not full_name and username:
            full_name = username
        elif not full_name:
            full_name = f"Игрок {rating.user_id}"

        top_users.append({
            "user_id": rating.user_id,
            "username": username,
            "full_name": full_name,
            "total_mascots": rating.total_mascots,
            "legendary_count": rating.legendary_count,
            "epic_count": rating.epic_count,
            "rare_count": rating.rare_count,
            "uncommon_count": rating.uncommon_count,
            "common_count": rating.common_count,
            "rating_score": rating.rating_score
        })

    return top_users
async def get_user_position(session: AsyncSession, user_id: int) -> int:
    """Gets user's position in the overall rating"""
    # Get the user's rating
    user_rating_result = await session.execute(
        select(UserRating.rating_score).where(UserRating.user_id == user_id)
    )
    user_rating = user_rating_result.scalar_one_or_none()

    if not user_rating:
        return 0

    # Count users with higher rating
    higher_ratings = await session.execute(
        select(func.count()).where(UserRating.rating_score > user_rating)
    )

    # Position is count of users with higher rating + 1
    return higher_ratings.scalar() + 1