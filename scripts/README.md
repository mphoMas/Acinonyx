# Scripts

Run commands from the repository root. These scripts have different purposes and side effects; inspect a runner before executing it.

| Purpose | Scripts |
|---|---|
| MCP interface | `mas_mcp_stdio.py` |
| Communication-vault CLI | `comms_tracker.py` — moved from `about_me/`; override `MAS_COMMS_VAULT_DB` for a disposable database |
| Quality and evidence | `run_quality_gate.sh`, `verify_research_swarm.py`, `audit_web_anti_slop.py`, `build_evidence_bundle.py` |
| Portal maintenance | `compile_portal_catalog.py`, `launch_portal.py` |
| Research collection | `download_mas_knowledge_base.py`, `research_gcp_agentic_infra.py` |
| Mission and browser demonstrations | `run_saas_mission.py`, `run_price_audit.py`, `test_computer_use.py`, `live_computer_use_demo.py`, `record_*_demo.py` |
| HR evaluations | `swarm_rate_hr.py`, `swarm_rate_hr_v2.py` |

Existing workstation-specific paths and simulated verification behavior are documented in the [architecture review](../docs/reviews/ARCHITECT_REVIEW.md). This folder reorganization does not fix those defects. `build_evidence_bundle.py` now writes the repository export under `archives/evidence/`; its existing external artifact-copy destination is unchanged.
