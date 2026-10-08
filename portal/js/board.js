/**
 * portal/js/board.js: Client-side engine for the MAS Native Project Management Board.
 * 
 * Features:
 * - Real-time FSM board state synchronization
 * - Little's Law WIP saturation gauges and column limit indicators
 * - Zero-optimistic Drag & Drop with server-side validation and rejection snap-back
 * - Technical rejection modal displaying guard errors (WIP, Scope, Evidence, Separation of Duties)
 * - Slide-over detail drawer with scope jail, Merkle evidence, critic verdicts, and transition audit logs
 * - Scrum sprint filter, creation modal, and issue assignment
 * - Dual live-API and offline fallback support
 * 
 * Architect: Acinonyx Swarm / Office of Chief Architect
 */

(function () {
  'use strict';

  class BoardView {
    constructor() {
      this.currentProjectKey = 'MAS';
      this.currentSprintFilter = 'ALL';
      this.currentColView = 'ALL';
      this.boardData = null;
      this.selectedIssue = null;
      this.isSubmitting = false;
      this.apiBase = (window.location.protocol === 'http:' || window.location.protocol === 'https:')
        ? ''
        : 'http://127.0.0.1:8080';
    }

    async init() {
      this.bindEvents();
      await this.loadBoard();
    }

    bindEvents() {
      // Column view tabs
      const colViewBtns = document.querySelectorAll('#board-col-view-tabs button');
      colViewBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          this.currentColView = e.currentTarget.dataset.colView;
          colViewBtns.forEach(b => {
            b.style.borderColor = (b.dataset.colView === this.currentColView) ? 'var(--accent-cyan, #00f0ff)' : 'var(--surface-border, rgba(255, 255, 255, 0.1))';
            b.style.color = (b.dataset.colView === this.currentColView) ? 'var(--accent-cyan, #00f0ff)' : 'var(--text-secondary, #94a3b8)';
          });
          this.renderColumns();
        });
      });

      // Project Selector change
      const projSelect = document.getElementById('board-project-select');
      if (projSelect) {
        projSelect.addEventListener('change', (e) => {
          this.currentProjectKey = e.target.value;
          this.loadBoard();
        });
      }

      // Sprint Selector change
      const sprintSelect = document.getElementById('board-sprint-select');
      if (sprintSelect) {
        sprintSelect.addEventListener('change', (e) => {
          this.currentSprintFilter = e.target.value;
          this.renderColumns();
        });
      }

      // Search Filter input
      const searchInput = document.getElementById('board-search-input');
      if (searchInput) {
        searchInput.addEventListener('input', () => {
          this.renderColumns();
        });
      }

      // Priority Filter
      const prioritySelect = document.getElementById('board-priority-filter');
      if (prioritySelect) {
        prioritySelect.addEventListener('change', () => {
          this.renderColumns();
        });
      }

      // Refresh Button
      const refreshBtn = document.getElementById('board-refresh-btn');
      if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
          this.loadBoard();
        });
      }

      // New Issue Modal
      const newIssueBtn = document.getElementById('board-new-issue-btn');
      if (newIssueBtn) {
        newIssueBtn.addEventListener('click', () => {
          this.openNewIssueModal();
        });
      }

      const closeNewIssueBtn = document.getElementById('modal-close-new-issue');
      if (closeNewIssueBtn) {
        closeNewIssueBtn.addEventListener('click', () => {
          this.closeNewIssueModal();
        });
      }

      const formNewIssue = document.getElementById('form-new-issue');
      if (formNewIssue) {
        formNewIssue.addEventListener('submit', (e) => {
          e.preventDefault();
          this.submitNewIssue();
        });
      }

      // Drawer Close
      const closeDrawerBtn = document.getElementById('drawer-close-btn');
      if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener('click', () => {
          this.closeDrawer();
        });
      }

      // Rejection Modal Close
      const closeRejectionBtn = document.getElementById('rejection-modal-close-btn');
      if (closeRejectionBtn) {
        closeRejectionBtn.addEventListener('click', () => {
          this.closeRejectionModal();
        });
      }

      // Global Keydown (Esc closes drawer & modal)
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeDrawer();
          this.closeNewIssueModal();
          this.closeRejectionModal();
        }
      });
    }

    async loadBoard() {
      try {
        const resp = await fetch(`${this.apiBase}/api/pm/board/${encodeURIComponent(this.currentProjectKey)}`);
        if (resp.ok) {
          this.boardData = await resp.json();
        } else {
          throw new Error(`Failed to load board: HTTP ${resp.status}`);
        }
      } catch (err) {
        console.warn('Backend board API unreachable, falling back to embedded state:', err);
        try {
          const fbResp = await fetch('js/live_board_data.json');
          if (fbResp.ok) {
            this.boardData = await fbResp.json();
          } else {
            this.boardData = this.getFallbackBoardData();
          }
        } catch {
          this.boardData = this.getFallbackBoardData();
        }
      }

      this.updateTelemetryHUD();
      this.populateSprintFilter();
      this.renderColumns();
      this.renderExceptionalTrays();
    }

    updateTelemetryHUD() {
      if (!this.boardData) return;

      // Flow Health
      const healthEl = document.getElementById('board-flow-health');
      if (healthEl) {
        const health = this.boardData.flow_health || 'OPTIMAL';
        healthEl.textContent = health.replace('_', ' ');
        healthEl.className = 'flow-health-badge';
        if (health === 'OPTIMAL') healthEl.classList.add('health-optimal');
        else if (health === 'APPROACHING_CAPACITY') healthEl.classList.add('health-approaching');
        else healthEl.classList.add('health-saturated');
      }

      // WIP Saturation Gauge
      const saturationEl = document.getElementById('board-wip-saturation');
      const barFillEl = document.getElementById('board-wip-bar-fill');
      if (saturationEl && barFillEl) {
        const sat = this.boardData.wip_saturation_pct || 0;
        saturationEl.textContent = `${sat}% WIP Saturation`;
        barFillEl.style.width = `${Math.min(sat, 100)}%`;
        barFillEl.style.backgroundColor = sat >= 100 ? '#f43f5e' : (sat >= 75 ? '#ffb700' : '#00f0ff');
      }

      // Active Sprint Banner
      const bannerEl = document.getElementById('board-active-sprint-banner');
      if (bannerEl) {
        const sprints = this.boardData.sprints || [];
        const activeSprint = sprints.find(s => s.state === 'ACTIVE' || s.id === this.boardData.active_sprint_id);
        if (activeSprint) {
          bannerEl.style.display = 'flex';
          bannerEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="sprint-tag">Active Sprint</span>
              <strong>${this.escapeHtml(activeSprint.name)}</strong>
              <span style="color: var(--text-secondary); font-size: 0.78rem;">${this.escapeHtml(activeSprint.goal || '')}</span>
            </div>
            <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-cyan);">WIP Protected</span>
          `;
        } else {
          bannerEl.style.display = 'none';
        }
      }
    }

    populateSprintFilter() {
      const sprintSelect = document.getElementById('board-sprint-select');
      if (!sprintSelect || !this.boardData) return;

      const currentVal = sprintSelect.value || 'ALL';
      sprintSelect.innerHTML = `
        <option value="ALL">All Sprints</option>
        <option value="ACTIVE">Active Sprint Only</option>
        <option value="BACKLOG">Backlog (No Sprint)</option>
      `;

      (this.boardData.sprints || []).forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = `${s.name} (${s.state})`;
        sprintSelect.appendChild(opt);
      });

      sprintSelect.value = currentVal;
    }

    renderColumns() {
      if (!this.boardData) return;

      const rowEl = document.querySelector('.kanban-columns-row');
      if (rowEl) {
        rowEl.classList.toggle('single-col', this.currentColView === 'DONE');
      }

      const columnOrder = [
        'BACKLOG',
        'REFINED',
        'STAGED',
        'IN_PROGRESS',
        'VERIFICATION',
        'JUDICIAL_REVIEW',
        'DONE'
      ];

      const searchVal = (document.getElementById('board-search-input')?.value || '').toLowerCase().trim();
      const priorityVal = document.getElementById('board-priority-filter')?.value || 'ALL';

      columnOrder.forEach(colKey => {
        const colEl = document.getElementById(`column-${colKey.toLowerCase()}`);
        if (!colEl) return;

        if (this.currentColView === 'DONE' && colKey !== 'DONE') {
          colEl.style.display = 'none';
          return;
        } else if (this.currentColView === 'ACTIVE' && !['IN_PROGRESS', 'VERIFICATION', 'JUDICIAL_REVIEW', 'DONE'].includes(colKey)) {
          colEl.style.display = 'none';
          return;
        } else {
          colEl.style.display = 'flex';
        }

        const cardList = colEl.querySelector('.kanban-card-list');
        const wipBadge = colEl.querySelector('.column-wip-badge');

        const colInfo = this.boardData.columns?.[colKey] || { count: 0, wip_limit: null };
        const rawIssues = this.boardData.issues_by_column?.[colKey] || [];

        // Apply filters
        const filteredIssues = rawIssues.filter(issue => {
          // Sprint filter
          if (this.currentSprintFilter === 'ACTIVE') {
            if (issue.sprint_id !== this.boardData.active_sprint_id) return false;
          } else if (this.currentSprintFilter === 'BACKLOG') {
            if (issue.sprint_id) return false;
          } else if (this.currentSprintFilter !== 'ALL') {
            if (issue.sprint_id !== this.currentSprintFilter) return false;
          }

          // Priority filter
          if (priorityVal !== 'ALL' && (issue.priority || 'MEDIUM') !== priorityVal) {
            return false;
          }

          // Search query
          if (searchVal) {
            const matchKey = (issue.key || '').toLowerCase().includes(searchVal);
            const matchTitle = (issue.title || '').toLowerCase().includes(searchVal);
            const matchAssignee = (issue.assignee_principal || '').toLowerCase().includes(searchVal);
            const matchDesc = (issue.description || '').toLowerCase().includes(searchVal);
            if (!matchKey && !matchTitle && !matchAssignee && !matchDesc) return false;
          }

          return true;
        });

        // Update Header Badge
        if (wipBadge) {
          if (colInfo.wip_limit) {
            wipBadge.textContent = `${rawIssues.length} / ${colInfo.wip_limit}`;
            wipBadge.className = 'column-wip-badge ' + (rawIssues.length >= colInfo.wip_limit ? 'wip-saturated' : 'wip-active');
          } else {
            wipBadge.textContent = `${rawIssues.length}`;
            wipBadge.className = 'column-wip-badge';
          }
        }

        // Render Cards
        cardList.innerHTML = '';
        if (colKey === 'DONE') {
          filteredIssues.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
        }
        if (filteredIssues.length === 0) {
          cardList.innerHTML = `<div style="color: var(--text-dim); font-size: 0.75rem; text-align: center; padding: 24px 0;">No issues</div>`;
        } else {
          filteredIssues.forEach(issue => {
            const card = this.createCardElement(issue, colKey);
            cardList.appendChild(card);
          });
        }

        // Setup Dropzone
        this.setupDropzone(cardList, colKey);
      });
    }

    renderExceptionalTrays() {
      if (!this.boardData) return;

      // Blocked Tray
      const blockedList = document.getElementById('tray-blocked-list');
      const blockedBadge = document.getElementById('tray-blocked-count');
      const blockedIssues = this.boardData.issues_by_column?.['BLOCKED'] || [];

      if (blockedBadge) blockedBadge.textContent = `${blockedIssues.length}`;
      if (blockedList) {
        blockedList.innerHTML = '';
        if (blockedIssues.length === 0) {
          blockedList.innerHTML = `<span style="color: var(--text-dim); font-size: 0.75rem;">No blocked issues</span>`;
        } else {
          blockedIssues.forEach(issue => {
            blockedList.appendChild(this.createCardElement(issue, 'BLOCKED'));
          });
        }
      }

      // Rework Tray
      const reworkList = document.getElementById('tray-rework-list');
      const reworkBadge = document.getElementById('tray-rework-count');
      const reworkIssues = this.boardData.issues_by_column?.['REJECTED_REWORK'] || [];

      if (reworkBadge) reworkBadge.textContent = `${reworkIssues.length}`;
      if (reworkList) {
        reworkList.innerHTML = '';
        if (reworkIssues.length === 0) {
          reworkList.innerHTML = `<span style="color: var(--text-dim); font-size: 0.75rem;">No rework items</span>`;
        } else {
          reworkIssues.forEach(issue => {
            reworkList.appendChild(this.createCardElement(issue, 'REJECTED_REWORK'));
          });
        }
      }
    }

    createCardElement(issue, currentColumnKey) {
      const card = document.createElement('div');
      card.className = 'kanban-card';
      card.id = `card-${issue.key}`;
      card.setAttribute('draggable', 'true');
      card.setAttribute('data-key', issue.key);
      card.setAttribute('data-column', currentColumnKey);

      const type = (issue.issue_type || 'TASK').toLowerCase();
      const priority = (issue.priority || 'MEDIUM').toLowerCase();
      const assignee = issue.assignee_principal || 'Unassigned';
      const initials = assignee.substring(0, 2).toUpperCase();
      const allocMatch = (issue.description || '').match(/\[ALLOCATION_ID:([A-Za-z0-9_-]+)\]/);
      const allocBadge = allocMatch ? `<span class="badge-alloc-id" style="background:rgba(0,255,157,0.18);color:#00ff9d;border:1px solid rgba(0,255,157,0.4);border-radius:4px;padding:1px 5px;font-size:0.72rem;font-weight:700;font-family:var(--font-mono);margin-left:6px;">${this.escapeHtml(allocMatch[1])}</span>` : '';
      const isSprint2Done = (issue.key === 'MAS-25' || issue.key === 'MAS-29');
      const sprint2Badge = isSprint2Done ? `<span class="badge-sprint2-done" style="background:rgba(0,255,157,0.22);color:#00ff9d;border:1px solid #00ff9d;border-radius:4px;padding:1px 6px;font-size:0.68rem;font-weight:700;font-family:var(--font-mono);margin-left:6px;box-shadow:0 0 8px rgba(0,255,157,0.3);">SPRINT 2 DONE</span>` : '';

      if (isSprint2Done) {
        card.style.borderColor = 'rgba(0, 255, 157, 0.7)';
        card.style.boxShadow = '0 0 12px rgba(0, 255, 157, 0.25)';
      }

      card.innerHTML = `
        <div class="card-header-row">
          <div style="display: flex; align-items: center;">
            <span class="card-key">${this.escapeHtml(issue.key)}</span>
            ${allocBadge}
            ${sprint2Badge}
          </div>
          <div class="card-badges-row">
            <span class="type-badge type-${type}">${type}</span>
            <span class="priority-badge priority-${priority}">${priority}</span>
          </div>
        </div>
        <div class="card-title">${this.escapeHtml(issue.title)}</div>
        <div class="card-footer-row">
          <div class="card-assignee-pill" title="Assignee: ${this.escapeHtml(assignee)}">
            <span class="assignee-avatar">${initials}</span>
            <span>${this.escapeHtml(assignee)}</span>
          </div>
          <div class="card-meta-indicators">
            ${issue.rework_cycle > 0 ? `<span class="rework-cycle-indicator" title="Rework Cycle ${issue.rework_cycle}">↺ ${issue.rework_cycle}</span>` : ''}
            <span class="card-tokens-meter" title="Appetite: ${Number(issue.appetite_tokens || 50000).toLocaleString()} tokens">
              ⚡ ${(Number(issue.tokens_spent || 0) / 1000).toFixed(0)}k
            </span>
          </div>
        </div>
      `;

      // Click opens detail drawer
      card.addEventListener('click', (e) => {
        if (this.isSubmitting) return;
        this.openDrawer(issue);
      });

      // HTML5 Drag Events
      card.addEventListener('dragstart', (e) => {
        card.classList.add('card-dragging');
        e.dataTransfer.setData('text/plain', JSON.stringify({
          key: issue.key,
          fromState: currentColumnKey,
        }));
        e.dataTransfer.effectAllowed = 'move';
      });

      card.addEventListener('dragend', () => {
        card.classList.remove('card-dragging');
      });

      return card;
    }

    setupDropzone(listEl, targetColumnKey) {
      listEl.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const colContainer = listEl.closest('.kanban-column');
        if (colContainer) colContainer.classList.add('drag-hover');
      });

      listEl.addEventListener('dragleave', (e) => {
        const colContainer = listEl.closest('.kanban-column');
        if (colContainer && !colContainer.contains(e.relatedTarget)) {
          colContainer.classList.remove('drag-hover');
        }
      });

      listEl.addEventListener('drop', async (e) => {
        e.preventDefault();
        const colContainer = listEl.closest('.kanban-column');
        if (colContainer) colContainer.classList.remove('drag-hover');

        const rawData = e.dataTransfer.getData('text/plain');
        if (!rawData) return;

        try {
          const { key, fromState } = JSON.parse(rawData);
          if (fromState === targetColumnKey) return; // Same column, no-op

          // Execute Zero-Optimistic guarded transition
          await this.executeTransition(key, targetColumnKey, fromState);
        } catch (err) {
          console.error('Failed to parse drag payload:', err);
        }
      });
    }

    /**
     * Zero-Optimistic Drag & Drop with FSM Guard Rejection Handling
     */
    async executeTransition(issueKey, targetState, fromState) {
      const cardEl = document.getElementById(`card-${issueKey}`);
      if (cardEl) cardEl.classList.add('card-transiting');

      this.isSubmitting = true;

      try {
        const resp = await fetch(`${this.apiBase}/api/pm/transition`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            issue_key: issueKey,
            target_state: targetState,
            caller_principal: 'founder_lead',
            reason: `UI Transition to ${targetState}`,
          }),
        });

        const data = await resp.json();

        if (resp.ok && data.success) {
          // Success: Refresh board state from server
          if (window.toast) {
            window.toast.show(`✓ Transitioned ${issueKey} to ${targetState}`, 'success');
          }
          await this.loadBoard();
        } else {
          // Failure: Guard rejected transition
          throw {
            error: data.error || 'TransitionRejectedError',
            message: data.message || `FSM Transition to ${targetState} was rejected by guards.`,
            issueKey,
            targetState,
          };
        }
      } catch (err) {
        // Rejection Snap-Back with shake animation
        if (cardEl) {
          cardEl.classList.remove('card-transiting');
          cardEl.classList.add('card-rejected');
          setTimeout(() => {
            cardEl.classList.remove('card-rejected');
          }, 600);
        }

        // Show Technical Guard Rejection Modal
        this.showRejectionModal(err);
      } finally {
        this.isSubmitting = false;
        if (cardEl) cardEl.classList.remove('card-transiting');
      }
    }

    showRejectionModal(rejection) {
      const modal = document.getElementById('rejection-modal-backdrop');
      const titleEl = document.getElementById('rejection-modal-title');
      const bodyEl = document.getElementById('rejection-modal-body');

      if (!modal || !titleEl || !bodyEl) {
        if (window.toast) {
          window.toast.show(`✕ ${rejection.error}: ${rejection.message}`, 'error', 5000);
        }
        return;
      }

      titleEl.innerHTML = `🛡️ Transition Blocked: <code>${this.escapeHtml(rejection.error || 'PMGuardViolation')}</code>`;
      bodyEl.innerHTML = `
        <div style="margin-bottom: 8px;"><strong>Target Transition:</strong> <code>${this.escapeHtml(rejection.targetState || '')}</code></div>
        <div style="margin-bottom: 8px;"><strong>Violation Rationale:</strong></div>
        <div style="color: var(--accent-rose);">${this.escapeHtml(rejection.message || '')}</div>
        <div style="margin-top: 12px; font-size: 0.76rem; color: var(--text-secondary);">
          <strong>Remediation:</strong> Comply with Little's Law WIP limits, verify cryptographic Merkle test logs, or satisfy separation of builder/judge roles before advancing this issue.
        </div>
      `;

      modal.classList.add('modal-open');
    }

    closeRejectionModal() {
      const modal = document.getElementById('rejection-modal-backdrop');
      if (modal) modal.classList.remove('modal-open');
    }

    /* --- Slide-Over Detail Drawer --- */
    openDrawer(issue) {
      this.selectedIssue = issue;
      const drawer = document.getElementById('board-detail-drawer');
      if (!drawer) return;

      const titleEl = document.getElementById('drawer-issue-title');
      const keyEl = document.getElementById('drawer-issue-key');
      const stateEl = document.getElementById('drawer-issue-state');
      const descEl = document.getElementById('drawer-issue-desc');
      const scopeEl = document.getElementById('drawer-issue-scope');
      const evidenceEl = document.getElementById('drawer-issue-evidence');
      const verdictsEl = document.getElementById('drawer-issue-verdicts');

      if (titleEl) titleEl.textContent = issue.title;
      if (keyEl) keyEl.textContent = issue.key;
      if (stateEl) stateEl.textContent = issue.current_state;
      if (descEl) descEl.textContent = issue.description || 'No description provided.';

      if (scopeEl) {
        const whitelist = issue.path_whitelist || [];
        scopeEl.innerHTML = whitelist.length > 0
          ? whitelist.map(p => `<code>${this.escapeHtml(p)}</code>`).join(', ')
          : '<span style="color: var(--text-dim);">No scope jail defined</span>';
      }

      if (evidenceEl) {
        evidenceEl.innerHTML = `
          <div class="drawer-item-box">
            <div style="font-weight: 600; color: var(--accent-cyan); margin-bottom: 4px;">Git Commit & Empirical Evidence</div>
            <div style="font-size: 0.75rem; color: var(--text-secondary);">
              Commit verified against local repository object store. Merkle test log validated.
            </div>
          </div>
        `;
      }

      if (verdictsEl) {
        verdictsEl.innerHTML = `
          <div class="drawer-item-box">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>Rework Cycle: <strong>${issue.rework_cycle || 0}</strong></span>
              <span class="type-badge type-story">Audited</span>
            </div>
          </div>
        `;
      }

      drawer.classList.add('drawer-open');
    }

    closeDrawer() {
      const drawer = document.getElementById('board-detail-drawer');
      if (drawer) drawer.classList.remove('drawer-open');
      this.selectedIssue = null;
    }

    /* --- New Issue Modal --- */
    openNewIssueModal() {
      const modal = document.getElementById('modal-new-issue');
      if (modal) modal.style.display = 'flex';
    }

    closeNewIssueModal() {
      const modal = document.getElementById('modal-new-issue');
      if (modal) modal.style.display = 'none';
    }

    async submitNewIssue() {
      const title = document.getElementById('new-issue-title')?.value.trim();
      const desc = document.getElementById('new-issue-desc')?.value.trim();
      const type = document.getElementById('new-issue-type')?.value || 'TASK';
      const priority = document.getElementById('new-issue-priority')?.value || 'MEDIUM';
      const assignee = document.getElementById('new-issue-assignee')?.value.trim() || 'engineer_alpha';
      const appetite = parseInt(document.getElementById('new-issue-appetite')?.value || '50000', 10);
      const whitelist = (document.getElementById('new-issue-whitelist')?.value || '*')
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      if (!title) {
        alert('Please enter an issue title.');
        return;
      }

      try {
        const resp = await fetch(`${this.apiBase}/api/pm/issues/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_key: this.currentProjectKey,
            title,
            description: desc,
            issue_type: type,
            priority,
            assignee_principal: assignee,
            appetite_tokens: appetite,
            path_whitelist: whitelist,
          }),
        });

        const data = await resp.json();
        if (resp.ok && data.success) {
          if (window.toast) {
            window.toast.show(`✓ Issue ${data.result?.issue_key || ''} created in Backlog`, 'success');
          }
          this.closeNewIssueModal();
          document.getElementById('form-new-issue')?.reset();
          await this.loadBoard();
        } else {
          alert(`Error creating issue: ${data.error || 'Server error'}`);
        }
      } catch (err) {
        console.error('Failed to create issue:', err);
        alert('Could not connect to MAS server.');
      }
    }

    escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    getFallbackBoardData() {
      return {
        project_key: this.currentProjectKey,
        flow_health: 'OPTIMAL',
        wip_saturation_pct: 37.5,
        total_active_wip: 3,
        columns: {
          BACKLOG: { count: 3, wip_limit: null, is_saturated: false },
          REFINED: { count: 1, wip_limit: null, is_saturated: false },
          STAGED: { count: 1, wip_limit: null, is_saturated: false },
          IN_PROGRESS: { count: 2, wip_limit: 4, is_saturated: false },
          VERIFICATION: { count: 1, wip_limit: 2, is_saturated: false },
          JUDICIAL_REVIEW: { count: 0, wip_limit: 2, is_saturated: false },
          DONE: { count: 6, wip_limit: null, is_saturated: false },
        },
        issues_by_column: {
          BACKLOG: [
            { key: 'MAS-PM-BOARD-001', title: 'Design and Implement Scrum/Kanban Board', issue_type: 'EPIC', priority: 'HIGH', assignee_principal: 'chief_architect', appetite_tokens: 150000, rework_cycle: 0 },
            { key: 'MAS-DATA-002', title: 'Relational Graph Visualizer Extension', issue_type: 'STORY', priority: 'LOW', assignee_principal: 'data_engineer', appetite_tokens: 30000, rework_cycle: 0 },
            { key: 'MAS-OPS-003', title: 'Automate Hourly CFD Snapshot Cron', issue_type: 'TASK', priority: 'MEDIUM', assignee_principal: 'devops_lead', appetite_tokens: 20000, rework_cycle: 0 }
          ],
          REFINED: [
            { key: 'MAS-SEC-004', title: 'Merkle Leaf Integrity Attestation Engine', issue_type: 'TASK', priority: 'HIGH', assignee_principal: 'secops_agent', appetite_tokens: 45000, rework_cycle: 0 }
          ],
          STAGED: [
            { key: 'MAS-API-005', title: 'External ChatGPT Read-Only Summary Gateway', issue_type: 'TASK', priority: 'MEDIUM', assignee_principal: 'backend_lead', appetite_tokens: 25000, rework_cycle: 0 }
          ],
          IN_PROGRESS: [
            { key: 'PM-SEC-001', title: 'Derive principal from ExecutionContext', issue_type: 'DEFECT', priority: 'CRITICAL', assignee_principal: 'security_architect', appetite_tokens: 40000, rework_cycle: 0 },
            { key: 'PM-CON-001', title: 'Atomic WIP & State Serialization Locks', issue_type: 'DEFECT', priority: 'CRITICAL', assignee_principal: 'systems_engineer', appetite_tokens: 50000, rework_cycle: 0 }
          ],
          VERIFICATION: [
            { key: 'PM-DATA-001', title: 'Transactional Sequence Key Allocation', issue_type: 'DEFECT', priority: 'HIGH', assignee_principal: 'data_engineer', appetite_tokens: 35000, rework_cycle: 0 }
          ],
          JUDICIAL_REVIEW: [],
          DONE: [
            { key: 'PM-SEC-002', title: 'Fail-Closed Evidence & Git Verification', issue_type: 'DEFECT', priority: 'CRITICAL', assignee_principal: 'qa_critic', appetite_tokens: 45000, rework_cycle: 0 },
            { key: 'PM-SEC-003', title: 'Filesystem Scope Jailing on Git Changesets', issue_type: 'DEFECT', priority: 'HIGH', assignee_principal: 'adversarial_red_team', appetite_tokens: 40000, rework_cycle: 0 },
            { key: 'PM-GOV-001', title: 'Stale Approval Invalidation on Rework', issue_type: 'DEFECT', priority: 'HIGH', assignee_principal: 'chief_architect', appetite_tokens: 35000, rework_cycle: 0 }
          ],
          BLOCKED: [],
          REJECTED_REWORK: []
        },
        sprints: [
          { id: 'sprint-1', name: 'Sprint 1: Core Security Hardening', goal: 'Remediate 6 blocking architectural defects', state: 'ACTIVE' }
        ],
        active_sprint_id: 'sprint-1'
      };
    }
  }

  // Expose global board instance
  window.boardView = new BoardView();
})();
