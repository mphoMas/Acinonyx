# Multi-Agent Systems (MAS) Research & Design Knowledge Base

This repository contains curated textbooks, foundational academic papers, architectural surveys,
and design patterns for building autonomous multi-agent systems and enterprise swarm frameworks.

## 📚 Curated PDF Library

| Document | Category | Authors / Source | Status |
| :--- | :--- | :--- | :--- |
| **[Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations](pdfs/Multiagent_Systems_Algorithmic_Game_Theoretic_Shoham_LeytonBrown.pdf)**<br>*The definitive graduate-level textbook uniting distributed artificial intelligence, game theory, mechanism design, multi-agent learning, and logical theories of belief and intention.* | `Foundational Textbook` | Yoav Shoham (Stanford) & Kevin Leyton-Brown (UBC) (Cambridge University Press (532 pages)) | ✅ Downloaded (3.73 MB) |
| **[Cognitive Architectures for Language Agents (CoALA)](pdfs/CoALA_Cognitive_Architectures_for_Language_Agents.pdf)**<br>*Proposes a landmark unified blueprint structuring language agents into Working Memory, Episodic/Semantic/Procedural Long-Term Memory, Perception, Action, and Internal Reasoning cycles.* | `Cognitive Architecture` | Theodore R. Sumers, Shunyu Yao, Karthik Narasimhan, Thomas L. Griffiths (Princeton / DeepMind) (arXiv:2309.02427) | ✅ Downloaded (2.66 MB) |
| **[AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](pdfs/AutoGen_Multi_Agent_Conversation_Framework.pdf)**<br>*Multi-agent conversational architecture enabling customizable, conversable agents that integrate LLMs, human input, and tool execution in dynamic conversation topologies.* | `Framework & Architecture` | Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Chi Wang et al. (Microsoft Research) (arXiv:2308.08155) | ✅ Downloaded (3.41 MB) |
| **[MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework](pdfs/MetaGPT_Meta_Programming_Multi_Agent_Collaboration.pdf)**<br>*Encodes human Standard Operating Procedures (SOPs) into multi-agent workflows, utilizing structured communication interfaces (PRDs, architecture diagrams, data APIs) to reduce cascades of errors.* | `Software Engineering MAS` | Sirui Hong, Mingchen Zhuge, Jonathan Chen, Xiawu Zheng, Chenglin Wu et al. (arXiv:2308.00352) | ✅ Downloaded (15.98 MB) |
| **[Communicative Agents for Software Development](pdfs/ChatDev_Communicative_Agents_for_Software_Development.pdf)**<br>*Simulates a virtual software company with CEO, CPO, CTO, Programmer, and Reviewer chatting through multi-turn waterfall and agile phases (designing, coding, testing, documenting).* | `Virtual Software Enterprise` | Chen Qian, Wei Liu, Hongning Wang, Cheng Yang, Zhiyuan Liu, Maosong Sun et al. (Tsinghua) (arXiv:2307.07924) | ✅ Downloaded (3.32 MB) |
| **[Large Language Model based Multi-Agents: A Survey of Progress and Challenges](pdfs/LLM_Based_Multi_Agents_Survey_Progress_Challenges.pdf)**<br>*Exhaustive survey categorizing LLM-MAS agent profiling, communication topologies, environment interaction, collective intelligence mechanisms, and evaluation benchmarks.* | `Comprehensive Survey` | Taicheng Guo, Xiuying Chen, Yaqi Wang, Ruidi Chang, Shichao Pei et al. (arXiv:2402.01680) | ✅ Downloaded (1.19 MB) |
| **[A Survey on Large Language Model based Autonomous Agents](pdfs/LLM_Autonomous_Agents_Survey.pdf)**<br>*Surveys the architecture of autonomous agents: profiling, memory mechanisms, planning (feedback vs non-feedback), action execution (tool usage), and application ecosystems.* | `Foundational Survey` | Lei Wang, Chen Ma, Xueyang Feng, Zeyu Zhang, Hao Yang, Jingsen Zhang et al. (Frontiers of Computer Science / arXiv:2308.11432) | ✅ Downloaded (5.52 MB) |
| **[A Survey on LLM-based Multi-Agent System: Recent Advances and New Frontiers in Application](pdfs/LLM_MultiAgent_Advances_Frontiers_Survey.pdf)**<br>*Analyzes latest advancements in multi-agent collaboration, game-theoretic negotiation, agent simulation in open environments, and self-improving agent swarms.* | `Frontier Survey` | Haoyuan Peng, Shengjie Zhang, Yuntian Chen et al. (arXiv:2412.17481) | ✅ Downloaded (0.39 MB) |

---

## 🏛️ Core Multi-Agent Architectural Patterns

### 1. Classical Foundations (Shoham & Leyton-Brown)
- **Game Theory & Mechanism Design**: Nash equilibria, Pareto optimality, auction mechanisms (Vickrey-Clarke-Groves), and voting protocols.
- **Logical Frameworks**: BDI (Belief-Desire-Intention) architectures, epistemic logics, and distributed consensus.
- **Communication & Interaction**: Speech act theory (KQML, FIPA-ACL), contract net protocols (CNP), and blackboard systems.

### 2. Cognitive Architectures for Language Agents (CoALA)
- **Working Memory**: Dynamic scratchpad maintaining immediate context, active goals, and perception inputs.
- **Long-Term Memory Hierarchy**:
  - *Episodic Memory*: Past trajectories, experiences, and reflections for few-shot in-context learning.
  - *Semantic Memory*: Grounded domain knowledge, vector embeddings, and knowledge graph facts.
  - *Procedural Memory*: System prompts, available tool schemas, and operational workflows.
- **Action Space**: Internal actions (reasoning, reflection, memory retrieval) vs. External actions (MCP tool execution, environment changes, inter-agent messaging).

### 3. Multi-Agent Conversation Topologies (AutoGen & MetaGPT)
- **Hierarchical / Supervisor-Worker**: Centralized orchestrator decomposing complex RFPs into DAG sub-tasks dispatched to specialized agents.
- **Peer-to-Peer / Joint Collaboration**: Communicative agents sharing a typed event bus (e.g., Architect -> Engineer -> QA Critic -> Red Team).
- **Standard Operating Procedures (SOPs)**: Enforcing strict artifacts (PRD, OpenAPI specs, test reports) at handover gates to prevent error cascade.
- **Reflexion & Critique Loops**: Iterative self-correction with bounded rounds ($K \le 3$) and independent verification before state commits.

### 4. [Multi-Agent Tooling & The MCP Fabric](knowledge_base/05_multi_agent_tooling_and_mcp_fabric.md)
- **Theoretical Foundations**: CoALA internal ($\mathcal{A}_{\text{internal}}$) vs external ($\mathcal{A}_{\text{external}}$) action space decomposition, Toolformer, and Gorilla.
- **Formal Definitions**: Precise mathematical contracts for **Function** ($\Sigma_{\text{in}}, \Sigma_{\text{out}}, \mathcal{P}_{\text{pre}}, \mathcal{P}_{\text{post}}, \mathcal{J}_{\text{scope}}$) versus **Usage** ($\mathcal{R}_{\text{caller}}, \mathcal{T}_{\text{phase}}, \mathcal{M}_{\text{sync}}, \mathcal{C}_{\text{finops}}$).
- **Comprehensive Audit**: 9 operational categories auditing all 24 implemented MAS tools versus 18 critical missing enterprise tools (BigQuery, GCS, dbt, A2A delegation, knowledge vault RAG).

---
*Curated for Acinonyx Labs Autonomous Agentic Swarm Engineering.*