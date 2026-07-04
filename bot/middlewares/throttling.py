from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis, rate_limit: int = 1):
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            key = f"throttle:{user.id}"
            if await self.redis.get(key):
                return
            await self.redis.set(key, 1, ex=self.rate_limit)
        return await handler(event, data)
