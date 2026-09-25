from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    live_model: str
    model_config= {"env_file": ".env"}

settings = Settings()