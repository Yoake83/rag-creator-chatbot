"""
POST /api/ingest

Orchestrates the full ingestion pipeline:
  1. Fetch transcripts (YouTube captions → Whisper fallback)
  2. Extract metadata (yt-dlp + optional Apify for Instagram followers)
  3. Chunk + embed → ChromaDB
  4. Initialise RAG session with metadata context
  5. Return session_id + metadata to frontend

Error handling: individual step failures are caught and surfaced with
clear messages rather than 500s — the frontend can show partial results.
"""

import uuid
import asyncio
import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import IngestRequest, IngestResponse
from app.services.transcript import get_youtube_transcript, get_instagram_transcript
from app.services.metadata import extract_youtube_metadata, extract_instagram_metadata
from app.services.embedder import chunk_and_embed
from app.services.rag_chain import init_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_videos(request: IngestRequest):
    session_id = str(uuid.uuid4())
    logger.info(f"[Ingest] New session {session_id}")

    # Run metadata extraction concurrently
    try:
        meta_a, meta_b = await asyncio.gather(
            asyncio.to_thread(extract_youtube_metadata, request.youtube_url, "A"),
            asyncio.to_thread(extract_instagram_metadata, request.instagram_url, "B"),
        )
    except Exception as e:
        logger.error(f"[Ingest] Metadata extraction failed: {e}")
        raise HTTPException(status_code=422, detail=f"Metadata extraction failed: {e}")

    # Fetch transcripts concurrently
    try:
        transcript_a, transcript_b = await asyncio.gather(
            asyncio.to_thread(get_youtube_transcript, request.youtube_url),
            asyncio.to_thread(get_instagram_transcript, request.instagram_url),
        )
    except Exception as e:
        logger.error(f"[Ingest] Transcript extraction failed: {e}")
        raise HTTPException(status_code=422, detail=f"Transcript extraction failed: {e}")

    if not transcript_a.strip():
        raise HTTPException(status_code=422, detail="Video A transcript is empty")
    if not transcript_b.strip():
        raise HTTPException(status_code=422, detail="Video B transcript is empty")

    # Chunk + embed (CPU-bound, run in thread)
    n_a = await asyncio.to_thread(chunk_and_embed, transcript_a, meta_a)
    n_b = await asyncio.to_thread(chunk_and_embed, transcript_b, meta_b)

    # Boot the RAG session
    init_session(session_id, meta_a, meta_b)

    return IngestResponse(
        session_id=session_id,
        video_a=meta_a,
        video_b=meta_b,
        chunks_stored=n_a + n_b,
        message=f"Ingested {n_a + n_b} chunks. Ready to chat.",
    )
