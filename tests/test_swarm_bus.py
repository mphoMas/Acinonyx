"""
tests/test_swarm_bus.py: Unit and Integration tests for Multi-Host Swarm Relay Topology.
Tests distributed event bus bridging, multi-node pub/sub, authentication, and loop prevention.

Architect: Acinonyx
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mas.core.event_bus import EventBus
from mas.core.message import Message, MessageMetadata
from mas.core.swarm import SwarmHub, SwarmNode


class TestSwarmTopology(unittest.IsolatedAsyncioTestCase):
    HUB_PORT = 19876

    async def asyncSetUp(self):
        self.hub = SwarmHub(auth_token="test-secret-token")
        await self.hub.start(host="127.0.0.1", port=self.HUB_PORT)

    async def asyncTearDown(self):
        await self.hub.stop()

    async def test_hub_running_and_stats(self):
        self.assertTrue(self.hub.is_running)
        self.assertEqual(self.hub.connected_node_count, 0)
        self.assertIn("connected_nodes", self.hub.stats)

    async def test_unauthorized_node_rejected(self):
        node = SwarmNode(node_id="rogue-node", auth_token="wrong-token")
        connected = await node.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)
        self.assertFalse(connected)
        self.assertFalse(node.is_connected)

    async def test_authorized_node_connect_and_disconnect(self):
        node = SwarmNode(node_id="worker-1", auth_token="test-secret-token")
        connected = await node.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)
        self.assertTrue(connected)
        self.assertTrue(node.is_connected)
        self.assertEqual(self.hub.connected_node_count, 1)

        node.disconnect()
        await asyncio.sleep(0.05)
        self.assertFalse(node.is_connected)

    async def test_multi_node_topic_routed_broadcast(self):
        # Node A: Publisher
        node_a = SwarmNode(node_id="node-a", auth_token="test-secret-token")
        await node_a.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)

        # Node B: Subscribed to wildcard *
        node_b = SwarmNode(node_id="node-b", auth_token="test-secret-token", subscribed_topics=["*"])
        bus_b = EventBus()
        node_b.bind_event_bus(bus_b)
        await node_b.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)

        # Node C: Subscribed only to 'fintech.*'
        node_c = SwarmNode(node_id="node-c", auth_token="test-secret-token", subscribed_topics=["fintech.transactions"])
        bus_c = EventBus()
        node_c.bind_event_bus(bus_c)
        await node_c.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)

        # Collect messages on B and C
        received_b = []
        received_c = []

        async def handler_b(msg: Message):
            received_b.append(msg)

        async def handler_c(msg: Message):
            received_c.append(msg)

        bus_b.subscribe("sub-b", handler_b, topic="*")
        bus_c.subscribe("sub-c", handler_c, topic="*")

        # 1. Publish matching topic
        msg1 = Message(
            sender="agent-a",
            recipient="broadcast",
            content="New Block Mined",
            metadata=MessageMetadata(topic="fintech.transactions"),
        )
        await node_a.publish_to_swarm(msg1)

        await asyncio.sleep(0.1)
        self.assertEqual(len(received_b), 1)
        self.assertEqual(len(received_c), 1)
        self.assertEqual(received_b[0].content, "New Block Mined")
        self.assertEqual(received_c[0].content, "New Block Mined")

        # 2. Publish non-matching topic for C (e.g. devops.deploy)
        msg2 = Message(
            sender="agent-a",
            recipient="broadcast",
            content="Deploy K8s",
            metadata=MessageMetadata(topic="devops.deploy"),
        )
        await node_a.publish_to_swarm(msg2)

        await asyncio.sleep(0.1)
        self.assertEqual(len(received_b), 2)  # B received it because it's wildcard
        self.assertEqual(len(received_c), 1)  # C did NOT receive it because topic didn't match

        node_a.disconnect()
        node_b.disconnect()
        node_c.disconnect()

    async def test_bidirectional_event_bus_bridging(self):
        # Two independent EventBus instances on two different simulated worker nodes
        bus_east = EventBus()
        node_east = SwarmNode(node_id="east-datacenter", auth_token="test-secret-token")
        node_east.bind_event_bus(bus_east)
        await node_east.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)

        bus_west = EventBus()
        node_west = SwarmNode(node_id="west-datacenter", auth_token="test-secret-token")
        node_west.bind_event_bus(bus_west)
        await node_west.connect(hub_host="127.0.0.1", hub_port=self.HUB_PORT)

        west_inbox = []

        async def on_west_event(msg: Message):
            west_inbox.append(msg)

        bus_west.subscribe("listener-west", on_west_event, topic="*")

        # An agent on East node publishes locally
        local_msg = Message(
            sender="EastExecutive",
            recipient="broadcast",
            content="Quarterly Strategy Sync",
            metadata=MessageMetadata(topic="executive.sync"),
        )
        tasks = await bus_east.publish(local_msg)
        if tasks:
            await asyncio.gather(*tasks)

        # Allow network relay
        await asyncio.sleep(0.1)

        # West should have received East's message via swarm bridge
        self.assertEqual(len(west_inbox), 1)
        self.assertEqual(west_inbox[0].content, "Quarterly Strategy Sync")
        self.assertTrue(west_inbox[0].metadata.extra.get("swarm_replicated"))

        node_east.disconnect()
        node_west.disconnect()


if __name__ == "__main__":
    unittest.main()
