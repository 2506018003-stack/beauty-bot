from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models import User
from bot.services.loyalty import get_or_create_referral_code

router = Router()


@router.message(F.text == "⭐ Лояльность")
async def show_loyalty(message: Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == message.from_user.id))
        user = result.scalar_one()
        ref_code = await get_or_create_referral_code(session, user)
        await session.commit()

    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={ref_code}"

    await message.answer(
        f"⭐ <b>Программа лояльности</b>\n\n"
        f"💰 Ваш баланс: <b>{user.loyalty_points} баллов</b>\n"
        f"(1 балл = 1 ₽ скидки, начисляем 5% от каждого визита)\n\n"
        f"🎁 <b>Реферальная программа</b>\n"
        f"Пригласите друга — получите 200 баллов после его первого визита! Друг тоже получит 200 баллов.\n\n"
        f"🔗 Ваша ссылка:\n<code>{ref_link}</code>",
        disable_web_page_preview=True
    )
