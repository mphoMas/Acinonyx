# Multi-Agent Systems Design Patterns & Swarm Topologies
*A comprehensive guide synthesizing MetaGPT, AutoGen, ChatDev, and Acinonyx Labs Liquid Strike Pod designs.*

---

## 1. Multi-Agent Coordination Topologies

```
A. Hierarchical (Orchestrator-Worker)       B. Peer-to-Peer (Event Bus)
             ┌───────────┐                         ┌─────────────┐
             │Supervisor │                         │  Event Bus  │
             └─┬───┬───┬─┘                         └──┬───┬───┬──┘
         ┌─────┘   │   └─────┐                        │   │   │
         ▼         ▼         ▼                    ┌───┘   │   └───┐
     ┌───────┐ ┌───────┐ ┌───────┐                ▼       ▼       ▼
     │Worker1│ │Worker2│ │Worker3│              [Agnt1] [Agnt2] [Agnt3]

C. Sequential Pipeline (Waterfall DAG)      D. Liquid Strike Pod (Hybrid Dynamic)
   ┌────┐     ┌────┐     ┌────┐                 [Capability Guild Pool]
   │PM  ├────►│Arch├────►│Dev │                          │ Assemble
   └────┘     └────┘     └─┬──┘                          ▼
                           │             ┌─────────────────────────────┐
                           ▼             │   Ephemeral Cross-Pod       │
                         ┌────┐          │ (Research->PRD->Arch->Dev)  │
                         │ QA │          │ • Level 2 Gated Milestones  │
                         └────┘          │ • Merkle Provenance Hash    │
                                         └──────────────┬──────────────┘
                                                        │ Auto-Disband
                                                        ▼
                                                [Guild Pool Reclaim]
```

### Pattern A: Hierarchical Orchestrator-Worker
- **Mechanism**: A primary Supervisor agent perceives user requirements, maintains the high-level roadmap, decomposes tasks into non-overlapping sub-problems, dispatches them to specialized workers, and synthesizes deliverables.
- **Best For**: Ambiguous, multi-disciplinary requests requiring centralized accountability.

### Pattern B: Peer-to-Peer Reactive Event Bus
- **Mechanism**: Agents publish and subscribe to strongly-typed event topics (e.g. `engineering:pr_created`, `qa:verification_passed`). Decentralized; agents react autonomously to incoming events.
- **Best For**: Asynchronous monitoring, alerting swarms, and CI/CD automation.

### Pattern C: Standardized Waterfall DAG with Handover Gates (MetaGPT Style)
- **Mechanism**: Standard Operating Procedures (SOPs) are encoded directly into the system. An agent cannot proceed until the previous agent produces a valid, typed artifact (PRD, Architecture Spec, Code, Test Suite).
- **Core Benefit**: Eradicates hallucination cascades. In unstructured group chats, agents easily wander off-topic or agree on flawed premises. Rigid schemas anchor every stage.

### Pattern D: Liquid Strike Pods (Acinonyx Enterprise)
- **Mechanism**: Combines long-term Capability Guilds (functional pools of competence) with dynamic, short-lived cross-functional strike pods assembled on-demand for specific client deliverables and auto-disbanded upon delivery.
- **Features**:
  - Gated human sign-off milestones (Design Review Gate 1, Production Deploy Gate 2).
  - Cryptographic Merkle provenance root hashing every intermediate artifact.
  - FinOps 2.0 ROI scoring enforcing strict token budgets.

---

## 2. Preventing Error Cascades & Hallucination Loops

### The $K$-Round Bounded Reflexion Invariant
Unbounded debate between LLM agents frequently leads to infinite circular argumentation or polite mutual agreement on incorrect code.
- **Rule**: Bound peer review loops to $K \le 3$ rounds.
- **Escalation**: If QA or Red-Team does not sign off after 3 rounds, halt automatically and escalate to a human supervisor or Level 2 Gate.

### Grounded Evidence Invariants
Every factual claim made by an agent must cite an explicit `evidence_id`:
- Sourced from tool observation (`tool:web_search:0`, `tool:run_python:1`) or episodic memory reflection (`reflection:14`).
- Statements without grounding are rejected by validation middleware.

### Merkle Provenance Tracking
To guarantee supply chain security and traceability for autonomous agent output:
$$\text{Merkle Root} = \mathcal{H}\left(\mathcal{H}(\text{Research}) \parallel \mathcal{H}(\text{PRD}) \parallel \mathcal{H}(\text{Arch}) \parallel \mathcal{H}(\text{Code}) \parallel \mathcal{H}(\text{Tests})\right)$$
Guarantees zero unauthorized post-audit modifications to generated artifacts.
