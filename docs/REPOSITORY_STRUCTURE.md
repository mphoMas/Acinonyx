# Repository structure

The repository separates company material, runtime code, technical documentation, research, learning, local work, and historical exports. Commands run from the repository root unless their documentation says otherwise.

```text
Acinonyx/
├── README.md, AGENTS.md              # Entry points and agent guidance
├── pyproject.toml                   # Python packaging and test configuration
├── package.json, package-lock.json  # Browser-tool dependencies
├── Dockerfile, docker-compose.yml   # Container configuration
├── main.py                          # Existing runtime/demo entry point
├── company/
│   ├── MANDATE.md, WAYS_OF_WORKING.md
│   └── founder/                     # Profile and supporting documents
├── mas/                             # Runtime package
├── tests/                           # Runtime verification
├── docs/
│   ├── architecture/                # Designs and frontier workstreams
│   ├── reviews/                     # Independent reviews and review tasks
│   ├── data/                        # SQL/data workflow guides
│   └── demos/portal/                # Reference screenshots
├── research/                        # Research library
├── portal/                          # Active research website
├── scripts/                         # Utilities and demo runners
├── templates/                       # Reusable starting points
├── study/resources/                 # Learning material and exam references
├── RunQL/                           # Tool-managed SQL workspace
├── workspace/data/                  # Runtime data and existing experiments
└── archives/
    ├── portal_snapshot/             # Preserved alternate portal
    ├── exports/                     # Portal ZIP versions
    └── evidence/                    # Exported evidence bundles
```

## File placement rules

1. Put executable runtime functionality in `mas/` and its tests in `tests/`.
2. Put company direction and founder material in `company/`; architecture, operational guides, and reviews in `docs/`.
3. Put reference studies in `research/` and learning exercises in `study/`.
4. Keep the active portal free of ZIP exports, historical application copies, and capture images.
5. Put generated local state and temporary experiments under `workspace/`; retain existing versioned evidence deliberately rather than moving it into application code.
6. Put historical versions and exported bundles in `archives/`. Archive placement is preservation, not production approval.
7. Keep standard build, package, CI, and agent-discovery files in their established locations. Use repository-relative document links.

## Migration map

| Previous path | Current path |
|---|---|
| `MANDATE.md` | `company/MANDATE.md` |
| `WAYS_OF_WORKING.md` | `company/WAYS_OF_WORKING.md` |
| `ACINONYX_FRONTIER.md` | `docs/architecture/ACINONYX_FRONTIER.md` |
| `docs/llm_mas_deep_dive.md` | `docs/architecture/llm_mas_deep_dive.md` |
| `ARCHITECT_REVIEW.md` | `docs/reviews/ARCHITECT_REVIEW.md` |
| `ARCHITECT_REVIEW_TODO.md` | `docs/reviews/ARCHITECT_REVIEW_TODO.md` |
| `README_RUNQL.md` | `docs/data/README_RUNQL.md` |
| `about_me/README.md`, profile documents and editor settings | `company/founder/` |
| `about_me/comms_tracker.py` | `scripts/comms_tracker.py` |
| `about_me/comms_vault.db` | `workspace/data/comms_vault.db` |
| Root certification PDF | `study/resources/professional_agentic_architect_exam_guide_english.pdf` |
| `portal.zip` | `archives/exports/portal-root.zip` |
| `portal/portal.zip` | `archives/exports/portal-nested.zip` |
| `portal/portal/` | `archives/portal_snapshot/` |
| `portal/*.png` | `docs/demos/portal/` |
| `evidence_bundle_pilot_brief_b.zip` | `archives/evidence/evidence_bundle_pilot_brief_b.zip` |

All 73 moved files were SHA-256 checked immediately after their move. Documents and path-dependent code were then updated where needed. The database, PDFs, PNGs, ZIPs, and archived portal variant were preserved byte-for-byte. No files were deleted and no alternative portal version was promoted.

The `MAS_COMMS_VAULT_DB` override is supported as before. Docker's mandate copy and the evidence-bundle output path were updated. Runtime package imports, existing script entry points other than the relocated communication tracker, SQL storage roots, research paths, and the active portal entry point retain their locations.

Historical review line references describe the audited commit; read them in that context. Existing absolute workstation links inside research compendiums and immutable archives remain historical content, not migration-generated links.

## Migration validation

- All 73 moved files exist at their destinations; 68 remain byte-identical and five have only the required documentation/CLI path updates.
- All moved database, PDF, PNG, ZIP, and archived portal files remain byte-identical.
- 376 unrelated tracked files, including the live portal implementation, remain byte-identical.
- 57 local documentation links and 16 active portal script/stylesheet references resolve.
- Docker `COPY` source paths, the communication database default, and the evidence-bundle export destination resolve.
- The relocated communication CLI executed a query against a disposable database successfully; the existing personal database was not opened for this check.
- The archived portal's dependency-free Node logic checks passed.
- Runtime pytest run: **212 passed, 3 failed, 4 skipped**. Remaining failures are the previously observed offline BigQuery and missing OmniLedger test-fixture issues; desktop/browser prerequisites remain unavailable.

Move manifests and command evidence are retained under `/workspace/review-evidence/acinonyx/` in the current cloud workspace. The folder migration does not change the remote repository until its commit is pushed.
