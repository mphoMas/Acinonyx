# 📚 Google Cloud Certified: Professional Agentic Architect — Master Syllabus

This syllabus directly maps the official Google Cloud Certification Exam Guide (`professional_agentic_architect_exam_guide_english.pdf`) to modular engineering lessons, practical terminal labs, and Google Cloud architectural equivalents.

---

## Module 1: Building Agents Using Low-Code Tools (~13% Exam Weight)

### 1.1 State-Based Workflows and Behavior
* **Mental Model:** Why pure prompt-driven LLM chatbots fail in enterprise production (non-deterministic routing, hallucinated next steps). How finite-state machines (FSM) bring mathematical determinism to generative AI.
* **Google Cloud Stack:** Gemini Enterprise Agent Designer, Customer Experience Agent Studio (CX Agent Studio).
* **Key Primitives:**
  * **Pages:** The isolated conversational context representing a specific state (e.g., `IntakePage`, `VerificationPage`, `EscalationPage`).
  * **Transition Routes:** Deterministic logic that determines when and how an agent moves from Page A to Page B based on user intent, slot fulfillment, or conditional expressions.
  * **Event Handlers:** Fallback logic executed when unexpected events occur (e.g., `sys.no-match-1`, `sys.no-input-2`, timeout, unhandled tool error).
* **System Instructions & In-Console Prompting:**
  * Few-shot prompting vs. zero-shot prompting in enterprise contexts.
  * Chain-of-thought (CoT) system instruction templates.

### 1.2 Enterprise Data Ingestion & Multimodal Grounding
* **Google Cloud Stack:** Gemini Enterprise, Agent Search (Vertex AI Search).
* **Key Primitives:**
  * Grounding agents on proprietary enterprise structured/unstructured documents (PDFs, confluence, databases).
  * Multimodal ingestion: parsing screenshots, audio recordings, and video feeds directly into the state workflow.

---

## Module 2: Using Coding Agents for Application Development (~17% Exam Weight)

### 2.1 Coding Agents & Tool Integration
* **Mental Model:** The shift from passive code generation to autonomous tool-using coding agents.
* **Google Cloud Stack:** Antigravity (CLI, SDK, App), Claude Code on Google Cloud, Cloud Workstations, Google Kubernetes Engine (GKE).
* **Key Primitives:**
  * **Model Context Protocol (MCP):** Open protocol standardizing how agents discover, authenticate, and call external tools and resources over JSON-RPC 2.0.
  * **Sandboxing:** Isolating agent code execution using Linux namespaces (Bubblewrap `bwrap`), unprivileged users, and containerized runtimes.
  * **Automated Code Operations:** Automated AST refactoring, runtime optimization, and dependency vulnerability patching.

### 2.2 Enterprise Customization of Coding Agents
* **Antigravity Customization Architecture:**
  * Custom Skills (`SKILL.md`), plugins, extension hooks, and workspace rules (`RULE.md`).
  * Hierarchical Subagent delegation (`invoke_subagent`, `define_subagent`).
  * The `Agents CLI` toolchain in Google Cloud.

---

## Module 3: Developing Custom Agents (~33% Exam Weight — The Core)

### 3.1 Designing and Building Agentic Workflows in Code
* **Model Strategy:**
  * Large Language Models (LLM) vs. Small Language Models (SLM).
  * Self-hosted (vLLM, Ollama) vs. Managed SaaS (Gemini 1.5 Pro / Flash).
  * Open-source (OSS) vs. Proprietary models (Cost, Latency, Data Privacy, Sovereignty).
* **Agent Frameworks:** Google Agent Development Kit (ADK).
* **Memory Architecture:**
  * Working Memory (sliding-window FIFO context, pinned instructions, token budgeting).
  * Managed Sessions and Persistent Memory Banks.

### 3.2 Enterprise RAG & Vector Retrieval Systems
* **Google Cloud Stack:** Vector Search 1.0 (Vertex AI Vector Search), Agent Retrieval, Agent Identity.
* **Key Primitives:**
  * Dense vector embeddings, subword token hashing, cosine similarity metrics.
  * $k$-Nearest Neighbors ($k$-NN) search, approximate nearest neighbors (ANN), reranking models.
  * Custom integration layers for managed databases (BigQuery, Cloud SQL, Firestore).

### 3.3 Multi-Agent Orchestration & Topologies
* **Protocols:** Model Context Protocol (MCP) and Agent2Agent (A2A).
* **Orchestration Patterns:**
  * **Sequential Pipelines:** Deterministic SOP pipelines.
  * **Parallel Execution:** Concurrent specialist evaluation.
  * **Hierarchical Supervisor DAGs:** Directed Acyclic Graphs with dependency resolution.
  * **Dialectical Anti-Sycophancy Debate:** Proponent (Thesis) vs Adversary (Antithesis) vs Adjudicator (Synthesis).

---

## Module 4: Evaluating and Deploying Agentic Workflows (~22% Exam Weight)

### 4.1 Evaluation Frameworks & Continuous Testing
* **Evaluation Methodologies:** Golden test sets, edge case test suites, regression gating.
* **Google Cloud Stack:** ADK evaluation tooling (`evalset`), Agent Platform Gen AI evaluation service, custom autoraters (LLM-as-a-Judge).
* **Automated GitOps:** Scaffolding CI/CD pipelines (.github/workflows, .gitlab-ci) and pre-commit test gates.
* **Visual Regression:** Playwright automated browser testing, pixel-by-pixel diff masks, and RMSE scoring.

### 4.2 Production Workloads & Deployment Runtimes
* **Runtime Selection:** Choosing between Google Cloud Run (serverless event-driven agents), Google Kubernetes Engine (GKE - persistent, high-throughput swarms), and Agent Runtime.
* **Runtime Diagnostics:** Diagnosing agent reasoning loops, tool invocation latency, context drift, and hallucinations.

---

## Module 5: Securing and Governing Agentic Workflows (~15% Exam Weight)

### 5.1 Security Architecture & Authentication
* **Agent Identity:** Principal Access Boundary (PAB) policies, service account scoping, OAuth 2.0 token propagation.
* **Google Cloud Model Armor:** Real-time prompt injection filtering, jailbreak detection, sensitive data redaction (PII/PHI).
* **Agent Gateway:** Centralized reverse proxy monitoring agent traffic, telemetry logging, and rate limiting.

### 5.2 Governance & Cost Management
* **Rate Limits & Circuit Breakers:** Request-per-minute (RPM) circuit breakers protecting against infinite tool loops.
* **Spend Ceilings:** Token quotas per engagement and cumulative budgets.
* **Safety Switches:** Staged preview vs armed live execution interlocks.
* **Human-in-the-Loop (HITL):** Transactional state machine approval gates.
