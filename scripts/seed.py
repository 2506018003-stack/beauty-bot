import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import AsyncSessionLocal, engine, Base
from api.models import ServiceCategory, Service, Master


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        hair = ServiceCategory(name="Волосы", sort_order=1)
        nails = ServiceCategory(name="Ногти", sort_order=2)
        face = ServiceCategory(name="Лицо", sort_order=3)
        session.add_all([hair, nails, face])
        await session.flush()

        services = [
            Service(name="Женская стрижка", description="Стрижка любой сложности + укладка", price=1800, duration_minutes=60, category_id=hair.id),
            Service(name="Окрашивание", description="Однотонное окрашивание, краска включена", price=3500, duration_minutes=120, category_id=hair.id),
            Service(name="Маникюр классический", description="Обработка + покрытие гель-лак", price=1500, duration_minutes=90, category_id=nails.id),
            Service(name="Педикюр", description="Аппаратный педикюр + покрытие", price=2000, duration_minutes=90, category_id=nails.id),
            Service(name="Чистка лица", description="Ультразвуковая чистка + маска", price=2500, duration_minutes=60, category_id=face.id),
            Service(name="Массаж лица", description="Классический расслабляющий массаж", price=1200, duration_minutes=40, category_id=face.id),
        ]
        session.add_all(services)

        masters = [
            Master(name="Анна Соколова", specialty="Парикмахер-стилист", bio="Стаж 8 лет, специалист по окрашиванию"),
            Master(name="Мария Ким", specialty="Мастер маникюра", bio="Стаж 5 лет, аппаратный маникюр"),
            Master(name="Елена Волкова", specialty="Косметолог", bio="Стаж 10 лет, уход за лицом"),
        ]
        session.add_all(masters)

        await session.commit()

    print("Seed complete: 3 categories, 6 services, 3 masters.")


if __name__ == "__main__":
    asyncio.run(seed())
