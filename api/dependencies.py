import hmac
import hashlib
from urllib.parse import parse_qsl
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

from bot.config import settings

security = HTTPBearer()


def verify_telegram_init_data(init_data: str) -> dict:
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        hash_value = parsed.pop('hash', None)
        if not hash_value:
            raise HTTPException(status_code=403, detail="Missing hash")

        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != hash_value:
            raise HTTPException(status_code=403, detail="Invalid signature")

        auth_date = int(parsed.get('auth_date', 0))
        if datetime.utcnow().timestamp() - auth_date > 86400:
            raise HTTPException(status_code=403, detail="Init data expired")

        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Auth failed: {str(e)}")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
        if user_id not in settings.ADMIN_IDS:
            raise HTTPException(status_code=403, detail="Not authorized")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_guest(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        return int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_telegram(init_data: str = Header(...)):
    return verify_telegram_init_data(init_data)
