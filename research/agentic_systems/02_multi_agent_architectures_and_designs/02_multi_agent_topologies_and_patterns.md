# Module 2: Multi-Agent Architectures & Designs
## Chapter 2: Multi-Agent Coordination Topologies & System Patterns

> *"Single-agent systems hit a complexity ceiling when tasks require diverse specialized competencies, conflicting perspectives, or extensive execution state. Multi-agent systems decompose complexity across specialized cognitive entities, but their success depends entirely on coordination topology."*

---

## 1. Taxonomy of Multi-Agent Topologies

Multi-agent coordination patterns fall into five canonical architectural paradigms:

```mermaid
graph TD
    subgraph Topologies ["The 5 Multi-Agent Coordination Topologies"]
        direction TB
        T1["1. Hierarchical<br>(Supervisor-Worker)"]
        T2["2. Sequential SOP<br>(Assembly Line)"]
        T3["3. Peer Swarm / Mesh<br>(Decentralized Bus)"]
        T4["4. Anti-Sycophancy Debate<br>(Adversarial Consensus)"]
        T5["5. Liquid Strike Pods<br>(Ephemeral Mission DAG)"]
    end
```

---

## 2. In-Depth Architectural Profiles

### 2.1 Hierarchical (Supervisor-Worker / Orchestrator-Subagent)
- **Mental Model:** A military command structure or corporate executive team.
- **Topology:** Star / Tree graph with a central root node.

```mermaid
graph TD
    User["User Task Objective"] --> Sup["Supervisor / Coordinator Agent"]
    Sup -->|1. Decompose & Dispatch| W1["Worker: Market Researcher"]
    Sup -->|2. Decompose & Dispatch| W2["Worker: Senior Backend Eng"]
    Sup -->|3. Decompose & Dispatch| W3["Worker: QA Test Critic"]
    W1 -->|Observation| Sup
    W2 -->|Code Patch| Sup
    W3 -->|Test Report| Sup
    Sup -->|Synthesize & Review| Final["Final Deliverable"]
```

- **Operational Mechanics:**
  - The Supervisor receives the high-level objective, decomposes it into a Directed Acyclic Graph (DAG) of sub-tasks, assigns each sub-task to a specialized worker agent, and collects the results.
  - Workers do not communicate directly with each other; all state transitions flow through the supervisor.
- **Strengths:** High controllability, clear ownership, easy observability, centralized rate-limiting and token budgeting.
- **Weaknesses:** Single point of failure (if supervisor hallucinates, entire mission fails); supervisor context window quickly becomes a token bottleneck.

---

### 2.2 Sequential SOP Pipeline (The Assembly Line)
- **Mental Model:** Industrial manufacturing line with strict quality gates (standardized by **MetaGPT** and **ChatDev**).
- **Topology:** Linear directed pipeline.

```mermaid
graph LR
    RFP["Client RFP"] --> A1["Product Manager<br>(Generates PRD)"]
    A1 -->|Schema Gate: Valid PRD| A2["System Architect<br>(Generates RFC / Design)"]
    A2 -->|Schema Gate: Valid OpenAPI| A3["Engineer Agent<br>(Synthesizes Code)"]
    A3 -->|Schema Gate: Code Compiles| A4["QA Critic Agent<br>(Runs Regression Tests)"]
    A4 -->|Pass / Fail Gate| Deploy["Production Deploy"]
```

- **Operational Mechanics:**
  - Standard Operating Procedures (SOPs) are encoded directly into the system.
  - Agent $N+1$ cannot begin until Agent $N$ outputs a verified, typed artifact conforming to a formal schema (e.g. JSON schema, OpenAPI spec, unit test suite).
- **Strengths:** Drastically minimizes error cascades; guarantees enterprise artifact compliance; high reproducibility.
- **Weaknesses:** Rigid and brittle; poorly suited for dynamic exploratory research or ad-hoc tasks requiring iterative backtracking.

---

### 2.3 Peer-to-Peer Swarm & Blackboard Mesh
- **Mental Model:** A trading floor, decentralized open-source community, or academic seminar.
- **Topology:** Fully connected or topic-routed asynchronous network.

```mermaid
graph TD
    subgraph SwarmMesh ["Decentralized EventBus & Blackboard"]
        Bus["High-Throughput Asynchronous EventBus (JSON-RPC / Pub-Sub)"]
        A_Data["Agent: Data Engineer"] <-->|Sub: data.* / Pub: data.clean| Bus
        A_Eng["Agent: Backend Coder"] <-->|Sub: code.* / Pub: code.pr| Bus
        A_Sec["Agent: Red Team SRE"] <-->|Sub: sec.* / Pub: sec.cve| Bus
        A_Doc["Agent: Tech Writer"] <-->|Sub: doc.* / Pub: doc.rfc| Bus
    end
```

- **Operational Mechanics:**
  - Agents subscribe to specific event topics on a shared message bus (e.g., `git.commit`, `pipeline.failed`).
  - Employs classical distributed protocols such as the **Contract Net Protocol (CNP)**: When a task appears, agents calculate capability bids; the task manager awards the contract to the best bidder.
  - Uses **Blackboard Architecture**: A shared memory board where agents asynchronously post partial solutions and refine hypotheses.
- **Strengths:** Maximum flexibility, natural parallelization, dynamic self-organization, zero central bottleneck.
- **Weaknesses:** Susceptible to conversational drift, infinite looping, chaotic emergent behavior, and explosive token consumption without strict round bounds.

---

### 2.4 Anti-Sycophantic Multi-Agent Debate
- **Mental Model:** Supreme Court judicial conference or peer-reviewed scientific referee panel.
- **Topology:** Iterative cyclic adversarial tournament.

```mermaid
sequenceDiagram
    autonumber
    participant Orchestrator as Debate Coordinator
    participant AgentA as Proponent Agent (Advocate)
    participant AgentB as Opponent Agent (Skeptic)
    participant Judge as Synthesis Judge / Arbiter

    Orchestrator->>AgentA: Pose claim: "Should we migrate auth to Passkeys?"
    Orchestrator->>AgentB: Pose same claim under Devil's Advocate instruction
    AgentA-->>Orchestrator: Argument A: Frictionless UX, Phishing-resistant
    AgentB-->>Orchestrator: Counter-Argument B: Legacy browser support, recovery complexity
    Note over Orchestrator: Anonymize Arguments (Strip agent names)
    Orchestrator->>AgentA: Review Counter-Argument B & Rebut
    Orchestrator->>AgentB: Review Argument A & Rebut
    AgentA-->>Orchestrator: Rebuttal A
    AgentB-->>Orchestrator: Rebuttal B
    Orchestrator->>Judge: Pass full debate transcript for synthesis
    Judge-->>Orchestrator: Final Synthesized Decision + Risk Mitigation Matrix
```

- **The Sycophancy Problem:** LLMs exhibit strong sycophancy—they tend to agree with whichever agent or user spoke last, causing multi-agent consensus to collapse into false unanimity.
- **The Anti-Sycophancy Solution:**
  1. **Anonymized Claims:** Arguments are stripped of agent names before cross-critique to prevent prestige bias.
  2. **Bounded Rounds:** Enforcing $K \le 3$ rounds to prevent cyclic fatigue.
  3. **Independent Arbiter:** A separate judge agent evaluates the strength of empirical evidence, calculating a sycophancy penalty score.

---

### 2.5 Liquid Strike Pods (The Acinonyx Enterprise Blueprint)
- **Mental Model:** An elite, cross-functional military or SWAT strike team assembled for an objective, delivering verified outcomes, and disbanding cleanly.
- **Topology:** Ephemeral mission-driven DAG with Level-2 Human Gateways.

```mermaid
graph TD
    Guilds["Corporate Capability Guilds (Persistent Pool)<br>• Executive • Research • Data/AI • Software • QA • Security • FinOps"]
    Mission["Client RFP / Mission Objective"] --> Assembly["1. Dynamic Pod Assembly<br>(Selects: Researcher, Architect, Engineer, QA, Red Team)"]
    Guilds -.->|Provision Agents| Assembly
    
    Assembly --> P0["Phase 0: Market Research & Feasibility"]
    P0 --> P1["Phase 1: PRD & UI Design Spec"]
    P1 --> P2["Phase 2: Architecture RFC & System Interfaces"]
    
    P2 --> Gate1["🛑 LEVEL 2 HUMAN APPROVAL GATE 1<br>(Human Operator Reviews Scope & Architecture)"]
    
    Gate1 -->|Approved| P3["Phase 3: Code Synthesis & Regression Test Pass"]
    P3 --> P4["Phase 4: Chaos Red Team Penetration Test"]
    
    P4 --> Gate2["🛑 LEVEL 2 HUMAN APPROVAL GATE 2<br>(Zero CVE Sign-off & Production State Commit)"]
    
    Gate2 -->|Approved| P5["Phase 5: Tech Docs, FinOps ROI & SHA-256 Merkle Provenance"]
    P5 --> Disband["🎉 AUTO-DISBAND POD<br>(Agents released back to corporate pool, Zero Resource Leaks)"]
    Disband -.-> Guilds
```

- **Architectural Invariants:**
  1. **Dynamic Ephemeral Lifecycle:** Pods exist only for the lifespan of the mission, preventing idle memory footprint.
  2. **Level-2 Human-in-the-Loop Gating:** Read/research actions are autonomous; destructive write/deploy actions halt for human sign-off.
  3. **Cryptographic Merkle Provenance:** Every intermediate deliverable is hashed into a SHA-256 Merkle DAG root, guaranteeing complete auditability.

---

## 3. Comprehensive Topology Trade-Off Matrix

| Coordination Topology | Token Efficiency | Hallucination Resistance | Scalability | Adaptability | Enterprise Compliance |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Hierarchical (Supervisor)** | Medium | High | High | Medium | High |
| **Sequential (SOP Pipeline)** | High | **Very High** | Medium | Low | **Very High** |
| **Peer Swarm (Mesh / Bus)** | Low | Low | **Very High** | **Very High** | Low |
| **Multi-Agent Debate** | Low | **Very High** | Low | Medium | High |
| **Liquid Strike Pods** | **High** | **Very High** | **Very High** | **Very High** | **Highest (SOC2/Merkle)** |
