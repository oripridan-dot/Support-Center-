from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Halilit Support Center (Local AI)"
    
    # Database
    DATABASE_URL: str = "sqlite:///./support_center.db"
    
    # Ollama / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Google Gemini (optional)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "dummy_key_for_local")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
