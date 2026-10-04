# Volume 2: AI Architectures & Paradigms
## Chapter 3: Agentic Systems, Cognitive Architectures & Swarm Protocols

> *"An agent is not merely an LLM that calls an API; an agent is a situated, stateful cognitive entity capable of closed-loop observation, dynamic planning, tool actuation, episodic memory consolidation, and self-repair."*

The transition from single-turn Large Language Models to **Autonomous Agentic Systems** represents the modern synthesis of cognitive psychology, distributed computing, and artificial intelligence.

---

## 1. The CoALA Framework: Cognitive Architectures for Language Agents

Formalized by Sumers et al. (Princeton, DeepMind, 2023), the **CoALA (Cognitive Architectures for Language Agents)** framework provides the standard taxonomy for agentic intelligence:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                COALA COGNITIVE SYSTEM                                  │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│             MEMORY MODULES               │               ACTION SPACES                 │
├──────────────────────────────────────────┼─────────────────────────────────────────────┤
│ 1. Working Memory (Context Window)       │ 1. Internal Actions (Planning & Reasoning)  │
│    • Current active state                │    • Subgoal decomposition                  │
│    • Scratchpad, recent observations     │    • Retrospective reflection & self-repair │
│                                          │                                             │
│ 2. Episodic Memory (Experience Log)      │ 2. External Actions (Tool Use & Environment)│
│    • Past trajectories, execution logs   │    • Web search, API invocations            │
│    • Dense vector embedding retrieval    │    • Sandboxed code execution (Python, Bash)│
│                                          │                                             │
│ 3. Semantic Memory (World Knowledge)     │ 3. Inter-Agent Communication                │
│    • Knowledge graphs, documentation     │    • Direct RPC / Task delegation           │
│    • Relational schemas, static docs     │    • Event-bus broadcast & artifact handoff │
│                                          │                                             │
│ 4. Procedural Memory (Skills & Rules)    │                                             │
│    • System prompt instructions          │                                             │
│    • JSON tool schema definitions        │                                             │
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 2. Dynamic Reasoning Loops

### 2.1 The ReAct Paradigm (Reason + Act)
Introduced by Yao et al. (ICLR 2023), **ReAct** interleaves reasoning traces ("Thoughts") with environmental actions ("Actions") and feedback ("Observations"):

```
User Task Objective
         │
         ▼
 ┌───────────────┐
 │    Thought    │ ◄── "I need to query the database to verify active accounts."
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │    Action     │ ──► Tool Call: `execute_sql(query="SELECT count(*) FROM users;")`
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │  Observation  │ ◄── Tool Result: `{"count": 14205}`
 └───────┬───────┘
         │
         ▼
   (Repeat Loop Until Final Answer is Formulated)
```

**Why ReAct Outperforms Pure Act or Pure Reason**:
- *Pure Reasoning (Chain-of-Thought)* suffers from error propagation and factual hallucination because it cannot verify external state.
- *Pure Tool Execution (Act-Only)* lacks tactical planning and struggles to synthesize multi-step observations.
- *ReAct* grounds internal thought steps in external environmental observations, dramatically reducing hallucination rates.

### 2.2 Reflexion: Reinforcement via Verbal Self-Reflection
Shinn et al. (NeurIPS 2023) introduced **Reflexion**, equipping agents with dynamic self-correction:
1. The agent executes an environmental trajectory $\tau_0$.
2. An automated evaluator or compiler returns an error signal (e.g., unit test failure, traceback).
3. The agent generates a verbal self-reflection $r_t$ analyzing *why* the attempt failed:
   > *"Reflection: My previous attempt failed because I assumed the array was 1-indexed. In Python, arrays are 0-indexed, leading to an IndexError on line 24. Next time, I must adjust the loop bounds to range(len(arr))."*
4. The reflection is written into episodic working memory, steering subsequent attempts $\tau_{t+1}$ toward success without requiring fine-tuning weight updates.

---

## 3. Inter-Agent Communication Protocols

As multi-agent ecosystems scale, proprietary ad-hoc JSON messaging yields to formalized open protocols:

```
┌───────────────────────────────────────────────┬───────────────────────────────────────────────┐
│     Model Context Protocol (MCP) — Anthropic   │       Agent2Agent (A2A) — Google Cloud        │
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ • Client-Host-Server architecture             │ • Standardized cross-agent RPC protocol       │
│ • Standardizes how agents discover tools,     │ • Multi-agent task handoff & delegation       │
│   resources, and prompts from external servers│ • Cross-language compatibility (Python/Go)    │
│ • Transports: stdio, Server-Sent Events (SSE) │ • Enterprise security: VPC-SC & mTLS identity │
└───────────────────────────────────────────────┴───────────────────────────────────────────────┘
```

### 3.1 Model Context Protocol (MCP) Primitive Architecture
An MCP host connects agents to external ecosystems via three unified primitives:
1. **Tools**: Executable functions callable by the model (e.g., `execute_sql`, `run_python`, `fetch_web_page`).
2. **Resources**: Read-only structured data sources exposed via URI schemes (e.g., `file:///path/to/doc`, `postgres://db/schema`).
3. **Prompts**: Parameterized reusable prompt templates managed server-side.

### 3.2 Agent2Agent (A2A) Protocol
Pioneered in Google Cloud’s Architecture Center (documented in `/research/google_cloud_agentic_infra`):
- Enables a **Coordinator Agent** running in Vertex AI Reasoning Engine to securely route sub-tasks to specialized domain worker agents running in containerized Cloud Run microservices.
- Enforces strict contract schemas, request-response timeouts, and mutual TLS (mTLS) identity attribution.

---

## 4. Multi-Agent Swarm Topologies

```
A. Centralized Coordinator           B. Hierarchical Tree               C. Liquid Strike Pod (MAS)
       ┌───────────┐                        ┌───────────┐                      ┌─────────────────┐
       │Supervisor │                        │    CEO    │                      │  Pod Supervisor │
       └──┬───┬───┬┘                        └───┬───┬───┘                      └───────┬─────────┘
      ┌───┘   │   └───┐                     ┌───┘   └───┐                              ▼
      ▼       ▼       ▼                     ▼           ▼                      [Dynamic Assembly]
    Agent1  Agent2  Agent3                 VP 1        VP 2                    ┌─────────────────┐
  (Star Topology / Hub-Spoke)           ┌───┴───┐   ┌───┴───┐                  │Cross-Functional │
                                        ▼       ▼   ▼       ▼                  │Workers: Res, Eng│
                                       Eng1   Eng2 QA1     QA2                 │QA, FinOps Critic│
                                                                               └────────┬────────┘
                                                                                        ▼
                                                                               [Disband on Deploy]
```

### 4.1 Liquid Strike Pods (The Acinonyx Enterprise Architecture)
Unlike rigid hierarchical trees (MetaGPT) or chaotic flat group chats (early AutoGen), **Liquid Strike Pods** operate on mission-driven, temporary lifecycles:
1. **Dynamic Assembly**: When a complex objective arrives, the Supervisor dynamically selects specialized agents (e.g., Market Researcher, Chief Architect, Senior Backend Engineer, QA Critic).
2. **Collaborative Execution**: Agents execute in synchronized phases with shared working memory and deterministic tool calling.
3. **Cryptographic Provenance**: Every artifact generated (code, schema, test report) is hashed into a **SHA-256 Merkle Root**, guaranteeing tamper-proof audit trails.
4. **Auto-Disbandment**: Once deliverables pass regression tests and Level-2 Human Approval, the pod disbands, releasing compute and memory resources.

---

## 5. Grounding, Sandboxing & Security Safeguards

Autonomous agents with code execution capabilities introduce profound security vectors (arbitrary code execution, SSRF, data exfiltration). Enterprise agentic architectures enforce strict multi-layer defenses:

```
Agent Proposed Action
         │
         ▼
[ Abstract Syntax Tree (AST) Validation ] ──► Regex & AST scan for forbidden calls:
                                               `subprocess`, `os.system`, `socket`, `eval`, `ctypes`
         │ (Passed)
         ▼
[ Sandboxed Execution Environment ] ────────► gVisor container / isolated sub-process
                                               CPU & memory limits, zero network egress
         │ (Executed)
         ▼
[ Structured Observation Injection ] ───────► Standardized stdout/stderr formatting back to LLM
```
