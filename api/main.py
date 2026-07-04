import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode
from redis.asyncio import Redis, ConnectionPool
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.database import engine, Base
from api.routers import auth, services as services_router, booking as booking_router, loyalty, reviews, crm
from bot.config import settings
from bot.handlers import start, services as bot_services, booking as bot_booking, loyalty as bot_loyalty, reviews as bot_reviews, admin
from bot.middlewares.db import DbMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from services.reminders import send_visit_reminders


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    redis_pool = ConnectionPool.from_url(
        str(settings.REDIS_URL),
        max_connections=50,
        decode_responses=True
    )
    redis = Redis(connection_pool=redis_pool)
    storage = RedisStorage(redis=redis)

    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage)
    dp.message.middleware(ThrottlingMiddleware(redis, rate_limit=1))
    dp.callback_query.middleware(ThrottlingMiddleware(redis, rate_limit=1))
    dp.message.middleware(DbMiddleware())
    dp.callback_query.middleware(DbMiddleware())
    dp.include_routers(
        start.router,
        bot_services.router,
        bot_booking.router,
        bot_loyalty.router,
        bot_reviews.router,
        admin.router,
    )

    await bot.delete_webhook(drop_pending_updates=True)
    polling_task = asyncio.create_task(dp.start_polling(bot))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_visit_reminders, "interval", hours=1, args=[bot], id="visit_reminders")
    scheduler.start()

    app.state.bot = bot
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)
    dp.stop_polling()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass
    await bot.session.close()
    await redis_pool.disconnect()
    await engine.dispose()


app = FastAPI(
    title="Beauty Salon Bot API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("DEBUG", "false").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("DEBUG", "false").lower() == "true" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "beauty-bot", "version": "1.0.0", "timestamp": str(datetime.utcnow())}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(services_router.router, prefix="/services", tags=["services"])
app.include_router(booking_router.router, prefix="/booking", tags=["booking"])
app.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
app.include_router(crm.router, prefix="/crm", tags=["crm"])


@app.get("/miniapp")
@app.get("/miniapp/")
@app.get("/miniapp/index.html")
async def miniapp_root():
    return FileResponse("miniapp/index.html")


@app.get("/crm")
@app.get("/crm/")
@app.get("/crm/index.html")
async def crm_root():
    return FileResponse("crm/index.html")


app.mount("/miniapp/static", StaticFiles(directory="miniapp"), name="miniapp-static")
app.mount("/crm/static", StaticFiles(directory="crm"), name="crm-static")
