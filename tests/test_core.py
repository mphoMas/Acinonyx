"""
Tests for mas.core (Message, EventBus, StateMachine, BaseAgent).
"""

import asyncio
import unittest
from mas.core.message import Message, Role, TokenUsage, MessageMetadata
from mas.core.event_bus import EventBus
from mas.core.state import StateMachine
from mas.core.agent import BaseAgent


class TestCorePrimitives(unittest.IsolatedAsyncioTestCase):

    def test_message_serialization(self):
        msg = Message(
            sender="architect",
            recipient="engineer",
            role=Role.ASSISTANT,
            content="Build the micro-kernel.",
            token_usage=TokenUsage.from_counts(prompt=10, completion=20),
        )
        self.assertEqual(msg.token_usage.total_tokens, 30)

        # To dict and from dict
        d = msg.to_dict()
        reconstructed = Message.from_dict(d)
        self.assertEqual(reconstructed.id, msg.id)
        self.assertEqual(reconstructed.content, msg.content)
        self.assertEqual(reconstructed.token_usage.total_tokens, 30)

        # JSON serialization
        json_str = msg.to_json()
        from_json_msg = Message.from_json(json_str)
        self.assertEqual(from_json_msg.id, msg.id)

        # Causal reply
        reply = msg.create_reply(sender="engineer", content="Acknowledged.")
        self.assertEqual(reply.metadata.parent_id, msg.id)
        self.assertEqual(reply.recipient, "architect")

    async def test_event_bus_routing(self):
        bus = EventBus(log_history=True)
        received_messages = []

        async def agent_callback(msg: Message):
            received_messages.append(msg)

        bus.subscribe("agent_1", agent_callback, topic="engineering")

        # 1. Publish to target topic
        msg1 = Message(
            sender="supervisor",
            recipient="agent_1",
            content="Task 1",
            metadata=MessageMetadata(topic="engineering"),
        )
        tasks = await bus.publish(msg1)
        await asyncio.gather(*tasks)

        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].content, "Task 1")

        # 2. Publish to different topic - should not be received
        msg2 = Message(
            sender="supervisor",
            recipient="agent_1",
            content="Task 2",
            metadata=MessageMetadata(topic="marketing"),
        )
        tasks = await bus.publish(msg2)
        await asyncio.gather(*tasks)
        self.assertEqual(len(received_messages), 1)

        # Check stats & history
        self.assertEqual(bus.stats["published_count"], 2)
        self.assertEqual(len(bus.get_history()), 2)

    def test_state_machine_checkpoint_and_rollback(self):
        sm = StateMachine({"counter": 0, "status": "idle"})
        self.assertEqual(sm.get("counter"), 0)

        sm.set("counter", 1)
        sm.commit_checkpoint("cp_1")

        sm.update({"counter": 5, "status": "running"})
        self.assertEqual(sm.get("counter"), 5)
        self.assertEqual(sm.get("status"), "running")

        # Rollback
        success = sm.rollback_to_checkpoint("cp_1")
        self.assertTrue(success)
        self.assertEqual(sm.get("counter"), 1)
        self.assertEqual(sm.get("status"), "idle")

    async def test_base_agent_lifecycle(self):
        bus = EventBus()
        agent = BaseAgent(name="worker_1", role=Role.ASSISTANT)
        agent.attach_event_bus(bus, topic="tasks")

        task_msg = Message(
            sender="supervisor",
            recipient="worker_1",
            content="Process data batch #42",
            metadata=MessageMetadata(topic="tasks"),
        )

        response = await agent.step(task_msg)
        self.assertIn("Processed[worker_1]", response.content)
        self.assertEqual(response.recipient, "supervisor")

        # Working memory should have pinned system msg + incoming + outgoing
        context = agent.working_memory.get_context()
        self.assertEqual(len(context), 3)


if __name__ == "__main__":
    unittest.main()
