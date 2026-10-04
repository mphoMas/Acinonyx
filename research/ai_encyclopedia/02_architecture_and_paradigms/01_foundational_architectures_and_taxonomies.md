# Volume 2: AI Architectures & Paradigms
## Chapter 1: Foundational Architectures & Deep Taxonomy

> *"Architecture is the geometry of computation."*

Modern artificial intelligence is defined by the evolution of deep neural network architectures—from sequential recurrent networks to massively parallelized self-attention Transformers, sparse Mixture-of-Experts (MoE), and sub-quadratic State Space Models (SSMs).

---

## 1. The Architectural Lineage: From Recurrence to Attention

```
Sequential & Recurrent                  Parallel & Attentional                  Sparse & Sub-Quadratic
     (1990–2016)                             (2017–2023)                             (2024–2026+)
┌──────────────────┐                    ┌──────────────────┐                    ┌──────────────────┐
│  RNN, LSTM, GRU  │                    │ Dense Transformer│                    │    Sparse MoE    │
│  $\mathcal{O}(T)$│ ──Parallelization──►  (GPT, Llama)    │ ───Specialization──► (DeepSeek, Mixtral)│
│ Sequential Bottle│                    │ $\mathcal{O}(T^2)│                    │ Active/Total W   │
└──────────────────┘                    └──────────────────┘                    └──────────────────┘
                                                 │                                       ▲
                                                 │ Linear Scaling                        │
                                                 ▼                                       │
                                        ┌──────────────────┐                             │
                                        │ State Space / SSM│ ────────────────────────────┘
                                        │  (Mamba, S4)     │
                                        │  $\mathcal{O}(T)$│
                                        └──────────────────┘
```

---

## 2. The Transformer: Mathematical Anatomy & Evolution

Published in *Attention Is All You Need* (Vaswani et al., 2017), the Transformer removed temporal recurrence, relying entirely on self-attention mechanisms to model global dependencies across sequence tokens in parallel.

### 2.1 Scaled Dot-Product Attention
Given input queries $Q \in \mathbb{R}^{N \times d_k}$, keys $K \in \mathbb{R}^{M \times d_k}$, and values $V \in \mathbb{R}^{M \times d_v}$:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}} + M\right)V$$

Where:
- $\sqrt{d_k}$ is the scaling factor preventing inner products from growing excessively large in high dimensions, which would push the softmax gradient into regions with vanishing gradients.
- $M$ is the attention mask matrix ($M_{ij} = -\infty$ for $j > i$ in autoregressive causal decoding to prevent looking into future tokens).

### 2.2 Multi-Head Attention (MHA) vs. MQA vs. GQA
To allow the model to jointly attend to information from different representation subspaces:

$$\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)W^O$$
$$\text{head}_i = \text{Attention}(QW_i^Q, KW_i^K, VW_i^V)$$

```
Multi-Head Attention (MHA)       Multi-Query Attention (MQA)      Grouped-Query Attention (GQA)
(Standard: 1 KV head per Q)      (Extreme: 1 KV head for ALL Q)   (Modern Standard: 1 KV per G Qs)

Q Q Q Q Q Q Q Q (8 Query)        Q Q Q Q Q Q Q Q (8 Query)        Q Q Q Q Q Q Q Q (8 Query)
│ │ │ │ │ │ │ │                  │ │ │ │ │ │ │ │                  └──┬──┘ └──┬──┘ (2 Groups)
▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼                  └───────┼───────┘                   ▼       ▼
K K K K K K K K (8 Key)                  ▼                         K   K   K   K   (2 Key)
V V V V V V V V (8 Value)                K (1 Key)                 V   V   V   V   (2 Value)
                                         V (1 Value)
[Max Memory, High KV Cache]      [Min Memory, Quality Drop]       [Optimal Memory/Quality Balance]
```

- **Grouped-Query Attention (GQA)** (Ainslie et al., 2023): Standardized in modern foundation models (Llama 3, Mistral, Qwen 2.5). GQA partitions query heads into $G$ groups sharing a single Key-Value head, slashing the Key-Value (KV) cache memory footprint during autoregressive inference by $4\times$ to $8\times$ without degrading perplexity.

### 2.3 Rotary Positional Embeddings (RoPE)
Instead of adding absolute positional embeddings ($x_i = e_i + p_i$), **Rotary Positional Embedding (RoPE)** (Su et al., 2021) encodes relative position by rotating query and key vectors in complex 2D subspaces:

$$\mathbf{R}_{\Theta, m}^d = \text{diag}\left( R_{\theta_1, m}, R_{\theta_2, m}, \dots, R_{\theta_{d/2}, m} \right)$$
$$R_{\theta_i, m} = \begin{pmatrix} \cos(m\theta_i) & -\sin(m\theta_i) \\ \sin(m\theta_i) & \cos(m\theta_i) \end{pmatrix}$$

**Properties**:
- Inner product $\langle \mathbf{R}_m q, \mathbf{R}_n k \rangle$ depends only on the relative distance $m - n$.
- Allows context window extension (via YaRN, RoPE interpolation) from 4K up to 128K–1,000,000 tokens.

### 2.4 IO-Aware Hardware Acceleration: FlashAttention
Traditional self-attention computes $S = QK^T$ and writes the intermediate $N \times N$ attention matrix to High Bandwidth Memory (HBM), incurring massive memory bandwidth bottlenecks.
- **FlashAttention-1, 2, and 3** (Tri Dao et al.): Fuses the attention operation into SRAM using **tiling** and **online softmax rescaling**, computing softmax without materializing the full $N \times N$ matrix in HBM, speeding up training and inference by $2\times$ to $4\times$ with zero loss of numerical precision.

---

## 3. Sparse Mixture-of-Experts (MoE) Architecture

As dense models encountered prohibitive compute scaling costs, **Mixture-of-Experts (MoE)** decoupled total parameter capacity from per-token computational cost.

```
                         Input Token Representation $x$
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
          ┌──────────────────┐                ┌──────────────────┐
          │  Routing / Gating│                │  Shared Experts  │
          │     Network      │                │  (Common Logic)  │
          └─────────┬────────┘                └─────────┬────────┘
                    │ Top-K Routing                     │
          ┌─────────┴─────────┐                         │
          ▼                   ▼                         │
   ┌─────────────┐     ┌─────────────┐                  │
   │  Expert 2   │     │  Expert 7   │                  │
   │   (FFN 2)   │     │   (FFN 7)   │                  │
   └──────┬──────┘     └──────┬──────┘                  │
          │                   │                         │
          └─────────┬─────────┘                         │
                    ▼                                   │
             Weighted Sum                               │
                    │                                   │
                    ▼                                   ▼
             Combined Token Representation Output ◄─────┘
```

### 3.1 Mathematical Formulation of MoE
In an MoE layer, the standard feed-forward network (FFN) is replaced by $N$ independent expert networks $\{E_i\}_{i=1}^N$ gated by a routing function $G(x)$:

$$y = \sum_{i=1}^N G(x)_i E_i(x)$$

Where the top-$K$ routing function is defined as:

$$G(x) = \text{Softmax}\left(\text{TopK}\left(H(x), K\right)\right)$$
$$H(x)_i = (x \cdot W_g)_i + \epsilon, \quad \epsilon \sim \mathcal{N}(0, \sigma^2)$$

### 3.2 Fine-Grained MoE & Multi-Head Latent Attention (MLA)
Pioneered by **DeepSeek-V3 / DeepSeek-R1**:
1. **Fine-Grained Expert Segmentation**: Rather than routing between 8 large experts (activating 2), DeepSeek divides parameters into **256 micro-experts**, activating **8 routed experts** alongside **1 dedicated shared expert** that processes every token. This drastically enhances specialized knowledge isolation.
2. **Multi-Head Latent Attention (MLA)**: Compresses the Key-Value cache into a low-dimensional latent vector via low-rank projection:
   $$c_t^{KV} = W^{DKV} h_t$$
   MLA achieves a **$93.3\%$ reduction in KV cache memory**, allowing frontier 671B parameter models to serve massive concurrent context windows on standard GPU clusters.

---

## 4. Alternative Sequence Paradigms: State Space Models (SSMs)

While Transformers have $\mathcal{O}(T^2)$ computational complexity and $\mathcal{O}(T)$ memory growth with sequence length $T$, **State Space Models (SSMs)** offer $\mathcal{O}(T)$ linear time complexity and $\mathcal{O}(1)$ constant memory during inference.

### 4.1 Continuous-Time State Space Equations
Mapped from classical control theory:

$$h'(t) = \mathbf{A}h(t) + \mathbf{B}x(t)$$
$$y(t) = \mathbf{C}h(t) + \mathbf{D}x(t)$$

Discretized using zero-order hold (ZOH) with step size $\Delta$:

$$\bar{\mathbf{A}} = \exp(\Delta \mathbf{A})$$
$$\bar{\mathbf{B}} = (\Delta \mathbf{A})^{-1}(\exp(\Delta \mathbf{A}) - \mathbf{I}) \cdot \Delta \mathbf{B}$$
$$h_t = \bar{\mathbf{A}}h_{t-1} + \bar{\mathbf{B}}x_t, \quad y_t = \mathbf{C}h_t + \mathbf{D}x_t$$

### 4.2 Mamba: Selective State Spaces (Gu & Dao, 2023)
Traditional linear time-invariant (LTI) SSMs (S4) could not perform content-based reasoning because matrices $\mathbf{A}, \mathbf{B}, \mathbf{C}$ remained static regardless of the input.
- **Mamba Innovation**: Makes matrices $\mathbf{B}$, $\mathbf{C}$, and parameter $\Delta$ explicit functions of input token $x_t$ (**Selective SSM**).
- **Hardware-Aware Parallel Scan**: Leverages GPU SRAM kernel fusion to compute recurrence across long sequences without materializing hidden states in HBM.

---

## 5. Architectural Comparison Matrix

| Property | Transformer (Dense) | Transformer (Sparse MoE) | State Space Model (Mamba) | Hybrid (Transformer + SSM) |
| :--- | :--- | :--- | :--- | :--- |
| **Inference Compute / Token** | Fixed $\mathcal{O}(P_{\text{total}})$ | Reduced $\mathcal{O}(P_{\text{active}})$ | Fixed $\mathcal{O}(P_{\text{total}})$ | Balanced |
| **KV Cache Footprint** | $\mathcal{O}(B \cdot L \cdot D)$ (Large) | $\mathcal{O}(B \cdot L \cdot D)$ (Reduced via MLA) | $\mathcal{O}(1)$ (Zero KV Cache) | Small / Partial |
| **In-Context Retrieval** | Perfect Associative Recall | High Associative Recall | Degradation on Needle-in-Haystack | High |
| **Training Parallelism** | Massive | High (Requires Expert Parallelism) | Massive (via Parallel Scan) | High |
| **Production Exemplars** | Llama 3.3 (70B), GPT-4 (early) | DeepSeek-V3, Mixtral 8x22B, Gemini | Mamba-2, Jamba | Jamba 1.5, Nemotron-4 |
