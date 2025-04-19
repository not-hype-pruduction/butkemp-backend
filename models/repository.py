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

    # Update user's rating
    rating_result = await session.execute(select(UserRating).where(UserRating.user_id == user_id))
    rating = rating_result.scalars().first()

    if not rating:
        # Create new rating for user with explicit default values
        rating = UserRating(
            user_id=user_id,
            total_mascots=0,  # Explicitly set defaults
            legendary_count=0,
            epic_count=0,
            rare_count=0,
            uncommon_count=0,
            common_count=0,
            rating_score=0.0
        )
        session.add(rating)

    # Update mascot counts
    rating.total_mascots += 1

    # Count mascot rarities and update counts
    rarities = [
        mascot_data.get("hat", {}).get("rarity", ""),
        mascot_data.get("body", {}).get("rarity", ""),
        mascot_data.get("stroke", {}).get("rarity", "")
    ]

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

    # Calculate rating score
    rating.rating_score = (
        rating.legendary_count * RARITY_WEIGHTS["легендарный"] +
        rating.epic_count * RARITY_WEIGHTS["эпический"] +
        rating.rare_count * RARITY_WEIGHTS["редкий"] +
        rating.uncommon_count * RARITY_WEIGHTS["необычный"] +
        rating.common_count * RARITY_WEIGHTS["обычный"]
    )

    rating.last_updated = datetime.utcnow()

    # Commit changes
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

    return {
        "user_id": user_id,
        "username": user.username if user else None,
        "full_name": f"{user.first_name} {user.last_name}".strip() if user else None,
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
    """Gets top users by rating"""
    result = await session.execute(
        select(UserRating, User)
        .join(User, UserRating.user_id == User.user_id)
        .order_by(desc(UserRating.rating_score))
        .limit(limit)
    )

    top_users = []
    for rating, user in result:
        top_users.append({
            "user_id": user.user_id,
            "username": user.username,
            "full_name": f"{user.first_name} {user.last_name}".strip(),
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