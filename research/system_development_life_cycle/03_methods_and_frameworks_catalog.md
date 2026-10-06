# Master Catalog of SDLC Methods, Frameworks & Standards

> **Acinonyx Enterprise Systems Research Directorate**  
> **Compendium Series:** System Development Life Cycle (SDLC)  
> **Module Code:** `RES-SDLC-2026-CH03`  
> **Purpose:** Operational Reference Encyclopedia, Schemas, Templates, and Architectural Patterns

---

## Index of Framework Categories

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SDLC METHODS & FRAMEWORKS TAXONOMY                   │
└────────────────────────────────────────────────────────────────────────┘
 1. PROCESS & AGILE       2. ARCHITECTURE         3. DATAOPS & ANALYTICS
 ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
 │ • Extreme Prog (XP) │ │ • Spec-Driven (SDD) │ │ • DataOps Framework │
 │ • Scrum Framework   │ │ • Domain-Driven(DDD)│ │ • Data Contracts    │
 │ • Kanban & Lean     │ │ • The C4 Model      │ │ • dbt Testing Matrix│
 │ • Shape Up          │ │ • ADR Methodology   │ │ • Great Expectations│
 └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
 4. SECURITY & GRC        5. DELIVERY & SRE       6. AGENTIC & AI-NATIVE
 ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
 │ • NIST SSDF 800-218 │ │ • GitOps (ArgoCD)   │ │ • Multi-Agent Debate│
 │ • STRIDE / PASTA    │ │ • SRE & Error Budget│ │ • Reflexion Loops   │
 │ • SLSA Supply Chain │ │ • DORA 4 & SPACE    │ │ • Eval-Driven (EDD) │
 │ • Sigstore / Cosign │ │ • Team Topologies   │ │ • Sandboxed Verif   │
 └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

---

## 1. Process & Agile Engineering Frameworks

### 1.1 Extreme Programming (XP)
* **Creator / History:** Kent Beck (1996, Chrysler Comprehensive Compensation System).
* **Core Philosophy:** If a practice is good, take it to the extreme (e.g., if code review is good, review code constantly via pair programming; if testing is good, test continuously via TDD).
* **The 12 Canonical Practices:**
  1. *Test-Driven Development (TDD):* Write unit tests before writing functional code.
  2. *Pair Programming:* Two engineers (or one engineer and an AI agent) collaborate on one workstation.
  3. *Continuous Integration (CI):* Integrate and test code into the mainline several times a day.
  4. *Refactoring:* Continuous restructuring of code without changing external behavior to minimize technical debt.
  5. *Small Releases:* Deploy valuable increments to production in rapid, short cycles.
  6. *Simple Design:* Build only what is needed today; satisfy all tests, maximize clarity, eliminate duplication.
  7. *System Metaphor / Ubiquitous Language:* Shared naming conventions mapping directly to domain concepts.
  8. *Collective Code Ownership:* Any team member can modify any part of the codebase at any time.
  9. *Coding Standards:* Strict formatting and linting conventions across all repositories.
  10. *Sustainable Pace:* 40-hour workweeks; elimination of overtime-driven crunch culture.
  11. *On-Site Customer:* Continuous direct access to domain experts and business stakeholders.
  12. *Planning Game:* Rapid alignment between business priorities and technical cost estimates.

### 1.2 The Scrum Framework
* **Creators:** Ken Schwaber & Jeff Sutherland (1995).
* **Structure:**
  - **Roles:** Product Owner (defines *what* and prioritizes), Scrum Master (coaches process and removes blockers), Developers (builds the increment).
  - **Ceremonies:** Sprint Planning, Daily Scrum (15 min), Sprint Review (demo), Sprint Retrospective, Backlog Refinement.
  - **Artifacts:** Product Backlog, Sprint Backlog, Potentially Releasable Product Increment.
* **Modern Best Practice (Eliminating "Water-Scrum-Fall"):**  
  Every sprint *must* culminate in code that is tested, verified, and ready for production deployment. Avoid deferring testing or integration to subsequent "hardening" sprints.

### 1.3 Kanban & Lean Software Development
* **Foundational Principles (Mary & Tom Poppendieck):**
  1. *Eliminate Waste (Muda):* Eliminate handoff queues, partially done work, extra features, and defects.
  2. *Amplify Learning:* Short feedback loops through automated testing.
  3. *Decide as Late as Possible:* Keep architectural options open until empirical evidence emerges.
  4. *Deliver as Fast as Possible:* Optimize cycle time and lead time.
  5. *Empower the Team:* Push decision-making to the people doing the work.
  6. *Build Integrity In:* Quality is an intrinsic property of the process, not an afterthought.
  7. *See the Whole:* Optimize the entire value stream, not localized developer output.
* **Little’s Law in Software Delivery:**
  $$\text{Cycle Time} = \frac{\text{Work-In-Progress (WIP)}}{\text{Throughput}}$$
  To reduce the time it takes for a feature to reach production, an organization must strictly reduce Work-in-Progress (WIP) limits rather than demanding engineers work faster.

### 1.4 Shape Up (Basecamp Framework)
* **Creator:** Ryan Singer / Basecamp (2019).
* **Core Mechanisms:**
  - **6-Week Cycles:** Dedicated build periods where teams work uninterrupted without daily standups or backlog grooming.
  - **2-Week Cool-Down:** Buffer period between cycles for bug fixing, exploring ideas, and technical debt remediation.
  - **Appetite vs. Estimates:** Instead of asking "how long will this feature take?", leadership asks "how much time do we want to invest in this problem?" (e.g., a "2-week appetite" vs. a "6-week appetite").
  - **Shaping & Pitching:** Senior architects "shape" the work at the right level of abstraction (rough wireframes, clear boundaries, solved technical rabbit holes) before presenting it to the Betting Table.
  - **The Circuit Breaker:** If a project does not ship within its allocated 6-week appetite, it does not get an automatic extension. It is stopped, reviewed, and re-pitched if still valuable, preventing runaway projects.

---

## 2. Architecture & Contract-Driven Frameworks

### 2.1 Spec-Driven Development (SDD) & Contract-First Design
* **Philosophy:** The formal interface specification is the primary, version-controlled source of truth. Implementation code, client SDKs, mock servers, and automated contract tests are all compiled downstream from the specification.
* **Core Standards:**
  - **OpenAPI 3.1:** For RESTful HTTP/JSON APIs.
  - **JSON Schema Draft 2020-12:** For message payloads, event bus validation, and configuration files.
  - **Protocol Buffers v3 (Protobuf):** For high-throughput gRPC services and binary microservice communication.
  - **AsyncAPI 3.0:** For event-driven architectures (Kafka, RabbitMQ, WebSockets).

### 2.2 The C4 Model for Visualizing Software Architecture
* **Creator:** Simon Brown.
* **Hierarchical Zoom Levels:**
  1. **Level 1: System Context Diagram:** High-level view showing how the system interacts with external users and third-party systems.
  2. **Level 2: Container Diagram:** High-level technical architecture showing deployable units (e.g., React frontend, Python API, BigQuery warehouse, Redis cache).
  3. **Level 3: Component Diagram:** Internal structure of a container, identifying modular services, controllers, repositories, and interfaces.
  4. **Level 4: Code Diagram:** Low-level class or entity diagrams (typically auto-generated by IDEs or AST tools).

### 2.3 Architectural Decision Records (ADRs)
* **Standard:** Michael Nygard ADR Template.
* **Directory Standard:** `/docs/adr/NNNN-title.md`
* **Canonical Schema:**
  ```markdown
  # ADR-0012: Adoption of BigQuery Partitioning & Clustering for Transactions Mart

  ## Status
  Accepted (Date: 2026-10-05)

  ## Context
  The core transactions mart has scaled past 500 million rows (180 GB). Full table 
  scans in Looker Studio are incurring $45/query in BigQuery on-demand analysis fees 
  and exceeding 45-second latency SLAs.

  ## Decision
  We will re-materialize `analytics_marts.fct_transactions` as an incremental table 
  partitioned daily by `transaction_timestamp` and clustered by `[client_id, status]`.

  ## Consequences
  - Positive: Looker queries filtered by client and date range will scan < 200 MB (< $0.01/query).
  - Positive: P95 dashboard latency reduced from 45s to 1.8s.
  - Negative: Upstream dbt model execution time increases by 2.5 minutes during the initial full-refresh build.
  ```

---

## 3. DataOps & Analytics Engineering Frameworks

### 3.1 The Modern DataOps Framework
* **Definition:** An automated, process-oriented methodology used by data analytics and engineering teams to improve the quality, cycle time, and governance of data products.
* **Core Capabilities:**
  - Version control for all transformation logic (`.sql`, `.py`, `.yml`).
  - Automated continuous integration testing on ephemeral data environments.
  - Automated data lineage graph generation (Dataplex / dbt docs).
  - Data observability and anomaly detection (volume, freshness, schema drift).

### 3.2 Data Contracts Specification
* **Definition:** A formal agreement between data producers (application engineering teams) and data consumers (data engineering, BI, and ML teams).
* **Reference Data Contract Schema (`data-contract.yml`):**
  ```yaml
  version: 1.0.0
  dataset: transactions_feed
  owner: payments_core_team
  sla:
    freshness: 15 minutes
    availability: 99.9%
  schema:
    - name: transaction_id
      type: string
      primary_key: true
      nullable: false
    - name: client_id
      type: string
      nullable: false
    - name: amount_cents
      type: integer
      minimum: 0
    - name: currency
      type: string
      pattern: "^[A-Z]{3}$"
    - name: status
      type: string
      enum: ["PENDING", "COMPLETED", "FAILED", "REVERSED"]
  quality_checks:
    - type: row_count_anomaly
      threshold_z_score: 3.0
  ```

---

## 4. Security, Governance & Supply Chain Frameworks

### 4.1 NIST SP 800-218 (Secure Software Development Framework - SSDF v1.2)
* **Published by:** National Institute of Standards and Technology (NIST).
* **The 4 Practice Groups:**
  1. **PO (Prepare the Organization):** Define security requirements, toolsets, and training.
  2. **PS (Protect the Software):** Protect code integrity, enforce code reviews, sign commits, generate SBOMs.
  3. **PW (Produce Well-Secured Software):** Design software to meet security requirements, review designs, test executable code for vulnerabilities (SAST/DAST).
  4. **RV (Respond to Vulnerabilities):** Identify and patch zero-days, disclose vulnerabilities responsibly, perform root cause post-mortems.

### 4.2 Threat Modeling Methodologies: STRIDE & PASTA
* **STRIDE (Microsoft):**
  - **S - Spoofing:** Pretending to be someone else. (*Mitigation: Strong authentication, mutual TLS*).
  - **T - Tampering:** Modifying data or code. (*Mitigation: Digital signatures, cryptographic integrity hashes, immutable logs*).
  - **R - Repudiation:** Claiming you didn't do something. (*Mitigation: Append-only audit logs, digital signatures*).
  - **I - Information Disclosure:** Leaking confidential data. (*Mitigation: Encryption in transit & at rest, least privilege IAM*).
  - **D - Denial of Service:** Making systems unavailable. (*Mitigation: Rate limiting, autoscaling, caching, DDoS protection*).
  - **E - Elevation of Privilege:** Gaining unauthorized administrative control. (*Mitigation: Role-Based Access Control, zero-trust sandboxing*).
* **PASTA (Process for Attack Simulation and Threat Analysis):**
  A 7-step risk-centric threat modeling framework aligning technical vulnerabilities directly with business impact and regulatory risks.

### 4.3 Supply-chain Levels for Software Artifacts (SLSA)
* **Goal:** End-to-end provenance and tampering prevention across the build and release pipeline.
  - **SLSA Level 1:** Build process is automated and generates provenance showing how the artifact was created.
  - **SLSA Level 2:** Build runs in an authenticated, isolated hosted build platform (e.g., GitHub Actions / Cloud Build) with signed provenance.
  - **SLSA Level 3:** Build environment is completely isolated and ephemeral; build definitions are immutable; provenance is cryptographically non-falsifiable (via Sigstore/Cosign).

---

## 5. Modern Delivery, SRE & Organizational Frameworks

### 5.1 GitOps Framework
* **Pillars (OpenGitOps Standard):**
  1. *Declarative:* The entire system is described declaratively (YAML/Kubernetes/Terraform).
  2. *Versioned & Immutable:* The canonical desired state is version-controlled in Git.
  3. *Pulled Automatically:* Software agents (ArgoCD, Flux) pull the desired state automatically.
  4. *Continuously Reconciled:* Software agents continuously monitor runtime state and actively reconcile drift back to the Git baseline.

### 5.2 Site Reliability Engineering (SRE)
* **Foundational Equations:**
  $$\text{Service Level Indicator (SLI)} = \frac{\text{Good Events}}{\text{Total Events}} \times 100\%$$
  $$\text{Error Budget} = 100\% - \text{Service Level Objective (SLO)}$$
* **The Error Budget Policy:**
  - If a service has $99.9\%$ SLO, its error budget is $0.1\%$.
  - When the error budget is $> 0\%$, the team is free to ship new features at maximum velocity.
  - When the error budget is depleted ($0\%$), all feature work stops. 100% of engineering bandwidth pivots to architectural stability, performance tuning, and technical debt elimination.

### 5.3 Team Topologies (Skelton & Pais, 2019)
* **The 4 Fundamental Team Types:**
  1. *Stream-Aligned Team:* Cross-functional product unit aligned directly to customer value streams.
  2. *Platform Team:* Internal provider delivering self-service developer infrastructure, CI/CD, and compute.
  3. *Enabling Team:* Expert coaches who temporarily embed to upskill stream-aligned teams in new technologies (e.g., AI tooling, DataOps).
  4. *Complicated-Subsystem Team:* Deep specialists owning specialized, high-math or cryptographic engines.
* **The 3 Interaction Modes:**
  - *Collaboration:* Two teams work closely together for a brief, defined period to discover new patterns.
  - *X-as-a-Service:* One team provides a service or API consumed self-service by other teams with zero meetings.
  - *Facilitating:* One team coaches or clears hurdles for another.

---

## 6. Frontier Agentic & AI-Augmented Frameworks (2026)

### 6.1 Multi-Agent Debate (MAD) with Anti-Sycophancy Scoring
* **Purpose:** Overcoming the fatal flaw of single-LLM sycophancy (where an AI agent agrees with previous bad code or inaccurate claims).
* **Protocol:**
  - Independent agents generate divergent candidate solutions anonymously.
  - A designated Contrarian Agent is explicitly prompted to find edge-case failures, security flaws, and performance bottlenecks.
  - A Judge / Synthesizer agent evaluates the debate transcript and produces a unified, verified consensus.
  - Sycophancy is dynamically scored based on semantic divergence across rounds ($K \le 3$).

### 6.2 Reflexion: Verbal Reinforcement Learning Architecture
* **Paper:** Shinn et al. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning*. NeurIPS.
* **Workflow:**
  1. *Execution:* Agent generates code and executes it in a sandboxed runtime.
  2. *Evaluation:* Sandboxed compiler captures stdout, stderr, and test failures.
  3. *Self-Reflection:* Agent generates a verbal reflection analyzing *why* the hypothesis failed, storing the failure pattern in episodic memory.
  4. *Memory-Grounded Re-attempt:* The agent re-executes the task with the episodic reflection injected into working context, achieving $2\times$ higher task resolution on complex coding benchmarks.

### 6.3 Evaluation-Driven Development (EDD)
* **Principle:** In the age of AI coding assistants, code is cheap and disposable; evaluation harnesses are precious and permanent.
* **Methodology:**
  Before deploying an autonomous agent squad to build a feature, human architects author the **Evaluation Suite** (unit test suites, boundary mocks, performance assertions, security fuzzers). The agent squad is tasked with driving the evaluation pass rate from $0\%$ to $100\%$. The evaluation suite acts as the deterministic mathematical bounds for the AI's creativity.

---

*Compiled and published by Project ACINONYX Research Directorate.*
