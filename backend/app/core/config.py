from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    openai_api_key: str = "dummy"
    groq_api_key: str = ""
    apify_token: str = ""
    chroma_persist_dir: str = "./chroma_db"
    vector_backend: str = "chroma"
    transcript_backend: str = "auto"
    environment: str = "development"
    embed_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "llama-3.1-8b-instant"
    chunk_size: int = 400
    chunk_overlap: int = 50
    retrieval_k: int = 6

    # cors handled directly, not from env
    @property
    def cors_origins(self) -> List[str]:
        return ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()