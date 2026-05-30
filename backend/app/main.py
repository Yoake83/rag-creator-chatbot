from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.vectorstore import init_vectorstore
from app.api.ingest import router as ingest_router
from app.api.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_vectorstore()
    yield


app = FastAPI(
    title="Creator Insight API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router, prefix="/api", tags=["ingest"])
app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.get("/health")
async def health():
    return {"status": "ok"}