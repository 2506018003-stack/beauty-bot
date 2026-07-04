from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject, Command
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from api.database import AsyncSessionLocal
from api.models import User
from bot.config import settings
from bot.keyboards.reply import get_main_menu
from bot.services.loyalty import get_or_create_referral_code

router = Router()


async def _upsert_user(message: Message, ref_code: str | None = None):
    async with AsyncSessionLocal() as session:
        stmt = insert(User).values(
            id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        ).on_conflict_do_nothing(index_elements=['id'])
        await session.execute(stmt)

        result = await session.execute(select(User).where(User.id == message.from_user.id))
        user = result.scalar_one()

        if ref_code and not user.referred_by:
            referrer = await session.execute(select(User).where(User.referral_code == ref_code))
            referrer_user = referrer.scalar_one_or_none()
            if referrer_user and referrer_user.id != user.id:
                user.referred_by = referrer_user.id
                session.add(user)

        await get_or_create_referral_code(session, user)
        await session.commit()


@router.message(CommandStart(deep_link=True))
async def cmd_start_referral(message: Message, command: CommandObject):
    await _upsert_user(message, ref_code=command.args)
    await _send_welcome(message)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await _upsert_user(message)
    await _send_welcome(message)


async def _send_welcome(message: Message):
    is_admin = message.from_user.id in settings.ADMIN_IDS
    await message.answer(
        f"👋 Добро пожаловать в <b>{settings.SALON_NAME}</b>!\n\n"
        "Выбирайте услугу, мастера и удобное время — запись займёт минуту.",
        reply_markup=get_main_menu(is_admin=is_admin)
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        f"💅 <b>{settings.SALON_NAME} — как пользоваться</b>\n\n"
        "💅 <b>Услуги</b> — каталог с ценами и длительностью\n"
        "📅 <b>Записаться</b> — выбрать услугу, мастера, дату и время\n"
        "🗓 <b>Мои записи</b> — статус и история визитов\n"
        "⭐ <b>Лояльность</b> — баллы за визиты + реферальная программа\n"
        "✍️ <b>Отзывы</b> — оставить оценку мастеру\n\n"
        f"Часы работы: {settings.OPEN_HOURS}\n"
        f"Телефон: {settings.SALON_PHONE}\n\n"
        "Вопросы: @tgbothelp_infinityfree"
    )


@router.message(F.text == "📞 Поддержка")
async def support_handler(message: Message):
    await message.answer(
        f"📞 <b>Служба поддержки</b>\n\n"
        f"Телефон: {settings.SALON_PHONE}\n"
        f"Часы работы: {settings.OPEN_HOURS}\n\n"
        "По техническим вопросам: @tgbothelp_infinityfree"
    )


@router.message(Command("admin_help"))
async def admin_help_handler(message: Message):
    if message.from_user.id not in settings.ADMIN_IDS:
        return
    await message.answer(
        "🔧 <b>Админ-команды</b>\n\n"
        "<code>/stats</code> — статистика\n"
        "<code>/broadcast</code> — рассылка всем клиентам\n\n"
        "<b>CRM (kanban записей, дашборд):</b>\n"
        f"{settings.CRM_URL}\n\n"
        "Новые записи приходят уведомлением с кнопками Подтвердить/Отклонить прямо в чат.",
        disable_web_page_preview=True
    )
