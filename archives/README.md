# Historical archives

| Location | Contents |
|---|---|
| `portal_snapshot/` | The previously nested `portal/portal/` variant, including its upgrade notes and dependency-free tests |
| `exports/portal-root.zip` | The ZIP previously at the repository root |
| `exports/portal-nested.zip` | The distinct ZIP previously inside `portal/` |
| `evidence/evidence_bundle_pilot_brief_b.zip` | Preserved exported pilot evidence bundle |

The two ZIPs and the nested portal are not identical. All versions are preserved; the folder migration does not choose or promote a different portal implementation. [portal/](../portal/README.md) remains the active portal. Snapshot contents and exported evidence are historical, not regenerated during this reorganization.

The archived portal's original relative links and workstation paths are retained as historical content. Its included logic checks can be run from `archives/portal_snapshot/` with `node tests/workspace.test.cjs`; it is not a supported deployment entry point.
