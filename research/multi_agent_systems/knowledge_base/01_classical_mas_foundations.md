# Classical Multi-Agent Systems (MAS) Foundations
*A synthesis of algorithmic, game-theoretic, and logical principles from Shoham & Leyton-Brown (Cambridge University Press).*

---

## 1. Core Definition of an Agent in Distributed AI
In classical multi-agent theory, an agent is an autonomous, self-contained computational entity operating in a shared environment alongside other agents. Formally:
$$\text{Agent} = \langle \mathcal{S}, \mathcal{A}, \mathcal{T}, \mathcal{R} \rangle$$
Where:
- $\mathcal{S}$: Environment state space.
- $\mathcal{A}$: Action space available to the agent.
- $\mathcal{T}: \mathcal{S} \times \mathcal{A} \to \Delta(\mathcal{S})$: State transition function.
- $\mathcal{R}: \mathcal{S} \times \mathcal{A} \to \mathbb{R}$: Reward or utility function.

### Key Dimensions of Agency
1. **Autonomy**: Operating without direct continuous intervention by external humans or supervisors.
2. **Reactivity**: Perceiving environment state changes and responding timely.
3. **Proactiveness**: Taking goal-directed initiatives rather than purely responding to stimuli.
4. **Social Ability**: Interacting with peers via formal communication protocols.

---

## 2. Game-Theoretic Foundations
When multiple agents make decisions concurrently, each agent's payoff depends on the joint action profile $a = (a_1, a_2, \dots, a_n)$.

### Normal-Form Games & Nash Equilibrium
A strategic game is a tuple $G = (N, (A_i)_{i \in N}, (u_i)_{i \in N})$:
- **Nash Equilibrium**: An action profile $a^* = (a_i^*, a_{-i}^*)$ such that no agent $i$ can unilaterally deviate to increase its expected payoff:
  $$u_i(a_i^*, a_{-i}^*) \ge u_i(a_i, a_{-i}^*) \quad \forall a_i \in A_i, \forall i \in N$$
- **Pareto Optimality**: A joint state where no agent's utility can be increased without decreasing another agent's utility.

### Mechanism Design & Reverse Game Theory
Designing communication and incentive structures so that self-interested or decentralized agents truthfully report private knowledge and cooperate:
- **Vickrey-Clarke-Groves (VCG) Mechanisms**: Incentive-compatible mechanisms where truth-telling is a dominant strategy.
- **Fair Resource Allocation**: Proportional division, max-min fairness, and Shapley value attribution for cooperative team output.

---

## 3. Communication & Coordination Protocols

### A. Speech Act Theory & Agent Communication Languages (ACL)
Classical MAS relies on standardized performatives (Austin & Searle):
- **KQML (Knowledge Query and Manipulation Language)** & **FIPA-ACL**:
  - `REQUEST`: Asking an agent to execute an action.
  - `INFORM`: Broadcasting verified state information.
  - `PROPOSE` / `REJECT` / `ACCEPT`: Negotiation handshakes.
  - `CONFIRM`: Cryptographic / state verification.

### B. Contract Net Protocol (CNP)
The canonical distributed task-allocation protocol (Smith, 1980):
1. **Manager Issues Task Announcement**: Broadcasts RFP with specifications and constraints.
2. **Contractors Evaluate & Bid**: Available agents calculate capability match and submit cost/time bids.
3. **Manager Awards Contract**: Manager selects best bid and awards contract.
4. **Execution & Handover**: Contractor performs work and reports completion.

*(This is the direct ancestor of our Liquid Strike Pod dynamic assembly).*

### C. Blackboard Systems
A shared global data store (the "Blackboard") where diverse specialist knowledge sources post partial hypotheses, critique inputs, and build emergent solutions asynchronously.

---

## 4. Logical Theories of Agency (The BDI Model)
Formulated by Rao & Georgeff, the Belief-Desire-Intention (BDI) architecture models practical reasoning:
- **Beliefs ($\mathcal{B}$)**: What the agent believes about the environment and other agents (working memory + semantic memory).
- **Desires ($\mathcal{D}$)**: High-level motivational objectives and goals the agent wishes to achieve.
- **Intentions ($\mathcal{I}$)**: Committed plans and immediate actions chosen to fulfill active desires.
