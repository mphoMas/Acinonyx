# Agent delivery reliability audit

## 1. Verdict and executive summary

**APPROVED WITH CONDITIONS as a bounded retrospective, not a provider benchmark.** Audited local revision `1315c456` on 13 October 2026. The five selected Antigravity implementation packages each failed their first recorded review. This establishes poor first-pass acceptance in this selected security-heavy sample; it does not establish an error percentage across all Antigravity work or attribute every correction to the model.

## 2. Findings and reproducible counts

Unit: one reviewed implementation package/submission, counting combined SBA-02/05 and CC-05/06 once. Only recorded implementation reviews are included. Conditional acceptance counts as passing the specifically reviewed scope, not production approval. The source-linked JSON ledger contains every counted round.

| Antigravity implementation package | Recorded rounds | Rejected rounds | Accepted rounds | Subsequent change of builder |
|---|---:|---:|---:|---|
| SBA-02/05 | 3 | 2 | 1 conditional | None in counted series |
| SBA-03 | 5 | 5 | 0 | Codex supplied corrective work; no standalone final SBA-03 acceptance counted |
| CC-03 | 3 | 3 | 0 | Codex correction independently accepted by Antigravity |
| CC-04 | 6 | 5 | 1 conditional | None in counted series |
| CC-05/06 | 2 | 2 | 0 | Codex correction conditionally accepted for offline scope; runtime pending |
| **Total** | **19** | **17** | **2** | |

- First-recorded-review acceptance: **0/5 = 0%**; first-recorded-review rejection: **5/5 = 100%**.
- Submission rejection fraction: **17/19 = 89.5%**. This is not percentage of code wrong, probability of failure, or margin of statistical error.
- Recorded follow-up submissions after first review: **19 - 5 = 14**. These are resubmission rounds, not 14 distinct defects or measured engineering hours.
- Cross-builder corrections are not credited as Antigravity implementation acceptance.
- No representative random sample, equal task difficulty, recorded labor denominator or independent field-defect census exists. Do not extrapolate these numbers to provider/model rankings.

### Codex comparison

Three original correction packages have explicit counterparty reviews:

| Codex package | Independent review | Scoring |
|---|---|---|
| Coordinator/evidence correction `03da60da` | [CC_02_CODEX_FIX_INDEPENDENT_REVIEW.md](CC_02_CODEX_FIX_INDEPENDENT_REVIEW.md) | First documented review conditionally accepted, bounded scope |
| CC-03 correction `a0c0aa51` | [CC_03_ANTIGRAVITY_INDEPENDENT_REVIEW.md](CC_03_ANTIGRAVITY_INDEPENDENT_REVIEW.md) | First documented review accepted, storage scope |
| CC-05/06 `70e446cb` / `e1c0eed3` | [CC_05_06_CODEX_FIX_INDEPENDENT_REVIEW.md](CC_05_06_CODEX_FIX_INDEPENDENT_REVIEW.md) and [reconciliation](CC_05_06_REVIEW_RECONCILIATION.md) | Offline scope conditionally accepted; complete containment acceptance remains pending |

Thus **2/2 fully adjudicated correction packages passed their first recorded review**, with **one additional package partially reviewed**. Reporting this as a general Codex 100% reliability score would be misleading: the sample is tiny, corrective rather than original implementation, and missing runtime review is excluded from that denominator. Later missing-Docker, image-portability and delayed-create recovery fixes demonstrate remaining defects and operational gaps; they must not be hidden by this narrow acceptance count. Latest container-recovery author tests are not independent acceptance. Frontend work and other authored changes without explicit independent verdicts are unscored, not automatically accepted.

### Defect versus requirement change

The recorded rejections include reproduced authority bypasses, false success, funding overruns, incomplete migrations and surviving execution. These are concrete implementation/trust failures, not merely stylistic objections. Some remedies also clarified design choices and supported scope during review. No per-finding attribution ledger reliably separates original-contract violations, newly introduced requirements, review mistakes and environment constraints. Therefore this audit counts acceptance outcomes only, not a model-caused defect percentage. Missing Docker is infrastructure; unsupported claims that Docker tests ran are evidence-reporting errors.

**High severity:** low first-pass acceptance and overstated completion require a separate gate. Fix: smaller packages, design review before implementation, original requirement IDs and mandatory adverse-case checks.

**Medium severity:** incomplete attribution and effort records prevent rework-cost/error-rate calculation. Fix: record finding origin, responsible change, minutes/cost and closure candidate.

**Low severity:** combined package granularity limits ticket-level comparison. Preserve this denominator; introduce per-package tracking prospectively rather than retroactively duplicating counts.

## 3. Pillar breakdown

- Platform: dispatch/termination/recovery failures repeatedly blocked acceptance.
- Data: ownership, transactions, migration and funding integrity failures recur.
- AI: test counts and agent claims cannot replace candidate-specific independent evidence; no controlled model comparison exists.
- Governance: separate author/reviewer identity and distinguish submission, acceptance, infrastructure-blocked and production qualification states.

## 4. Action directive

1. Track each next submission with package ID, builder/provider/model version, requirement version, immutable candidate and separate reviewer.
2. Classify each finding as original requirement violation, requirement change, infrastructure gap or review/evidence error; allow multiple labels with rationale.
3. Capture correction effort and provider cost, not just number of review rounds.
4. Measure first-pass acceptance, resubmission count, rework time share and post-acceptance defects on the same observation window for both agents.
5. Use the next complete-loop pilot to collect comparable evidence. Do not modify live tickets or claim full-loop acceptance from this report.

[Machine-readable source ledger](AGENT_DELIVERY_AUDIT_LEDGER.json). Local document review only; no tests rerun, no provider calls and no live board mutation.
