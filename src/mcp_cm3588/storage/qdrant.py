"""Qdrant-based knowledge storage for CM3588."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from ..config import config


class KnowledgeEntry(BaseModel):
    """A knowledge entry about CM3588."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    content: str
    category: str  # hardware, voice-pipeline, npu, docker, troubleshooting
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChangeLogEntry(BaseModel):
    """A changelog entry for tracking changes on CM3588."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    what: str  # What was changed
    why: str  # Why it was changed
    details: str  # Detailed description
    files_changed: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)


class KnowledgeStore:
    """Vector store for CM3588 knowledge using Qdrant."""

    KNOWLEDGE_COLLECTION = "cm3588_knowledge"
    CHANGELOG_COLLECTION = "cm3588_changelog"

    def __init__(self):
        self._client: QdrantClient | None = None
        self._encoder: SentenceTransformer | None = None
        self._vector_size: int = 384  # MiniLM default

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(
                host=config.qdrant.host,
                port=config.qdrant.port,
                timeout=60,
                check_compatibility=False,
            )
            self._ensure_collections()
        return self._client

    @property
    def encoder(self) -> SentenceTransformer:
        if self._encoder is None:
            self._encoder = SentenceTransformer(config.embedding.model_name)
            self._vector_size = self._encoder.get_sentence_embedding_dimension()
        return self._encoder

    def _ensure_collections(self) -> None:
        """Create collections if they don't exist."""
        # Initialize encoder to get vector size
        _ = self.encoder

        collections = self._client.get_collections().collections
        existing = {c.name for c in collections}

        # Knowledge collection
        if self.KNOWLEDGE_COLLECTION not in existing:
            self._client.create_collection(
                collection_name=self.KNOWLEDGE_COLLECTION,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )

        # Changelog collection
        if self.CHANGELOG_COLLECTION not in existing:
            self._client.create_collection(
                collection_name=self.CHANGELOG_COLLECTION,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )

    # =========================================================================
    # Knowledge operations
    # =========================================================================

    def save_knowledge(self, entry: KnowledgeEntry) -> str:
        """Save a knowledge entry to the store."""
        text = f"{entry.title}\n\n{entry.content}"
        vector = self.encoder.encode(text).tolist()

        point = PointStruct(
            id=entry.id,
            vector=vector,
            payload=entry.model_dump(),
        )

        self.client.upsert(collection_name=self.KNOWLEDGE_COLLECTION, points=[point])
        return entry.id

    def search_knowledge(
        self, query: str, limit: int = 5, category: str | None = None
    ) -> list[KnowledgeEntry]:
        """Search for relevant knowledge entries."""
        vector = self.encoder.encode(query).tolist()

        filter_conditions = None
        if category:
            filter_conditions = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )

        results = self.client.query_points(
            collection_name=self.KNOWLEDGE_COLLECTION,
            query=vector,
            limit=limit,
            query_filter=filter_conditions,
        )

        return [KnowledgeEntry(**hit.payload) for hit in results.points]

    def get_knowledge_by_id(self, entry_id: str) -> KnowledgeEntry | None:
        """Get a specific knowledge entry by ID."""
        results = self.client.retrieve(
            collection_name=self.KNOWLEDGE_COLLECTION,
            ids=[entry_id],
        )
        if results:
            return KnowledgeEntry(**results[0].payload)
        return None

    def list_by_category(self, category: str, limit: int = 100) -> list[KnowledgeEntry]:
        """List all entries in a category."""
        results = self.client.scroll(
            collection_name=self.KNOWLEDGE_COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            ),
            limit=limit,
        )

        return [KnowledgeEntry(**point.payload) for point in results[0]]

    def delete_knowledge(self, entry_id: str) -> bool:
        """Delete a knowledge entry."""
        self.client.delete(
            collection_name=self.KNOWLEDGE_COLLECTION,
            points_selector=[entry_id],
        )
        return True

    def get_categories(self) -> list[str]:
        """Get all unique categories."""
        results, _ = self.client.scroll(
            collection_name=self.KNOWLEDGE_COLLECTION,
            limit=1000,
            with_payload=["category"],
        )
        categories = set()
        for point in results:
            if point.payload and "category" in point.payload:
                categories.add(point.payload["category"])
        return sorted(categories)

    # =========================================================================
    # Changelog operations
    # =========================================================================

    def save_changelog(self, entry: ChangeLogEntry) -> str:
        """Save a changelog entry."""
        text = f"{entry.what}\n{entry.why}\n{entry.details}"
        vector = self.encoder.encode(text).tolist()

        point = PointStruct(
            id=entry.id,
            vector=vector,
            payload=entry.model_dump(),
        )

        self.client.upsert(collection_name=self.CHANGELOG_COLLECTION, points=[point])
        return entry.id

    def get_changelog(self, limit: int = 20) -> list[ChangeLogEntry]:
        """Get recent changelog entries (newest first)."""
        results, _ = self.client.scroll(
            collection_name=self.CHANGELOG_COLLECTION,
            limit=limit,
            with_payload=True,
        )

        entries = [ChangeLogEntry(**point.payload) for point in results]
        # Sort by timestamp descending
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def search_changelog(self, query: str, limit: int = 10) -> list[ChangeLogEntry]:
        """Search changelog entries."""
        vector = self.encoder.encode(query).tolist()

        results = self.client.query_points(
            collection_name=self.CHANGELOG_COLLECTION,
            query=vector,
            limit=limit,
        )

        return [ChangeLogEntry(**hit.payload) for hit in results.points]
