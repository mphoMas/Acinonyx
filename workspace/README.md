# Local workspace

| Folder | Purpose |
|---|---|
| `data/` | Runtime databases; communication vault defaults to `data/comms_vault.db` |
| `projects/` | Project work areas and existing linked project entries |
| `computer_use/` | Browser/desktop experiment captures |
| `computer_use_research/` | Dated investigation reports and verification runners |
| `pilot_brief_b/` | Pilot candidates, execution runner, and recorded results |
| `evidence_bundle_staging/` | Input files for the exported evidence bundle |
| `audit/`, `scratch/` | Generated logs and temporary work, ignored by Git |

Use dated folders for new experiments. Promote reusable implementation to `mas/` or `scripts/`, tests to `tests/`, and reviewed documentation to `docs/`. Exported bundles belong in `archives/evidence/`.

The existing communication database was moved without changing its bytes. Existing project entries remain in place; this migration does not provision their missing checkout/submodule metadata.
