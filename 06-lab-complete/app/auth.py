from fastapi import Header, HTTPException
from .config import settings

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="X-API-Key header missing")
    if x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # Giả sử username được mã hóa trong key, ở đây dùng tạm dummy user
    return "user1"
