"""
mas.mcp.transport: Transport abstractions and in-memory/stdio MCP client implementations.
Architect: Acinonyx
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from mas.mcp.protocol import JsonRpcRequest, MCPRegistry


class MCPClient:
    """
    Client interface for interacting with an MCP server instance or registry.
    """

    def __init__(self, registry: MCPRegistry) -> None:
        self.registry = registry
        self._req_counter = 0
        self._initialized = False

    def _next_id(self) -> int:
        self._req_counter += 1
        return self._req_counter

    async def initialize(self) -> Dict[str, Any]:
        req = JsonRpcRequest(
            id=self._next_id(),
            method="initialize",
            params={"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "mas-client"}},
        )
        resp = await self.registry.handle_request(req)
        if resp and resp.error:
            raise RuntimeError(f"initialize error: {resp.error.message}")
        self._initialized = True
        await self.registry.handle_request(
            JsonRpcRequest(method="notifications/initialized", params={})
        )
        return resp.result if resp else {}

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Query available tools from the server."""
        req = JsonRpcRequest(id=self._next_id(), method="tools/list")
        resp = await self.registry.handle_request(req)
        if resp and resp.error:
            raise RuntimeError(f"tools/list error: {resp.error.message}")
        return resp.result.get("tools", []) if resp and resp.result else []

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        principal: Optional[str] = None,
    ) -> str:
        """Call a specific tool by name with arguments and return text content."""
        params: Dict[str, Any] = {"name": name, "arguments": arguments or {}}
        if principal:
            params["principal"] = principal
        req = JsonRpcRequest(
            id=self._next_id(),
            method="tools/call",
            params=params,
        )
        resp = await self.registry.handle_request(req, principal=principal)
        if resp and resp.error:
            raise RuntimeError(f"Tool '{name}' error: {resp.error.message}")
        if resp and resp.result:
            contents = resp.result.get("content", [])
            return "\n".join(c.get("text", "") for c in contents if c.get("type") == "text")
        return ""

    async def list_resources(self) -> List[Dict[str, Any]]:
        req = JsonRpcRequest(id=self._next_id(), method="resources/list")
        resp = await self.registry.handle_request(req)
        if resp and resp.error:
            raise RuntimeError(f"resources/list error: {resp.error.message}")
        return resp.result.get("resources", []) if resp and resp.result else []

    async def read_resource(self, uri: str) -> str:
        req = JsonRpcRequest(
            id=self._next_id(),
            method="resources/read",
            params={"uri": uri},
        )
        resp = await self.registry.handle_request(req)
        if resp and resp.error:
            raise RuntimeError(f"Resource '{uri}' error: {resp.error.message}")
        if resp and resp.result:
            contents = resp.result.get("contents", [])
            return "\n".join(c.get("text", "") for c in contents)
        return ""

    async def list_prompts(self) -> List[Dict[str, Any]]:
        req = JsonRpcRequest(id=self._next_id(), method="prompts/list")
        resp = await self.registry.handle_request(req)
        if resp and resp.error:
            raise RuntimeError(f"prompts/list error: {resp.error.message}")
        return resp.result.get("prompts", []) if resp and resp.result else []

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        req = JsonRpcRequest(
            id=self._next_id(),
            method="prompts/get",
            params={"name": name, "arguments": arguments or {}},
        )
        resp = await self.registry.handle_request(req)
        if resp and resp.error:
            raise RuntimeError(f"Prompt '{name}' error: {resp.error.message}")
        if resp and resp.result:
            messages = resp.result.get("messages", [])
            texts = []
            for m in messages:
                content = m.get("content", {})
                if isinstance(content, dict):
                    texts.append(content.get("text", ""))
                else:
                    texts.append(str(content))
            return "\n".join(texts)
        return ""
