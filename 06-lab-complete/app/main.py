import signal
import time
import json
import logging
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, Depends, Request, Response
from pydantic import BaseModel

from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit, redis_client
from .cost_guard import check_budget
from utils.mock_llm import ask

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger(__name__)

is_ready = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    logger.info("Application starting up...")
    
    # Kiểm tra Redis connection
    try:
        redis_client.ping()
        logger.info("Connected to Redis successfully.")
        is_ready = True
    except redis.ConnectionError:
        logger.error("Could not connect to Redis! Ready state is False.")

    yield
    
    is_ready = False
    logger.info("Application shutting down gracefully... Waiting for in-flight requests to complete.")
    time.sleep(1) # Chờ 1 giây để các requests hiện tại xử lý xong
    redis_client.close()
    logger.info("Shutdown complete.")

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

def handle_sigterm(*args):
    logger.info("Received SIGTERM signal!")
    # Uvicorn handles graceful shutdown if we give it time

signal.signal(signal.SIGTERM, handle_sigterm)

class AskRequest(BaseModel):
    question: str
    user_id: str = None # Allow passing user_id in body for testing, otherwise auth header sets it

@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version}

@app.get("/ready")
def ready(response: Response):
    if not is_ready:
        response.status_code = 503
        return {"status": "not ready"}
    
    try:
        redis_client.ping()
        return {"status": "ready"}
    except Exception as e:
        response.status_code = 503
        return {"status": "not ready", "error": str(e)}

@app.post("/ask")
def ask_question(
    req: AskRequest,
    user_id: str = Depends(verify_api_key)
):
    # Nếu user_id được gửi kèm để test, ưu tiên nó
    final_user_id = req.user_id if req.user_id else user_id

    # 1. Check Rate Limit & Budget (Security checks)
    check_rate_limit(final_user_id)
    check_budget(final_user_id)
    
    # 2. Stateless Design: Lấy history từ Redis thay vì lưu biến trong Memory
    history_key = f"history:{final_user_id}"
    # Redis lrange returns bytes
    history_bytes = redis_client.lrange(history_key, 0, -1)
    
    # 3. Process LLM
    logger.info(json.dumps({"event": "ask_llm", "user": final_user_id, "question": req.question}))
    answer = ask(req.question)
    
    # 4. Lưu lại History vào Redis (Giữ tối đa 20 tin nhắn)
    redis_client.rpush(history_key, f"Q: {req.question}")
    redis_client.rpush(history_key, f"A: {answer}")
    redis_client.ltrim(history_key, -20, -1) 
    
    return {"user": final_user_id, "answer": answer}
