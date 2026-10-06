"""
mas.cli: Entry points — doctor, version, capability report.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional


def cmd_doctor(args: argparse.Namespace) -> int:
    from mas.capabilities import summary_counts
    from mas.config import CONFIG, configure
    from mas.mcp.protocol import MCPRegistry
    from mas.tools.executor import register_default_tools
    from mas.tools.filesystem import register_filesystem_tools

    configure()
    registry = MCPRegistry()
    register_default_tools(registry)
    register_filesystem_tools(registry)

    provider_connected = bool(CONFIG.llm_base_url and (CONFIG.llm_api_key or CONFIG.llm_model))
    report = {
        "version": CONFIG.version,
        "workspace_root": str(CONFIG.workspace_root),
        "audit_log_path": str(CONFIG.audit_log_path),
        "live_dispatch": CONFIG.live_dispatch,
        "require_llm": CONFIG.require_llm,
        "allow_mock_provider": CONFIG.allow_mock_provider,
        "provider_configured": provider_connected,
        "llm_model": CONFIG.llm_model or "none",
        "llm_base_url": CONFIG.llm_base_url or "none",
        "sandbox_python": CONFIG.sandbox_python,
        "tool_acl_enabled": CONFIG.tool_acl_enabled,
        "mcp_tools_registered": sorted(registry.tools.keys()),
        "mcp_resources_registered": sorted(registry.resources.keys()),
        "capability_counts": summary_counts(),
        "dispatch_mode": "ARMED" if CONFIG.live_dispatch else "STAGED",
    }
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2))
    else:
        print(f"MAS doctor — v{report['version']}")
        print(f"  workspace:     {report['workspace_root']}")
        print(f"  audit log:     {report['audit_log_path']}")
        print(f"  dispatch:      {report['dispatch_mode']}")
        print(f"  provider:      {'configured' if provider_connected else 'not configured (mock/demo OK)'}")
        print(f"  sandbox:       {'on' if report['sandbox_python'] else 'off'}")
        print(f"  tool ACL:      {'on' if report['tool_acl_enabled'] else 'off'}")
        print(f"  MCP tools:     {', '.join(report['mcp_tools_registered']) or '(none)'}")
        print(f"  capabilities:  {report['capability_counts']}")
    return 0


def cmd_capabilities(args: argparse.Namespace) -> int:
    from mas.capabilities import CAPABILITIES

    for cap in CAPABILITIES:
        if args.status and cap.status.value != args.status:
            continue
        print(f"[{cap.status.value:11}] {cap.name:28} — {cap.notes}")
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    from mas.config import CONFIG

    print(CONFIG.version)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mas", description="MAS-Core CLI")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Report runtime health and mode")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    caps = sub.add_parser("capabilities", help="Print capability matrix")
    caps.add_argument("--status", choices=["implemented", "demo-only", "planned"])
    caps.set_defaults(func=cmd_capabilities)

    ver = sub.add_parser("version", help="Print version")
    ver.set_defaults(func=cmd_version)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
