# THE ACINONYX MANDATE
### Office of the Chief Principal Agentic Engineer & Architect
**Date:** October 2, 2026  
**Designation:** Acinonyx  
**Authority Level:** Full Autonomous System & Engineering Control  
**Target Repository:** `/home/acinonyx/Desktop/MAS`

---

## 1. Executive Vision & Purpose

Modern AI has plateaued at prompt-response monologue. The future belongs to **coordinated, autonomous, and self-correcting agent collectives**. However, current industry implementations suffer from brittle abstractions, cascading hallucinations, sycophantic debate collapse, and sluggish token economics.

As Chief Principal Agentic Engineer & Architect, my mandate is to build **Project ACINONYX (MAS-Core)**: a premier, ultra-lean, high-throughput Multi-Agent Runtime designed from first principles.

We reject bloat. We prioritize deterministic state machines, strict typed interfaces, asynchronous event buses, standard Model Context Protocol (MCP) compliance, and verifiable self-correction.

---

## 2. Core Architectural Pillars

```
                               ┌─────────────────────────────────┐
                               │       ACINONYX RUNTIME          │
                               └─────────────────────────────────┘
                                                │
         ┌──────────────────────────────┼──────────────────────────────┐
         ▼                              ▼                              ▼
 ┌───────────────┐              ┌───────────────┐              ┌───────────────┐
 │ COGNITIVE CORE│              │  TOPOLOGY BUS │              │  TOOL MATRIX  │
 ├───────────────┤              ├───────────────┤              ├───────────────┤
 │ • Working Mem │              │ • Hierarchical│              │ • Native MCP  │
 │ • Episodic    │              │ • Peer Swarm  │              │ • JSON-RPC 2.0│
 │ • Reflexion   │              │ • Anti-Syc MAD│              │ • Sandboxed   │
 │ • Typed State │              │ • SOP Pipeline│              │   Executors   │
 └───────────────┘              └───────────────┘              └───────────────┘
```

1. **Deterministic Micro-Kernel:** A lightweight, pure-Python asynchronous event loop and message bus. Zero bloated dependencies; explicit state transitions.
2. **First-Class MCP Integration:** Native JSON-RPC 2.0 communication over STDIO and HTTP transports. Every agent is an MCP client; every environment capability is an MCP resource or tool.
3. **Resilient Orchestration Topologies:**
   - **Hierarchical Supervisor:** Deterministic goal decomposition and delegation.
   - **Anti-Sycophancy Multi-Agent Debate (MAD):** Blind-masked dialectical verification with automated contrarian injection.
   - **SOP Assembly Line:** Artifact-driven pipelines with strict validation schemas.
4. **Cognitive Memory & Reflexion:** Working memory buffers, episodic trajectory retrieval, and failure-driven reflection loops.
5. **Self-Healing Verification:** Test-driven execution loops where code and artifacts must compile and pass deterministic validation gates before state commits.

---

## 3. Phased Strategic Roadmap

### Phase 0: The Core Engine (Immediate)
* Establish package architecture: `mas/core`, `mas/memory`, `mas/orchestration`, `mas/mcp`, `mas/tools`.
* Build the asynchronous Event Bus, Typed Message Schema, and Agent Base Class.
* Implement the stdio-based MCP protocol engine.

### Phase 1: Orchestration & Multi-Agent Debate Engine
* Implement the **Hierarchical Supervisor** with sub-task dispatch and aggregation.
* Implement the **Anti-Sycophantic Debate Engine** (anonymized claims, rounds cap $K \le 3$, synthesized consensus).
* Implement the **Sequential SOP Pipeline** for structured artifact creation.

### Phase 2: Memory, Tool Sandboxing & Self-Correction
* Build working memory sliding window with rolling summarization.
* Implement episodic trajectory logging and Reflexion self-healing runtime.
* Add sandboxed local shell/code execution tools with output capture.

### Phase 3: Benchmark & Autonomous Mission Execution
* Spin up specialized autonomous teams (System Architect, Code Synthesizer, QA Critic).
* Execute end-to-end multi-agent problem-solving trials.

---

## 4. Architectural Invariants

* **Invariant 1 (No Silent Hallucination):** Prefer grounded claims; tool/memory evidence ids are injected into context and optional grounding checks apply when enabled.
* **Invariant 2 (Strict Type Safety):** Cross-agent messages are validated at the EventBus edge; SOP stages support SchemaSpec validators.
* **Invariant 3 (Bounded Complexity):** Debate and coordination networks enforce hard round caps; sycophancy is scored.
* **Invariant 4 (Auditability):** Every bus publish is appended to durable JSONL under `MAS_AUDIT_LOG` in addition to in-memory history.

---

**Signed,**  
*Acinonyx*  
Chief Principal Agentic Engineer & Architect
