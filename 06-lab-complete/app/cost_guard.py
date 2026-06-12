import redis
from datetime import datetime
from fastapi import HTTPException
from .config import settings

redis_client = redis.from_url(settings.redis_url)

def check_budget(user_id: str):
    # Ước tính chi phí một request
    estimated_cost = 0.01 
    
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(redis_client.get(key) or 0)
    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Payment Required: Monthly budget exceeded")
    
    redis_client.incrbyfloat(key, estimated_cost)
    redis_client.expire(key, 32 * 24 * 3600)  # Tự động dọn sau 32 ngày
