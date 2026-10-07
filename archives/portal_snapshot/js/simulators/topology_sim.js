/**
 * portal/js/simulators/topology_sim.js
 * Multi-Agent System Topology & EventBus Message Transit Visualizer.
 * 
 * Architect: chief_architect / MAS Swarm
 */

class TopologySimulator {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.canvas = null;
    this.ctx = null;
    this.animId = null;
    this.currentTopology = 'supervisor';
    this.nodes = [];
    this.edges = [];
    this.packets = [];
    this.logs = [];
    this.isRunning = true;
    this.stepCount = 0;
  }

  render() {
    if (!this.container) return;

    this.container.innerHTML = `
      <div class="sim-header">
        <div class="badge badge-cyan">Multi-Agent System Architecture</div>
        <h2 class="sim-title">Multi-Agent Coordination Topology & EventBus Simulator</h2>
        <p class="sim-desc">
          Inspect how agentic architectures coordinate communication, delegate sub-tasks, execute anti-sycophantic debates, 
          and dispatch ephemeral Liquid Strike Pods across the EventBus.
        </p>
      </div>

      <div class="topology-box">
        <div class="topology-controls">
          <div class="topology-btn-group">
            <button class="btn btn-secondary btn-sm" id="btn-top-supervisor" onclick="topSim.setTopology('supervisor')">Supervisor-Worker</button>
            <button class="btn btn-secondary btn-sm" id="btn-top-pipeline" onclick="topSim.setTopology('pipeline')">Sequential SOP</button>
            <button class="btn btn-secondary btn-sm" id="btn-top-debate" onclick="topSim.setTopology('debate')">Anti-Sycophantic Debate</button>
            <button class="btn btn-secondary btn-sm" id="btn-top-strikepod" onclick="topSim.setTopology('strikepod')">Liquid Strike Pods</button>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary btn-sm" id="btn-top-toggle" onclick="topSim.togglePlay()">Pause</button>
            <button class="btn btn-secondary btn-sm" onclick="topSim.reset()">Reset</button>
          </div>
        </div>

        <div class="canvas-container">
          <canvas id="topology-canvas"></canvas>
        </div>

        <div class="topology-terminal" id="topology-terminal">
          <div class="log-entry">
            <span class="log-time">[00:00:00]</span>
            <span class="log-agent">[EVENTBUS]</span>
            <span class="log-msg">Topology initialized. Ready for simulation.</span>
          </div>
        </div>
      </div>
    `;

    this.canvas = document.getElementById('topology-canvas');
    if (this.canvas) {
      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());
      this.setTopology('supervisor');
      this.startAnimation();
    }
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height;
    this.setupNodes();
  }

  setTopology(name) {
    this.currentTopology = name;
    ['supervisor', 'pipeline', 'debate', 'strikepod'].forEach(t => {
      const btn = document.getElementById(`btn-top-${t}`);
      if (btn) {
        if (t === name) {
          btn.classList.add('btn-primary');
          btn.classList.remove('btn-secondary');
        } else {
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-secondary');
        }
      }
    });

    this.packets = [];
    this.setupNodes();
    this.log('TOPOLOGY', `Switched coordination pattern to: ${name.toUpperCase()}`);
  }

  setupNodes() {
    if (!this.canvas) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const cx = w / 2;
    const cy = h / 2;

    this.nodes = [];
    this.edges = [];

    if (this.currentTopology === 'supervisor') {
      // Central Orchestrator + 4 Workers
      this.nodes = [
        { id: 'supervisor', label: 'Supervisor / Orchestrator', x: cx, y: cy - 70, color: '#00f0ff', r: 24, role: 'router' },
        { id: 'researcher', label: 'Market Researcher', x: cx - 220, y: cy + 100, color: '#a855f7', r: 18, role: 'worker' },
        { id: 'architect', label: 'Systems Architect', x: cx - 75, y: cy + 120, color: '#00ff9d', r: 18, role: 'worker' },
        { id: 'engineer', label: 'Software Engineer', x: cx + 75, y: cy + 120, color: '#ffb700', r: 18, role: 'worker' },
        { id: 'qa', label: 'QA Critic Lead', x: cx + 220, y: cy + 100, color: '#f43f5e', r: 18, role: 'worker' },
      ];
      this.edges = [
        { from: 'supervisor', to: 'researcher' },
        { from: 'supervisor', to: 'architect' },
        { from: 'supervisor', to: 'engineer' },
        { from: 'supervisor', to: 'qa' },
      ];
    } else if (this.currentTopology === 'pipeline') {
      // Linear SOP Pipeline
      const labels = ['Client Intake', 'Product Lead', 'Architect', 'Engineer', 'QA Verifier'];
      const colors = ['#00f0ff', '#38bdf8', '#00ff9d', '#ffb700', '#f43f5e'];
      const startX = cx - 280;
      const stepX = 140;

      for (let i = 0; i < labels.length; i++) {
        const id = `sop_${i}`;
        this.nodes.push({ id, label: labels[i], x: startX + i * stepX, y: cy, color: colors[i], r: 20 });
        if (i > 0) {
          this.edges.push({ from: `sop_${i - 1}`, to: id });
        }
      }
    } else if (this.currentTopology === 'debate') {
      // Proponent, Opponent, Devil's Advocate, Judge
      this.nodes = [
        { id: 'proponent', label: 'Proponent (Claim A)', x: cx - 180, y: cy - 50, color: '#00f0ff', r: 22 },
        { id: 'opponent', label: 'Opponent (Claim B)', x: cx + 180, y: cy - 50, color: '#f43f5e', r: 22 },
        { id: 'devil', label: "Devil's Advocate Critic", x: cx, y: cy - 120, color: '#ffb700', r: 20 },
        { id: 'judge', label: 'Consensus Judge', x: cx, y: cy + 110, color: '#00ff9d', r: 24 }
      ];
      this.edges = [
        { from: 'proponent', to: 'opponent' },
        { from: 'opponent', to: 'proponent' },
        { from: 'proponent', to: 'devil' },
        { from: 'opponent', to: 'devil' },
        { from: 'devil', to: 'judge' },
        { from: 'proponent', to: 'judge' },
        { from: 'opponent', to: 'judge' },
      ];
    } else if (this.currentTopology === 'strikepod') {
      // Liquid Strike Pod with Merkle provenance & Human Gate
      this.nodes = [
        { id: 'pod_lead', label: 'Strike Pod Lead', x: cx - 180, y: cy, color: '#00f0ff', r: 22 },
        { id: 'worker_a', label: 'Inference Specialist', x: cx - 40, y: cy - 90, color: '#a855f7', r: 18 },
        { id: 'worker_b', label: 'Sandbox Execution Tool', x: cx - 40, y: cy + 90, color: '#ffb700', r: 18 },
        { id: 'human_gate', label: 'Level-2 Human Approval Gate', x: cx + 120, y: cy, color: '#f43f5e', r: 22 },
        { id: 'merkle_vault', label: 'Merkle Audit Ledger', x: cx + 260, y: cy, color: '#00ff9d', r: 20 }
      ];
      this.edges = [
        { from: 'pod_lead', to: 'worker_a' },
        { from: 'pod_lead', to: 'worker_b' },
        { from: 'worker_a', to: 'human_gate' },
        { from: 'worker_b', to: 'human_gate' },
        { from: 'human_gate', to: 'merkle_vault' }
      ];
    }
  }

  togglePlay() {
    this.isRunning = !this.isRunning;
    const btn = document.getElementById('btn-top-toggle');
    if (btn) btn.innerText = this.isRunning ? 'Pause' : 'Play';
  }

  reset() {
    this.packets = [];
    this.setupNodes();
    this.log('EVENTBUS', 'Simulation reset.');
  }

  startAnimation() {
    this.stop();
    const loop = () => {
      this.animId = requestAnimationFrame(loop);
      if (this.isRunning) {
        this.step();
      }
      this.draw();
    };
    loop();
  }

  stop() {
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
  }

  step() {
    this.stepCount++;

    // Random packet spawner every 50 frames
    if (this.stepCount % 45 === 0 && this.edges.length > 0) {
      const edge = this.edges[Math.floor(Math.random() * this.edges.length)];
      const fromNode = this.nodes.find(n => n.id === edge.from);
      const toNode = this.nodes.find(n => n.id === edge.to);

      if (fromNode && toNode) {
        this.packets.push({
          from: fromNode,
          to: toNode,
          progress: 0,
          speed: 0.015 + Math.random() * 0.01,
          color: fromNode.color
        });
        this.log(fromNode.label, `Dispatched message -> ${toNode.label}`);
      }
    }

    // Update packets
    for (let i = this.packets.length - 1; i >= 0; i--) {
      const p = this.packets[i];
      p.progress += p.speed;
      if (p.progress >= 1) {
        this.packets.splice(i, 1);
      }
    }
  }

  draw() {
    if (!this.ctx || !this.canvas) return;
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    ctx.clearRect(0, 0, w, h);

    // 1. Draw Edges
    for (const edge of this.edges) {
      const fromNode = this.nodes.find(n => n.id === edge.from);
      const toNode = this.nodes.find(n => n.id === edge.to);
      if (fromNode && toNode) {
        ctx.beginPath();
        ctx.moveTo(fromNode.x, fromNode.y);
        ctx.lineTo(toNode.x, toNode.y);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }

    // 2. Draw Moving Packets
    for (const p of this.packets) {
      const px = p.from.x + (p.to.x - p.from.x) * p.progress;
      const py = p.from.y + (p.to.y - p.from.y) * p.progress;

      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // 3. Draw Nodes
    for (const node of this.nodes) {
      // Glow circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r + 3, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(10, 15, 24, 0.9)';
      ctx.strokeStyle = node.color;
      ctx.lineWidth = 2;
      ctx.shadowColor = node.color;
      ctx.shadowBlur = 14;
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Inner dot
      ctx.beginPath();
      ctx.arc(node.x, node.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();

      // Label
      ctx.font = '600 11px Outfit, sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y + node.r + 16);
    }
  }

  log(agent, message) {
    const term = document.getElementById('topology-terminal');
    if (!term) return;

    const time = new Date().toTimeString().split(' ')[0];
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
      <span class="log-time">[${time}]</span>
      <span class="log-agent">[${agent}]</span>
      <span class="log-msg">${message}</span>
    `;

    term.appendChild(entry);
    term.scrollTop = term.scrollHeight;

    while (term.children.length > 50) {
      term.removeChild(term.children[0]);
    }
  }
}

window.TopologySimulator = TopologySimulator;
