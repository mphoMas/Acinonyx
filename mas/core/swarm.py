"""
mas.core.swarm: Multi-Host Swarm Relay Topology for Distributed EventBus Communication.
Connects multiple MAS worker nodes across network boundaries using authenticated,
high-throughput asynchronous stream relays.

Architect: Acinonyx
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from mas.core.message import Message

logger = logging.getLogger("mas.swarm")


@dataclass
class SwarmNodeInfo:
    node_id: str
    host: str
    port: int
    subscribed_topics: List[str] = field(default_factory=lambda: ["*"])
    connected_at: float = field(default=0.0)


class SwarmHub:
    """
    Central or Regional Relay Hub that orchestrates multi-host agent communication.
    Authenticates worker nodes, routes topic-targeted messages, and maintains connection states.
    """

    def __init__(self, auth_token: str = "acinonyx-swarm-secret-key") -> None:
        self.auth_token = auth_token
        self._server: Optional[asyncio.Server] = None
        self._nodes: Dict[str, asyncio.StreamWriter] = {}
        self._node_info: Dict[str, SwarmNodeInfo] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._messages_relayed: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def connected_node_count(self) -> int:
        return len(self._nodes)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "connected_nodes": list(self._nodes.keys()),
            "messages_relayed": self._messages_relayed,
            "node_details": {k: asdict(v) for k, v in self._node_info.items()},
        }

    async def start(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        """Start the async TCP relay hub server."""
        self._server = await asyncio.start_server(self._handle_client, host, port)
        self._running = True
        logger.info(f"SwarmHub active and listening on {host}:{port}")

    async def stop(self) -> None:
        """Gracefully disconnect all nodes and shut down the relay server."""
        self._running = False
        async with self._lock:
            for node_id, writer in list(self._nodes.items()):
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
            self._nodes.clear()
            self._node_info.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("SwarmHub stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        node_id: Optional[str] = None
        try:
            # 1. Read Authentication Handshake
            auth_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if not auth_line:
                writer.close()
                return

            auth_req = json.loads(auth_line.decode("utf-8"))
            if auth_req.get("auth_token") != self.auth_token:
                err_resp = json.dumps({"type": "AUTH_FAILED", "error": "Invalid auth token"}) + "\n"
                writer.write(err_resp.encode("utf-8"))
                await writer.drain()
                writer.close()
                return

            node_id = auth_req.get("node_id", f"node-{id(writer)}")
            topics = auth_req.get("topics", ["*"])

            async with self._lock:
                self._nodes[node_id] = writer
                self._node_info[node_id] = SwarmNodeInfo(
                    node_id=node_id,
                    host=str(peer[0]) if peer else "unknown",
                    port=peer[1] if peer else 0,
                    subscribed_topics=topics,
                    connected_at=asyncio.get_event_loop().time(),
                )

            # Confirm handshake
            ack = json.dumps({"type": "AUTH_OK", "node_id": node_id}) + "\n"
            writer.write(ack.encode("utf-8"))
            await writer.drain()
            logger.info(f"Node registered in swarm: {node_id} ({peer}) subscribed to {topics}")

            # 2. Main message relay loop
            while self._running:
                line = await reader.readline()
                if not line:
                    break

                raw_text = line.decode("utf-8").strip()
                if not raw_text:
                    continue

                packet = json.loads(raw_text)
                pkt_type = packet.get("type")

                if pkt_type == "PUBLISH":
                    msg_dict = packet.get("message", {})
                    topic = msg_dict.get("metadata", {}).get("topic", "*")
                    origin_node = packet.get("origin_node", node_id)

                    # Relay to matching target nodes
                    await self._broadcast_message(origin_node, topic, msg_dict)
                    self._messages_relayed += 1

                elif pkt_type == "SUBSCRIBE":
                    new_topics = packet.get("topics", [])
                    async with self._lock:
                        if node_id in self._node_info:
                            self._node_info[node_id].subscribed_topics = new_topics

                elif pkt_type == "PING":
                    writer.write((json.dumps({"type": "PONG"}) + "\n").encode("utf-8"))
                    await writer.drain()

        except (asyncio.IncompleteReadError, ConnectionResetError, asyncio.TimeoutError):
            pass
        except Exception as e:
            logger.warning(f"Error handling swarm node {node_id}: {e}")
        finally:
            if node_id:
                async with self._lock:
                    self._nodes.pop(node_id, None)
                    self._node_info.pop(node_id, None)
                logger.info(f"Node disconnected from swarm: {node_id}")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _broadcast_message(self, origin_node: str, topic: str, msg_dict: Dict[str, Any]) -> None:
        """Route a message to all connected worker nodes whose subscription matches topic."""
        payload = json.dumps({
            "type": "RELAY",
            "topic": topic,
            "origin_node": origin_node,
            "message": msg_dict,
        }) + "\n"
        encoded = payload.encode("utf-8")

        async with self._lock:
            for dest_id, writer in list(self._nodes.items()):
                if dest_id == origin_node:
                    continue  # Do not echo back to origin node

                info = self._node_info.get(dest_id)
                if not info:
                    continue

                # Check topic subscription
                matches = ("*" in info.subscribed_topics) or (topic in info.subscribed_topics)
                if matches:
                    try:
                        writer.write(encoded)
                        await writer.drain()
                    except Exception as e:
                        logger.warning(f"Failed to relay message to node {dest_id}: {e}")


class SwarmNode:
    """
    Client agent running on a worker host. Connects to the SwarmHub and bridges
    messages bi-directionally with a local EventBus.
    """

    def __init__(
        self,
        node_id: str,
        auth_token: str = "acinonyx-swarm-secret-key",
        subscribed_topics: Optional[List[str]] = None,
    ) -> None:
        self.node_id = node_id
        self.auth_token = auth_token
        self.subscribed_topics = subscribed_topics or ["*"]
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._connected = False
        self._event_bus = None
        self._messages_sent: int = 0
        self._messages_received: int = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "connected": self._connected,
            "subscribed_topics": self.subscribed_topics,
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
        }

    def bind_event_bus(self, event_bus) -> None:
        """Attach local EventBus to bridge with the distributed swarm."""
        self._event_bus = event_bus
        if hasattr(event_bus, "attach_swarm"):
            event_bus.attach_swarm(self)

    async def connect(self, hub_host: str = "127.0.0.1", hub_port: int = 8765) -> bool:
        """Establish connection to the remote SwarmHub and authenticate."""
        try:
            self._reader, self._writer = await asyncio.open_connection(hub_host, hub_port)

            # Handshake
            auth_req = {
                "auth_token": self.auth_token,
                "node_id": self.node_id,
                "topics": self.subscribed_topics,
            }
            self._writer.write((json.dumps(auth_req) + "\n").encode("utf-8"))
            await self._writer.drain()

            # Await acknowledgement
            resp_line = await asyncio.wait_for(self._reader.readline(), timeout=5.0)
            if not resp_line:
                self.disconnect()
                return False

            resp = json.loads(resp_line.decode("utf-8"))
            if resp.get("type") != "AUTH_OK":
                logger.error(f"Swarm authentication rejected: {resp}")
                self.disconnect()
                return False

            self._connected = True
            self._listen_task = asyncio.create_task(self._listen_loop())
            logger.info(f"SwarmNode {self.node_id} successfully linked to SwarmHub at {hub_host}:{hub_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect SwarmNode to {hub_host}:{hub_port}: {e}")
            self.disconnect()
            return False

    def disconnect(self) -> None:
        """Disconnect node from swarm hub."""
        self._connected = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
        if self._writer:
            try:
                self._writer.close()
            except Exception:
                pass
            self._writer = None
        self._reader = None

    async def publish_to_swarm(self, message: Message) -> None:
        """Send a locally published message out across the swarm."""
        if not self._connected or not self._writer:
            return

        packet = {
            "type": "PUBLISH",
            "origin_node": self.node_id,
            "message": message.to_dict(),
        }
        encoded = (json.dumps(packet) + "\n").encode("utf-8")
        try:
            self._writer.write(encoded)
            await self._writer.drain()
            self._messages_sent += 1
        except Exception as e:
            logger.warning(f"Error publishing to swarm hub: {e}")

    async def _listen_loop(self) -> None:
        """Background task receiving incoming relayed messages from SwarmHub."""
        while self._connected and self._reader:
            try:
                line = await self._reader.readline()
                if not line:
                    break

                raw = line.decode("utf-8").strip()
                if not raw:
                    continue

                packet = json.loads(raw)
                if packet.get("type") == "RELAY":
                    msg_dict = packet.get("message", {})
                    if self._event_bus:
                        if "metadata" not in msg_dict or not isinstance(msg_dict["metadata"], dict):
                            msg_dict["metadata"] = {}
                        if "extra" not in msg_dict["metadata"] or not isinstance(msg_dict["metadata"]["extra"], dict):
                            msg_dict["metadata"]["extra"] = {}
                        msg_dict["metadata"]["extra"]["swarm_replicated"] = True
                        msg = Message.from_dict(msg_dict)
                        await self._event_bus.publish(msg)
                    self._messages_received += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Swarm listener error on node {self.node_id}: {e}")
                break

        self.disconnect()
