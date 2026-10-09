# Project ACINONYX: MAS-Core

**Multi-Agent Operating Runtime** built from first principles in Python.  
Version **0.2.0** — development prototype; enterprise engagement demos remain **staged** unless live dispatch is armed. See the [independent architecture review](docs/reviews/ARCHITECT_REVIEW.md) for verified limitations and production blockers.

See [release readiness](docs/RELEASE_READINESS_CHECKLIST.md) for current admission limits.

See [docs/CAPABILITIES.md](docs/CAPABILITIES.md) for an honest implemented / demo-only / planned matrix.

The new [supervised coding swarm](docs/architecture/SUPERVISED_SWARM.md) provides a
separate `mas-swarm` CLI with isolated candidate execution, host-owned verification,
durable signed state and a separate human approval gate. Its initial scope is
Python functions; it does not establish enterprise readiness for the legacy runtime.
See the [MAS architecture diagram](docs/architecture/MAS_ARCHITECTURE.md) for the
relationship between the legacy runtime and the supervised swarm.

## Repository map

| Folder | What belongs here |
|---|---|
| [`company/`](company/README.md) | Company mandate, ways of working, and founder material |
| [`mas/`](mas/) | Python agent runtime and its tools |
| [`tests/`](tests/) | Runtime unit and integration tests |
| [`docs/`](docs/README.md) | Architecture, independent reviews, workflow documentation, and demo evidence |
| [`research/`](research/README.md) | Research library and reference papers |
| [`portal/`](portal/README.md) | Active research portal HTML, CSS, JavaScript, and catalog data |
| [`scripts/`](scripts/README.md) | Operational utilities, catalog tooling, and demo runners |
| [`templates/`](templates/) | Reusable document, data-contract, and web templates |
| [`study/`](study/README.md) | Learning plans, labs, and certification resources |
| [`RunQL/`](docs/data/README_RUNQL.md) | SQL workspace managed by RunQL |
| [`workspace/`](workspace/README.md) | Local runtime data, experiments, project work, and evidence staging |
| [`archives/`](archives/README.md) | Preserved portal snapshot and exported ZIP bundles |

Start with the [documentation index](docs/README.md). The [structure guide](docs/REPOSITORY_STRUCTURE.md) explains where to put new files and lists moved paths. Runtime commands continue to run from the repository root.

---

## What is real vs demo

| Surface | Mode |
|---|---|
| Event bus, supervisor DAG, debate, SOP pipeline, MCP, memory, tools | **Implemented** (unit + eval covered) |
| Native Scrum/Kanban PM engine + visual board | **Implemented** (guarded FSM + Little's Law WIP + Playwright verified) |
| LLM ReAct / squad LLM repair / HR LLM gap analysis | **Implemented** when an LLM provider is attached |
| Echo agents in `main.py`, enterprise engagement without LLM | **Demo / staged** (deterministic templates) |
| Durable IAM + tenant-bound PM/MCP + explicit shared swarm identity | **Implemented** within the reviewed pilot scope; wider cutover pending |
| Managed vector SaaS | **Demo / simulated**; no remote persistence |

Default dispatch is **STAGED** (`MAS_ENABLE_LIVE_DISPATCH=false`).

---

## Architecture

```
mas/
├── config.py, audit.py, validation.py, security.py, observability.py, capabilities.py, cli.py
├── core/           # Message, EventBus (+ JSONL audit), BaseAgent, State, Swarm
├── orchestration/  # Supervisor (timeout/retry/FailurePolicy), Debate (+ sycophancy score), SOP (+ SchemaSpec)
├── pm/             # Embedded SQLite WAL, guarded FSM, Little's Law WIP, evidence verification
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
python3 -m pytest tests -q

# Mission demos (template agents unless LLM env configured)
python3 main.py --mode supervisor
python3 main.py --mode enterprise   # staged dry-run by default
python3 main.py --mode dashboard --port 8080   # Observability at / and Living Portal & PM Board at /portal
```

### Authentication and durable state

Set `MAS_DASHBOARD_TOKEN` through your secret manager to enable protected reads and mutations; without it, those requests are denied. `MAS_DASHBOARD_PRINCIPAL` binds that token to one trusted operator identity (default `dashboard_operator`). Request bodies cannot select a different reviewer. One shared dashboard token is not a multi-user identity system.

Persistent governance records require private keys of at least 32 bytes: `MAS_VERDICT_SECRET` and `MAS_EVIDENCE_SECRET` (the latter can use the verdict key if omitted). Keep keys outside Git and restore the same keys with database backups. Existing records signed using the removed public defaults require fresh trusted review/evidence; do not relabel them as authentic. IAM uses `MAS_IAM_SECRET` when configured. Set `MAS_IAM_DB_PATH` or pass `db_path` to persist tenants, principals, issued sessions and revocations; durable mode requires the configured private key and an owner-only storage directory outside tenant workspaces. Without a database path, identity state remains process-local. See [durable identity and session recovery](docs/architecture/DURABLE_IDENTITY.md). Configure `MAS_IAM_ANCHOR_URL`, `MAS_IAM_ANCHOR_NAMESPACE` and `MAS_IAM_ANCHOR_TOKEN` to require a separately administered HTTPS audit witness. An anchored identity store refuses authorization when the witness is unavailable or differs from local history. See [external audit anchoring](docs/architecture/EXTERNAL_AUDIT_ANCHOR.md) for enrollment and crash recovery.

The default runtime container serves the dashboard/portal but its Docker security policy may prevent nested bubblewrap execution; `run_python` then refuses execution. Use a supported dedicated swarm coordinator for coding workers rather than weakening container isolation.

Set `MAS_PM_DB_PATH` for durable PM storage. The container uses `/app/workspace/mas_pm.db`, inside the existing Compose workspace mount. The swarm has its separate private state directory and credentials.

For full verification, install `.[dev,browser]`, Chromium (`python -m playwright install --with-deps chromium`), Xvfb, xdotool, bubblewrap and OpenSSL (TLS witness tests). Provide a local digest-pinned `MAS_SWARM_TEST_IMAGE`; the CI workflow pulls its pinned Python image. Run `bash scripts/run_quality_gate.sh`. Research checks cover local assets and links, not factual accuracy or live agent review.

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
| `MAS_SANDBOX_PYTHON` | `true` | Require bubblewrap isolation for `run_python`; refuse execution if unavailable |
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


The coding swarm can explicitly share durable platform IAM sessions with tenant-bound PM interfaces. See [shared identity setup](docs/architecture/SHARED_SWARM_IDENTITY.md) for permissions, persisted binding and revocation recovery. Historical local stores are not automatically migrated.
