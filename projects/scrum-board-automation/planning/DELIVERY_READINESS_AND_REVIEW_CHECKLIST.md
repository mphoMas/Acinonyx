# Delivery readiness and review checklist

Adopted 13 October 2026 as a refinement of the rework research proposals. Apply prospectively inside authorized task scope. This document is process guidance, not implemented coordinator enforcement or new release authority.

## Before implementation

- Identify task, owner, separate reviewer, immutable baseline and requirement version.
- Share known acceptance and adverse-case checks with expected outcomes and actual prerequisites.
- Record new requirements explicitly as scope changes; a new probe of an existing requirement is not automatically new scope.
- Use a short design checkpoint proportional to risk, with explicit enforcement mechanisms for authority/funding/isolation/evidence/recovery changes.

## Before formal submission

- Identify exact candidate and changes; preserve concurrent work.
- Map every requirement/finding to changed or inspected paths and actual evidence.
- Report failures, skips, unavailable checks and remaining uncertainty explicitly.
- Coordinator screens completeness without claiming independent correctness. Record incomplete screening as READINESS_RETURNED, not silently discarded work.

## Independent review and challenges

- Each blocker cites applicable requirement/version, reproduction or essential missing evidence, impact and required closure evidence.
- Distinguish original violation, changed scope, infrastructure gap and reviewer/reporting error.
- Resolve challenges to applicability, facts or severity before another patch. Ordinary technical resolution does not require owner message relay; business/scope/release choices retain owner authority.
- Known checks do not replace independent probes. Authors cannot approve their own candidate.

## Recurrence

- If a claimed-closed invariant fails again, record RECURRENCE_PAUSED and revisit design, paths, brief and tests.
- Agree a concrete corrective plan before another implementation attempt; verify the original reproduction and related paths on the new candidate.

## Measurement

Track readiness returns, design revisions, formal rejections, recurrence, rounds to scoped acceptance and routine owner handoffs. Do not improve rejection statistics by hiding upstream repeats or lowering quality. These labels are proposed record categories, not newly deployed FSM/API states. No live board changes are made by publishing this checklist.
