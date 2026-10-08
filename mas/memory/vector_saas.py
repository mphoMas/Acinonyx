"""
mas.memory.vector_saas: External Managed Vector Database Adapters.
Provides local simulations of Vertex AI Vector Search, Pinecone and Qdrant.
These adapters do not connect to remote services or provide durable storage.

Architect: Acinonyx / Data & AI Architecture Directorate
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class VectorProvider(str, Enum):
    VERTEX_AI = "vertex_ai"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    MOCK = "mock"


@dataclass
class VectorRecord:
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    text_content: Optional[str] = None


@dataclass
class VectorQueryResult:
    id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    text_content: Optional[str] = None


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes exact cosine similarity between two float vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class BaseManagedVectorStore(ABC):
    """Abstract interface for external managed vector SaaS providers."""

    @abstractmethod
    def upsert(self, records: List[VectorRecord], namespace: Optional[str] = None) -> int:
        pass

    @abstractmethod
    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[VectorQueryResult]:
        pass

    @abstractmethod
    def delete(self, ids: List[str], namespace: Optional[str] = None) -> int:
        pass

    @abstractmethod
    def describe_index(self) -> Dict[str, Any]:
        pass


class MockManagedVectorStore(BaseManagedVectorStore):
    """
    In-memory, zero-dependency managed vector store simulation.
    Used for local sandbox verification, test suites, and offline dev runs.
    """

    def __init__(self, dimension: int = 64, index_name: str = "acinonyx-mock-index") -> None:
        self.dimension = dimension
        self.index_name = index_name
        self._storage: Dict[str, Dict[str, VectorRecord]] = {"default": {}}  # namespace -> id -> record

    def _get_namespace(self, ns: Optional[str]) -> Dict[str, VectorRecord]:
        ns_key = ns or "default"
        return self._storage.setdefault(ns_key, {})

    def upsert(self, records: List[VectorRecord], namespace: Optional[str] = None) -> int:
        store = self._get_namespace(namespace)
        count = 0
        for rec in records:
            store[rec.id] = rec
            count += 1
        return count

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[VectorQueryResult]:
        store = self._get_namespace(namespace)
        scored: List[VectorQueryResult] = []

        for rec in store.values():
            # Apply metadata filters if provided
            if filter_criteria:
                match = all(rec.metadata.get(k) == v for k, v in filter_criteria.items())
                if not match:
                    continue

            score = cosine_similarity(vector, rec.vector)
            scored.append(
                VectorQueryResult(
                    id=rec.id,
                    score=score,
                    metadata=rec.metadata,
                    text_content=rec.text_content,
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def delete(self, ids: List[str], namespace: Optional[str] = None) -> int:
        store = self._get_namespace(namespace)
        deleted = 0
        for r_id in ids:
            if r_id in store:
                del store[r_id]
                deleted += 1
        return deleted

    def describe_index(self) -> Dict[str, Any]:
        total_vectors = sum(len(v) for v in self._storage.values())
        return {
            "provider": VectorProvider.MOCK.value,
            "index_name": self.index_name,
            "dimension": self.dimension,
            "total_records": total_vectors,
            "namespaces": list(self._storage.keys()),
            "status": "SIMULATED",
            "mode": "simulated",
            "backend_provider": "mock",
            "persistent": False,
        }


class VertexAIVectorSearchAdapter(BaseManagedVectorStore):
    """
    Google Cloud Vertex AI Vector Search (formerly Matching Engine) Adapter.
    Supports index endpoints, Private Service Connect (PSC), and tree-AH algorithms.
    """

    def __init__(
        self,
        project_id: str = "acinonyx-enterprise-prod",
        region: str = "us-central1",
        index_endpoint_id: str = "endpoint-001",
        deployed_index_id: str = "acinonyx_deployed_index",
        fallback_store: Optional[BaseManagedVectorStore] = None,
    ) -> None:
        self.project_id = project_id
        self.region = region
        self.index_endpoint_id = index_endpoint_id
        self.deployed_index_id = deployed_index_id
        # Resilient local fallback store when live cloud connection is simulated/offline
        self._fallback = fallback_store or MockManagedVectorStore(dimension=768, index_name="vertex-ai-mirror")

    def upsert(self, records: List[VectorRecord], namespace: Optional[str] = None) -> int:
        return self._fallback.upsert(records, namespace)

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[VectorQueryResult]:
        return self._fallback.query(vector, top_k, namespace, filter_criteria)

    def delete(self, ids: List[str], namespace: Optional[str] = None) -> int:
        return self._fallback.delete(ids, namespace)

    def describe_index(self) -> Dict[str, Any]:
        base_desc = self._fallback.describe_index()
        base_desc.update({
            "provider": VectorProvider.VERTEX_AI.value,
            "project_id": self.project_id,
            "region": self.region,
            "index_endpoint_id": self.index_endpoint_id,
            "deployed_index_id": self.deployed_index_id,
            "psc_enabled": False,
        })
        return base_desc


class PineconeAdapter(BaseManagedVectorStore):
    """Pinecone serverless vector database adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: str = "acinonyx-core",
        dimension: int = 1536,
        fallback_store: Optional[BaseManagedVectorStore] = None,
    ) -> None:
        self.api_key = api_key or "mock-pinecone-key"
        self.index_name = index_name
        self.dimension = dimension
        self._fallback = fallback_store or MockManagedVectorStore(dimension=dimension, index_name=index_name)

    def upsert(self, records: List[VectorRecord], namespace: Optional[str] = None) -> int:
        return self._fallback.upsert(records, namespace)

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[VectorQueryResult]:
        return self._fallback.query(vector, top_k, namespace, filter_criteria)

    def delete(self, ids: List[str], namespace: Optional[str] = None) -> int:
        return self._fallback.delete(ids, namespace)

    def describe_index(self) -> Dict[str, Any]:
        base_desc = self._fallback.describe_index()
        base_desc.update({
            "provider": VectorProvider.PINECONE.value,
            "index_name": self.index_name,
            "dimension": self.dimension,
            "serverless": False,
        })
        return base_desc


class QdrantAdapter(BaseManagedVectorStore):
    """Qdrant high-performance vector search engine adapter."""

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "acinonyx_collection",
        dimension: int = 1536,
        fallback_store: Optional[BaseManagedVectorStore] = None,
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.dimension = dimension
        self._fallback = fallback_store or MockManagedVectorStore(dimension=dimension, index_name=collection_name)

    def upsert(self, records: List[VectorRecord], namespace: Optional[str] = None) -> int:
        return self._fallback.upsert(records, namespace)

    def query(
        self,
        vector: List[float],
        top_k: int = 5,
        namespace: Optional[str] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[VectorQueryResult]:
        return self._fallback.query(vector, top_k, namespace, filter_criteria)

    def delete(self, ids: List[str], namespace: Optional[str] = None) -> int:
        return self._fallback.delete(ids, namespace)

    def describe_index(self) -> Dict[str, Any]:
        base_desc = self._fallback.describe_index()
        base_desc.update({
            "provider": VectorProvider.QDRANT.value,
            "url": self.url,
            "collection_name": self.collection_name,
            "dimension": self.dimension,
        })
        return base_desc


class ManagedVectorStoreFactory:
    """Factory creating configured managed vector store adapters."""

    @staticmethod
    def create(
        provider: str = VectorProvider.MOCK.value,
        dimension: int = 64,
        index_name: str = "acinonyx-vectors",
        **kwargs: Any,
    ) -> BaseManagedVectorStore:
        prov = provider.lower()
        if prov == VectorProvider.VERTEX_AI.value:
            return VertexAIVectorSearchAdapter(
                project_id=kwargs.get("project_id", "acinonyx-enterprise-prod"),
                region=kwargs.get("region", "us-central1"),
                index_endpoint_id=kwargs.get("index_endpoint_id", "endpoint-001"),
                deployed_index_id=kwargs.get("deployed_index_id", index_name),
            )
        elif prov == VectorProvider.PINECONE.value:
            return PineconeAdapter(
                api_key=kwargs.get("api_key"),
                index_name=index_name,
                dimension=dimension,
            )
        elif prov == VectorProvider.QDRANT.value:
            return QdrantAdapter(
                url=kwargs.get("url", "http://localhost:6333"),
                collection_name=index_name,
                dimension=dimension,
            )
        else:
            return MockManagedVectorStore(dimension=dimension, index_name=index_name)
