# Volume 5: Education, Curricula & Courses
## Chapter 3: Master Self-Study Roadmap — From Novice to AI Research Engineer

> *"The highest mastery of AI is achieved not by reading high-level API documentation, but by implementing algorithms from scratch in raw code, verifying convergence, and scaling them on distributed silicon."*

This curriculum outlines a 6-phase journey to progress from computer programming fundamentals to frontier AI research engineering and multi-agent system design.

---

## The 6-Phase Progression Map

```
Phase 1: Mathematical Foundations ──► Linear Algebra, Multivariable Calculus, Probability & Info Theory
                 │
                 ▼
Phase 2: Scientific Python & Data  ──► NumPy, Vectorized Computation, PyTorch Autograd Engine
                 │
                 ▼
Phase 3: Deep Learning Foundations ──► Micrograd, Multi-Layer Perceptrons, CNNs, LSTMs from Scratch
                 │
                 ▼
Phase 4: Modern LLM Engineering    ──► NanoGPT, Multi-Head Attention, RoPE, LoRA/PEFT, vLLM Serving
                 │
                 ▼
Phase 5: Autonomous Agent Systems  ──► CoALA Framework, ReAct Loops, MCP Protocol, Multi-Agent Swarms
                 │
                 ▼
Phase 6: Frontier Post-Training    ──► DPO, GRPO Reasoning Chains, Mechanistic Interpretability (SAEs)
```

---

## Phase 1: Mathematical & Algorithmic Foundations (Weeks 1 – 6)

### Core Competencies
- **Linear Algebra**: Matrix multiplications, eigenvalues and eigenvectors, singular value decomposition (SVD), positive semi-definite matrices, vector projection.
- **Multivariable Calculus**: Partial derivatives, gradient vectors, Jacobians, Hessians, multivariate chain rule, directional derivatives.
- **Probability & Statistics**: Bayes' Theorem, conditional expectation, maximum likelihood estimation (MLE), maximum a posteriori (MAP), Kullback-Leibler (KL) divergence, cross-entropy.
- **Key Reference Text**: *Mathematics for Machine Learning* (Deisenroth, Faisal, Ong).

---

## Phase 2: Scientific Python & Tensors (Weeks 7 – 10)

### Hands-On Milestones
1. **NumPy from Scratch**: Implement matrix multiplication, convolution operations, and numerical gradients using raw NumPy broadcasting without third-party frameworks.
2. **Build an Autograd Engine**: Code an automatic differentiation computational graph engine from scratch (reproducing Andrej Karpathy's `micrograd`).
3. **Data Pipelines**: Master Hugging Face `datasets` with streaming mode, tokenization with Hugging Face `tokenizers` (Byte-Pair Encoding - BPE).

---

## Phase 3: Classical Deep Learning & Representation (Weeks 11 – 16)

### Hands-On Milestones
1. **Computer Vision**: Implement a ResNet-18 architecture in pure PyTorch with custom training loops, mixed-precision FP16, and data augmentation.
2. **Sequence Modeling**: Build an LSTM-based character-level language model capable of generating Shakespearean sonnets.
3. **Representation Learning**: Implement Word2Vec (Skip-Gram with negative sampling) and visualize word vector embeddings using t-SNE or UMAP.

---

## Phase 4: Modern Transformer & LLM Engineering (Weeks 17 – 24)

### Hands-On Milestones
1. **Build `nanoGPT` from Scratch**:
   - Implement Scaled Dot-Product Attention, Multi-Head Attention (MHA), and Grouped-Query Attention (GQA).
   - Integrate Rotary Positional Embeddings (RoPE).
   - Implement SwiGLU activation functions and RMSNorm.
2. **Parameter-Efficient Fine-Tuning (PEFT)**:
   - Implement Low-Rank Adaptation (LoRA) from scratch: $W' = W + \frac{\alpha}{r} (B \times A)$.
   - Fine-tune an open 7B/8B model (Llama 3 or Qwen 2.5) on a specialized coding instruction dataset using QLoRA (4-bit quantization).
3. **High-Throughput Production Serving**:
   - Deploy models with **vLLM**, configuring PagedAttention, continuous batching, and tensor parallelism across multiple GPUs.

---

## Phase 5: Autonomous Multi-Agent Architectures (Weeks 25 – 32)

### Hands-On Milestones
1. **The ReAct Execution Loop**: Implement a dual-mode ReAct loop capable of parsing both structured native JSON tool calls and raw text thoughts/actions.
2. **Sandboxed Code Execution**: Build an execution sandbox with Abstract Syntax Tree (AST) validation to block unsafe system operations (`subprocess`, `eval`, `socket`).
3. **Model Context Protocol (MCP)**: Build and connect an MCP server exposing external tools (database queries, web search) to an agent.
4. **Liquid Strike Pod Swarm**: Design a multi-agent swarm (Coordinator, Architect, Engineer, QA Critic) that collaborates via an event bus and outputs deliverables verified by cryptographic Merkle root hashes.

---

## Phase 6: Frontier Post-Training & Research Engineering (Weeks 33+)

### Hands-On Milestones
1. **Direct Preference Optimization (DPO)**: Implement the DPO loss function in PyTorch; align an instruction model using human preference datasets.
2. **Group Relative Policy Optimization (GRPO)**: Implement DeepSeek-style GRPO:
   - Sample candidate outputs in groups of $G$.
   - Calculate group-relative normalized advantage scores $A_i$.
   - Train on verifiable math proofs (GSM8K/MATH) with reward verifiers.
3. **Mechanistic Interpretability**:
   - Train a Sparse Autoencoder (SAE) with an L1 sparsity penalty on an intermediate layer of a language model.
   - Extract and inspect monosemantic feature directions using dictionary learning.
