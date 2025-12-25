from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Halilit Support Center (Local AI)"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
