import secrets
import string
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import User, LoyaltyLedger, ReferralBonus

POINTS_PER_RUB = 0.05          # 5% суммы визита возвращается баллами
REFERRAL_BONUS_POINTS = 200    # бонус обеим сторонам при первом визите реферала


def generate_referral_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))


async def get_or_create_referral_code(session: AsyncSession, user: User) -> str:
    if user.referral_code:
        return user.referral_code
    code = generate_referral_code()
    user.referral_code = code
    session.add(user)
    await session.flush()
    return code


async def add_points(session: AsyncSession, user_id: int, delta: int, reason: str):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.loyalty_points = max(0, user.loyalty_points + delta)
    session.add(user)
    session.add(LoyaltyLedger(user_id=user_id, delta=delta, reason=reason))
    await session.flush()
    return user.loyalty_points


async def award_first_visit_referral_bonus(session: AsyncSession, user: User):
    """Called once, on a referred user's first completed booking."""
    if not user.referred_by:
        return
    result = await session.execute(
        select(ReferralBonus).where(ReferralBonus.referred_id == user.id)
    )
    bonus = result.scalar_one_or_none()
    if bonus and bonus.awarded:
        return
    if not bonus:
        bonus = ReferralBonus(referrer_id=user.referred_by, referred_id=user.id, bonus_points=REFERRAL_BONUS_POINTS)
        session.add(bonus)
    bonus.awarded = True
    await add_points(session, user.referred_by, REFERRAL_BONUS_POINTS, "referral_bonus")
    await add_points(session, user.id, REFERRAL_BONUS_POINTS, "referral_welcome")
    await session.flush()


def points_earned_for_amount(amount) -> int:
    return int(float(amount) * POINTS_PER_RUB)
