# Rework quantity and cause analysis — initial evidence-backed extraction

## 1. Verdict and executive summary

**APPROVED WITH CONDITIONS as an initial diagnostic, not an exhaustive causal census.** Records were collected from all current branch history, GitHub PR/issue/Actions metadata, uploaded transcripts and local reports. This extraction covers the five implementation packages in the prior source ledger, eight recurring issue families and thirteen selected remediation candidates. Hours are deliberately excluded. Findings identify recurring engineering/process failures, not inherent superiority of a provider.

## 2. Quantity, sequence and critical findings

| Implementation package | Recorded submissions | Follow-up submissions | Rejected submissions | Recorded outcome |
|---|---:|---:|---:|---|
| SBA-02/05 | 3 | 2 | 2 | Conditional development acceptance |
| SBA-03 | 5 | 4 | 5 | Codex corrective package followed; no standalone final SBA-03 acceptance counted |
| CC-03 | 3 | 2 | 3 | Codex corrective package subsequently accepted separately |
| CC-04 | 6 | 5 | 5 | Conditional synthetic-only acceptance |
| CC-05/06 | 2 | 1 | 2 | Codex corrective package later partially accepted; runtime gate pending |
| **Total** | **19** | **14** | **17** | |

**14/19 = 73.7% of the counted submission rounds are follow-up rounds.** This is a repeat-submission proportion, not effort wasted or lines rewritten. **17/19 = 89.5% rejected** describes acceptance outcomes. A follow-up may contain both correction and newly specified work. The underlying code can be partly correct in a rejected submission. Two accepted packages required 2 and 5 follow-up submissions respectively. Three package sequences changed implementation owner; do not treat those as Antigravity-only completed delivery cycles.

### Traceable recurring issue families

| Issue family | Review rounds observing the family | What the changes failed to address completely |
|---|---:|---|
| SBA-03 planning authority | 4 | Identity text, allowed-looking names and suffixes substituted for verified permission |
| SBA-03 active policy preservation | 2 | Staging a change did not correctly preserve removal/null semantics |
| SBA-03 proposal binding | 3 | Version binding was missing, then optional, then HTTP values insufficiently strict |
| CC-03 historical upgrades | 3 | Fresh-schema success did not establish safe upgrades of already-shipped databases |
| CC-03 settlement truth/integrity | 3 | Funding, outcome and conflicting-replay rules were incomplete across lifecycle paths |
| CC-04 physical termination | 5 | Stop signals, declared capability and class allowlisting did not prevent surviving execution or unsafe configuration |
| CC-05/06 measured verification | 2 | Candidate checkout did not stop stdout from manufacturing apparent test success |
| CC-05/06 whole-boundary isolation | 2 | Environment filtering and parent-process handling did not contain guest code or orphan descendants |

These families overlap and contain distinct manifestations. Do not add the row counts and call the result unique bugs. Source filenames and candidate links are in [REWORK_CAUSE_LEDGER.json](REWORK_CAUSE_LEDGER.json).

### Concrete correction sequence: CC-04

`2aee5ac9` original worker → rejected; `490e2ce0` correction → rejected; `f6d2f34a` strict-result/deadline/FSM correction → rejected; `276c2e1f` launch/termination correction → rejected; `07294b0f` registry correction → rejected; `a12c945a` unsafe configuration/timing correction → conditionally accepted for synthetic scheduling only.

The reviews progressively demonstrate late filesystem effects after worker return. Quarantining a late result and retaining its funding are useful, but do not physically terminate execution. A registry then addressed adapter identity, while unsafe options still defeated the registered adapter's stop guarantee. This is direct evidence of correcting the visible symptom without closing the entire invariant.

### High severity: confirmed recurring mechanisms

1. **Incomplete boundary fixes.** The same requirement reappeared in changed form after correction. Impact: repeated acceptance failures. Required fix: enumerate every entry point/state/configuration affected by the rule and submit a closure matrix, rather than one reproducer-specific patch.
2. **Tests did not challenge the claimed guarantee.** Examples include a forged receipt test expecting admission, an early no-write check ending before the child write deadline, printed pytest-like output accepted as measured results, and browser reports claiming tickets without DOM assertions. Impact: green suites supported false confidence. Required fix: reviewer-owned failure probes and exact candidate-bound, actual execution evidence.
3. **Control mechanisms were weaker than the promised behavior.** Cooperative signals/process groups/worktrees/HMAC were treated as sufficient for termination/isolation/truth. Impact: architecture-level repair rather than local code edits. Required fix: design review of the enforcement mechanism before implementation.

### Medium severity: supported process contributors and inference limits

4. **Contract detail matured during delivery.** Proposal-version typing, dispatch fencing, legacy migration and explicit controlled-only scope became more precise across reviews. Existing documented review directives make later repeats demonstrably incomplete; initial responsibility cannot all be assigned to the implementer. Required fix: freeze requirement/version and classify new requirements separately from original violations.
5. **Inconsistent environment qualification.** Missing Docker and author-local image identifiers prevented some checks; later delayed-create behavior required additional recovery work. Infrastructure gaps are not model defects. Unsupported claims that those checks ran are reporting defects. Required fix: explicit prerequisites and separate offline/runtime verdicts.
6. **Human-relayed handoffs.** Transcripts document the owner repeatedly carrying delivery and correction instructions. This confirms coordination burden, but does not prove it caused a specific code defect. Required fix: persistent task/candidate-linked handoffs and automatic submission/review notifications.

### Evidence reporting failure on both sides of delivery

Antigravity's review of Codex CC-05/06 had incorrect counts and unobserved full-gate/container claims, subsequently corrected. Codex author tests cannot substitute for independent acceptance. Codex-authored missing-Docker/portability/recovery corrections show the code was not faultless after initial delivery. No agent gets a general zero-defect score.

### Low severity: measurement gaps

Agent attribution remains unresolved where Git identity is insufficient; transcripts are supplemental claims. GitHub's three PRs do not capture every direct branch submission. The corpus contains 186 commits, not 186 tasks. No hours, labor savings, defect-density percentage or causal percentage is calculated. Rewritten line counts are not an effort measure.

## 3. Pillar-by-pillar breakdown

- **Platform:** execution lifecycle guarantees repeatedly outran process/container supervision mechanisms.
- **Data:** historical upgrades, ownership, policy changes, transactional admission and settlement are recurring integration boundaries.
- **AI:** agent-generated evidence and self-authored happy-path tests created premature confidence; exact model/provider performance cannot be inferred.
- **Resilience/governance:** uncertainty and author/reviewer separation must remain explicit. Accepted scope is not live-production acceptance.

## 4. Architect's action directive

1. For each next task, agree a versioned contract with invariants, supported scope, failure matrix and actual acceptance evidence before coding.
2. Review the enforcement design first for authority, funds, isolation and recovery tasks.
3. Require correction submissions to map every finding to affected entry points, changed code and negative checks, including unchanged related paths.
4. Record outcomes as implemented, submitted, rejected, accepted-with-scope, or infrastructure-blocked; no self-marked completion.
5. Use the next loop pilot to compare first-pass acceptance and recurrence for both agents on comparable task types.

The thirteen remediation commits are a verified selected set, not an exhaustive commit count. Eight recurrence chains and 484 transcript line pointers were retained in the private research analysis folder. Pointer matches locate evidence; they are not 484 defects. Original source bytes and collection manifest remain preserved. This report changes no runtime tasks, code or provider configuration.
