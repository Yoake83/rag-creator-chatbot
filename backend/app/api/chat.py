"""
POST /api/chat  →  Server-Sent Events stream

Why SSE over WebSockets?
  - Simpler to implement and debug (plain HTTP)
  - Works with standard fetch + ReadableStream on the frontend
  - Sufficient for unidirectional LLM token streaming
  - Scales fine behind nginx/CloudFront

WebSockets make sense when you need bidirectional real-time (e.g., multi-user collab).
For a chatbot, SSE is the right tool.
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest
from app.services.rag_chain import stream_answer, _sessions

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat")
async def chat(request: ChatRequest):
    if request.session_id not in _sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Ingest videos first.",
        )

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    async def event_stream():
        try:
            async for token in stream_answer(request.session_id, request.message):
                # SSE format: "data: <token>\n\n"
                # Newlines inside tokens need escaping so the client parser doesn't break
                safe_token = token.replace("\n", "\\n")
                yield f"data: {safe_token}\n\n"
        except Exception as e:
            logger.error(f"[Chat] Streaming error: {e}")
            yield f"data: __ERROR__{str(e)}\n\n"
        finally:
            yield "data: __DONE__\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering
        },
    )
