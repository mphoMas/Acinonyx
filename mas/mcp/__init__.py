"""
mas.mcp: Model Context Protocol (MCP) native implementation.
"""

from mas.mcp.protocol import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcError,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
    MCPRegistry,
)
from mas.mcp.transport import MCPClient

__all__ = [
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcError",
    "ToolDefinition",
    "ResourceDefinition",
    "PromptDefinition",
    "MCPRegistry",
    "MCPClient",
]
