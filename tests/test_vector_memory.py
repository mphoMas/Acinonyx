"""
tests.test_vector_memory: Verification suite for embedded pure-Python / SQLite vector database.
Architect: Acinonyx
"""

import os
import shutil
import tempfile
import unittest
from mas.memory.episodic import EpisodicMemory, Reflection, SQLiteVectorDatabase, SemanticVectorizer, Trajectory


class TestSemanticVectorizer(unittest.TestCase):
    def setUp(self):
        self.vectorizer = SemanticVectorizer(dim=128)

    def test_embedding_dimensions(self):
        vec = self.vectorizer.embed("Database connection timeout")
        self.assertEqual(len(vec), 128)

    def test_l2_normalization(self):
        import math
        vec = self.vectorizer.embed("Secure HTTPS REST API with authentication")
        norm = math.sqrt(sum(v * v for v in vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_semantic_similarity_related_queries(self):
        # Similar technical concepts
        v1 = self.vectorizer.embed("User authentication token expired")
        v2 = self.vectorizer.embed("Authentication JWT token invalid")
        v3 = self.vectorizer.embed("CSS flexbox grid alignment issue")

        sim_related = self.vectorizer.cosine_similarity(v1, v2)
        sim_unrelated = self.vectorizer.cosine_similarity(v1, v3)

        self.assertGreater(
            sim_related, sim_unrelated,
            f"Expected auth tokens ({sim_related:.3f}) > auth vs css ({sim_unrelated:.3f})"
        )

    def test_pack_unpack_roundtrip(self):
        vec = self.vectorizer.embed("Roundtrip test payload")
        packed = self.vectorizer.pack_vector(vec)
        unpacked = self.vectorizer.unpack_vector(packed)
        self.assertEqual(len(vec), len(unpacked))
        for a, b in zip(vec, unpacked):
            self.assertAlmostEqual(a, b, places=5)


class TestSQLiteVectorDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_vector.db")
        self.db = SQLiteVectorDatabase(db_path=self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_insert_and_count(self):
        r = Reflection(
            task="Optimize SQL query latency",
            success=False,
            critique="Missing compound index on tenant_id and created_at",
            suggested_strategy="Add composite index to schema",
            tags=["database", "sql", "performance"],
        )
        self.db.insert_reflection(r)
        self.assertEqual(self.db.count_reflections(), 1)

    def test_sql_vector_knn_search(self):
        self.db.insert_reflection(
            Reflection(
                task="Fix Docker container out of memory error",
                success=False,
                critique="JVM heap exceeded container memory limit",
                suggested_strategy="Set -XX:MaxRAMPercentage=75.0 in Dockerfile",
                tags=["docker", "memory", "devops"],
            )
        )
        self.db.insert_reflection(
            Reflection(
                task="Stripe webhook signature verification failed",
                success=False,
                critique="Raw body was parsed before HMAC signature check",
                suggested_strategy="Verify signature using raw unparsed request body",
                tags=["fintech", "stripe", "security"],
            )
        )

        results = self.db.search_reflections("Container OOM crashed killed", limit=1)
        self.assertEqual(len(results), 1)
        self.assertIn("Docker", results[0].task)
        self.assertGreater(results[0].similarity_score, 0.0)

    def test_persistence_across_connections(self):
        self.db.insert_reflection(
            Reflection(
                task="Persistent lesson",
                success=True,
                critique="None",
                suggested_strategy="Continue standard practice",
            )
        )
        self.db.close()

        # Reopen same database file
        new_db = SQLiteVectorDatabase(db_path=self.db_path)
        self.assertEqual(new_db.count_reflections(), 1)
        new_db.close()


class TestEpisodicMemoryEndToEnd(unittest.TestCase):
    def setUp(self):
        self.memory = EpisodicMemory()

    def test_record_reflection_and_semantic_retrieval(self):
        self.memory.record_reflection(
            task="API rate limiting 429 Too Many Requests",
            success=False,
            critique="Sent bursts without exponential backoff",
            suggested_strategy="Implement jittered exponential backoff retry loop",
            tags=["api", "rate_limit", "resilience"],
        )
        self.memory.record_reflection(
            task="React frontend button re-rendering",
            success=True,
            critique="Memoized with useCallback",
            suggested_strategy="Use React.memo on child components",
            tags=["frontend", "react", "performance"],
        )

        # Query using semantically synonymous words
        retrieved = self.memory.retrieve_relevant_reflections(
            "HTTP 429 throttling too many calls", limit=1
        )
        self.assertEqual(len(retrieved), 1)
        self.assertIn("rate limiting", retrieved[0].task)
        self.assertGreater(retrieved[0].similarity_score, 0.0)

    def test_format_reflections_for_prompt(self):
        self.memory.record_reflection(
            task="SQL injection vulnerability",
            success=False,
            critique="Raw string formatting in SQL clause",
            suggested_strategy="Always use parameterized prepared statements",
            tags=["security", "sql"],
        )

        prompt_section = self.memory.format_reflections_for_prompt("Database security vulnerability")
        self.assertIn("### Past Reflections & Lessons Learned:", prompt_section)
        self.assertIn("SQL injection vulnerability", prompt_section)
        self.assertIn("parameterized prepared statements", prompt_section)
        self.assertIn("Semantic Relevance", prompt_section)


if __name__ == "__main__":
    unittest.main()
