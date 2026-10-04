# Cognitive Architectures for Language Agents (CoALA)
*Based on the seminal framework by Sumers, Yao, Narasimhan, and Griffiths (Princeton / Stanford / DeepMind).*

---

## 1. Motivation: Grounding LLMs in Cognitive Science
Traditional LLMs operate as passive text-in, text-out probability distributions. To function as autonomous agents capable of sustained reasoning, planning, and tool usage across long horizons, they must be augmented with structured cognitive memory, perception, and action spaces.

CoALA organizes language agents into four foundational modules:
1. **Working Memory (WM)**
2. **Long-Term Memory (LTM)**
3. **Action Space & External Environment**
4. **Decision Cycle & Reasoning Loop**

```
                     ┌────────────────────────┐
                     │   External Environment │
                     └───────────┬────────────┘
                                 │ Perception
                                 ▼
                     ┌────────────────────────┐
                     │     Working Memory     │◄─────┐
                     │ (Context + Goals + WM) │      │
                     └───────────┬────────────┘      │
                                 │                   │ LTM
            ┌────────────────────┴──────────────┐    │ Retrieval
            ▼                                   ▼    │
┌────────────────────────┐         ┌─────────────────┴──────┐
│     Decision Cycle     │         │   Long-Term Memory     │
│ (Reasoning & Planning) │         │ • Episodic (Past Runs) │
└───────────┬────────────┘         │ • Semantic (Knowledge) │
            │                      │ • Procedural (Tools)   │
            ▼ Internal/External    └────────────────────────┘
┌────────────────────────┐
│      Action Space      │
│ • Tool Execution (MCP) │
│ • State Updates / Msg  │
└────────────────────────┘
```

---

## 2. Memory Taxonomy

### A. Working Memory (Short-Term Scratchpad)
- **Role**: Active context window holding immediate goals, perception inputs, scratch thoughts, and intermediate tool results.
- **Constraints**: Bounded token capacity; managed via eviction strategies, sliding windows, and hierarchical summarization.

### B. Episodic Memory (Experience & Trajectories)
- **Role**: Records timestamped histories of past actions, successes, failures, and verbal critiques.
- **Cognitive Mechanism**: *Reflexion* (Shinn et al.). Agents generate verbal self-reflections on task failure, store them as episodic records, and retrieve them via semantic similarity during subsequent attempts to prevent repeating mistakes.

### C. Semantic Memory (Factual & World Knowledge)
- **Role**: Generalized domain knowledge, schemas, documents, and rules that exist independently of specific task episodes.
- **Mechanism**: Vector RAG (Retrieval-Augmented Generation), knowledge graphs, and embedded document chunks.

### D. Procedural Memory (Skills & Tool Schemas)
- **Role**: "How-to" knowledge detailing available actions, code libraries, tool signatures (MCP schemas), and operational prompts.

---

## 3. Decision Cycle & The ReAct Loop

### The ReAct Pattern (Reasoning + Acting)
Introduced by Yao et al., ReAct interleaves chain-of-thought reasoning with real-world tool execution:
1. **Thought**: Agent analyzes current working memory and articulates a sub-goal.
2. **Action**: Agent emits a structured tool call (e.g., `run_python` or `web_search`).
3. **Observation**: Environment/tool returns output; observation is appended to working memory.
4. **Repeat**: Loop iterates until agent possesses sufficient information to formulate final answer.

### Reflexion & Verbal Reinforcement Learning
Rather than updating model weights (which is slow and compute-heavy), the agent updates its memory weights via verbal reinforcement:
$$\text{Trajectory } \tau = (s_0, a_0, o_0, \dots, s_T) \quad \to \quad \text{Critique } c = \mathcal{M}_{\text{eval}}(\tau) \quad \to \quad \text{Store in Episodic Memory}$$
On subsequent runs:
$$\text{Prompt} = \text{System} + \text{Few-Shot Episodic Reflections} + \text{User Task}$$
This achieves significant performance jumps (e.g. +30% on HumanEval / AlfWorld) without fine-tuning.
