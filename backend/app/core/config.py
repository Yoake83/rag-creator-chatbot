from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    openai_api_key: str
    chroma_persist_dir: str = "./chroma_db"
    vector_backend: str = "chroma"  # "chroma" | "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    apify_token: str = ""
    rapidapi_key: str = ""
    transcript_backend: str = "auto"  # "auto" | "whisper"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:5173"]

    # Embedding + LLM model names — easy to swap centrally
    embed_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"

    # Chunking strategy
    chunk_size: int = 400          # tokens
    chunk_overlap: int = 50        # tokens
    retrieval_k: int = 6           # top-k chunks per query

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
