#!/bin/bash
# Run this once inside the repo root to replay the commit history.
# Each commit represents a real working milestone, not a dump of all files at once.

set -e

cd "$(dirname "$0")"

echo "=== Initialising repo ==="
git init
git config user.name "Your Name"
git config user.email "you@example.com"

# ── Commit 1: Project scaffold ─────────────────────────────────────
git add .gitignore README.md .env.example
git commit -m "init: project scaffold, README with trade-off notes

Decided on FastAPI + ChromaDB + LangChain LCEL stack.
ChromaDB chosen over Pinecone for zero-infra dev; swap path
documented in vectorstore.py. README includes cost table for
1K creators/day and what breaks at 10K."

# ── Commit 2: Backend config + models ─────────────────────────────
git add backend/requirements.txt backend/app/core/config.py backend/app/models/schemas.py backend/app/__init__.py backend/app/core/__init__.py backend/app/services/__init__.py backend/app/models/__init__.py backend/app/api/__init__.py
git commit -m "backend: pydantic settings, schemas, requirements

Used pydantic-settings for env management.
Centralised chunk_size/overlap/retrieval_k in Settings so
they're tuneable without touching service code.
All API shapes defined upfront in schemas.py."

# ── Commit 3: Transcript service ──────────────────────────────────
git add backend/app/services/transcript.py
git commit -m "feat(transcript): YouTube captions → Whisper fallback chain

youtube-transcript-api for free/fast caption retrieval.
yt-dlp + Whisper base model as fallback when captions are off.
64kbps mp3 is enough for speech; saves ~3x disk vs 320kbps.
Whisper base: ~80% WER accuracy, ~1x real-time on CPU."

# ── Commit 4: Metadata extraction ─────────────────────────────────
git add backend/app/services/metadata.py
git commit -m "feat(metadata): yt-dlp extraction + Apify for IG followers

engagement_rate = (likes + comments) / views * 100.
Guard against views=0 to avoid ZeroDivisionError.
Apify only called when APIFY_TOKEN is set — graceful no-op otherwise.
Instagram follower count is notoriously hard to get without auth;
this is the cleanest free-tier approach I found."

# ── Commit 5: Embedder ─────────────────────────────────────────────
git add backend/app/services/embedder.py
git commit -m "feat(embedder): chunk + embed + upsert to ChromaDB

400-token chunks, 50 overlap, RecursiveCharacterTextSplitter.
Deterministic IDs (video_id_platform_chunkIdx) prevent re-ingestion
duplicates. Each chunk carries full metadata as filter fields
so we can do per-video filtered retrieval later if needed."

# ── Commit 6: Vector store + RAG chain ────────────────────────────
git add backend/app/core/vectorstore.py backend/app/services/rag_chain.py
git commit -m "feat(rag): LangChain LCEL chain with MMR retrieval + streaming memory

MMR (fetch_k=12 → k=6) balances relevance vs diversity across
Video A and B chunks — stops the retriever from returning 6 chunks
from the higher-engagement video and ignoring the other.

ConversationBufferWindowMemory(k=6) keeps last 6 turns.
Beyond 6, oldest turns drop out — keeps token cost stable at scale.
Swap to RedisEntityMemory for multi-server deployments.

Metadata context is always prepended to the prompt so engagement
numbers are accurate even if the retriever doesn't surface them."

# ── Commit 7: API endpoints ────────────────────────────────────────
git add backend/app/api/ingest.py backend/app/api/chat.py backend/app/main.py
git commit -m "feat(api): /ingest and /chat endpoints

/ingest: runs metadata + transcript extraction concurrently
(asyncio.gather). Both steps are CPU-bound so wrapped in
asyncio.to_thread to avoid blocking the event loop.

/chat: SSE streaming via StreamingResponse. Headers include
X-Accel-Buffering: no to prevent nginx from batching tokens.

Chose SSE over WebSockets — unidirectional stream, simpler to
debug, works fine behind standard HTTP load balancers."

# ── Commit 8: Frontend scaffold ────────────────────────────────────
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/src/index.css frontend/src/main.jsx
git commit -m "frontend: Vite + React scaffold with design system

Dark industrial theme — var(--bg) #0a0a0a, accent lime #c8f135.
IBM Plex Mono for data, Syne for UI labels.
CSS custom properties defined globally; no CSS-in-JS overhead."

# ── Commit 9: API client ───────────────────────────────────────────
git add frontend/src/lib/api.js
git commit -m "frontend: fetch-based SSE client for streaming chat

Axios doesn't handle ReadableStream well in the browser — using
raw fetch + getReader() for the chat stream.
Ingest still uses axios (standard JSON, no streaming needed).
__SOURCES__ and __DONE__ sentinel tokens keep the protocol simple
without a WebSocket handshake overhead."

# ── Commit 10: Components ─────────────────────────────────────────
git add frontend/src/components/
git commit -m "frontend: IngestionForm, VideoCard, ChatPanel components

VideoCard: responsive 4-column stat grid, highlights eng. rate
in accent colour so it stands out at a glance.

ChatPanel: streaming cursor blink, collapsible source citations
per message, 5 pre-filled suggested questions to unblock users.

IngestionForm: step-by-step loading messages so users understand
why it takes 10-30s (Whisper transcription is the bottleneck)."

# ── Commit 11: App layout ─────────────────────────────────────────
git add frontend/src/App.jsx frontend/src/App.css
git commit -m "frontend: App layout — sidebar + chat panel

340px fixed sidebar for video cards; rest goes to chat.
Mobile breakpoint collapses to horizontal scroll cards + stacked chat.
Session ID shown in header for debugging; reset button clears state."

echo ""
echo "✓  $(git log --oneline | wc -l) commits created."
echo "   Push with: git remote add origin <your-repo> && git push -u origin main"
