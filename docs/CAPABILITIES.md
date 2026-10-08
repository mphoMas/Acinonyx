# MAS Capability Matrix

Honest status of runtime capabilities as of **v0.2.0**.  
Statuses: `implemented` | `demo-only` | `planned`

| Capability | Status | Module | Notes |
|---|---|---|---|
| Typed message bus + edge validation | implemented | `mas.core.event_bus` | Validates Message; JSONL audit |
| Supervisor DAG + timeout/retry | implemented | `mas.orchestration.supervisor` | `FailurePolicy` fail-fast / continue |
| Anti-sycophancy debate | implemented | `mas.orchestration.debate` | Masking + sycophancy score |
| SOP pipeline schemas | implemented | `mas.orchestration.pipeline` | `SchemaSpec` validators |
| MCP tools/resources/prompts | implemented | `mas.mcp` | `initialize` handshake |
| Working + episodic memory | implemented | `mas.memory` | SQLite vector k-NN |
| Sandboxed Python | implemented | `mas.tools.executor` | Deny dangerous imports |
| Filesystem jail | implemented | `mas.tools.filesystem` | Allowlisted roots |
| HTTP LLM provider | implemented | `mas.providers` | OpenAI-compatible |
| ReAct tool loop | implemented | `mas.core.agent` | When provider attached |
| Squad self-heal | implemented | `mas.squad` | LLM repair or generator fallback |
| HR gap analysis | implemented | `mas.organization.hr` | LLM + keyword fallback |
| Eval harness | implemented | `mas.eval` | Golden missions |
| CLI doctor | implemented | `mas.cli` | Runtime health report |
| Enterprise engagement | **demo-only** | `mas.organization.engagement` | Scripted pipeline; dry-run default |
| Echo / template agents | **demo-only** | `main.py` | Pass-through without LLM |
| Native Scrum/Kanban PM board | implemented | `mas.pm` | Guarded FSM, Little's Law WIP, Playwright verified |
| Multi-tenant IAM / OAuth | planned | — | Not shipped |
| Managed vector SaaS adapters | planned | — | Not shipped |

Regenerate a machine-readable view:

```bash
PYTHONPATH=. python3 -m mas.cli capabilities
PYTHONPATH=. python3 -m mas.cli doctor
```
