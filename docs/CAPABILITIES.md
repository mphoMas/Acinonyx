# MAS capability matrix

Status reflects code scope, not production admission. Regrouping baseline: `3311a4fa4a99957d9f4c13dde89fc97f0e8817f3`.

`implemented` means an implementation exists; fixture/local checks do not establish live cloud availability, whole-platform tenancy or operational qualification. `demo-only` means simulated or scripted behavior. Unsupported consolidated adapters remain unavailable until their acceptance gates pass.

| Capability | Status | Module | Scope |
| --- | --- | --- | --- |
| typed_message_bus | implemented | `mas.core.event_bus` | Async topic bus + validation + JSONL audit |
| supervisor_dag | implemented | `mas.orchestration.supervisor` | Dependency-aware concurrent subtasks with timeout/retry |
| anti_sycophancy_debate | implemented | `mas.orchestration.debate` | Blind masking, contrarian, sycophancy score |
| sop_pipeline | implemented | `mas.orchestration.pipeline` | Sequential stages with schema validators |
| mcp_jsonrpc | implemented | `mas.mcp.protocol` | tools/resources/prompts + initialize handshake |
| working_episodic_memory | implemented | `mas.memory` | Sliding window + SQLite vector episodic store |
| sandboxed_python | implemented | `mas.tools.executor` | Required bubblewrap isolation, bounded output and process-group cleanup |
| filesystem_jail | implemented | `mas.tools.filesystem` | Path allowlist roots |
| llm_provider_http | implemented | `mas.providers.http_provider` | OpenAI-compatible HTTP provider |
| agent_react_loop | implemented | `mas.core.agent` | Tool loop when provider attached |
| squad_self_heal | implemented | `mas.squad.squad` | QA loop; LLM repair when provider present else generator fallback |
| hr_gap_analysis | implemented | `mas.organization.hr` | LLM analysis with keyword catalog fallback |
| enterprise_engagement | demo-only | `mas.organization.engagement` | Scripted consulting workflow; dispatch gates do not establish live engagement quality |
| demo_echo_agents | demo-only | `main` | Deterministic zero-key topology demo runners for offline verification |
| distributed_swarm_auth | implemented | `mas.core.swarm` | Swarm relay with token auth |
| visual_diff_gate | implemented | `mas.tools.visual_diff` | Pixel RMSE visual regression |
| eval_harness | implemented | `mas.eval` | Golden missions + structural/quality scoring |
| cli_doctor | implemented | `mas.cli` | Runtime health / mode report |
| multi_tenant_iam | implemented | `mas.iam` | HMAC/RBAC tenant-bound MCP/PM APIs; optional durable identity and revocation; isolated SQLite/workspaces; legacy endpoints remain single-tenant |
| external_identity_audit_anchor | implemented | `mas.audit_anchor` | HTTPS forward-only witness checkpoint protocol; independent deployment and restore boundary required |
| managed_vector_saas | demo-only | `mas.memory.vector_saas` | Local in-memory cloud adapter simulations; no remote persistence |
| computer_use | implemented | `mas.tools.computer_use` | Virtual Xvfb display + discrete OS mouse/keyboard actions + SoM grounding + Scope Jail |
| bigquery_finops_sql | implemented | `mas.tools.bigquery_tool` | Native Google Cloud BigQuery execution + dry-run cost estimation + mandatory labeling |
| data_contract_validator | implemented | `mas.tools.data_contract_tool` | YAML Data Contract validation asserting schema, nullability, uniqueness & enums |
| gcs_storage_manager | implemented | `mas.tools.storage_tool` | GCS CLI bucket listing and object reading; requires authenticated gcloud |
| agent_to_agent_delegation | implemented | `mas.tools.delegation_tool` | Dynamic subtask delegation to specialized agent personas within ReAct loop |
| surgical_file_patching | implemented | `mas.tools.patch_tool` | Surgical contiguous line replacement preventing full-file overwrite token bloat |
| research_knowledge_vault_rag | implemented | `mas.tools.knowledge_vault_tool` | Active full-text retrieval across 8-volume AI Encyclopedia and research archives |
| human_in_the_loop_gate | implemented | `mas.tools.hitl_tool` | Structured clarification question queue with interactive and autonomous resolution |
| popia_pii_anonymizer | implemented | `mas.tools.pii_tool` | POPIA & GDPR compliance tool redacting South African IDs (Luhn), cards, emails & phones |
| native_pm_board | implemented | `mas.pm` | Agent-native Scrum/Kanban board, FSM engine, Little's Law WIP, and cryptographic evidence verification |

## Admission limits

Durable IAM and tenant-bound PM/MCP are implemented. OAuth is not claimed. Shared swarm identity is explicitly enabled for fresh platform-bound stores; it does not protect every legacy runtime surface. External witness protocol implementation does not establish an independently operated deployment.

Browser/desktop, distributed relay and external data tools have code implementations but are excluded from the initial consolidated pilot. BigQuery/GCS require real configured credentials and service qualification; local or mocked checks are insufficient. Managed vector adapters remain simulations.

The supervised coding workflow retains at most three model calls, measured worker verification and separate human approval. Live provider quality needs its own candidate-specific evidence. See [release readiness](RELEASE_READINESS_CHECKLIST.md), [acceptance gates](architecture/MAS_CONSOLIDATION_ACCEPTANCE.md) and [scope inventory](architecture/MAS_CONSOLIDATION_INVENTORY.md).

Regenerate the machine-readable view with `python -m mas.cli capabilities`.
