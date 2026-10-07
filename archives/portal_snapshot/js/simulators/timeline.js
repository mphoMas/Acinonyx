/**
 * portal/js/simulators/timeline.js
 * Chronological Interactive AI Evolution Timeline (1950 – 2026+).
 * 
 * Architect: product_director / MAS Swarm
 */

class AITimeline {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.milestones = [
      {
        year: '1950',
        era: 'The Theoretical Genesis',
        title: 'Turing Test & Computing Machinery',
        desc: 'Alan Turing publishes "Computing Machinery and Intelligence," introducing the Imitation Game and asking: "Can machines think?"',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_01_chronological_history_from_turing_to_agi',
        tags: ['Theory', 'Foundations']
      },
      {
        year: '1956',
        era: 'The Dartmouth Workshop',
        title: 'Birth of Artificial Intelligence',
        desc: 'John McCarthy, Marvin Minsky, Claude Shannon, and Nathaniel Rochester convene at Dartmouth College, officially coining the term "Artificial Intelligence."',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_01_chronological_history_from_turing_to_agi',
        tags: ['Dartmouth', 'Pioneers']
      },
      {
        year: '1957–1969',
        era: 'The First Golden Era',
        title: 'Rosenblatt’s Perceptron & Symbolic Logic',
        desc: 'Frank Rosenblatt develops the Mark I Perceptron at Cornell. Newell and Simon build the Logic Theorist and General Problem Solver (GPS).',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_01_chronological_history_from_turing_to_agi',
        tags: ['Perceptron', 'Symbolic']
      },
      {
        year: '1974–1980',
        era: 'The First AI Winter',
        title: 'Lighthill Report & Combinatorial Explosion',
        desc: 'Sir James Lighthill reports to the UK Science Research Council that AI failed to achieve grand promises; US DARPA funding collapses.',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_02_the_ai_winters_and_revivals',
        tags: ['AI Winter', 'Funding Cuts']
      },
      {
        year: '1980–1987',
        era: 'The Expert Systems Boom',
        title: 'Knowledge Engineering & Lisp Machines',
        desc: 'Rule-based expert systems (XCON/R1, MYCIN) promise millions in corporate savings. Dedicated Lisp hardware titans (Symbolics, LMI) flourish.',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_02_the_ai_winters_and_revivals',
        tags: ['Expert Systems', 'Lisp']
      },
      {
        year: '1987–1993',
        era: 'The Second AI Winter',
        title: 'Collapse of Specialized Hardware',
        desc: 'Commodity 32-bit x86 PCs surpass expensive Lisp machines. Expert systems prove fragile and impossible to maintain at enterprise scale.',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_02_the_ai_winters_and_revivals',
        tags: ['AI Winter 2', 'PC Revolution']
      },
      {
        year: '1997',
        era: 'Superhuman Symbolic Milestones',
        title: 'Deep Blue Defeats Garry Kasparov',
        desc: 'IBM Deep Blue executes 200 million chess board evaluations per second with custom VLSI chips, defeating the reigning World Champion.',
        chapterId: 'ai_encyclopedia_01_history_and_evolution_01_chronological_history_from_turing_to_agi',
        tags: ['Deep Blue', 'Games']
      },
      {
        year: '2012',
        era: 'The Deep Learning Revolution',
        title: 'AlexNet Smashes ImageNet',
        desc: 'Alex Krizhevsky, Ilya Sutskever, and Geoffrey Hinton train an 8-layer Convolutional Neural Network on two NVIDIA GeForce GTX 580 GPUs, halving error rates.',
        chapterId: 'ai_encyclopedia_04_academic_research_and_benchmarks_01_seminal_papers_that_shaped_ai',
        tags: ['AlexNet', 'GPU Compute']
      },
      {
        year: '2017',
        era: 'The Architecture Watershed',
        title: 'Attention Is All You Need (Transformers)',
        desc: 'Vaswani et al. at Google Brain replace recurrent and convolutional architectures with Scaled Dot-Product Self-Attention and Multi-Head Attention.',
        chapterId: 'ai_encyclopedia_02_architecture_and_paradigms_01_foundational_architectures_rnn_cnn_transformer',
        tags: ['Transformers', 'Self-Attention']
      },
      {
        year: '2020–2023',
        era: 'Generative AI & LLM Foundation',
        title: 'GPT-3, Scaling Laws & ChatGPT',
        desc: 'Kaplan et al. and Chinchilla formalize compute-optimal scaling. ChatGPT launches, achieving 100M users in two months and igniting enterprise AI.',
        chapterId: 'ai_encyclopedia_04_academic_research_and_benchmarks_02_scaling_laws_and_compute_optimal_training',
        tags: ['Scaling Laws', 'LLMs']
      },
      {
        year: '2024–2026+',
        era: 'The Agentic Era & Test-Time Compute',
        title: 'Reasoning Models (o1/o3/R1) & Multi-Agent Swarms',
        desc: 'The paradigm shifts from pre-training scaling to test-time inference scaling (MCTS, PRMs, GRPO). Autonomous swarms (MCP, A2A) disrupt enterprise labor into Work-as-a-Service.',
        chapterId: 'agentic_systems_01_frontier_models_and_intelligence_02_reasoning_models_test_time_compute',
        tags: ['Test-Time Compute', 'Agentic Systems', 'WaaS']
      }
    ];
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="sim-header">
        <div class="badge badge-purple">Historical Evolution</div>
        <h2 class="sim-title">Chronological AI History Timeline (1950 – 2026+)</h2>
        <p class="sim-desc">
          Navigate 75+ years of computer science milestones—from Turing’s theoretical foundations, through the brutal AI Winters, to the modern Test-Time Compute and Agentic Swarm revolution.
        </p>
      </div>

      <div class="timeline-container">
        <div class="timeline-line"></div>
        ${this.milestones.map(m => `
          <div class="timeline-milestone" onclick="app.loadDocument('${m.chapterId}')">
            <div class="timeline-dot"></div>
            <div class="timeline-header">
              <span class="timeline-era">${m.era}</span>
              <span class="timeline-year">${m.year}</span>
            </div>
            <div style="font-weight: 700; color: #fff; font-size: 1.05rem; margin-bottom: 4px;">${m.title}</div>
            <p class="timeline-body">${m.desc}</p>
            <div class="timeline-links">
              ${m.tags.map(t => `<span class="tag-chip">${t}</span>`).join('')}
              <span class="tag-chip" style="color: var(--accent-cyan); border-color: rgba(0,240,255,0.3);">Read Encyclopedia Chapter →</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }
}

window.AITimeline = AITimeline;
