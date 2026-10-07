/**
 * portal/js/app.js: Main Web Application Router & State Manager.
 * Orchestrates navigation, views, search modal, Merkle audit, and simulators.
 * 
 * Architect: frontend_engineer / MAS Swarm
 */

class PortalApp {
  constructor() {
    this.catalog = window.RESEARCH_CATALOG || { documents: [], volumes: {}, pdfs: [], diagrams: [] };
    this.searchEngine = new ResearchSearchEngine(this.catalog);
    this.readerEngine = new MarkdownReaderEngine();
    
    this.activeView = 'reader'; // 'reader' | 'finops' | 'topology' | 'benchmarks' | 'timeline' | 'vault'
    this.activeDocId = null;
    this.selectedSearchIndex = 0;
    this.searchResults = [];

    // Simulator instances
    this.finOpsCalc = null;
    this.topologySim = null;
    this.benchMatrix = null;
    this.aiTimeline = null;
  }

  init() {
    console.log("[MAS PORTAL] Initializing Acinonyx Living AI Research Portal...");

    // Simulators must exist before the first route is resolved
    window.finOpsCalc = new FinOpsCalculator('sim-mount');
    window.topSim = new TopologySimulator('sim-mount');
    window.benchMatrix = new BenchmarkMatrix('sim-mount');
    window.aiTimeline = new AITimeline('sim-mount');

    this.renderSidebar();
    this.renderHome();
    this.setupEventListeners();
    this.setupGlobalShortcuts();

    if (window.copilot) {
      window.copilot.init();
    }

    window.addEventListener('popstate', () => this.route());
    this.route();
  }

  /* ------------------------------------------------------------------------
     Hash routing:  #/home  #/finops  #/doc/<docId>
     ------------------------------------------------------------------------ */
  route() {
    const parts = (location.hash || '#/home').replace(/^#\/?/, '').split('/');
    const kind = parts[0];
    const views = ['home', 'reader', 'finops', 'topology', 'benchmarks', 'timeline', 'vault'];
    if (kind === 'doc' && parts[1]) {
      this.loadDocument(decodeURIComponent(parts.slice(1).join('/')), { noPush: true });
    } else if (views.includes(kind)) {
      this.switchView(kind, { noPush: true });
    } else {
      this.switchView('home', { noPush: true });
    }
  }

  setHash(hash, noPush) {
    if (noPush || location.hash === hash) return;
    history.pushState(null, '', hash);
  }

  renderSidebar() {
    const navContainer = document.getElementById('sidebar-volumes');
    if (!navContainer) return;

    const docs = this.catalog.documents.filter(d => d.volumeKey !== 'README.md');
    const indexDoc = this.catalog.documents.find(d => d.volumeKey === 'README.md');

    // Group: volume -> module -> docs (Overview first, then by path order)
    const volumes = {};
    for (const doc of docs) {
      const v = volumes[doc.volumeKey] || (volumes[doc.volumeKey] = {
        title: doc.volumeTitle, color: doc.volumeColor, modules: {}, count: 0
      });
      (v.modules[doc.moduleLabel] = v.modules[doc.moduleLabel] || []).push(doc);
      v.count++;
    }

    let html = '';
    if (indexDoc) {
      html += `<a href="#/doc/${indexDoc.id}" class="chapter-link index-link" id="link-${indexDoc.id}"
                 onclick="event.preventDefault(); app.loadDocument('${indexDoc.id}')">
                 <span class="chapter-name">Library index</span></a>`;
    }

    Object.keys(volumes).forEach((vKey, i) => {
      const vol = volumes[vKey];
      const modNames = Object.keys(vol.modules).sort((a, b) =>
        (a === 'Overview' ? -1 : 0) - (b === 'Overview' ? -1 : 0));
      html += `
        <div class="volume-group ${i === 0 ? '' : 'collapsed'}" id="vol-group-${vKey}" style="--vol-color:${vol.color}">
          <button class="volume-header" onclick="app.toggleVolume('${vKey}')" aria-expanded="${i === 0}">
            <span class="volume-dot"></span>
            <span class="volume-title">${vol.title}</span>
            <span class="volume-count">${vol.count}</span>
            <span class="volume-arrow" aria-hidden="true">▾</span>
          </button>
          <div class="volume-chapters">
            ${modNames.map(m => `
              ${m === 'Overview' ? '' : `<div class="module-label">${m}</div>`}
              ${vol.modules[m].map(d => {
                const isStarred = this.readerEngine && this.readerEngine.isBookmarked(d.id);
                return `
                <a href="#/doc/${d.id}" class="chapter-link" id="link-${d.id}"
                   onclick="event.preventDefault(); app.loadDocument('${d.id}')">
                  ${isStarred ? '<span class="star-badge">★</span>' : ''}
                  <span class="chapter-name">${d.shortTitle}</span>
                  <span class="chapter-meta">${d.readTimeMin}m</span>
                </a>`;
              }).join('')}
            `).join('')}
          </div>
        </div>`;
    });

    navContainer.innerHTML = html;
  }

  toggleVolume(vKey) {
    const group = document.getElementById(`vol-group-${vKey}`);
    if (group) {
      const collapsed = group.classList.toggle('collapsed');
      const btn = group.querySelector('.volume-header');
      if (btn) btn.setAttribute('aria-expanded', String(!collapsed));
    }
  }

  switchView(viewName, opts = {}) {
    // Reader with nothing loaded yet: open the first chapter instead of a blank page
    if (viewName === 'reader' && !this.activeDocId) {
      const first = this.catalog.documents.find(d => d.volumeKey === 'agentic_systems' && !/README/i.test(d.id))
        || this.catalog.documents[0];
      if (first) { this.loadDocument(first.id, opts); return; }
    }
    this.activeView = viewName;
    if (viewName !== 'reader') this.setHash('#/' + viewName, opts.noPush);

    // Stop the topology animation loop whenever we leave that view
    if (window.topSim && viewName !== 'topology') window.topSim.stop();

    // Set body view state class for CSS adaptive layouts
    document.body.className = `view-${viewName}`;

    // Update nav links
    ['home', 'reader', 'finops', 'topology', 'benchmarks', 'timeline', 'vault'].forEach(v => {
      const el = document.getElementById(`nav-${v}`);
      if (el) {
        el.classList.toggle('active', v === viewName);
        if (v === viewName) el.setAttribute('aria-current', 'page');
        else el.removeAttribute('aria-current');
      }
    });

    const homeView = document.getElementById('view-home');
    const readerView = document.getElementById('view-reader');
    const simMount = document.getElementById('sim-mount');
    const rightRail = document.getElementById('right-rail');

    if (homeView) homeView.style.display = viewName === 'home' ? 'block' : 'none';

    if (viewName === 'home') {
      if (readerView) readerView.style.display = 'none';
      if (simMount) simMount.style.display = 'none';
      if (rightRail) rightRail.style.display = 'none';
      window.scrollTo(0, 0);
    } else if (viewName === 'reader') {
      if (readerView) readerView.style.display = 'block';
      if (simMount) simMount.style.display = 'none';
      if (rightRail) rightRail.style.display = 'flex';
      window.scrollTo(0, 0);
    } else {
      if (readerView) readerView.style.display = 'none';
      if (simMount) simMount.style.display = 'block';
      if (rightRail) rightRail.style.display = 'none';
      window.scrollTo(0, 0);

      if (viewName === 'finops') {
        window.finOpsCalc.render();
      } else if (viewName === 'topology') {
        window.topSim.render();
      } else if (viewName === 'benchmarks') {
        window.benchMatrix.render();
      } else if (viewName === 'timeline') {
        window.aiTimeline.render();
      } else if (viewName === 'vault') {
        this.renderVault();
      }
    }
  }

  toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    if (this.currentView === 'reader') {
      sidebar.classList.toggle('collapsed');
    } else {
      sidebar.classList.toggle('open');
    }
  }

  renderHome() {
    const mount = document.getElementById('view-home');
    if (!mount) return;
    const meta = this.catalog.metadata || {};
    const docs = this.catalog.documents || [];
    const totalWords = docs.reduce((s, d) => s + (d.wordCount || 0), 0);

    const byVolume = {};
    docs.forEach(d => {
      if (d.volumeKey === 'README.md') return;
      (byVolume[d.volumeKey] = byVolume[d.volumeKey] || { vol: d, items: [] }).items.push(d);
    });

    const volumeIcons = {
      agentic_systems: '🧠',
      ai_encyclopedia: '📚',
      google_cloud_agentic_infra: '☁️',
      multi_agent_systems: '🤖',
      system_development_life_cycle: '🔄',
      devops_dataops_mlops: '⚡',
      agile_kanban_frameworks: '🏃',
      company_governance_and_self_improvement: '🏛️'
    };

    const volumeBlurbs = {
      agentic_systems: 'Frontier reasoning models, test-time compute scaling, multi-agent topologies, MCP/A2A protocols, WaaS economics, and production sandboxing.',
      ai_encyclopedia: 'Eight comprehensive volumes spanning 1950 to 2026: theoretical history, Transformer architectures, frontier silicon, seminal papers, and curricula.',
      google_cloud_agentic_infra: 'Vertex AI Reasoning Engine, Cloud Run gVisor sandboxing, Cloud Workstations, and A2A inter-agent reference architectures.',
      multi_agent_systems: 'Formal textbook foundations, ReAct loops, CoALA cognitive memory architecture, and schema-constrained multi-agent design patterns.',
      system_development_life_cycle: 'Modern 2026 Spec-Driven Agentic SDLC, ISO/IEC/IEEE 12207 standards, NIST SSDF v1.2, and automated quality verification gates.',
      devops_dataops_mlops: 'Comparative architecture and lifecycle convergence across code GitOps, BigQuery DataOps contracts, and Vertex MLOps model governance.',
      agile_kanban_frameworks: 'Mathematical flow theory, Little’s Law, Monte Carlo probabilistic forecasting, Shape Up, and 2026 AI-augmented swarm agility.',
      company_governance_and_self_improvement: 'Grand Squad Symposium synthesis, ratified Ways of Working, ADR decision frameworks, and Scope Jail boundary containment.'
    };

    const tools = [
      {
        id: 'finops',
        title: 'Token FinOps & WaaS ROI Calculator',
        badge: 'Interactive Calculator',
        desc: 'Model dynamic cost savings from prompt caching (up to 90% discount), reasoning expansion, and Digital FTE SaaS replacement.',
        icon: '💎'
      },
      {
        id: 'topology',
        title: 'Multi-Agent Topology Simulator',
        badge: 'Live EventBus Simulation',
        desc: 'Simulate message routing and consensus across Supervisor, Sequential SOP, Anti-Sycophantic Debate, and Liquid Strike Pods.',
        icon: '🕸️'
      },
      {
        id: 'benchmarks',
        title: 'Frontier Model Benchmark Matrix',
        badge: 'Dynamic ELO & Radar',
        desc: 'Filter and rank frontier models across SWE-bench Verified, AIME, GPQA Diamond, and LiveCode with price-to-intelligence curves.',
        icon: '📊'
      },
      {
        id: 'timeline',
        title: 'AI Historical & Cognitive Timeline',
        badge: '1950 – 2026 Milestone Map',
        desc: 'Walk milestones from the Turing Test and Dartmouth Workshop to modern test-time compute and sovereign multi-agent swarms.',
        icon: '⏳'
      }
    ];

    mount.innerHTML = `
      <section class="hero">
        <div class="hero-copy">
          <span class="hero-eyebrow">
            <span class="live-dot"></span>
            Acinonyx Labs · Frontier Swarm Directorate
          </span>
          <h1 class="hero-title">The living atlas of <span class="hero-accent">autonomous AI swarms</span></h1>
          <p class="hero-sub">A cross-referenced knowledge repository and interactive laboratory exploring frontier reasoning models, multi-agent coordination architectures, Token FinOps, and enterprise cognitive systems.</p>
          <div class="hero-actions">
            <button class="btn btn-primary" onclick="app.openSearch()">
              <span>🔍 Search 82 Modules</span>
              <span class="search-kbd" style="margin-left: 6px; font-size: 0.75rem; background: rgba(0,0,0,0.25); color: #040914;">Ctrl K</span>
            </button>
            <button class="btn btn-secondary" onclick="app.loadDocument('${(docs.find(d => d.id.includes('agentic_systems_README')) || docs[0] || {}).id}')">
              <span>📖 Start with Master Compendium</span>
            </button>
          </div>
          <dl class="stat-strip">
            <div class="stat"><dt>Documents</dt><dd>${docs.length}</dd></div>
            <div class="stat"><dt>Words</dt><dd>${totalWords.toLocaleString()}</dd></div>
            <div class="stat"><dt>Deep Papers</dt><dd>${meta.pdfCount || 8}</dd></div>
            <div class="stat"><dt>Diagrams</dt><dd>${meta.diagramCount || 15}</dd></div>
          </dl>
        </div>

        <div class="hero-art" aria-hidden="true">
          <div class="hero-art-backdrop"></div>
          <svg viewBox="0 0 440 440" class="hero-svg">
            <defs>
              <radialGradient id="g-core" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.8"/>
                <stop offset="40%" stop-color="#00bcd4" stop-opacity="0.25"/>
                <stop offset="100%" stop-color="#00f0ff" stop-opacity="0"/>
              </radialGradient>
              <linearGradient id="g-mesh" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#00f0ff" stop-opacity="0.8"/>
                <stop offset="50%" stop-color="#a855f7" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="#00ff9d" stop-opacity="0.8"/>
              </linearGradient>
              <filter id="glow-filter" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3.5" result="blur"/>
                <feComposite in="SourceGraphic" in2="blur" operator="over"/>
              </filter>
            </defs>

            <!-- Atmospheric Core Aura -->
            <circle cx="220" cy="220" r="195" fill="url(#g-core)"/>
            
            <!-- Animated Orbital Rings -->
            <g class="orbit-1">
              <circle cx="220" cy="220" r="155" fill="none" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 8" stroke-width="1.5"/>
              <circle cx="220" cy="65" r="3" fill="#00f0ff" opacity="0.7"/>
              <circle cx="375" cy="220" r="3" fill="#a855f7" opacity="0.7"/>
              <circle cx="220" cy="375" r="3" fill="#00ff9d" opacity="0.7"/>
              <circle cx="65" cy="220" r="3" fill="#ffb700" opacity="0.7"/>
            </g>

            <g class="orbit-2">
              <circle cx="220" cy="220" r="105" fill="none" stroke="rgba(0, 240, 255, 0.16)" stroke-dasharray="4 6" stroke-width="1.5"/>
            </g>

            <!-- Synaptic Neural Connections -->
            <g stroke="url(#g-mesh)" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.7">
              <line x1="220" y1="220" x2="220" y2="70"/>
              <line x1="220" y1="220" x2="350" y2="145"/>
              <line x1="220" y1="220" x2="350" y2="295"/>
              <line x1="220" y1="220" x2="220" y2="370"/>
              <line x1="220" y1="220" x2="90" y2="295"/>
              <line x1="220" y1="220" x2="90" y2="145"/>

              <!-- Outer Hexagonal Synapse Ring -->
              <line x1="220" y1="70" x2="350" y2="145" stroke="#a855f7" opacity="0.45"/>
              <line x1="350" y1="145" x2="350" y2="295" stroke="#f43f5e" opacity="0.45"/>
              <line x1="350" y1="295" x2="220" y2="370" stroke="#00ff9d" opacity="0.45"/>
              <line x1="220" y1="370" x2="90" y2="295" stroke="#ffb700" opacity="0.45"/>
              <line x1="90" y1="295" x2="90" y2="145" stroke="#38bdf8" opacity="0.45"/>
              <line x1="90" y1="145" x2="220" y2="70" stroke="#00f0ff" opacity="0.45"/>
            </g>

            <!-- 6 Swarm Agent Nodes -->
            <!-- Chief Architect (Cyan) -->
            <g filter="url(#glow-filter)">
              <circle cx="220" cy="70" r="13" fill="#06121e" stroke="#00f0ff" stroke-width="2.5"/>
              <circle cx="220" cy="70" r="5" fill="#00f0ff"/>
              <text x="220" y="46" fill="#f8fafc" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="600" text-anchor="middle">Chief Architect</text>
            </g>

            <!-- FinOps Governor (Amber) -->
            <g filter="url(#glow-filter)">
              <circle cx="350" cy="145" r="13" fill="#181308" stroke="#ffb700" stroke-width="2.5"/>
              <circle cx="350" cy="145" r="5" fill="#ffb700"/>
              <text x="366" y="141" fill="#f8fafc" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="600" text-anchor="start">FinOps Gov</text>
            </g>

            <!-- Adversarial Red (Rose) -->
            <g filter="url(#glow-filter)">
              <circle cx="350" cy="295" r="13" fill="#1c0910" stroke="#f43f5e" stroke-width="2.5"/>
              <circle cx="350" cy="295" r="5" fill="#f43f5e"/>
              <text x="366" y="299" fill="#f8fafc" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="600" text-anchor="start">Adversarial Red</text>
            </g>

            <!-- QA Critic (Purple) -->
            <g filter="url(#glow-filter)">
              <circle cx="220" cy="370" r="13" fill="#160c24" stroke="#a855f7" stroke-width="2.5"/>
              <circle cx="220" cy="370" r="5" fill="#a855f7"/>
              <text x="220" y="398" fill="#f8fafc" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="600" text-anchor="middle">QA Critic</text>
            </g>

            <!-- Market Researcher (Emerald) -->
            <g filter="url(#glow-filter)">
              <circle cx="90" cy="295" r="13" fill="#081812" stroke="#00ff9d" stroke-width="2.5"/>
              <circle cx="90" cy="295" r="5" fill="#00ff9d"/>
              <text x="74" y="299" fill="#f8fafc" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="600" text-anchor="end">Market Res</text>
            </g>

            <!-- Cloud Architect (Blue) -->
            <g filter="url(#glow-filter)">
              <circle cx="90" cy="145" r="13" fill="#081420" stroke="#38bdf8" stroke-width="2.5"/>
              <circle cx="90" cy="145" r="5" fill="#38bdf8"/>
              <text x="74" y="141" fill="#f8fafc" font-size="10" font-family="'JetBrains Mono', monospace" font-weight="600" text-anchor="end">Cloud Arch</text>
            </g>

            <!-- Center Core MAS-Core EventBus Nexus -->
            <circle cx="220" cy="220" r="34" fill="rgba(0, 240, 255, 0.12)" stroke="rgba(0, 240, 255, 0.35)" stroke-width="1.5"/>
            <circle cx="220" cy="220" r="24" fill="#06080e" stroke="#00f0ff" stroke-width="2.5" filter="url(#glow-filter)"/>
            <circle cx="220" cy="220" r="9" fill="#00f0ff" class="core-pulse-node"/>
            <text x="220" y="223" fill="#00f0ff" font-size="7.5" font-family="'JetBrains Mono', monospace" font-weight="700" text-anchor="middle">EVENTBUS</text>
          </svg>
        </div>
      </section>

      <div class="section-header-wrap">
        <h2 class="section-title">Browse Research Collections</h2>
        <span class="section-badge">8 Master Volumes · Peer Reviewed</span>
      </div>

      <div class="volume-cards">
        ${Object.entries(byVolume).map(([key, g]) => {
          const first = g.items.find(i => !/README/i.test(i.id)) || g.items[0];
          const volMeta = (this.catalog.volumes && this.catalog.volumes[key]) || {};
          const color = volMeta.color || g.vol.volumeColor || '#00f0ff';
          const icon = volumeIcons[key] || '📄';
          const glow = color + '28';
          const title = volMeta.title || g.vol.volumeTitle;
          const desc = volumeBlurbs[key] || g.vol.summary || '';
          return `
          <button class="volume-card" style="--vol-color:${color}; --vol-glow:${glow};" onclick="app.loadDocument('${first.id}')">
            <div class="volume-card-top">
              <div class="volume-card-icon">${icon}</div>
              <span class="volume-card-count">${g.items.length} Modules</span>
            </div>
            <h3 class="volume-card-title">${title}</h3>
            <p class="volume-card-desc">${desc}</p>
            <div class="volume-card-cta">
              <span>Explore Collection</span>
              <span>→</span>
            </div>
          </button>`;
        }).join('')}
      </div>

      <div class="section-header-wrap">
        <h2 class="section-title">Interactive Simulators & Calculators</h2>
        <span class="section-badge">Autonomous Tool Suite</span>
      </div>

      <div class="tool-grid">
        ${tools.map(t => `
          <button class="tool-card" onclick="app.switchView('${t.id}')">
            <div class="tool-card-badge">${t.icon} ${t.badge}</div>
            <h3 class="tool-card-title">${t.title}</h3>
            <p class="tool-card-desc">${t.desc}</p>
            <div class="tool-card-cta">
              <span>Launch Simulator</span>
              <span>⚡</span>
            </div>
          </button>`).join('')}
      </div>
    `;
  }

  loadDocument(docId, opts = {}) {
    const doc = this.catalog.documents.find(d => d.id === docId);
    if (!doc) { this.switchView('home', { noPush: true }); return; }

    this.activeDocId = docId;
    this.switchView('reader', { noPush: true });
    this.setHash('#/doc/' + docId, opts.noPush);
    document.title = `${doc.shortTitle} · Acinonyx Research Portal`;

    // Update active link in sidebar
    document.querySelectorAll('.chapter-link').forEach(el => el.classList.remove('active'));
    const linkEl = document.getElementById(`link-${docId}`);
    if (linkEl) {
      linkEl.classList.add('active');
      // Ensure volume accordion is open
      const volGroup = linkEl.closest('.volume-group');
      if (volGroup) volGroup.classList.remove('collapsed');
    }

    // Update Reader Header & Breadcrumbs
    const bcEl = document.getElementById('reader-breadcrumbs');
    if (bcEl) {
      bcEl.innerHTML = `
        <a href="#/home" onclick="event.preventDefault(); app.switchView('home')">Library</a>
        <span aria-hidden="true">/</span>
        <span>${doc.volumeTitle}</span>
        ${doc.moduleLabel && doc.moduleLabel !== 'Overview' ? `<span aria-hidden="true">/</span><span class="crumb-current">${doc.moduleLabel}</span>` : ''}
      `;
    }

    const titleEl = document.getElementById('reader-title');
    if (titleEl) titleEl.innerText = doc.title;

    const metaBarEl = document.getElementById('reader-meta-bar');
    if (metaBarEl) {
      metaBarEl.innerHTML = `
        <span class="badge ${this.getBadgeClass(doc.volumeKey)}">${doc.volumeBadge}</span>
        <span class="reader-meta-item">${doc.readTimeMin} min read</span>
        <span class="reader-meta-sep" aria-hidden="true"></span>
        <span class="reader-meta-item">${doc.wordCount.toLocaleString()} words</span>
        <span class="reader-meta-sep" aria-hidden="true"></span>
        <span class="reader-meta-item">${doc.lineCount.toLocaleString()} lines</span>
      `;
    }

    // Update Bookmark Button state
    const isStarred = this.readerEngine && this.readerEngine.isBookmarked(docId);
    const starBtn = document.getElementById('star-btn');
    if (starBtn) {
      starBtn.classList.toggle('star-active', isStarred);
      const icon = document.getElementById('star-btn-icon');
      const txt = document.getElementById('star-btn-text');
      if (icon) icon.innerText = isStarred ? '★' : '☆';
      if (txt) txt.innerText = isStarred ? 'Saved' : 'Save';
    }

    // Render Markdown (drop the leading H1: the page header already shows it)
    const bodyEl = document.getElementById('markdown-body');
    if (bodyEl) {
      const src = doc.content.replace(/^\s*#\s+.*\n+/, '');
      bodyEl.innerHTML = this.readerEngine.render(src);
      // Run Mermaid
      setTimeout(() => this.readerEngine.initMermaid(), 50);
    }

    // Render Chapter Pagination Footer
    const nonIndexDocs = this.catalog.documents.filter(d => d.volumeKey !== 'README.md');
    const curIdx = nonIndexDocs.findIndex(d => d.id === docId);
    const prevDoc = curIdx > 0 ? nonIndexDocs[curIdx - 1] : null;
    const nextDoc = curIdx >= 0 && curIdx < nonIndexDocs.length - 1 ? nonIndexDocs[curIdx + 1] : null;
    const pagEl = document.getElementById('chapter-pagination');
    if (pagEl) {
      pagEl.innerHTML = `
        ${prevDoc ? `
          <a href="#/doc/${prevDoc.id}" class="page-nav-card" onclick="event.preventDefault(); app.loadDocument('${prevDoc.id}')">
            <span class="page-nav-label">← Previous Chapter</span>
            <span class="page-nav-title">${prevDoc.shortTitle || prevDoc.title}</span>
          </a>
        ` : `<div></div>`}
        ${nextDoc ? `
          <a href="#/doc/${nextDoc.id}" class="page-nav-card" style="text-align: right; margin-left: auto;" onclick="event.preventDefault(); app.loadDocument('${nextDoc.id}')">
            <span class="page-nav-label">Next Chapter →</span>
            <span class="page-nav-title">${nextDoc.shortTitle || nextDoc.title}</span>
          </a>
        ` : `<div></div>`}
      `;
    }

    // Render Right-Rail TOC & Document Stats
    this.renderRightRail(doc);
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Close mobile drawer if open
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.remove('open');
  }

  scrollToAnchor(anchor) {
    let el = document.getElementById(anchor);
    if (!el) {
      // Fall back to a fuzzy match on heading text (anchor rules differ slightly between Python and JS)
      const want = anchor.replace(/-/g, '');
      el = Array.from(document.querySelectorAll('#markdown-body h1,h2,h3,h4'))
        .find(h => h.textContent.toLowerCase().replace(/[^a-z0-9]/g, '') === want.replace(/[^a-z0-9]/g, ''));
    }
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  /** Resolve a link found inside a research document to a catalog doc or a served asset. */
  resolveDocLink(href) {
    const ROOT = 'file:///home/acinonyx/Desktop/MAS/research/';
    let rel = null;
    if (href.startsWith(ROOT)) {
      rel = href.slice(ROOT.length);
    } else if (!/^[a-z][a-z0-9+.-]*:/i.test(href) && !href.startsWith('#')) {
      const cur = this.catalog.documents.find(d => d.id === this.activeDocId);
      const base = 'http://x/' + (cur ? cur.relPath.replace(/[^/]*$/, '') : '');
      rel = new URL(href, base).pathname.slice(1);
    }
    if (rel === null) return null;
    const [path, hash] = decodeURIComponent(rel).split('#');
    const clean = path.replace(/\/$/, '');
    const doc = this.catalog.documents.find(d => d.relPath === clean || d.relPath === clean + '/README.md');
    if (doc) return { type: 'doc', id: doc.id, hash };
    if (/\.(pdf|png|jpe?g|svg)$/i.test(clean)) return { type: 'asset', url: '../research/' + clean };
    return null;
  }

  getBadgeClass(vKey) {
    if (vKey === 'agentic_systems') return 'badge-cyan';
    if (vKey === 'ai_encyclopedia') return 'badge-purple';
    if (vKey === 'google_cloud_agentic_infra') return 'badge-emerald';
    return 'badge-amber';
  }

  renderRightRail(doc) {
    const tocList = document.getElementById('toc-list');
    if (tocList) {
      if (doc.headings && doc.headings.length) {
        tocList.innerHTML = doc.headings.map(h => `
          <li>
            <a href="#${h.anchor}" onclick="event.preventDefault(); app.scrollToAnchor('${h.anchor}')" class="toc-item ${h.level === 3 ? 'level-3' : ''}">${h.title}</a>
          </li>
        `).join('');
      } else {
        tocList.innerHTML = '<li style="color: var(--text-muted); font-size: 0.8rem;">Overview</li>';
      }
    }

    // Update Rail Stats
    const linesEl = document.getElementById('rail-doc-lines');
    const wordsEl = document.getElementById('rail-doc-words');
    const pathEl = document.getElementById('rail-doc-path');
    if (linesEl) linesEl.innerText = doc.lineCount.toLocaleString();
    if (wordsEl) wordsEl.innerText = doc.wordCount.toLocaleString();
    if (pathEl) pathEl.innerText = doc.relPath;
  }

  renderVault() {
    const mount = document.getElementById('sim-mount');
    if (!mount) return;

    mount.innerHTML = `
      <div class="sim-header">
        <div class="badge badge-cyan">Primary Research Artifacts</div>
        <h2 class="sim-title">Academic Papers & Architecture Diagram Vault</h2>
        <p class="sim-desc">
          Original foundational PDFs (Vaswani et al. Attention, CoALA Cognitive Architecture, ReAct, Shoham Textbook) 
          and Google Cloud Agentic Infrastructure diagram captures on disk.
        </p>
      </div>

      <div style="margin-bottom: 2rem;">
        <h3 style="color: #fff; font-family: var(--font-display); margin-bottom: 1rem;">Seminal Academic Research Papers (PDFs)</h3>
        <div class="vault-grid">
          ${(this.catalog.pdfs || []).map(pdf => `
            <div class="vault-card">
              <div>
                <div class="vault-icon">📄</div>
                <div class="vault-title">${pdf.title}</div>
                <div class="vault-meta">Size: ${pdf.sizeMb} MB • Local File</div>
              </div>
              <a href="../research/${pdf.relPath}" target="_blank" class="btn btn-secondary btn-sm" style="width: 100%;">
                Open PDF Reader ↗
              </a>
            </div>
          `).join('')}
        </div>
      </div>

      <div>
        <h3 style="color: #fff; font-family: var(--font-display); margin-bottom: 1rem;">Google Cloud Architecture Blueprints & Captures</h3>
        <div class="vault-grid">
          ${(this.catalog.diagrams || []).map(diag => `
            <div class="vault-card">
              <div>
                <div class="vault-icon">🖼️</div>
                <div class="vault-title">${diag.title}</div>
                <div class="vault-meta">Format: PNG • Local Capture</div>
              </div>
              <a href="../research/${diag.relPath}" target="_blank" class="btn btn-secondary btn-sm" style="width: 100%;">
                View Fullscreen ↗
              </a>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  /* ------------------------------------------------------------------------
     Search Modal Controller
     ------------------------------------------------------------------------ */
  openSearch() {
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('search-input');
    if (modal && input) {
      modal.classList.add('active');
      input.value = '';
      input.focus();
      this.executeSearch('');
    }
  }

  closeSearch() {
    const modal = document.getElementById('search-modal');
    if (modal) modal.classList.remove('active');
  }

  executeSearch(query) {
    this.searchResults = this.searchEngine.search(query, 12);
    this.selectedSearchIndex = 0;
    this.renderSearchResults(query);
  }

  setSearchFilter(category) {
    this.searchEngine.setFilter(category);
    ['ALL', 'FAVORITES', 'agentic_systems', 'ai_encyclopedia', 'google_cloud_agentic_infra', 'multi_agent_systems'].forEach(c => {
      const chip = document.getElementById(`filter-chip-${c}`);
      if (chip) {
        if (c === category) chip.classList.add('active');
        else chip.classList.remove('active');
      }
    });
    const input = document.getElementById('search-input');
    this.executeSearch(input ? input.value : '');
  }

  renderSearchResults(query) {
    const resultsContainer = document.getElementById('search-results');
    if (!resultsContainer) return;

    if (!this.searchResults.length) {
      resultsContainer.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.9rem;">
          No matching research documents found for "${query}".
        </div>
      `;
      return;
    }

    resultsContainer.innerHTML = this.searchResults.map((res, i) => `
      <div class="search-result-item ${i === this.selectedSearchIndex ? 'selected' : ''}" 
        onclick="app.selectSearchResult(${i})" onmouseover="app.hoverSearchResult(${i})">
        <div class="result-header">
          <span class="result-title">${this.searchEngine.highlightMatch(res.doc.title, query)}</span>
          <span class="badge ${this.getBadgeClass(res.doc.volumeKey)}">${res.doc.volumeBadge}</span>
        </div>
        <p class="result-snippet">${this.searchEngine.highlightMatch(res.snippet, query)}</p>
      </div>
    `).join('');
  }

  hoverSearchResult(idx) {
    this.selectedSearchIndex = idx;
    document.querySelectorAll('.search-result-item').forEach((el, i) => {
      if (i === idx) el.classList.add('selected');
      else el.classList.remove('selected');
    });
  }

  selectSearchResult(idx) {
    const item = this.searchResults[idx];
    if (item && item.doc) {
      this.closeSearch();
      this.loadDocument(item.doc.id);
    }
  }

  /* ------------------------------------------------------------------------
     Merkle Cryptographic Audit Modal
     ------------------------------------------------------------------------ */
  openAuditModal() {
    const modal = document.getElementById('audit-modal');
    if (modal) modal.classList.add('active');
  }

  closeAuditModal() {
    const modal = document.getElementById('audit-modal');
    if (modal) modal.classList.remove('active');
  }

  /* ------------------------------------------------------------------------
     Global Keyboard Shortcuts & Event Listeners
     ------------------------------------------------------------------------ */
  setupEventListeners() {
    const body = document.getElementById('markdown-body');
    if (body) {
      body.addEventListener('click', (e) => {
        const a = e.target.closest('a[href]');
        if (!a) return;
        const href = a.getAttribute('href');
        if (href.startsWith('#')) {
          e.preventDefault();
          this.scrollToAnchor(decodeURIComponent(href.slice(1)));
          return;
        }
        const target = this.resolveDocLink(href);
        if (!target) return;
        e.preventDefault();
        if (target.type === 'doc') {
          this.loadDocument(target.id);
          if (target.hash) setTimeout(() => this.scrollToAnchor(target.hash), 80);
        } else {
          window.open(target.url, '_blank', 'noopener');
        }
      });
    }

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => this.executeSearch(e.target.value));
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.selectedSearchIndex = (this.selectedSearchIndex + 1) % Math.max(1, this.searchResults.length);
          this.renderSearchResults(searchInput.value);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.selectedSearchIndex = (this.selectedSearchIndex - 1 + this.searchResults.length) % Math.max(1, this.searchResults.length);
          this.renderSearchResults(searchInput.value);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          this.selectSearchResult(this.selectedSearchIndex);
        } else if (e.key === 'Escape') {
          this.closeSearch();
        }
      });
    }

    // Mobile menu toggle
    const toggle = document.getElementById('mobile-toggle');
    if (toggle) {
      toggle.addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.toggle('open');
      });
    }
  }

  // Reader Interactive Controls
  toggleStarCurrentDoc() {
    if (!this.activeDocId) return;
    const starred = this.readerEngine.toggleBookmark(this.activeDocId);
    const starBtn = document.getElementById('star-btn');
    if (starBtn) {
      starBtn.classList.toggle('star-active', starred);
      const icon = document.getElementById('star-btn-icon');
      const txt = document.getElementById('star-btn-text');
      if (icon) icon.innerText = starred ? '★' : '☆';
      if (txt) txt.innerText = starred ? 'Saved' : 'Save';
    }
  }

  copyShareLink() {
    if (!this.activeDocId) return;
    const url = `${window.location.origin}${window.location.pathname}#/doc/${this.activeDocId}`;
    navigator.clipboard.writeText(url).then(() => {
      if (window.toast) window.toast.show('Share link copied to clipboard 🔗', 'success');
    });
  }

  copyMarkdown() {
    const doc = this.catalog.documents.find(d => d.id === this.activeDocId);
    if (!doc) return;
    navigator.clipboard.writeText(doc.content).then(() => {
      if (window.toast) window.toast.show('Raw markdown copied to clipboard 📄', 'success');
    });
  }

  toggleDensity() {
    const newMode = this.readerEngine.density === 'comfortable' ? 'compact' : 'comfortable';
    this.readerEngine.setDensity(newMode);
  }

  openCopilot() {
    if (window.copilot) window.copilot.open();
  }

  closeCopilot() {
    if (window.copilot) window.copilot.close();
  }

  openShortcutsModal() {
    const modal = document.getElementById('shortcuts-modal');
    if (modal) modal.classList.add('active');
  }

  closeShortcutsModal() {
    const modal = document.getElementById('shortcuts-modal');
    if (modal) modal.classList.remove('active');
  }

  prevChapter() {
    const docs = this.catalog.documents.filter(d => d.volumeKey !== 'README.md');
    const idx = docs.findIndex(d => d.id === this.activeDocId);
    if (idx > 0) this.loadDocument(docs[idx - 1].id);
  }

  nextChapter() {
    const docs = this.catalog.documents.filter(d => d.volumeKey !== 'README.md');
    const idx = docs.findIndex(d => d.id === this.activeDocId);
    if (idx >= 0 && idx < docs.length - 1) this.loadDocument(docs[idx + 1].id);
  }

  setupGlobalShortcuts() {
    window.addEventListener('keydown', (e) => {
      const isInput = ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName);

      // Ctrl+K or Cmd+K opens search
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        this.openSearch();
        return;
      }

      // Ctrl+J or Cmd+J opens Copilot
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        this.openCopilot();
        return;
      }

      // Escape closes any open modal or drawer
      if (e.key === 'Escape') {
        this.closeSearch();
        this.closeAuditModal();
        this.closeCopilot();
        this.closeShortcutsModal();
        return;
      }

      // Non-input single key shortcuts
      if (!isInput) {
        if (e.key === '/') {
          e.preventDefault();
          this.openSearch();
        } else if (e.key === '?') {
          e.preventDefault();
          this.openShortcutsModal();
        } else if (e.key === '[') {
          e.preventDefault();
          this.prevChapter();
        } else if (e.key === ']') {
          e.preventDefault();
          this.nextChapter();
        } else if (e.key.toLowerCase() === 'b') {
          e.preventDefault();
          this.toggleStarCurrentDoc();
        } else if (e.key.toLowerCase() === 'h') {
          this.switchView('home');
        } else if (e.key.toLowerCase() === 'r') {
          this.switchView('reader');
        } else if (e.key.toLowerCase() === 't') {
          this.switchView('topology');
        } else if (e.key.toLowerCase() === 'f') {
          this.switchView('finops');
        }
      }
    });
  }
}

// Global Application Instance
window.app = new PortalApp();
document.addEventListener('DOMContentLoaded', () => {
  window.app.init();
});
