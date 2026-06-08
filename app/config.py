from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./sales_agent.db"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.1-8b-instant"
    eval_confidence_threshold: float = 0.55

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
