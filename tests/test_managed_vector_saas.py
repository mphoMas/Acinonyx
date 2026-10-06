"""
tests/test_managed_vector_saas.py: Test suite for Managed Vector Database SaaS Adapters.
Tests vector indexing, cosine similarity scoring, metadata filtering, and adapter factory.
"""

import pytest
from mas.memory.vector_saas import (
    BaseManagedVectorStore,
    ManagedVectorStoreFactory,
    MockManagedVectorStore,
    PineconeAdapter,
    QdrantAdapter,
    VectorProvider,
    VectorQueryResult,
    VectorRecord,
    VertexAIVectorSearchAdapter,
    cosine_similarity,
)


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0

    v_orth = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v_orth)) == 0.0

    v_opp = [-1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v_opp)) == -1.0


def test_mock_managed_vector_store():
    store = MockManagedVectorStore(dimension=3)

    records = [
        VectorRecord(id="doc-1", vector=[1.0, 0.0, 0.0], metadata={"category": "ai"}, text_content="AI systems"),
        VectorRecord(id="doc-2", vector=[0.0, 1.0, 0.0], metadata={"category": "infra"}, text_content="Cloud infra"),
        VectorRecord(id="doc-3", vector=[0.7, 0.7, 0.0], metadata={"category": "ai"}, text_content="Agent infra"),
    ]

    count = store.upsert(records, namespace="tenant-1")
    assert count == 3

    # Query with query vector close to doc-1
    results = store.query([0.9, 0.1, 0.0], top_k=2, namespace="tenant-1")
    assert len(results) == 2
    assert results[0].id == "doc-1"
    assert results[0].score > 0.9

    # Query with metadata filter
    filtered = store.query([0.0, 1.0, 0.0], top_k=5, namespace="tenant-1", filter_criteria={"category": "infra"})
    assert len(filtered) == 1
    assert filtered[0].id == "doc-2"

    # Delete
    del_count = store.delete(["doc-2"], namespace="tenant-1")
    assert del_count == 1
    desc = store.describe_index()
    assert desc["total_records"] == 2


def test_managed_vector_store_factory_and_adapters():
    # 1. Mock provider
    mock_store = ManagedVectorStoreFactory.create(provider="mock", dimension=128)
    assert isinstance(mock_store, MockManagedVectorStore)

    # 2. Vertex AI provider
    vertex_store = ManagedVectorStoreFactory.create(
        provider="vertex_ai",
        project_id="test-proj",
        region="europe-west1",
        index_name="test-index",
    )
    assert isinstance(vertex_store, VertexAIVectorSearchAdapter)
    desc = vertex_store.describe_index()
    assert desc["provider"] == "vertex_ai"
    assert desc["psc_enabled"] is True

    # 3. Pinecone provider
    pinecone_store = ManagedVectorStoreFactory.create(
        provider="pinecone",
        api_key="pk-secret",
        index_name="test-pinecone",
        dimension=1536,
    )
    assert isinstance(pinecone_store, PineconeAdapter)
    assert pinecone_store.describe_index()["serverless"] is True

    # 4. Qdrant provider
    qdrant_store = ManagedVectorStoreFactory.create(
        provider="qdrant",
        url="http://qdrant.cluster.local:6333",
        index_name="test-qdrant",
    )
    assert isinstance(qdrant_store, QdrantAdapter)
    assert qdrant_store.describe_index()["provider"] == "qdrant"
