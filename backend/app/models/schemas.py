from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube video URL (Video A)")
    instagram_url: str = Field(..., description="Instagram Reel URL (Video B)")


class VideoMetadata(BaseModel):
    video_id: str                     # "A" or "B"
    url: str
    platform: str                     # "youtube" | "instagram"
    title: Optional[str] = None
    creator: Optional[str] = None
    follower_count: Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    engagement_rate: Optional[float] = None   # computed
    hashtags: List[str] = []
    upload_date: Optional[str] = None
    duration_seconds: Optional[float] = None
    thumbnail_url: Optional[str] = None


class IngestResponse(BaseModel):
    session_id: str
    video_a: VideoMetadata
    video_b: VideoMetadata
    chunks_stored: int
    message: str


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceChunk(BaseModel):
    video_id: str
    chunk_index: int
    content_preview: str   # first 120 chars


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
