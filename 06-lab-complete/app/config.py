from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Production AI Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"
    
    agent_api_key: str
    redis_url: str
    
    rate_limit_per_minute: int = 10
    monthly_budget_usd: float = 10.0
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
