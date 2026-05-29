# Creator Insight — RAG Chatbot for Video Analytics

A full-stack RAG chatbot that ingests YouTube + Instagram Reel transcripts, embeds them into a vector store, and lets creators ask natural-language questions about their content performance.

---

## What It Does

1. Takes two video URLs (YouTube + Instagram Reel) as input
2. Pulls transcripts + metadata (views, likes, comments, follower count, hashtags, upload date, duration)
3. Computes engagement rate: `(likes + comments) / views × 100`
4. Chunks + embeds transcripts → stores in ChromaDB, tagged by `video_id`
5. Streams RAG answers with source citations, maintains chat memory across turns
6. Side-by-side video cards + chat panel in the frontend

---

## Tech Stack & Why

| Layer | Choice | Reasoning |
|---|---|---|
| Backend | FastAPI | Async-native, plays well with LangChain's async chain invocation |
| Orchestration | LangChain (LCEL) | Composable retrieval chains, built-in memory, streaming support |
| Embeddings | `text-embedding-3-small` | $0.00002/1K tokens — ~50x cheaper than ada-002 with better perf |
| Vector DB | ChromaDB (local) | Zero infra cost, persistent, swappable to Qdrant/Pinecone via one env var |
| LLM | GPT-4o-mini | 10x cheaper than GPT-4o, handles RAG+reasoning well up to ~1000 creators/day |
| Transcripts | `youtube-transcript-api` + `yt-dlp` + Whisper | Free YouTube captions when available; Whisper fallback for Instagram |
| Frontend | React + Vite | Fast HMR, no Next.js overhead needed for a single-page chat app |

---

## Cost at Scale (1,000 Creators/Day)

Assumptions: 2 videos per creator, avg 5 min each, ~800 tokens/min transcript.

| Operation | Cost/Creator | Cost/Day (1K) |
|---|---|---|
| Embedding (2 × 5 min) | ~$0.0008 | ~$0.80 |
| GPT-4o-mini (10 Q&A turns) | ~$0.002 | ~$2.00 |
| ChromaDB (local) | $0 | $0 |
| yt-dlp + Whisper (self-hosted) | ~$0.001 | ~$1.00 |
| **Total** | **~$0.004** | **~$3.80/day** |

At 10K creators/day, switch to: Qdrant Cloud ($25/mo), batch embedding jobs, and a Redis cache for repeat video lookups. Total still under $50/day.

**If GPT-4o-mini degrades quality**: fall back to Claude Haiku — similar price, often better at structured reasoning.

---

## What Breaks at 10,000 Users

- ChromaDB is single-process — migrate to **Qdrant** (distributed, production-ready)
- Transcript fetching is synchronous per request — move to **Celery + Redis** task queue
- No dedup — same video URL gets re-embedded. Add a **URL hash cache** (Redis/Postgres)
- Whisper on CPU is slow (~2-3x real time) — use **faster-whisper** on GPU or AssemblyAI

---

## Setup

### Prerequisites
- Python 3.11+
- Node 18+
- `ffmpeg` installed (for yt-dlp audio extraction)
- OpenAI API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# fill in your keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env.local
# set VITE_API_URL=http://localhost:8000
npm run dev
```

---

## Project Structure

```
rag-creator-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── api/
│   │   │   ├── ingest.py        # POST /ingest — fetch + embed videos
│   │   │   └── chat.py          # POST /chat — streaming RAG response
│   │   ├── core/
│   │   │   ├── config.py        # env + settings
│   │   │   └── vectorstore.py   # ChromaDB client singleton
│   │   ├── services/
│   │   │   ├── transcript.py    # YouTube + Instagram transcript fetching
│   │   │   ├── metadata.py      # engagement rate + metadata extraction
│   │   │   ├── embedder.py      # chunk + embed + upsert to Chroma
│   │   │   └── rag_chain.py     # LangChain LCEL RAG chain w/ memory
│   │   └── models/
│   │       └── schemas.py       # Pydantic request/response models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── VideoCard.jsx    # per-video metadata card
│   │   │   ├── ChatPanel.jsx    # streaming chat UI
│   │   │   └── IngestionForm.jsx
│   │   ├── hooks/
│   │   │   └── useStream.js     # SSE streaming hook
│   │   └── lib/
│   │       └── api.js           # axios client
│   ├── index.html
│   └── vite.config.js
├── .env.example
└── README.md
```

---

## Demo Questions to Ask

- *Why did Video A get more engagement than Video B?*
- *What's the engagement rate of each video?*
- *Compare the hooks in the first 5 seconds.*
- *Who's the creator of Video B and what's their follower count?*
- *Suggest improvements for Video B based on what worked in A.*

---

## Chunk Strategy

- Chunk size: **400 tokens**, overlap: **50 tokens**
- Why: Short enough for precise retrieval, long enough for semantic context. At 400 tokens, a 5-min video (~2,500 tokens) produces ~7 chunks — manageable MMR retrieval without noise.
- Each chunk is tagged: `{ video_id: "A", source_url: "...", chunk_index: N }`
