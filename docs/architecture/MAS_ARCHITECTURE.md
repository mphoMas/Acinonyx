# MAS architecture

MAS has two distinct execution surfaces. The legacy runtime is a development
prototype with known production blockers. The supervised coding swarm is a newer,
bounded workflow for creating and verifying Python functions; it is deliberately
kept outside the legacy dashboard, MCP and tool routes.

```mermaid
flowchart TB
    User[Operator / application] --> Entry[CLI, dashboard, or MCP entry point]

    subgraph Legacy[Legacy MAS runtime — prototype]
        Entry --> Core[Core: messages, agents, EventBus, state]
        Core --> Orch[Orchestration: supervisor, debate, SOP, strike pod]
        Core --> Provider[Provider adapters]
        Core --> Memory[Working, episodic, vector memory]
        Core --> MCP[MCP registry and transport]
        MCP --> Tools[Tools: filesystem, Git, browser, executor, data]
        Core --> Org[Organisation and squad roles]
        Core --> Eval[Golden missions and evaluation harness]
        Core --> Obs[Audit, metrics and configuration]
    end

    Provider --> LLM[Configured model provider]
    Memory --> Store[(Local SQLite / vector data)]
    Tools --> Host[Host services and project workspace]

    subgraph Swarm[Supervised coding swarm — bounded pilot]
        SCLI[mas-swarm CLI] --> Auth[Local tenant, role and token checks]
        Auth --> Coord[Trusted coordinator]
        Coord --> Architect[Architect model call]
        Architect --> Engineer[Engineer model call]
        Engineer --> Worker[Ephemeral restricted Docker worker]
        Worker --> Verify[Host-owned verifier]
        Verify --> Reviewer[Separate reviewer model call]
        Reviewer --> Gate[Separate human approval]
        Gate --> Export[Approved source export]
        Coord --> State[(Signed SQLite state and audit)]
    end

    Coord --> LiveLLM[Live HTTPS model provider]
    Verify -. private expected results .-> State
```

The key boundary is between untrusted agent output and trusted control-plane work.
Agents can propose plans and code; they cannot change identities, tests, budgets,
verification evidence or release approval. Candidate code runs in a temporary
restricted container. The verifier compares output against operator-owned expected
results outside that container.

See the [supervised swarm design](SUPERVISED_SWARM.md) for the exact controls and
the [independent review](../reviews/SUPERVISED_SWARM_REVIEW.md) for tested evidence
and remaining limitations.
