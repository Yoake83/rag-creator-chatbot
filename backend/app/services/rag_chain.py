"""
LangChain LCEL RAG chain.

Flow per turn:
  1. MMR retrieval (k=6, fetch_k=12) — balances relevance + diversity across A/B
  2. Build context block from retrieved chunks, each labelled [Video A] / [Video B]
  3. Prepend structured metadata summary so the LLM always has engagement numbers
  4. Stream response tokens via AsyncIterator
  5. Memory: ConversationBufferWindowMemory (last 6 turns) — keeps context without
     blowing up the context window at scale

Per-session memory is stored in a dict keyed by session_id.
At scale, swap this for Redis-backed LangChain memory (RedisEntityMemory).
"""

import logging
from typing import AsyncIterator, Dict, Any

from langchain_groq import ChatGroq
from langchain_classic.memory import ConversationBufferWindowMemory

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_core.documents import Document

from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from app.core.config import settings
from app.core.vectorstore import get_vectorstore
from app.models.schemas import VideoMetadata, SourceChunk

logger = logging.getLogger(__name__)

# ── In-memory session store ───────────────────────────────────────────────────
# { session_id: { "memory": ConversationBufferWindowMemory, "meta": {...} } }
_sessions: Dict[str, Dict[str, Any]] = {}

SYSTEM_PROMPT = """You are an expert social media analytics assistant called Creator Insight.
You have access to transcripts and metadata from two videos.

VIDEO METADATA (always accurate, sourced from platform APIs):
{metadata_context}

Use the retrieved transcript chunks below to answer questions about content, hooks, tone, and suggestions.
Always cite which video (A or B) and the chunk index your answer is based on.
Be specific, data-driven, and actionable.

RETRIEVED CHUNKS:
{context}

If the question cannot be answered from the provided content, say so clearly.
"""

HUMAN_PROMPT = "{question}"


def init_session(
    session_id: str,
    video_a: VideoMetadata,
    video_b: VideoMetadata,
) -> None:
    """Called after ingestion to register session metadata."""
    _sessions[session_id] = {
        "memory": ConversationBufferWindowMemory(
            k=6,
            return_messages=True,
            memory_key="chat_history",
        ),
        "video_a": video_a,
        "video_b": video_b,
    }
    logger.info(f"[RAG] Session {session_id} initialised")


def _build_metadata_context(session_id: str) -> str:
    sess = _sessions.get(session_id, {})
    va: VideoMetadata = sess.get("video_a")
    vb: VideoMetadata = sess.get("video_b")
    if not va or not vb:
        return "No metadata available."

    def fmt(v: VideoMetadata) -> str:
        return (
            f"  Title: {v.title}\n"
            f"  Creator: {v.creator} | Followers: {v.follower_count or 'N/A'}\n"
            f"  Views: {v.views} | Likes: {v.likes} | Comments: {v.comments}\n"
            f"  Engagement Rate: {v.engagement_rate}%\n"
            f"  Duration: {v.duration_seconds}s | Uploaded: {v.upload_date}\n"
            f"  Hashtags: {', '.join(v.hashtags[:5]) or 'none'}"
        )

    return f"[Video A — YouTube]\n{fmt(va)}\n\n[Video B — Instagram]\n{fmt(vb)}"


def _retrieve_chunks(session_id: str, question: str) -> list[Document]:
    vs = get_vectorstore()
    # MMR: fetch_k=12 candidates, return k=6 diverse ones
    retriever = vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": settings.retrieval_k,
            "fetch_k": settings.retrieval_k * 2,
        },
    )
    return retriever.invoke(question)


def _docs_to_context(docs: list[Document]) -> str:
    parts = []
    for doc in docs:
        vid = doc.metadata.get("video_id", "?")
        idx = doc.metadata.get("chunk_index", "?")
        parts.append(f"[Video {vid} | Chunk {idx}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _docs_to_sources(docs: list[Document]) -> list[SourceChunk]:
    return [
        SourceChunk(
            video_id=doc.metadata.get("video_id", "?"),
            chunk_index=doc.metadata.get("chunk_index", 0),
            content_preview=doc.page_content[:120],
        )
        for doc in docs
    ]


async def stream_answer(
    session_id: str,
    question: str,
) -> AsyncIterator[str]:
    """
    Yields token strings as they stream from the LLM.
    The final yielded item is a JSON-serialisable sources payload prefixed with '\n\n__SOURCES__'.
    """
    if session_id not in _sessions:
        yield "Session not found. Please ingest videos first."
        return

    sess = _sessions[session_id]
    memory: ConversationBufferWindowMemory = sess["memory"]

    docs = _retrieve_chunks(session_id, question)
    context = _docs_to_context(docs)
    metadata_context = _build_metadata_context(session_id)
    sources = _docs_to_sources(docs)

    chat_history = memory.load_memory_variables({}).get("chat_history", [])

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", HUMAN_PROMPT),
    ])

    llm = ChatGroq(
        model=settings.llm_model,
        groq_api_key=settings.groq_api_key,
        streaming=True,
        temperature=0.3,
    )
    # Format the prompt
    messages = prompt.format_messages(
        metadata_context=metadata_context,
        context=context,
        chat_history=chat_history,
        question=question,
    )

    full_answer = ""
    async for chunk in llm.astream(messages):
        token = chunk.content
        full_answer += token
        yield token

    # Save to memory after streaming
    memory.save_context({"input": question}, {"output": full_answer})

    # Emit sources as a structured suffix the frontend can parse
    import json
    sources_payload = json.dumps([s.model_dump() for s in sources])
    yield f"\n\n__SOURCES__{sources_payload}"
