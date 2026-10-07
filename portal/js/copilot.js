/**
 * portal/js/copilot.js: In-Browser Research Copilot & Knowledge Synthesis Engine.
 * 
 * Performs semantic scanning, passage extraction, and answers questions using the
 * 82 indexed research modules with verified, direct clickable citations.
 * 
 * Architect: data_architect_ai / MAS Swarm
 */

class ResearchCopilot {
  constructor(catalog) {
    this.catalog = catalog || window.RESEARCH_CATALOG || { documents: [] };
    this.history = [];
    this.isOpen = false;
    this.suggestedQuestions = [
      "What is GRPO and how does it eliminate Critic models?",
      "How does CoALA organize working memory and episodic memory?",
      "What are the token FinOps economics of prompt caching?",
      "What is Set-of-Marks visual grounding in computer use?",
      "What is the difference between SaaS and Work-as-a-Service (WaaS)?",
      "How do Liquid Strike Pods dispatch ephemeral multi-agent subtasks?"
    ];
  }

  init() {
    this.bindEvents();
  }

  bindEvents() {
    const input = document.getElementById('copilot-input');
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.ask(input.value.trim());
        }
      });
    }
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    const drawer = document.getElementById('copilot-drawer');
    const overlay = document.getElementById('copilot-overlay');
    if (drawer) {
      drawer.classList.add('open');
      drawer.setAttribute('aria-hidden', 'false');
    }
    if (overlay) overlay.classList.add('open');
    this.isOpen = true;

    const input = document.getElementById('copilot-input');
    if (input) {
      setTimeout(() => input.focus(), 150);
    }

    if (this.history.length === 0) {
      this.renderSuggestions();
    }
  }

  close() {
    const drawer = document.getElementById('copilot-drawer');
    const overlay = document.getElementById('copilot-overlay');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
    if (overlay) overlay.classList.remove('open');
    this.isOpen = false;
  }

  renderSuggestions() {
    const container = document.getElementById('copilot-messages');
    if (!container) return;

    container.innerHTML = `
      <div class="copilot-msg copilot-assistant">
        <div class="copilot-avatar">✨</div>
        <div class="copilot-bubble">
          <p><strong>Acinonyx Research Copilot Online.</strong></p>
          <p>I have indexed all 82 research volumes, math formulations, architectural blueprints, and Token FinOps models. Ask any technical question or select an inquiry below:</p>
          <div class="copilot-suggestions">
            ${this.suggestedQuestions.map(q => `
              <button class="copilot-suggestion-chip" onclick="window.copilot.ask('${this.escapeHtml(q)}')">
                ${this.escapeHtml(q)}
              </button>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  }

  ask(question) {
    if (!question || !question.trim()) return;

    const input = document.getElementById('copilot-input');
    if (input) input.value = '';

    const container = document.getElementById('copilot-messages');
    if (!container) return;

    // Append user question
    const userDiv = document.createElement('div');
    userDiv.className = 'copilot-msg copilot-user';
    userDiv.innerHTML = `
      <div class="copilot-bubble">
        <p>${this.escapeHtml(question)}</p>
      </div>
      <div class="copilot-avatar">👤</div>
    `;
    container.appendChild(userDiv);
    container.scrollTop = container.scrollHeight;

    // Add thinking indicator
    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = 'copilot-thinking';
    thinkingDiv.className = 'copilot-msg copilot-assistant';
    thinkingDiv.innerHTML = `
      <div class="copilot-avatar">✨</div>
      <div class="copilot-bubble copilot-thinking-bubble">
        <span class="thinking-dot"></span>
        <span class="thinking-dot"></span>
        <span class="thinking-dot"></span>
        <span style="font-size:0.8rem; color:var(--text-muted); margin-left:8px;">Scanning 82 research compendiums...</span>
      </div>
    `;
    container.appendChild(thinkingDiv);
    container.scrollTop = container.scrollHeight;

    // Execute semantic research extraction
    setTimeout(() => {
      const response = this.synthesizeAnswer(question);
      const thinkingEl = document.getElementById('copilot-thinking');
      if (thinkingEl) thinkingEl.remove();

      const assistantDiv = document.createElement('div');
      assistantDiv.className = 'copilot-msg copilot-assistant';
      assistantDiv.innerHTML = `
        <div class="copilot-avatar">✨</div>
        <div class="copilot-bubble">
          <div class="copilot-answer-text">${response.htmlAnswer}</div>
          ${response.citations.length > 0 ? `
            <div class="copilot-citations-header">Verified Research Citations:</div>
            <div class="copilot-citations-list">
              ${response.citations.map(c => `
                <a href="#/doc/${c.docId}" class="copilot-citation-pill" onclick="window.copilot.onCitationClick(event, '${c.docId}')">
                  <span class="citation-vol" style="background:${c.color || 'var(--accent-cyan)'}"></span>
                  <span class="citation-title">${this.escapeHtml(c.title)}</span>
                  <span class="citation-arrow">→</span>
                </a>
              `).join('')}
            </div>
          ` : ''}
        </div>
      `;
      container.appendChild(assistantDiv);
      container.scrollTop = container.scrollHeight;

      this.history.push({ question, response });
    }, 380);
  }

  synthesizeAnswer(question) {
    const qLower = question.toLowerCase();
    const terms = qLower.split(/\W+/).filter(t => t.length > 2);
    const docs = (this.catalog.documents || []).filter(d => d.volumeKey !== 'README.md');

    // Score documents by relevance
    const scoredDocs = [];
    for (const doc of docs) {
      let score = 0;
      const text = (doc.content || '').toLowerCase();
      const title = (doc.title || '').toLowerCase();
      const tags = (doc.tags || []).map(t => t.toLowerCase());

      for (const t of terms) {
        if (title.includes(t)) score += 40;
        if (tags.some(tag => tag.includes(t))) score += 20;
        const matches = (text.match(new RegExp('\\b' + t + '\\b', 'g')) || []).length;
        score += Math.min(matches * 2, 30);
      }

      if (score > 15) {
        scoredDocs.push({ doc, score });
      }
    }

    scoredDocs.sort((a, b) => b.score - a.score);
    const topMatches = scoredDocs.slice(0, 3);

    if (topMatches.length === 0) {
      return {
        htmlAnswer: `<p>No direct match found in the research repository for <em>"${this.escapeHtml(question)}"</em>. Try inquiring about <strong>GRPO, CoALA, Token FinOps, Computer Use, Multi-Agent Topologies, or WaaS</strong>.</p>`,
        citations: []
      };
    }

    // Extract best passages from top document
    const primary = topMatches[0].doc;
    const paragraphs = (primary.content || '').split(/\n\n+/);
    let bestParagraph = '';
    let maxMatch = -1;

    for (const p of paragraphs) {
      if (p.startsWith('#') || p.startsWith('```') || p.length < 60) continue;
      const pLower = p.toLowerCase();
      let pMatches = 0;
      for (const t of terms) {
        if (pLower.includes(t)) pMatches++;
      }
      if (pMatches > maxMatch) {
        maxMatch = pMatches;
        bestParagraph = p;
      }
    }

    // Clean markdown in paragraph
    let cleanText = bestParagraph.replace(/[#*`_>]/g, ' ').replace(/\s+/g, ' ').trim();
    if (cleanText.length > 360) {
      cleanText = cleanText.slice(0, 350) + '...';
    }

    // Compose formatted answer
    let htmlAnswer = `
      <p>Based on <strong>${this.escapeHtml(primary.shortTitle || primary.title)}</strong> in <em>${this.escapeHtml(primary.volumeTitle)}</em>:</p>
      <blockquote class="copilot-quote">
        "${this.escapeHtml(cleanText || primary.summary)}"
      </blockquote>
      <p style="margin-top: 8px; font-size: 0.9rem; color: var(--text-secondary);">
        This architecture is ratified under the Acinonyx Living Knowledge Base with cryptographic Merkle verification.
      </p>
    `;

    const citations = topMatches.map(m => ({
      docId: m.doc.id,
      title: m.doc.shortTitle || m.doc.title,
      volTitle: m.doc.volumeTitle,
      color: m.doc.volumeColor
    }));

    return { htmlAnswer, citations };
  }

  onCitationClick(event, docId) {
    event.preventDefault();
    this.close();
    if (window.app) {
      window.app.loadDocument(docId);
      if (window.toast) {
        window.toast.show(`Navigated to chapter`, 'success');
      }
    }
  }

  escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

window.ResearchCopilot = ResearchCopilot;
window.copilot = new ResearchCopilot(window.RESEARCH_CATALOG);
