# Volume 2: AI Architectures & Paradigms
## Chapter 2: Training, Alignment, and the Reasoning Revolution

> *"Alignment is not about restricting what a model can do; it is about steering its high-dimensional capabilities toward truth, utility, and verifiable reasoning."*

The lifecycle of a modern frontier model spans three distinct thermodynamic phases: **Large-Scale Unsupervised Pre-training**, **Post-Training Alignment**, and **Inference-Time (Test-Time) Reasoning**.

---

## 1. Phase 1: Pre-training (Causal Language Modeling)

During pre-training, the model compresses vast cross-lingual internet corpora, code repositories, and mathematical texts into continuous weight matrices.

```
Raw Internet Corpora (15T+ Tokens)
                 │
                 ▼
[ Deduplication & Heuristic Filtering ] (MinHash, CCNet, Perplexity Filtering)
                 │
                 ▼
[ Safety & Quality Filtering ] (Synthetic Augmentation, UltraChat, Cosmopedia)
                 │
                 ▼
[ Autoregressive Next-Token Prediction ]
  $\mathcal{L}_{\text{CLM}}(\theta) = -\sum_{t=1}^T \log P(x_t \mid x_{<t}; \theta)$
                 │
                 ▼
Base Foundation Model (Stochastic World Simulator)
```

### 1.1 Mathematical Objective
For a sequence of tokens $\mathbf{x} = (x_1, \dots, x_T)$, the causal language modeling objective minimizes the cross-entropy loss:

$$\mathcal{L}_{\text{CLM}}(\theta) = -\frac{1}{T} \sum_{t=1}^T \log P_\theta(x_t \mid x_1, \dots, x_{t-1})$$

Where token probabilities are parameterized by the final softmax projection over vocabulary $\mathcal{V}$:

$$P_\theta(x_t \mid x_{<t}) = \frac{\exp(h_t^T w_{x_t})}{\sum_{v \in \mathcal{V}} \exp(h_t^T w_v)}$$

### 1.2 Optimization Dynamics
- **Optimizer**: AdamW ($\beta_1 = 0.9, \beta_2 = 0.95, \epsilon = 10^{-8}, \text{weight\_decay} = 0.1$).
- **Learning Rate Schedule**: Cosine decay with linear warmup (typically 2,000–5,000 warmup steps decaying to $10\%$ of peak learning rate).
- **Batch Size Scaling**: Dynamic batch size ramping from 2M tokens up to 16M+ tokens per gradient step to maintain gradient signal-to-noise ratio as loss decreases.

---

## 2. Phase 2: Post-Training Alignment

While a pre-trained base model can complete text, it cannot reliably follow instructions, converse helpfully, or refrain from generating toxic content. Post-training converts a completion engine into a compliant, aligned assistant.

```
       Base Pre-trained Model
                 │
                 ▼
[ Supervised Fine-Tuning (SFT) ]  ◄── High-Quality Multi-Turn Demonstrations
                 │
                 ▼
         Instruct Model
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
[ RLHF / PPO ]       [ Direct Preference Optimization (DPO) ]
(Critic + Reward)     (Implicit Reward via Closed-Form Policy)
      │                     │
      └──────────┬──────────┘
                 ▼
        Aligned Assistant
```

### 2.1 Supervised Fine-Tuning (SFT)
The model is trained on curated human and synthetic instruction-response pairs $\mathcal{D}_{\text{SFT}} = \{(x^{(i)}, y^{(i)})\}$:

$$\mathcal{L}_{\text{SFT}}(\theta) = -\sum_{(x, y)} \sum_{t=1}^{|y|} \log P_\theta(y_t \mid x, y_{<t})$$

Loss is masked over the user prompt $x$, training gradients only on the assistant's response tokens $y$.

### 2.2 Classical RLHF with PPO (Proximal Policy Optimization)
Introduced by Christiano et al. (2017) and standardized in InstructGPT (Ouyang et al., 2022):
1. **Reward Modeling**: Train a scalar reward model $r_\psi(x, y)$ on pairwise preferences $(y_w \succ y_l)$:
   $$\mathcal{L}_R(\psi) = -\mathbb{E}_{(x, y_w, y_l)} \left[ \log \sigma \left( r_\psi(x, y_w) - r_\psi(x, y_l) \right) \right]$$
2. **Policy Optimization via PPO**: Optimize policy $\pi_\theta$ to maximize expected reward while penalizing divergence from the reference policy $\pi_{\text{ref}}$:
   $$\max_\theta \mathbb{E}_{x \sim \mathcal{D}, y \sim \pi_\theta} \left[ r_\psi(x, y) - \beta D_{\text{KL}}(\pi_\theta(y \mid x) \parallel \pi_{\text{ref}}(y \mid x)) \right]$$

*Disadvantages*: Requires maintaining four massive models in GPU memory simultaneously (Actor $\pi_\theta$, Critic $V_\phi$, Reference $\pi_{\text{ref}}$, Reward $r_\psi$), making PPO unstable and resource-intensive.

### 2.3 Direct Preference Optimization (DPO)
Rafailov et al. (2023) derived an exact closed-form substitution that expresses the ground-truth reward implicitly in terms of the optimal policy:

$$r(x, y) = \beta \log \frac{\pi_\theta(y \mid x)}{\pi_{\text{ref}}(y \mid x)}$$

Substituting into the Bradley-Terry preference model yields the **DPO Loss**, completely eliminating the reward model and critic:

$$\mathcal{L}_{\text{DPO}}(\theta) = -\mathbb{E}_{(x, y_w, y_l)} \left[ \log \sigma \left( \beta \log \frac{\pi_\theta(y_w \mid x)}{\pi_{\text{ref}}(y_w \mid x)} - \beta \log \frac{\pi_\theta(y_l \mid x)}{\pi_{\text{ref}}(y_l \mid x)} \right) \right]$$

---

## 3. Phase 3: The Reasoning Revolution & Group Relative Policy Optimization (GRPO)

In late 2024 and early 2025, a paradigm shift occurred: models began developing autonomous, internal multi-step Chain-of-Thought (CoT) reasoning capabilities trained directly on objective verification rules.

### 3.1 The GRPO Algorithm (DeepSeek-Math & DeepSeek-R1)
**Group Relative Policy Optimization (GRPO)** eliminates the Value/Critic network of traditional PPO, achieving massive memory savings:

```
For Each Query $q$:
Sample $G$ Candidate Outputs: $\{o_1, o_2, \dots, o_G\} \sim \pi_{\theta_{\text{old}}}(O \mid q)$
                    │
                    ▼
Compute Rule-Based Rewards: $\{r_1, r_2, \dots, r_G\}$
(Accuracy: Math proof / Unit test pass; Format: Strict <think>...</think> tags)
                    │
                    ▼
Normalize Advantages Within Group:
$A_i = \frac{r_i - \text{mean}(\mathbf{r})}{\text{std}(\mathbf{r})}$
                    │
                    ▼
Update Policy $\pi_\theta$ using Clipped Surrogate Gradient + KL Penalty
```

### 3.2 The GRPO Objective Function
$$\mathcal{J}_{\text{GRPO}}(\theta) = \mathbb{E}_{q, \{o_i\}_{i=1}^G} \left[ \frac{1}{G} \sum_{i=1}^G \left( \min \left( \frac{\pi_\theta(o_i \mid q)}{\pi_{\theta_{\text{old}}}(o_i \mid q)} A_i, \text{clip}\left(\frac{\pi_\theta(o_i \mid q)}{\pi_{\theta_{\text{old}}}(o_i \mid q)}, 1-\epsilon, 1+\epsilon\right) A_i \right) - \beta D_{\text{KL}}(\pi_\theta \parallel \pi_{\text{ref}}) \right) \right]$$

Where the advantage $A_i$ is computed purely relative to the peer group of responses generated for that exact prompt.

### 3.3 The "Aha Moment" in R1-Zero
When DeepSeek trained a base model purely using GRPO without any human demonstration data (SFT cold start), the model autonomously learned to allocate test-time compute:
- Generating thousands of hidden `<think>` tokens.
- Backtracking when a mathematical step yielded an inconsistency (*"Wait, let me double check this equation... Ah, that is incorrect, let me restart"*).
- Verifying candidate solutions against boundary conditions before returning the final answer.

---

## 4. Test-Time Compute (Inference Scaling Laws)

Traditionally, model performance was bounded by **Pre-training Compute** ($C_{\text{train}} \approx 6 N D$). The new frontier shows that performance scales logarithmically with **Inference (Test-Time) Compute**:

$$\text{Accuracy} \propto \alpha \log(\text{Tokens}_{\text{reasoning}}) + \beta \log(\text{Search Candidates})$$

```
                   TEST-TIME SEARCH STRATEGIES
┌─────────────────────────────────┬─────────────────────────────────┐
│     Dense Generation Search     │    Step-Level Guided Search     │
├─────────────────────────────────┼─────────────────────────────────┤
│ • Best-of-N (Sample N, pick max)│ • Tree of Thoughts (ToT)        │
│ • Self-Consistency Voting       │ • Monte Carlo Tree Search (MCTS)│
│ • Verifier Re-ranking (ORM)     │ • Process Reward Models (PRMs)  │
└─────────────────────────────────┴─────────────────────────────────┘
```

### Process Reward Models (PRMs) vs. Outcome Reward Models (ORMs)
- **Outcome Reward Model (ORM)**: Evaluates only the final answer at the end of the sequence. If an answer is wrong, the model cannot distinguish whether the error occurred on step 1 or step 10.
- **Process Reward Model (PRM)** (Lightman et al., 2023): Scores every intermediate reasoning step $\hat{r}(s_t)$, providing fine-grained credit assignment and enabling guided beam search and tree pruning during test-time inference.
