"""
mas.memory.episodic: Persistent trajectory logging and Reflexion self-correction memory
powered by an embedded pure-Python / SQLite semantic vector database.

Architect: Acinonyx
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import struct
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from mas.core.message import Message


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Reflection:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    success: bool = False
    critique: str = ""
    suggested_strategy: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)
    similarity_score: float = 0.0


@dataclass
class Trajectory:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    steps: List[Message] = field(default_factory=list)
    success: bool = False
    reflections: List[Reflection] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pure Python Semantic Vectorizer (Subword N-Gram Cosine Space)
# ---------------------------------------------------------------------------

class SemanticVectorizer:
    """
    Zero-dependency, high-precision dense vectorizer operating in L2-normalized cosine space.
    Uses subword n-gram hashing and term weighting to generate continuous semantic embeddings
    without requiring external model weights or GPU acceleration.
    """

    DEFAULT_DIM: int = 512
    STOPWORDS = {'a', 'an', 'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are'}

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self.dim = dim

    def _hash_feature(self, feature: str) -> int:
        """Deterministic 32-bit FNV-1a hash to vector bucket."""
        h = 2166136261
        for b in feature.encode("utf-8"):
            h = ((h ^ b) * 16777619) & 0xFFFFFFFF
        return h % self.dim

    def embed(self, text: str) -> List[float]:
        """
        Generate a normalized dense vector for the input text.
        Combines words, subwords, and bigrams in L2-normalized cosine space.
        """
        if not text or not text.strip():
            return [0.0] * self.dim

        vec = [0.0] * self.dim
        clean_text = text.lower().strip()
        words = [w for w in re.findall(r"\b\w+\b", clean_text) if w not in self.STOPWORDS]

        # 1. Whole-word features (primary semantic anchors)
        for w in words:
            h = self._hash_feature(f"w:{w}")
            vec[h] += 8.0

            # Subword 4-grams for roots/inflections
            if len(w) >= 4:
                for i in range(len(w) - 3):
                    h4 = self._hash_feature(f"4:{w[i : i + 4]}")
                    vec[h4] += 0.8

        # 2. Word bi-grams for composite phrase semantics
        for i in range(len(words) - 1):
            h_bi = self._hash_feature(f"bi:{words[i]}_{words[i + 1]}")
            vec[h_bi] += 4.0

        # 3. L2 Normalization (so dot product equals cosine similarity)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-12:
            vec = [v / norm for v in vec]
        return vec

    def pack_vector(self, vec: List[float]) -> bytes:
        """Serialize float vector into a binary BLOB."""
        return struct.pack(f"{len(vec)}f", *vec)

    def unpack_vector(self, blob: bytes) -> List[float]:
        """Deserialize float vector from a binary BLOB."""
        count = len(blob) // 4
        return list(struct.unpack(f"{count}f", blob))

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two unit vectors (dot product)."""
        if len(vec1) != len(vec2):
            return 0.0
        return sum(a * b for a, b in zip(vec1, vec2))


# ---------------------------------------------------------------------------
# SQLite Vector Database Engine
# ---------------------------------------------------------------------------

class SQLiteVectorDatabase:
    """
    ACID transactional SQLite vector database for storing and querying
    reflections, trajectories, and semantic embeddings with SQL-native k-NN.
    """

    def __init__(self, db_path: str = ":memory:", dim: int = SemanticVectorizer.DEFAULT_DIM) -> None:
        self.db_path = db_path
        self.dim = dim
        self.vectorizer = SemanticVectorizer(dim=dim)

        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._register_functions()
        self._create_schema()

    def _register_functions(self) -> None:
        """Register custom SQLite function for computing cosine similarity in SQL."""
        dim = self.dim

        def _sql_cosine_sim(b1: Optional[bytes], b2: Optional[bytes]) -> float:
            if not b1 or not b2:
                return 0.0
            try:
                v1 = struct.unpack(f"{dim}f", b1)
                v2 = struct.unpack(f"{dim}f", b2)
                return float(sum(x * y for x, y in zip(v1, v2)))
            except Exception:
                return 0.0

        self._conn.create_function("cosine_sim", 2, _sql_cosine_sim)

    def _create_schema(self) -> None:
        with self._conn:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    critique TEXT NOT NULL,
                    suggested_strategy TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trajectories (
                    id TEXT PRIMARY KEY,
                    task TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    steps_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_refl_task ON reflections(task)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_traj_task ON trajectories(task)")

    def insert_reflection(self, reflection: Reflection, vector: Optional[List[float]] = None) -> None:
        if vector is None:
            # Semantic composite representation
            embed_text = f"{reflection.task} {' '.join(reflection.tags)} {reflection.critique} {reflection.suggested_strategy}"
            vector = self.vectorizer.embed(embed_text)

        packed = self.vectorizer.pack_vector(vector)
        tags_str = json.dumps(reflection.tags)

        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO reflections 
                (id, task, success, critique, suggested_strategy, tags_json, timestamp, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reflection.id,
                    reflection.task,
                    1 if reflection.success else 0,
                    reflection.critique,
                    reflection.suggested_strategy,
                    tags_str,
                    reflection.timestamp,
                    packed,
                ),
            )

    def insert_trajectory(self, trajectory: Trajectory) -> None:
        steps_dicts = [m.to_dict() for m in trajectory.steps]
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO trajectories
                (id, task, success, steps_json, timestamp, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    trajectory.id,
                    trajectory.task,
                    1 if trajectory.success else 0,
                    json.dumps(steps_dicts),
                    trajectory.timestamp,
                    json.dumps(trajectory.metadata),
                ),
            )
        # Also store associated reflections
        for r in trajectory.reflections:
            self.insert_reflection(r)

    def search_reflections(self, query: str, limit: int = 3, threshold: float = 0.0) -> List[Reflection]:
        """SQL k-NN vector search using cosine similarity function."""
        query_vec = self.vectorizer.embed(query)
        query_blob = self.vectorizer.pack_vector(query_vec)

        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, task, success, critique, suggested_strategy, tags_json, timestamp,
                   cosine_sim(embedding, ?) AS similarity
            FROM reflections
            WHERE similarity >= ?
            ORDER BY similarity DESC
            LIMIT ?
            """,
            (query_blob, threshold, limit),
        )

        rows = cursor.fetchall()
        results = []
        for row in rows:
            r_id, task, succ, critique, strat, tags_json, ts, sim = row
            try:
                tags = json.loads(tags_json)
            except Exception:
                tags = []
            results.append(
                Reflection(
                    id=r_id,
                    task=task,
                    success=bool(succ),
                    critique=critique,
                    suggested_strategy=strat,
                    timestamp=ts,
                    tags=tags,
                    similarity_score=round(float(sim), 4),
                )
            )
        return results

    def count_reflections(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reflections")
        return cur.fetchone()[0]

    def count_trajectories(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trajectories")
        return cur.fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "SQLiteVectorDatabase":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Episodic Memory (High-Level Façade)
# ---------------------------------------------------------------------------

class EpisodicMemory:
    """
    Episodic memory store recording execution trajectories and verbal reflections.
    Powered by an embedded SQLite Vector Database with semantic cosine similarity search.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
    ) -> None:
        self.vector_db = SQLiteVectorDatabase(db_path=db_path)
        self.embedding_fn = embedding_fn

    def record_trajectory(self, trajectory: Trajectory) -> None:
        """Record an execution trajectory and its associated reflections."""
        self.vector_db.insert_trajectory(trajectory)

    def record_reflection(
        self,
        task: str,
        success: bool,
        critique: str,
        suggested_strategy: str,
        tags: Optional[List[str]] = None,
    ) -> Reflection:
        """Persist a verbal self-reflection into the vector database."""
        reflection = Reflection(
            task=task,
            success=success,
            critique=critique,
            suggested_strategy=suggested_strategy,
            tags=tags or [],
        )

        custom_vec = None
        if self.embedding_fn:
            text = f"{task} {' '.join(reflection.tags)} {critique} {suggested_strategy}"
            custom_vec = self.embedding_fn(text)

        self.vector_db.insert_reflection(reflection, vector=custom_vec)
        return reflection

    def retrieve_relevant_reflections(self, query: str, limit: int = 3) -> List[Reflection]:
        """
        True semantic vector retrieval: finds reflections conceptually most relevant
        to the query using dense cosine similarity in SQLite.
        """
        return self.vector_db.search_reflections(query, limit=limit, threshold=-1.0)

    def format_reflections_for_prompt(self, query: str, limit: int = 3) -> str:
        """Format retrieved lessons into an injected prompt section for agent self-correction."""
        reflections = self.retrieve_relevant_reflections(query, limit)
        if not reflections:
            return ""

        lines = ["### Past Reflections & Lessons Learned:"]
        for idx, r in enumerate(reflections, 1):
            status = "SUCCESS" if r.success else "FAILURE"
            score_str = f" (Semantic Relevance: {r.similarity_score:.2f})" if r.similarity_score > 0 else ""
            lines.append(f"{idx}. [{status}]{score_str} Task: {r.task}")
            lines.append(f"   Critique: {r.critique}")
            lines.append(f"   Adjustment Strategy: {r.suggested_strategy}")
        return "\n".join(lines)

    @property
    def total_trajectories(self) -> int:
        return self.vector_db.count_trajectories()

    @property
    def total_reflections(self) -> int:
        return self.vector_db.count_reflections()
