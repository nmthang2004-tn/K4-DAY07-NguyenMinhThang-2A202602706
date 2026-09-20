from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401

            # TODO: initialize chromadb client + collection
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        # Copy metadata to avoid mutating caller's object
        # Always include doc_id in metadata — needed by delete_document
        meta = dict(doc.metadata) if doc.metadata else {}
        # Keep a source-level doc_id supplied by the caller.  Chunked records
        # need ``Document.id`` to be unique (for example ``policy#2``) while
        # metadata ``doc_id`` must still identify the original document.
        meta.setdefault("doc_id", doc.id)
        return {
            "id": doc.id,
            "content": doc.content,
            "embedding": self._embedding_fn(doc.content),
            "metadata": meta,
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records:
            return []
        query_emb = self._embedding_fn(query)
        scored = []
        for rec in records:
            score = _dot(query_emb, rec["embedding"])
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, rec in scored[:top_k]:
            # Strip embedding to keep output clean
            r = {k: v for k, v in rec.items() if k != "embedding"}
            r["score"] = score
            results.append(r)
        return results

    def add_documents(self, docs: list[Document]) -> None:
        for doc in docs:
            record = self._make_record(doc)
            self._store.append(record)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        # Filter FIRST, then search — never get top-k then filter
        if metadata_filter:
            candidates = [
                rec for rec in self._store
                if all(rec["metadata"].get(k) == v for k, v in metadata_filter.items())
            ]
        else:
            candidates = self._store

        return self._search_records(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        before = len(self._store)
        self._store = [r for r in self._store if r["metadata"].get("doc_id") != doc_id]
        return len(self._store) < before
