"""
mas.mcp.protocol: Pure-Python Model Context Protocol (MCP) JSON-RPC 2.0 specification.
Architect: Acinonyx
"""

from __future__ import annotations
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from mas.config import CONFIG
from mas.security import ToolACL, default_tool_acl, sanitize_tool_arguments


# Standard JSON-RPC 2.0 Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
APPLICATION_ERROR = -32000


@dataclass
class JsonRpcError:
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


@dataclass
class JsonRpcRequest:
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    jsonrpc: str = "2.0"

    def is_notification(self) -> bool:
        return self.id is None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            d["params"] = self.params
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JsonRpcRequest:
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid jsonrpc version, expected '2.0'")
        if "method" not in data or not isinstance(data["method"], str):
            raise ValueError("Missing or invalid 'method'")
        return cls(
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
        )


@dataclass
class JsonRpcResponse:
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[JsonRpcError] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = self.error.to_dict()
        else:
            d["result"] = self.result
        return d

    @classmethod
    def success(cls, id: Optional[Union[str, int]], result: Any) -> JsonRpcResponse:
        return cls(id=id, result=result)

    @classmethod
    def fail(cls, id: Optional[Union[str, int]], code: int, message: str, data: Any = None) -> JsonRpcResponse:
        return cls(id=id, error=JsonRpcError(code=code, message=message, data=data))


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class ResourceDefinition:
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    handler: Callable[[], Coroutine[Any, Any, str]] = field(default=None)


@dataclass
class PromptDefinition:
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    handler: Callable[..., Coroutine[Any, Any, str]] = field(default=None)


class MCPRegistry:
    """
    Registry for MCP Tools, Resources, and Prompts implementing standard JSON-RPC dispatch.
    """

    def __init__(self, tool_acl: Optional[ToolACL] = None) -> None:
        self.tools: Dict[str, ToolDefinition] = {}
        self.resources: Dict[str, ResourceDefinition] = {}
        self.prompts: Dict[str, PromptDefinition] = {}
        self.tool_acl = tool_acl if tool_acl is not None else default_tool_acl()
        self.server_info = {
            "name": "mas-mcp",
            "version": CONFIG.version,
        }
        self._initialized = False

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
        )
        self.tool_acl.default_allow.add(name)

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Synchronously execute a registered tool handler."""
        if name not in self.tools:
            raise KeyError(f"Tool '{name}' not found")
        args = arguments or {}
        tool = self.tools[name]
        if inspect.iscoroutinefunction(tool.handler):
            import asyncio
            return asyncio.run(tool.handler(**args))
        return tool.handler(**args)

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        handler: Callable[[], Coroutine[Any, Any, str]],
        mime_type: str = "text/plain",
    ) -> None:
        self.resources[uri] = ResourceDefinition(
            uri=uri,
            name=name,
            description=description,
            handler=handler,
            mime_type=mime_type,
        )

    def register_prompt(
        self,
        name: str,
        description: str,
        handler: Callable[..., Coroutine[Any, Any, str]],
        arguments: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.prompts[name] = PromptDefinition(
            name=name,
            description=description,
            arguments=arguments or [],
            handler=handler,
        )

    async def handle_request(
        self,
        request: JsonRpcRequest,
        principal: Optional[str] = None,
    ) -> Optional[JsonRpcResponse]:
        """Dispatch JSON-RPC request to appropriate MCP handler."""
        method = request.method
        params = request.params or {}

        try:
            if method == "initialize":
                self._initialized = True
                return JsonRpcResponse.success(
                    request.id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "resources": {},
                            "prompts": {},
                        },
                        "serverInfo": self.server_info,
                    },
                )

            if method == "notifications/initialized":
                self._initialized = True
                return None if request.is_notification() else JsonRpcResponse.success(request.id, {})

            # 1. Tools API
            if method == "tools/list":
                tool_list = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in self.tools.values()
                ]
                return JsonRpcResponse.success(request.id, {"tools": tool_list})

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                caller = params.get("principal") or principal
                if not tool_name or tool_name not in self.tools:
                    return JsonRpcResponse.fail(
                        request.id,
                        METHOD_NOT_FOUND,
                        f"Tool '{tool_name}' not found",
                    )

                if CONFIG.tool_acl_enabled and not self.tool_acl.is_allowed(caller, tool_name):
                    # Principals without explicit ACL still use default_allow
                    if caller and caller in self.tool_acl.principals:
                        return JsonRpcResponse.fail(
                            request.id,
                            APPLICATION_ERROR,
                            f"ACL denied tool '{tool_name}' for principal '{caller}'",
                        )
                    if tool_name not in self.tool_acl.default_allow:
                        return JsonRpcResponse.fail(
                            request.id,
                            APPLICATION_ERROR,
                            f"ACL denied tool '{tool_name}'",
                        )

                try:
                    arguments = sanitize_tool_arguments(arguments or {})
                except PermissionError as exc:
                    return JsonRpcResponse.fail(request.id, APPLICATION_ERROR, str(exc))

                tool = self.tools[tool_name]
                if inspect.iscoroutinefunction(tool.handler):
                    output = await tool.handler(**arguments)
                else:
                    output = tool.handler(**arguments)

                return JsonRpcResponse.success(
                    request.id,
                    {"content": [{"type": "text", "text": str(output)}]},
                )

            # 2. Resources API
            elif method == "resources/list":
                res_list = [
                    {
                        "uri": r.uri,
                        "name": r.name,
                        "description": r.description,
                        "mimeType": r.mime_type,
                    }
                    for r in self.resources.values()
                ]
                return JsonRpcResponse.success(request.id, {"resources": res_list})

            elif method == "resources/read":
                uri = params.get("uri")
                if not uri or uri not in self.resources:
                    return JsonRpcResponse.fail(
                        request.id,
                        INVALID_PARAMS,
                        f"Resource URI '{uri}' not found",
                    )
                res = self.resources[uri]
                content = await res.handler() if inspect.iscoroutinefunction(res.handler) else res.handler()
                return JsonRpcResponse.success(
                    request.id,
                    {"contents": [{"uri": uri, "mimeType": res.mime_type, "text": content}]},
                )

            # 3. Prompts API
            elif method == "prompts/list":
                prompt_list = [
                    {
                        "name": p.name,
                        "description": p.description,
                        "arguments": p.arguments,
                    }
                    for p in self.prompts.values()
                ]
                return JsonRpcResponse.success(request.id, {"prompts": prompt_list})

            elif method == "prompts/get":
                name = params.get("name")
                arguments = params.get("arguments", {})
                if not name or name not in self.prompts:
                    return JsonRpcResponse.fail(
                        request.id,
                        METHOD_NOT_FOUND,
                        f"Prompt '{name}' not found",
                    )
                prompt = self.prompts[name]
                if inspect.iscoroutinefunction(prompt.handler):
                    text = await prompt.handler(**(arguments or {}))
                else:
                    text = prompt.handler(**(arguments or {}))
                return JsonRpcResponse.success(
                    request.id,
                    {
                        "description": prompt.description,
                        "messages": [
                            {"role": "user", "content": {"type": "text", "text": str(text)}}
                        ],
                    },
                )

            else:
                return JsonRpcResponse.fail(
                    request.id,
                    METHOD_NOT_FOUND,
                    f"Unknown method '{method}'",
                )

        except Exception as ex:
            return JsonRpcResponse.fail(
                request.id,
                INTERNAL_ERROR,
                f"Execution failed: {str(ex)}",
            )
