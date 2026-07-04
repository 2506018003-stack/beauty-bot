import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from api.database import AsyncSessionLocal, engine, Base
from api.models import ServiceCategory, Service, Master, Review, User
from bot.config import settings


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        hair = ServiceCategory(name="Волосы", sort_order=1)
        nails = ServiceCategory(name="Ногти", sort_order=2)
        face = ServiceCategory(name="Лицо", sort_order=3)
        brows = ServiceCategory(name="Брови и ресницы", sort_order=4)
        session.add_all([hair, nails, face, brows])
        await session.flush()

        services = [
            Service(name="Женская стрижка", description="Стрижка любой сложности + укладка", price=1800, duration_minutes=60, category_id=hair.id),
            Service(name="Мужская стрижка", description="Классическая или модельная стрижка", price=1200, duration_minutes=40, category_id=hair.id),
            Service(name="Окрашивание в один тон", description="Однотонное окрашивание, краска включена", price=3500, duration_minutes=120, category_id=hair.id),
            Service(name="Мелирование / балаяж", description="Сложное окрашивание с эффектом выгоревших прядей", price=5500, duration_minutes=180, category_id=hair.id),
            Service(name="Укладка феном", description="Укладка на любую длину волос", price=1000, duration_minutes=40, category_id=hair.id),
            Service(name="Маникюр классический", description="Обработка + покрытие гель-лак", price=1500, duration_minutes=90, category_id=nails.id),
            Service(name="Маникюр с дизайном", description="Гель-лак + художественная роспись", price=2200, duration_minutes=120, category_id=nails.id),
            Service(name="Педикюр", description="Аппаратный педикюр + покрытие", price=2000, duration_minutes=90, category_id=nails.id),
            Service(name="Наращивание ногтей", description="Гелевое наращивание любой формы", price=2800, duration_minutes=150, category_id=nails.id),
            Service(name="Чистка лица", description="Ультразвуковая чистка + маска", price=2500, duration_minutes=60, category_id=face.id),
            Service(name="Массаж лица", description="Классический расслабляющий массаж", price=1200, duration_minutes=40, category_id=face.id),
            Service(name="Пилинг лица", description="Химический пилинг для обновления кожи", price=2800, duration_minutes=45, category_id=face.id),
            Service(name="Коррекция + окрашивание бровей", description="Форма + стойкая краска", price=900, duration_minutes=30, category_id=brows.id),
            Service(name="Ламинирование ресниц", description="Долговременный эффект без наращивания", price=1800, duration_minutes=60, category_id=brows.id),
            Service(name="Наращивание ресниц 2D", description="Объёмное наращивание", price=2500, duration_minutes=120, category_id=brows.id),
        ]
        session.add_all(services)

        masters = [
            Master(name="Анна Соколова", specialty="Парикмахер-стилист", bio="Стаж 8 лет, специалист по окрашиванию и сложным техникам"),
            Master(name="Мария Ким", specialty="Мастер маникюра", bio="Стаж 5 лет, аппаратный маникюр и художественный дизайн"),
            Master(name="Елена Волкова", specialty="Косметолог", bio="Стаж 10 лет, уход за лицом и аппаратные методики"),
            Master(name="Ольга Петрова", specialty="Бровист/лешмейкер", bio="Стаж 4 года, коррекция бровей и наращивание ресниц"),
        ]
        session.add_all(masters)
        await session.flush()

        reviews = []
        if settings.ADMIN_IDS:
            demo_user_id = settings.ADMIN_IDS[0]
            existing = await session.execute(select(User).where(User.id == demo_user_id))
            if not existing.scalar_one_or_none():
                session.add(User(id=demo_user_id, first_name="Demo Admin"))
                await session.flush()

            reviews = [
                Review(user_id=demo_user_id, master_id=masters[0].id, rating=5, text="Анна — просто волшебница, окрашивание держится уже месяц!"),
                Review(user_id=demo_user_id, master_id=masters[1].id, rating=5, text="Маникюр держится 3 недели без сколов, очень аккуратно"),
                Review(user_id=demo_user_id, master_id=masters[2].id, rating=4, text="Кожа после чистки просто сияет, немного больно было но того стоило"),
                Review(user_id=demo_user_id, master_id=masters[3].id, rating=5, text="Брови стали идеальной формы, всем советую"),
            ]
            session.add_all(reviews)
        else:
            print("WARNING: ADMIN_IDS not set, skipping demo reviews (need a valid user_id).")

        await session.commit()

    print(f"Seed complete: 4 categories, {len(services)} services, {len(masters)} masters, {len(reviews)} reviews.")


if __name__ == "__main__":
    asyncio.run(seed())
