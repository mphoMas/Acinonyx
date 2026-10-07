/* Acinonyx workspace upgrade. Buildless; all personal state stays in this browser. */
(() => {
  'use strict';
  const app = window.app;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const read = (key, fallback) => { try { const value = JSON.parse(localStorage.getItem(key)); return Array.isArray(fallback) ? (Array.isArray(value) ? value : fallback) : (value ?? fallback); } catch { return fallback; } };
  const write = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch {} };
  const docs = app.catalog.documents || [];
  const groups = Object.entries(docs.reduce((out, d) => {
    if (d.volumeKey !== 'README.md') (out[d.volumeKey] ||= []).push(d);
    return out;
  }, {}));
  const labels = {
    agentic_systems: ['Agentic systems', 'Reasoning, orchestration, memory and the systems that connect them.', '01'],
    ai_encyclopedia: ['AI encyclopedia', 'A reference library of architectures, research and foundational ideas.', '02'],
    google_cloud_agentic_infra: ['Cloud infrastructure', 'Deployment patterns and agent infrastructure on Google Cloud.', '03'],
    multi_agent_systems: ['Multi-agent foundations', 'Coordination, cognitive architectures and agent design patterns.', '04'],
    system_development_life_cycle: ['Development lifecycle', 'From specifications and implementation to verification and delivery.', '05'],
    devops_dataops_mlops: ['DevOps, DataOps & MLOps', 'Operational practices across software, data and machine learning.', '06'],
    agile_kanban_frameworks: ['Agile & flow', 'Planning, delivery systems and the mechanics of work in progress.', '07'],
    company_governance_and_self_improvement: ['Governance', 'Decision records, working agreements and continuous improvement.', '08']
  };
  const docLink = d => `<a class="ws-doc" href="#/doc/${encodeURIComponent(d.id)}" data-doc="${esc(d.id)}"><span><small>${esc(labels[d.volumeKey]?.[0] || d.volumeTitle)}</small><strong>${esc(d.shortTitle || d.title)}</strong></span><span>${d.readTimeMin || 1} min ↗</span></a>`;
  app.renderHome = function () {
    const recent = read('acinonyx_recent', []);
    const saved = read('acinonyx_bookmarks', []);
    const last = docs.find(d => d.id === recent[0]);
    const words = docs.reduce((sum,d) => sum + (d.wordCount || 0), 0);
    const featured = ['agentic_systems', 'google_cloud_agentic_infra', 'multi_agent_systems'].map(k => docs.find(d=>d.volumeKey===k && d.shortTitle!=='Overview')).filter(Boolean);
    document.getElementById('view-home').innerHTML = `
      <div class="ws-status"><span><i></i> YOUR RESEARCH WORKSPACE</span><button class="ws-text" data-action="audit">Catalogue details ↗</button></div>
      <section class="ws-intro" aria-labelledby="ws-title">
        <div class="ws-intro-copy"><div class="ws-eyebrow">ACINONYX / RESEARCH ATLAS</div><h1 id="ws-title">Understand the systems.<br><em>Build what comes next.</em></h1><p>A working library for AI and agentic engineering. Explore the research, compare approaches, and put ideas to work.</p>
          <div class="ws-actions"><button class="ws-primary" data-action="search">Search the library <span>↗</span></button><a class="ws-secondary" href="#collections" data-action="collections">Browse collections ↓</a></div>
        </div>
        <aside class="ws-resume"><span class="ws-eyebrow">${last ? 'PICK UP WHERE YOU LEFT OFF' : 'A PLACE TO BEGIN'}</span><div class="ws-book-mark" aria-hidden="true">A<span> / </span>R</div><h2>${esc(last?.shortTitle || 'Inside agentic systems')}</h2><p>${last ? esc(last.volumeTitle) : 'Start with the intelligence layer, then explore how agents reason, collaborate and act.'}</p><button class="ws-text" data-doc="${esc((last || featured[0] || docs[0])?.id)}">${last ? 'Continue reading' : 'Open the first chapter'} <span>→</span></button></aside>
      </section>
      <div class="ws-stats" aria-label="Catalogue statistics"><div><strong>${docs.length}</strong><span>documents</span></div><div><strong>${groups.length}</strong><span>collections</span></div><div><strong>${Math.round(words/1000)}k</strong><span>words indexed</span></div><div><strong>${saved.length}</strong><span>saved chapters</span></div><span class="ws-local">Your reading history stays on this device.</span></div>
      <section class="ws-library" id="collections" aria-labelledby="collections-title"><div class="ws-section-head"><div><span class="ws-eyebrow">THE LIBRARY</span><h2 id="collections-title">Choose a direction.</h2></div><label class="ws-filter"><span class="sr-only">Filter collections</span><span aria-hidden="true">⌕</span><input id="collection-filter" type="search" placeholder="Filter collections…" autocomplete="off"></label></div>
        <div class="ws-collections">${groups.sort((a,b)=>(labels[a[0]]?.[2]||'').localeCompare(labels[b[0]]?.[2]||'')).map(([key,items])=>{
          const [name,description,num]=labels[key] || [items[0].volumeTitle,items[0].summary,'—'];
          return `<a class="ws-collection" href="#/doc/${encodeURIComponent(items[0].id)}" data-doc="${esc(items[0].id)}" data-collection="${esc((name+' '+description+' '+items[0].volumeTitle).toLowerCase())}"><span class="ws-collection-top"><span>${num}</span><span>${items.length} chapters ↗</span></span><h3>${esc(name)}</h3><p>${esc(description)}</p><span class="ws-collection-bottom">Explore collection <span>→</span></span></a>`;
        }).join('')}</div><p id="collection-empty" class="ws-empty" hidden>No collections match. Try “cloud”, “agents” or “data”.</p>
      </section>
      <section class="ws-tools" aria-labelledby="tools-title"><div><span class="ws-eyebrow">WORKBENCH</span><h2 id="tools-title">Explore by doing.</h2><p>Interactive tools for testing assumptions and understanding trade-offs.</p></div><div class="ws-tool-links">${[['finops','01','Token economics','Estimate costs for your workload.'],['topology','02','Agent topologies','Explore how agents coordinate.'],['benchmarks','03','Model comparisons','Inspect the bundled benchmark data.'],['timeline','04','AI timeline','Trace the ideas behind today’s systems.']].map(([id,num,title,desc])=>`<a href="#/${id}" data-view="${id}"><span class="ws-tool-number">${num}</span><span><strong>${title}</strong><small>${desc}</small></span><span>↗</span></a>`).join('')}</div></section>
      <section class="ws-reading"><div><div class="ws-section-head"><h2>Start exploring</h2><button class="ws-text" data-action="search">All documents ↗</button></div>${featured.map(docLink).join('')}</div><div><div class="ws-section-head"><h2>${recent.length ? 'Recently opened' : 'Your reading list'}</h2><button class="ws-text" data-action="saved">Saved ↗</button></div>${(recent.length ? recent.map(id=>docs.find(d=>d.id===id)).filter(Boolean).slice(0,3) : saved.map(id=>docs.find(d=>d.id===id)).filter(Boolean).slice(0,3)).map(docLink).join('') || '<div class="ws-empty">A little research, every day.<br><span>Open a chapter to begin. Use Save in the reader to keep it for later.</span></div>'}</div></section>
      <footer class="ws-footer"><span>ACINONYX LABS <span class="ws-muted">/ Living Agentic Atlas</span></span><span>Local catalogue · ${esc(new Date(app.catalog.metadata.generatedAt).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}))}</span></footer>`;
    document.getElementById('collection-filter').addEventListener('input', e => {
      let count=0; const q=e.target.value.toLowerCase().trim();
      document.querySelectorAll('.ws-collection').forEach(el=>{el.hidden=!el.dataset.collection.includes(q);if(!el.hidden)count++;});
      document.getElementById('collection-empty').hidden=count>0;
    });
  };
  const load = app.loadDocument.bind(app);
  app.loadDocument = function (id, opts) {
    if(docs.some(d=>d.id===id)) write('acinonyx_recent',[id,...read('acinonyx_recent',[]).filter(x=>x!==id)].slice(0,8));
    load(id,opts);
    if(innerWidth<=960) document.getElementById('sidebar').classList.remove('open');
  };
  const switchView = app.switchView.bind(app);
  app.switchView = function (view,opts) {
    if(view==='home') this.renderHome();
    switchView(view,opts);
    if(view!=='reader') document.title = `${({home:'Research workspace',finops:'Token economics',topology:'Agent topologies',benchmarks:'Model comparisons',timeline:'AI timeline',vault:'Source vault'})[view] || 'Research'} · Acinonyx`;
    document.querySelectorAll('.nav-link').forEach(a=>a.setAttribute('href','#/'+a.id.replace('nav-','')));
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('mobile-toggle').setAttribute('aria-expanded','false');
    if(['finops','benchmarks'].includes(view)){
      const header=document.querySelector('#sim-mount .sim-header');
      if(header){const note=document.createElement('p');note.className='ws-data-note';note.textContent='Planning reference · Uses bundled assumptions and data, not live prices or independently verified benchmark results.';header.appendChild(note);}
    }
    document.querySelectorAll('.slider-input').forEach(input=>{
      const label=input.closest('.control-group')?.querySelector('.control-header span');
      if(label)input.setAttribute('aria-label',label.textContent);
    });
  };
  app.toggleSidebar = function () {
    const sidebar=document.getElementById('sidebar');
    if(innerWidth>960 && this.activeView==='reader') sidebar.classList.toggle('collapsed');
    else sidebar.classList.toggle('open');
    document.getElementById('mobile-toggle').setAttribute('aria-expanded',String(sidebar.classList.contains('open')));
  };
  const oldInit=app.init.bind(app);
  app.init=function(){
    oldInit();
    document.querySelector('.sidebar-stats').textContent=`${docs.length} docs`;
    document.querySelector('#search-trigger-btn span').textContent='Search library';
    document.getElementById('search-input').placeholder=`Search ${docs.length} documents, topics and ideas…`;
    document.getElementById('search-modal').setAttribute('aria-label','Search research library');
    document.getElementById('search-modal').removeAttribute('aria-labelledby');
    document.getElementById('copilot-input').setAttribute('aria-label','Find passages in the local catalogue');
    document.getElementById('main-content').setAttribute('tabindex','-1');
    document.querySelector('#audit-modal .audit-dialog').innerHTML=`<div class="ws-section-head"><h2 id="audit-modal-label">Catalogue details</h2><button class="copilot-close-btn" onclick="app.closeAuditModal()" aria-label="Close catalogue details">×</button></div><p>This workspace contains ${docs.length} documents across ${groups.length} collections.</p><dl class="ws-provenance"><dt>Catalogue generated</dt><dd>${esc(this.catalog.metadata.generatedAt)}</dd><dt>Recorded root (not verified by this app)</dt><dd>${esc(this.catalog.metadata.merkleRoot || 'Not supplied')}</dd></dl><p class="ws-muted">Source claims and benchmark values come from the bundled research. This interface does not independently validate them or fetch live updates.</p>`;
    // Additional navigation behavior belongs to native controls, including keyboard activation.
    document.addEventListener('click',e=>{
      const el=e.target.closest('[data-doc],[data-view],[data-action]'); if(!el)return;
      if(el.dataset.doc){e.preventDefault();app.loadDocument(el.dataset.doc);}
      else if(el.dataset.view){e.preventDefault();app.switchView(el.dataset.view);}
      else if(el.dataset.action==='collections'){e.preventDefault();document.getElementById('collections').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});}
      else if(el.dataset.action==='search')app.openSearch();
      else if(el.dataset.action==='audit')app.openAuditModal();
      else if(el.dataset.action==='saved'){app.openSearch();app.setSearchFilter('FAVORITES');}
    });
    document.querySelectorAll('[role="button"]').forEach(el=>el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.click();}}));
    document.querySelectorAll('.modal-overlay').forEach(el=>el.addEventListener('click',e=>{if(e.target===el)closeDialogs();}));
    document.getElementById('mobile-toggle').addEventListener('click',()=>{
      document.getElementById('mobile-toggle').setAttribute('aria-expanded',String(document.getElementById('sidebar').classList.contains('open')));
    });
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape'){document.getElementById('sidebar').classList.remove('open');document.getElementById('mobile-toggle').setAttribute('aria-expanded','false');}
    });
    document.getElementById('search-results').setAttribute('aria-live','polite');
    document.getElementById('copilot-messages').setAttribute('aria-live','polite');
  };
  function closeDialogs(){app.closeSearch();app.closeAuditModal();app.closeShortcutsModal();app.closeCopilot();}
  // Focus is trapped inside the active dialog and restored to its opener.
  let returnFocus=null;
  const openFns=['openSearch','openAuditModal','openShortcutsModal','openCopilot'];
  openFns.forEach(name=>{const fn=app[name].bind(app);app[name]=function(){closeDialogs();returnFocus=document.activeElement;fn();const dialog=activeDialog();if(dialog)requestAnimationFrame(()=>dialog.querySelector('input,button,[tabindex="0"]')?.focus());};});
  ['closeSearch','closeAuditModal','closeShortcutsModal','closeCopilot'].forEach(name=>{const fn=app[name].bind(app);app[name]=function(){const wasOpen=activeDialog();fn();if(wasOpen&&!activeDialog()&&returnFocus?.isConnected)returnFocus.focus();};});
  function activeDialog(){return document.querySelector('.modal-overlay.active, .copilot-drawer.open');}
  document.addEventListener('keydown',e=>{
    const dialog=activeDialog();if(!dialog)return;
    if(e.key==='Tab'){
      const els=[...dialog.querySelectorAll('button,a[href],input,[tabindex="0"]')].filter(x=>!x.disabled&&x.getClientRects().length);
      if(!els.length)return;const first=els[0],last=els[els.length-1];
      if(e.shiftKey&&(document.activeElement===first||!dialog.contains(document.activeElement))){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&(document.activeElement===last||!dialog.contains(document.activeElement))){e.preventDefault();first.focus();}
    }
  },true);
  window.addEventListener('hashchange',()=>{if(location.hash.startsWith('#/'))app.route();});
})();
