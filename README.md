# Project ACINONYX: MAS-Core

**Multi-Agent Operating Runtime** built from first principles in Python.  
Version **0.2.0** — production packaging ready; enterprise engagement demos remain **staged** unless live dispatch is armed.

See [docs/CAPABILITIES.md](docs/CAPABILITIES.md) for an honest implemented / demo-only / planned matrix.

---

## What is real vs demo

| Surface | Mode |
|---|---|
| Event bus, supervisor DAG, debate, SOP pipeline, MCP, memory, tools | **Implemented** (unit + eval covered) |
| LLM ReAct / squad LLM repair / HR LLM gap analysis | **Implemented** when an LLM provider is attached |
| Echo agents in `main.py`, enterprise engagement without LLM | **Demo / staged** (deterministic templates) |
| Multi-tenant IAM, managed vector SaaS | **Planned** |

Default dispatch is **STAGED** (`MAS_ENABLE_LIVE_DISPATCH=false`).

---

## Architecture

```
mas/
├── config.py, audit.py, validation.py, security.py, observability.py, capabilities.py, cli.py
├── core/           # Message, EventBus (+ JSONL audit), BaseAgent, State, Swarm
├── orchestration/  # Supervisor (timeout/retry/FailurePolicy), Debate (+ sycophancy score), SOP (+ SchemaSpec)
├── mcp/            # JSON-RPC tools / resources / prompts + initialize
├── memory/         # Working + episodic SQLite vector store
├── providers/      # Mock + HTTP OpenAI-compatible
├── squad/          # Architect → Engineer → QA with LLM or generator repair
├── organization/   # Consulting enterprise (engagement is demo-scripted)
├── tools/          # Sandboxed Python, filesystem jail, git, browser, visual diff, gitops
└── eval/           # Golden mission harness
```

---

## Quickstart

```bash
# Runtime health
PYTHONPATH=. python3 -m mas.cli doctor

# Capability matrix
PYTHONPATH=. python3 -m mas.cli capabilities

# Unit + integration + upgrade tests
PYTHONPATH=. python3 -m unittest discover -s tests -v

# Mission demos (template agents unless LLM env configured)
python3 main.py --mode supervisor
python3 main.py --mode enterprise   # staged dry-run by default
python3 main.py --mode dashboard --port 8080
```

### Optional live LLM

```bash
export MAS_LLM_BASE_URL=http://127.0.0.1:11434/v1
export MAS_LLM_MODEL=llama3.1
# or OPENAI_API_KEY + OPENAI_BASE_URL
```

### Docker

```bash
docker compose up --build
```

---

## Environment knobs

| Variable | Default | Meaning |
|---|---|---|
| `MAS_ENABLE_LIVE_DISPATCH` | `false` | Arm real engagement side-effects |
| `MAS_SANDBOX_PYTHON` | `true` | Block dangerous imports in `run_python` |
| `MAS_TOOL_ACL` | `true` | Enforce tool allowlists |
| `MAS_AUDIT_LOG` | `workspace/audit/events.jsonl` | Append-only bus audit |
| `MAS_REQUIRE_LLM` | `false` | Fail closed if no provider when set |

---

## Mandate invariants (enforced in code)

1. Edge validation on bus publish (`mas.validation`)
2. Typed messages + schema validators on SOP stages
3. Debate round caps + sycophancy scoring
4. Durable JSONL audit of publishes

---

## Research Directorate & Knowledge Compendiums

Exhaustive theoretical, architectural, and benchmark studies supporting Project ACINONYX:

- [**Research Directorate Master Portal**](research/README.md): Master landing page linking all research divisions.
- [**Agentic Systems Master Study Compendium**](research/agentic_systems/README.md): Frontier AI models (o1/o3, Sonnet 3.5, DeepSeek-R1), test-time compute, multi-agent topologies (CoALA, ReAct, Swarms, MCP/A2A), hyperscaler stacks, Work-as-a-Service (WaaS) economics, enterprise use cases, and production sandboxing.
- [**Master AI Encyclopedia (8 Volumes)**](research/ai_encyclopedia/README.md): 70+ year comprehensive history, mathematical foundations, frontier labs, university curricula, and future horizons.
- [**Google Cloud Agentic Infrastructure**](research/google_cloud_agentic_infra/README.md): Cloud-native agent deployment on Vertex AI Reasoning Engine and Cloud Run.

