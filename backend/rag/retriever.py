from backend.config import RETRIEVAL_TOP_K
from backend.rag.ingest import get_collection


def query_knowledge_base(query_text: str, k: int = RETRIEVAL_TOP_K) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []

    result = collection.query(query_texts=[query_text], n_results=min(k, collection.count()))

    matches: list[dict] = []
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]

    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        matches.append(
            {
                "text": text,
                "source": metadata.get("source"),
                "section": metadata.get("section"),
                "distance": distance,
            }
        )
    return matches
