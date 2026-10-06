/**
 * portal/js/simulators/benchmark_matrix.js
 * Interactive Frontier Model Benchmark & Economics Comparative Matrix.
 * 
 * Architect: qa_critic / MAS Swarm
 */

class BenchmarkMatrix {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.activeFilter = 'ALL';
    this.sortCol = 'swe';
    this.sortAsc = false;

    this.models = [
      {
        name: 'OpenAI o1',
        org: 'OpenAI',
        category: 'reasoning',
        isOpen: false,
        swe: 48.9,
        math500: 96.4,
        gpqa: 75.7,
        aime: 83.3,
        mmluPro: 79.2,
        context: '200K',
        costIn: '$15.00',
        costOut: '$60.00',
        badge: 'Proprietary'
      },
      {
        name: 'OpenAI o3-mini (High)',
        org: 'OpenAI',
        category: 'reasoning',
        isOpen: false,
        swe: 49.3,
        math500: 97.9,
        gpqa: 79.7,
        aime: 87.3,
        mmluPro: 81.5,
        context: '200K',
        costIn: '$1.10',
        costOut: '$4.40',
        badge: 'High Value'
      },
      {
        name: 'Claude 3.5 Sonnet (v2)',
        org: 'Anthropic',
        category: 'agentic',
        isOpen: false,
        swe: 49.0,
        math500: 78.3,
        gpqa: 65.0,
        aime: 38.0,
        mmluPro: 78.0,
        context: '200K',
        costIn: '$3.00',
        costOut: '$15.00',
        badge: 'Tool Calling'
      },
      {
        name: 'DeepSeek-R1 (671B MoE)',
        org: 'DeepSeek',
        category: 'reasoning',
        isOpen: true,
        swe: 49.2,
        math500: 97.3,
        gpqa: 71.5,
        aime: 79.8,
        mmluPro: 84.0,
        context: '128K',
        costIn: '$0.55',
        costOut: '$2.19',
        badge: 'Open Weights'
      },
      {
        name: 'Gemini 2.0 Pro',
        org: 'Google',
        category: 'agentic',
        isOpen: false,
        swe: 48.1,
        math500: 90.8,
        gpqa: 72.3,
        aime: 68.2,
        mmluPro: 79.8,
        context: '2M',
        costIn: '$1.25',
        costOut: '$5.00',
        badge: '2M Context'
      },
      {
        name: 'Llama 3.3 70B Instruct',
        org: 'Meta',
        category: 'open',
        isOpen: true,
        swe: 37.8,
        math500: 73.1,
        gpqa: 54.2,
        aime: 28.5,
        mmluPro: 71.4,
        context: '128K',
        costIn: '$0.15',
        costOut: '$0.60',
        badge: 'Enterprise Open'
      },
      {
        name: 'Qwen 2.5 Coder 32B',
        org: 'Alibaba',
        category: 'coding',
        isOpen: true,
        swe: 43.1,
        math500: 83.2,
        gpqa: 58.0,
        aime: 42.0,
        mmluPro: 73.0,
        context: '128K',
        costIn: '$0.10',
        costOut: '$0.40',
        badge: 'Code SLM'
      }
    ];
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="sim-header">
        <div class="badge badge-emerald">Empirical Benchmarks</div>
        <h2 class="sim-title">Frontier Model Benchmark & Token Economics Matrix</h2>
        <p class="sim-desc">
          Compare leading test-time compute reasoners, agentic coding models, and open-weights titans 
          across SWE-bench Verified, MATH 500, GPQA Diamond, AIME 2024, and inference pricing.
        </p>
      </div>

      <div class="benchmark-card">
        <div class="benchmark-filters">
          <button class="filter-chip ${this.activeFilter === 'ALL' ? 'active' : ''}" onclick="benchMatrix.setFilter('ALL')">All Models (7)</button>
          <button class="filter-chip ${this.activeFilter === 'reasoning' ? 'active' : ''}" onclick="benchMatrix.setFilter('reasoning')">Reasoning / Test-Time (3)</button>
          <button class="filter-chip ${this.activeFilter === 'agentic' ? 'active' : ''}" onclick="benchMatrix.setFilter('agentic')">General Agentic (2)</button>
          <button class="filter-chip ${this.activeFilter === 'open' ? 'active' : ''}" onclick="benchMatrix.setFilter('open')">Open Weights (3)</button>
        </div>

        <div style="overflow-x: auto;">
          <table class="benchmark-table">
            <thead>
              <tr>
                <th onclick="benchMatrix.sortBy('name')">Model</th>
                <th onclick="benchMatrix.sortBy('org')">Lab</th>
                <th onclick="benchMatrix.sortBy('swe')">SWE-bench Verified ↕</th>
                <th onclick="benchMatrix.sortBy('aime')">AIME 2024 ↕</th>
                <th onclick="benchMatrix.sortBy('math500')">MATH 500 ↕</th>
                <th onclick="benchMatrix.sortBy('gpqa')">GPQA Diamond ↕</th>
                <th onclick="benchMatrix.sortBy('mmluPro')">MMLU-Pro ↕</th>
                <th>Context</th>
                <th>Input / 1M</th>
                <th>Output / 1M</th>
              </tr>
            </thead>
            <tbody id="benchmark-tbody">
            </tbody>
          </table>
        </div>
      </div>
    `;

    this.renderRows();
  }

  setFilter(f) {
    this.activeFilter = f;
    this.render();
  }

  sortBy(col) {
    if (this.sortCol === col) {
      this.sortAsc = !this.sortAsc;
    } else {
      this.sortCol = col;
      this.sortAsc = false;
    }
    this.renderRows();
  }

  renderRows() {
    const tbody = document.getElementById('benchmark-tbody');
    if (!tbody) return;

    let filtered = this.models.filter(m => {
      if (this.activeFilter === 'ALL') return true;
      if (this.activeFilter === 'open') return m.isOpen;
      return m.category === this.activeFilter;
    });

    filtered.sort((a, b) => {
      let va = a[this.sortCol];
      let vb = b[this.sortCol];
      if (typeof va === 'string') return this.sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
      return this.sortAsc ? va - vb : vb - va;
    });

    // Find max for highlighting
    const maxSwe = Math.max(...this.models.map(m => m.swe));
    const maxAime = Math.max(...this.models.map(m => m.aime));
    const maxMath = Math.max(...this.models.map(m => m.math500));
    const maxGpqa = Math.max(...this.models.map(m => m.gpqa));

    tbody.innerHTML = filtered.map(m => `
      <tr>
        <td>
          <div style="font-weight: 600; color: #fff;">${m.name}</div>
          <span class="badge ${m.isOpen ? 'badge-emerald' : 'badge-cyan'}" style="font-size: 0.65rem; margin-top: 3px;">${m.badge}</span>
        </td>
        <td style="color: var(--text-secondary);">${m.org}</td>
        <td class="score-cell ${m.swe === maxSwe ? 'score-top' : ''}">${m.swe}%</td>
        <td class="score-cell ${m.aime === maxAime ? 'score-top' : ''}">${m.aime}%</td>
        <td class="score-cell ${m.math500 === maxMath ? 'score-top' : ''}">${m.math500}%</td>
        <td class="score-cell ${m.gpqa === maxGpqa ? 'score-top' : ''}">${m.gpqa}%</td>
        <td class="score-cell">${m.mmluPro}%</td>
        <td style="font-family: var(--font-mono); color: var(--text-secondary);">${m.context}</td>
        <td style="font-family: var(--font-mono); color: var(--accent-cyan);">${m.costIn}</td>
        <td style="font-family: var(--font-mono); color: var(--accent-amber);">${m.costOut}</td>
      </tr>
    `).join('');
  }
}

window.BenchmarkMatrix = BenchmarkMatrix;
