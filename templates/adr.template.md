# ADR-[NNNN]: [Short Title of Architectural Decision]

## Status
[Proposed | Accepted | Superseded | Deprecated] (Date: YYYY-MM-DD)

## Context & Problem Statement
*Describe the technical context, business drivers, performance requirements, and constraints that motivate this decision. Cite relevant research, telemetry, or incident reports.*

## Decision Drivers & Trade-Offs
* List key architectural forces in tension:
  * e.g., Latency vs. BigQuery scan costs
  * e.g., Autonomous agent throughput vs. token budget consumption
  * e.g., Ease of development vs. strict type safety

## Considered Options
1. **Option A:** [Description of option 1]
2. **Option B:** [Description of option 2]
3. **Option C:** [Description of option 3]

## Decision Outcome
**Chosen Option:** **[Option A/B/C]**, because [justification anchored in empirical evidence or strategic mandates].

### Positive Consequences
* [Benefit 1, e.g., Reduces P95 dashboard query latency from 30s to 1.5s]
* [Benefit 2, e.g., Eliminates circular import dependencies between core modules]

### Negative Consequences & Mitigations
* [Trade-off 1, e.g., Increases initial dbt compile time by 45 seconds; mitigated via incremental caching]
* [Trade-off 2, e.g., Requires engineers to learn new declarative YAML schema syntax]

## Compliance & Invariants
* Aligns with Acinonyx Invariant [X] ([Staged Dispatch / Filesystem Jail / Cost Cap / etc.])
* Standard Alignment: [ISO/IEC/IEEE 12207, NIST SP 800-218, DORA AI Capabilities]
