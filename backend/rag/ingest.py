"""Builds (or loads) the Chroma collection of FCRM knowledge chunks.

Uses Chroma's bundled default local embedding function (all-MiniLM-L6-v2 via
onnxruntime) - no API key or external network call required for embeddings.
Idempotent: skips ingestion if the collection is already populated.
"""

import chromadb

from backend.config import CHROMA_PATH, KNOWLEDGE_COLLECTION, KNOWLEDGE_DIR
from backend.rag.chunker import chunk_markdown

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection():
    client = get_client()
    return client.get_or_create_collection(name=KNOWLEDGE_COLLECTION)


def ensure_knowledge_base_ingested() -> None:
    collection = get_collection()
    if collection.count() > 0:
        return

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text, source=path.name)
        for i, chunk in enumerate(chunks):
            documents.append(chunk.text)
            metadatas.append({"source": chunk.source, "section": chunk.section})
            ids.append(f"{path.stem}-{i}")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
