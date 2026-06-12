import time
import redis
from fastapi import HTTPException
from .config import settings

# Khởi tạo kết nối Redis
redis_client = redis.from_url(settings.redis_url)

def check_rate_limit(user_id: str):
    current_minute = int(time.time() / 60)
    key = f"rate_limit:{user_id}:{current_minute}"
    
    requests = redis_client.incr(key)
    if requests == 1:
        redis_client.expire(key, 120) # expire sau 2 phút
        
    if requests > settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Too Many Requests")
