from fastapi import APIRouter, HTTPException
from datetime import timedelta
import json

from api.dependencies import create_access_token, verify_telegram_init_data

router = APIRouter()


@router.post("/login")
async def login(init_data: str):
    try:
        user_data = verify_telegram_init_data(init_data)
        user_json = json.loads(user_data.get("user", "{}"))
        user_id = int(user_json.get("id", 0))
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid user data")

        token = create_access_token(data={"sub": str(user_id)}, expires_delta=timedelta(days=7))
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
