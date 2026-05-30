import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.core.config import settings

_chroma_client = None
_vectorstore = None

COLLECTION_NAME = "creator_videos"


def init_vectorstore():
    global _chroma_client, _vectorstore

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    _vectorstore = Chroma(
        client=_chroma_client,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )


def get_vectorstore():
    if _vectorstore is None:
        init_vectorstore()
    return _vectorstore