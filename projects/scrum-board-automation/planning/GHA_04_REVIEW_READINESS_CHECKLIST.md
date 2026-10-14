# GHA-04 review readiness

- [ ] Revised design addresses B1–B6 in `GHA_04_DESIGN_REVIEW.md`.
- [ ] Witness cannot mutate delivery phase, budgets, dispatch or trusted evidence.
- [ ] Token/action/attempt/source/MAS identities and relational constraints are explicit.
- [ ] Same/fresh/expired-token retry and historical receipt retrieval outcomes are unambiguous.
- [ ] Source freshness protocol handles force push, base changes and delayed responses.
- [ ] Authorization linearization covers IAM and connector update boundaries.
- [ ] Artifact durability/quota/orphan cleanup and local rollback versus remote uncertainty are distinguished.
- [ ] Immutable history, mutable projections, retention and migration compatibility are specified.
- [ ] Shared scenarios in `GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md` are mapped to proposed mechanisms before coding.
- [ ] Codex design agreement recorded before implementation/schema changes.

Status today: specification prepared, not executed; rejected design remains awaiting revision. This is reviewer/implementer work, not a checklist for the CEO to administer.
