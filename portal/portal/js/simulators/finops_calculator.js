/**
 * portal/js/simulators/finops_calculator.js
 * Interactive Enterprise Token FinOps, Prompt Caching & WaaS ROI Calculator.
 * 
 * Architect: finops_governor / MAS Swarm
 */

class FinOpsCalculator {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.state = {
      workflows: 50000,
      inputTokens: 8000,
      outputTokens: 1200,
      cacheHitRate: 85,
      agentLoops: 3,
      saasSeats: 150,
      costPerSeat: 75
    };
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="sim-header">
        <div class="badge badge-amber">FinOps & WaaS Economics</div>
        <h2 class="sim-title">Enterprise Token FinOps & WaaS ROI Simulator</h2>
        <p class="sim-desc">
          Model dynamic cost savings from Prompt Caching (up to 90% discount on cached inputs), 
          Agentic Reasoning loop expansion, and Digital FTE Work-as-a-Service (WaaS) replacement of traditional SaaS seat licenses.
        </p>
      </div>

      <div class="finops-grid">
        <!-- Controls Column -->
        <div class="finops-card">
          <h3 style="font-family: var(--font-display); font-size: 1.1rem; color: #fff;">Workload & Model Parameters</h3>
          
          <div class="control-group">
            <div class="control-header">
              <span>Monthly Task Executions</span>
              <span class="control-val" id="val-workflows">${this.state.workflows.toLocaleString()}</span>
            </div>
            <input type="range" class="slider-input" min="5000" max="500000" step="5000" 
              value="${this.state.workflows}" oninput="finOpsCalc.update('workflows', this.value)">
          </div>

          <div class="control-group">
            <div class="control-header">
              <span>Input Tokens / Task (System Prompt + History)</span>
              <span class="control-val" id="val-inputTokens">${this.state.inputTokens.toLocaleString()}</span>
            </div>
            <input type="range" class="slider-input" min="1000" max="64000" step="1000" 
              value="${this.state.inputTokens}" oninput="finOpsCalc.update('inputTokens', this.value)">
          </div>

          <div class="control-group">
            <div class="control-header">
              <span>Prompt Cache Hit Rate (%)</span>
              <span class="control-val" id="val-cacheHitRate">${this.state.cacheHitRate}%</span>
            </div>
            <input type="range" class="slider-input" min="0" max="95" step="5" 
              value="${this.state.cacheHitRate}" oninput="finOpsCalc.update('cacheHitRate', this.value)">
          </div>

          <div class="control-group">
            <div class="control-header">
              <span>Reasoning Loops / Agent Steps per Task</span>
              <span class="control-val" id="val-agentLoops">${this.state.agentLoops} rounds</span>
            </div>
            <input type="range" class="slider-input" min="1" max="10" step="1" 
              value="${this.state.agentLoops}" oninput="finOpsCalc.update('agentLoops', this.value)">
          </div>

          <div class="control-group">
            <div class="control-header">
              <span>Replaced SaaS Seats ($75/seat/mo)</span>
              <span class="control-val" id="val-saasSeats">${this.state.saasSeats} seats</span>
            </div>
            <input type="range" class="slider-input" min="10" max="1000" step="10" 
              value="${this.state.saasSeats}" oninput="finOpsCalc.update('saasSeats', this.value)">
          </div>
        </div>

        <!-- Real-Time Metrics & Charts -->
        <div class="finops-card">
          <h3 style="font-family: var(--font-display); font-size: 1.1rem; color: #fff;">Financial Impact & TCO Breakeven</h3>

          <div class="metric-row">
            <div class="metric-box">
              <span class="metric-label">Uncached API Cost</span>
              <span class="metric-value" id="metric-uncached">$0</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Cached API Cost (With Hit Rate)</span>
              <span class="metric-value cyan" id="metric-cached">$0</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Prompt Cache Savings</span>
              <span class="metric-value emerald" id="metric-savings">$0</span>
            </div>
            <div class="metric-box">
              <span class="metric-label">Replaced SaaS Seat Cost</span>
              <span class="metric-value amber" id="metric-saas">$0</span>
            </div>
          </div>

          <div class="finops-chart-card">
            <span style="font-size: 0.8rem; font-weight: 600; color: #fff; margin-bottom: 8px;">Cost Structure Comparison (Monthly)</span>
            
            <div class="chart-bar-wrap">
              <div class="chart-bar-label">
                <span>Traditional SaaS Seat Subscriptions</span>
                <span id="chart-lbl-saas">$0</span>
              </div>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" id="bar-saas" style="background: var(--accent-amber); width: 80%;"></div>
              </div>
            </div>

            <div class="chart-bar-wrap">
              <div class="chart-bar-label">
                <span>Raw Uncached Frontier API Calls</span>
                <span id="chart-lbl-uncached">$0</span>
              </div>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" id="bar-uncached" style="background: var(--accent-rose); width: 60%;"></div>
              </div>
            </div>

            <div class="chart-bar-wrap">
              <div class="chart-bar-label">
                <span>Optimized Agentic Token Cost (Cached)</span>
                <span id="chart-lbl-cached">$0</span>
              </div>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" id="bar-cached" style="background: var(--accent-cyan); width: 20%;"></div>
              </div>
            </div>

            <div class="chart-bar-wrap">
              <div class="chart-bar-label">
                <span>Self-Hosted Cluster (vLLM on H100s)</span>
                <span id="chart-lbl-vllm">$0</span>
              </div>
              <div class="chart-bar-bg">
                <div class="chart-bar-fill" id="bar-vllm" style="background: var(--accent-purple); width: 25%;"></div>
              </div>
            </div>
          </div>

          <div style="font-size: 0.82rem; color: var(--text-muted); background: var(--bg-hover); padding: 10px; border-radius: 8px;">
            💡 <strong>Executive Takeaway:</strong> Prompt caching delivers up to <strong>90% token price reduction</strong> on static system prompts and agent memory schemas, yielding an estimated net monthly operational ROI of <span id="metric-roi" style="color: var(--accent-emerald); font-weight: 700;">+340%</span> compared to legacy seat-based software.
          </div>
        </div>
      </div>
    `;

    this.recalculate();
  }

  update(key, val) {
    this.state[key] = parseFloat(val);
    const labelElem = document.getElementById(`val-${key}`);
    if (labelElem) {
      if (key === 'workflows' || key === 'inputTokens') {
        labelElem.innerText = this.state[key].toLocaleString();
      } else if (key === 'cacheHitRate') {
        labelElem.innerText = `${this.state[key]}%`;
      } else if (key === 'agentLoops') {
        labelElem.innerText = `${this.state[key]} rounds`;
      } else if (key === 'saasSeats') {
        labelElem.innerText = `${this.state[key]} seats`;
      }
    }
    this.recalculate();
  }

  recalculate() {
    const { workflows, inputTokens, outputTokens, cacheHitRate, agentLoops, saasSeats, costPerSeat } = this.state;

    // Pricing assumptions: $3.00/1M uncached input, $0.30/1M cached input (90% discount), $15.00/1M output
    const totalExecutions = workflows * agentLoops;
    const rawInputTokens = totalExecutions * inputTokens;
    const totalOutputTokens = totalExecutions * outputTokens;

    const uncachedCost = (rawInputTokens / 1000000) * 3.00 + (totalOutputTokens / 1000000) * 15.00;

    const cachedInputTokens = rawInputTokens * (cacheHitRate / 100);
    const nonCachedInputTokens = rawInputTokens * (1 - cacheHitRate / 100);

    const cachedCost = (cachedInputTokens / 1000000) * 0.30 + (nonCachedInputTokens / 1000000) * 3.00 + (totalOutputTokens / 1000000) * 15.00;
    const savings = uncachedCost - cachedCost;

    const saasCost = saasSeats * costPerSeat;
    // vLLM baseline: roughly fixed GPU node ($2.50/hr * 730 hrs = ~$1,825/mo per 8x GPU node)
    const neededGpus = Math.max(1, Math.ceil(totalExecutions / 150000));
    const vllmCost = neededGpus * 1850;

    const netSavings = saasCost - cachedCost;
    const roi = saasCost > 0 ? Math.round((netSavings / (cachedCost || 1)) * 100) : 0;

    // Update DOM metrics
    const uncachedEl = document.getElementById('metric-uncached');
    const cachedEl = document.getElementById('metric-cached');
    const savingsEl = document.getElementById('metric-savings');
    const saasEl = document.getElementById('metric-saas');
    const roiEl = document.getElementById('metric-roi');

    if (uncachedEl) uncachedEl.innerText = `$${Math.round(uncachedCost).toLocaleString()}`;
    if (cachedEl) cachedEl.innerText = `$${Math.round(cachedCost).toLocaleString()}`;
    if (savingsEl) savingsEl.innerText = `$${Math.round(savings).toLocaleString()}`;
    if (saasEl) saasEl.innerText = `$${Math.round(saasCost).toLocaleString()}`;
    if (roiEl) roiEl.innerText = `${roi > 0 ? '+' : ''}${roi}%`;

    // Update Charts
    const maxCost = Math.max(saasCost, uncachedCost, cachedCost, vllmCost, 100);

    const setBar = (id, lblId, cost) => {
      const bar = document.getElementById(id);
      const lbl = document.getElementById(lblId);
      if (bar) bar.style.width = `${Math.min(100, Math.max(5, (cost / maxCost) * 100))}%`;
      if (lbl) lbl.innerText = `$${Math.round(cost).toLocaleString()}/mo`;
    };

    setBar('bar-saas', 'chart-lbl-saas', saasCost);
    setBar('bar-uncached', 'chart-lbl-uncached', uncachedCost);
    setBar('bar-cached', 'chart-lbl-cached', cachedCost);
    setBar('bar-vllm', 'chart-lbl-vllm', vllmCost);
  }
}

window.FinOpsCalculator = FinOpsCalculator;
