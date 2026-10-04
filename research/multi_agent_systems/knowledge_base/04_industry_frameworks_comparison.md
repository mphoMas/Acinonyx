# Industry Multi-Agent Frameworks Comparison
*An architectural evaluation comparing AutoGen, CrewAI, LangGraph, MetaGPT, ChatDev, and Acinonyx MAS.*

---

## 1. High-Level Comparison Matrix

| Framework | Creator / Backing | Primary Topology | Communication Primitive | Memory System | Code Execution Sandbox | Provenance & Audit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AutoGen** | Microsoft Research | Conversable GroupChat | Multi-turn dialog turns | Conversational history / Cache | Docker / Native Python | Basic telemetry logs |
| **CrewAI** | CrewAI Inc. | Hierarchical / Sequential | Task output passing | Memory buffers (ChromaDB) | Subprocess execution | Logging callbacks |
| **LangGraph** | LangChain | StateGraph DAG / Cyclic | Shared central state dict | Checkpointers (Postgres / Sqlite) | Tool node execution | LangSmith traces |
| **MetaGPT** | DeepWisdom | Role-based SOP DAG | Structured documents & publish-subscribe | Message queue + Doc memory | Local shell / Docker | Git commits |
| **ChatDev** | Tsinghua / Brown | Waterfall phase chats | Chat chain between two roles | Phase memory boards | Subprocess interpreter | Visual chat logs |
| **Acinonyx MAS** | Acinonyx Labs | **Liquid Strike Pods + Capability Guilds** | **Typed EventBus + MCP Protocol** | **CoALA (Working + Episodic Reflexion + Vector RAG)** | **MCP Sandboxed Runner with AST Import Denial** | **SHA-256 Merkle Root + Durable JSONL Audit** |

---

## 2. In-Depth Architectural Profiles

### A. AutoGen (Microsoft)
- **Strengths**: High flexibility; conversable agents can represent both LLMs, tools, and human-in-the-loop users; excellent integration with Jupyter notebooks and code interpreters.
- **Weaknesses**: Unstructured group chats suffer from conversational drift and high token consumption; difficult to enforce strict corporate compliance gates.

### B. MetaGPT (DeepWisdom)
- **Strengths**: Replaces free-form chit-chat with Standard Operating Procedures (SOPs). Employs software engineering roles (Product Manager, Architect, Project Manager, Engineer, QA) generating typed deliverables (PRD, System Design, File List, Code).
- **Weaknesses**: Rigid sequential flow makes ad-hoc problem solving harder; heavily tailored to software generation over general-purpose business workflows.

### C. LangGraph (LangChain)
- **Strengths**: First-class support for cyclic graphs, branching logic, state persistence, and human approval interrupts; highly programmable.
- **Weaknesses**: Lower-level primitive requiring developers to manually design every node, transition edge, and state schema from scratch.

### D. Acinonyx MAS (This Repository)
- **Strengths**:
  - Implements the complete **CoALA cognitive architecture** (perceive, episodic reflection, procedural tools, grounded evidence).
  - Native **Model Context Protocol (MCP)** integration for secure tool execution.
  - **Liquid Strike Pods**: Ephemeral cross-functional squads pulled from 7 persistent Capability Guilds, executing 5-phase delivery with Level 2 Human Gates and auto-disbanding to eliminate resource leaks.
  - **FinOps 2.0 & Merkle Provenance**: Guarantees supply chain tamper-evidence and cost tracking per mission.
