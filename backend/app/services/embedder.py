"""
Text chunking + embedding pipeline.

Chunk strategy: RecursiveCharacterTextSplitter at 400 tokens / 50 overlap.
Why 400? A 5-min video ≈ 2,500 tokens → ~7 chunks.
MMR retrieval on 7 chunks is fast and precise without losing context.

Each chunk carries metadata:
  - video_id:     "A" | "B"
  - source_url:   original video URL
  - chunk_index:  0-based position for ordering
  - platform:     "youtube" | "instagram"
  - creator:      channel/username
  - engagement_rate: float (for LLM context)
"""

import logging
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.core.vectorstore import get_vectorstore
from app.models.schemas import VideoMetadata

logger = logging.getLogger(__name__)


def chunk_and_embed(transcript: str, metadata: VideoMetadata) -> int:
    """
    Split transcript into chunks, attach metadata, embed + store in ChromaDB.
    Returns the number of chunks stored.
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-4o",
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    raw_chunks = splitter.split_text(transcript)

    documents: List[Document] = []
    for i, chunk_text in enumerate(raw_chunks):
        doc = Document(
            page_content=chunk_text,
            metadata={
                "video_id": metadata.video_id,
                "source_url": metadata.url,
                "chunk_index": i,
                "platform": metadata.platform,
                "creator": metadata.creator or "unknown",
                "follower_count": metadata.follower_count or 0,
                "engagement_rate": metadata.engagement_rate or 0.0,
                "views": metadata.views or 0,
                "likes": metadata.likes or 0,
                "comments": metadata.comments or 0,
                "upload_date": metadata.upload_date or "",
                "duration_seconds": metadata.duration_seconds or 0,
                "title": metadata.title or "",
            },
        )
        documents.append(doc)

    vs = get_vectorstore()

    # Generate deterministic IDs so re-ingesting the same video doesn't duplicate
    ids = [
        f"{metadata.video_id}_{metadata.platform}_{i}"
        for i in range(len(documents))
    ]

    vs.add_documents(documents, ids=ids)
    logger.info(
        f"[Embedder] Stored {len(documents)} chunks for Video {metadata.video_id}"
    )
    return len(documents)


def clear_session(session_id: str) -> None:
    """
    Remove all chunks for a session.
    Useful when the user submits new URLs — avoids stale data contaminating answers.
    """
    vs = get_vectorstore()
    # ChromaDB supports direct collection wipe; for production use filtered delete
    try:
        vs._collection.delete(where={"session_id": session_id})
    except Exception:
        pass  # collection may not exist yet
