"""
Tests for mas.memory (WorkingMemory, EpisodicMemory, and Reflexion).
"""

import unittest
from mas.core.message import Message, Role
from mas.memory.working import WorkingMemory
from mas.memory.episodic import EpisodicMemory


class TestMemorySubsystems(unittest.TestCase):

    def test_working_memory_sliding_window_and_pinned(self):
        evicted_items = []

        def on_evict(msgs):
            evicted_items.extend(msgs)

        wm = WorkingMemory(capacity=3, eviction_callback=on_evict)

        # Pin a system prompt
        sys_msg = Message(role=Role.SYSTEM, content="System Prompt Instructions")
        wm.add(sys_msg, pin=True)

        # Add messages up to and exceeding capacity
        m1 = Message(content="Msg 1")
        m2 = Message(content="Msg 2")
        m3 = Message(content="Msg 3")
        m4 = Message(content="Msg 4")

        wm.add(m1)
        wm.add(m2)
        wm.add(m3)
        self.assertEqual(len(evicted_items), 0)

        # Adding 4th should evict m1
        wm.add(m4)
        self.assertEqual(len(evicted_items), 1)
        self.assertEqual(evicted_items[0].content, "Msg 1")

        # Context must still have pinned system message + m2, m3, m4
        ctx = wm.get_context()
        self.assertEqual(len(ctx), 4)
        self.assertEqual(ctx[0].content, "System Prompt Instructions")
        self.assertEqual(ctx[1].content, "Msg 2")
        self.assertEqual(ctx[2].content, "Msg 3")
        self.assertEqual(ctx[3].content, "Msg 4")

    def test_episodic_memory_reflection_retrieval(self):
        em = EpisodicMemory()

        em.record_reflection(
            task="Optimize database query performance",
            success=False,
            critique="Full table scan on large dataset caused timeout.",
            suggested_strategy="Create composite index on (user_id, created_at).",
            tags=["database", "sql", "performance"],
        )

        em.record_reflection(
            task="Design API authentication middleware",
            success=True,
            critique="JWT signature verification is secure and fast.",
            suggested_strategy="Use RS256 with rotating public keys.",
            tags=["auth", "api", "security"],
        )

        # Retrieve relevant reflections for SQL task
        reflections = em.retrieve_relevant_reflections("slow database query optimization", limit=2)
        self.assertGreater(len(reflections), 0)
        self.assertEqual(reflections[0].task, "Optimize database query performance")
        self.assertIn("composite index", reflections[0].suggested_strategy)

        # Prompt formatting
        prompt_block = em.format_reflections_for_prompt("database query")
        self.assertIn("Past Reflections & Lessons Learned", prompt_block)
        self.assertIn("Full table scan", prompt_block)


if __name__ == "__main__":
    unittest.main()
