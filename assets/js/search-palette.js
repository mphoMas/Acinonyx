/**
 * Universal Command Palette & Quick Search (Cmd+K)
 * Laerskool Kempton Park Designated Full Service School
 */

document.addEventListener('DOMContentLoaded', () => {
  initSearchPalette();
});

function initSearchPalette() {
  // Institutional Search Database
  const searchIndex = [
    // Admissions & Enrolment
    { title: 'Grade R Intake & Applications', category: 'Admissions', url: 'admissions.html#grade-r-intake', snippet: 'Direct school enrolment for Grade R learners. Closes 9 October 2026.' },
    { title: 'GDE Online Admissions (Grades 1–7)', category: 'Admissions', url: 'admissions.html#gde-roadmap', snippet: 'Official Gauteng Department of Education feeder-zone application steps and dates.' },
    { title: 'Interactive Document Checklist', category: 'Admissions', url: 'admissions.html#checklist', snippet: 'Certified birth certificate, clinic card, parent IDs, proof of address, and vaccination records.' },
    { title: 'School Fees & Debit Order Schedule', category: 'Finances', url: 'admissions.html#fees', snippet: 'R1,350 monthly debit order (x10 months) or R13,500 annual with 5% early settlement rebate.' },
    { title: 'Statutory Fee Exemption (SASA Section 39)', category: 'Finances', url: 'admissions.html#exemptions', snippet: 'National quintile fee exemption guidelines for qualifying families under South African Schools Act.' },
    { title: 'Stationery & Book Packs (Grades R–7)', category: 'Parent Hub', url: 'admissions.html#downloads', snippet: 'Complete grade-specific stationery lists, textbook requisitions, and digital downloads.' },

    // Full-Service & Clinical Therapies
    { title: 'Full-Service Accreditation & Ethos', category: 'Inclusion', url: 'full-service.html', snippet: 'GDE-designated full-service campus with zero exclusion policy and on-site multidisciplinary support.' },
    { title: 'Sister Howe — Campus Health & Clinic', category: 'Therapies', url: 'full-service.html#clinic', snippet: 'Full-time campus Sister offering primary health care, chronic care coordination, and emergency response.' },
    { title: 'Occupational Therapy (OT) Suite', category: 'Therapies', url: 'full-service.html#therapies', snippet: 'On-site sensory integration, fine motor skills development, and bilateral coordination therapy.' },
    { title: 'Speech-Language Pathology', category: 'Therapies', url: 'full-service.html#therapies', snippet: 'Phonological awareness, receptive language, and articulation therapy for primary learners.' },
    { title: 'Remedial Learner Support (LSE Wing)', category: 'Support', url: 'full-service.html#lse', snippet: 'Dedicated remedial reading, numeracy foundation, and individualized educational plans (IEP).' },
    { title: 'School-Based Support Team (SBST)', category: 'Inclusion', url: 'full-service.html#sbst', snippet: 'Formal triage and multidisciplinary referral protocol led by Ms. D. Opperman.' },

    // Academics & Curriculum
    { title: 'Foundation Phase (Grades R–3)', category: 'Academics', url: 'school-life.html#foundation', snippet: 'Home Language English, Mathematics, Life Skills, and Afrikaans First Additional Language.' },
    { title: 'Intermediate Phase (Grades 4–6)', category: 'Academics', url: 'school-life.html#intermediate', snippet: 'Natural Sciences, Technology, Social Sciences (History & Geography), English, and Maths.' },
    { title: 'Senior Phase (Grade 7 Transition)', category: 'Academics', url: 'school-life.html#senior', snippet: 'Economic & Management Sciences, Creative Arts, Technology, and High School readiness.' },
    { title: 'Computer Lab & Robotics Curriculum', category: 'Academics', url: 'school-life.html#robotics', snippet: 'Coding fundamentals, digital literacy, and modern computer lab workstations.' },

    // School Life, Sports & Culture
    { title: 'Athletics & Track & Field (Term 1)', category: 'Sports', url: 'school-life.html#sports', snippet: 'Sprint hurdles, long jump, high jump, shot put, and inter-school championship meets.' },
    { title: 'Netball & Winter Rugby (Term 2)', category: 'Sports', url: 'school-life.html#sports', snippet: 'Junior and Senior A/B league fixtures, coach training, and regional tournaments.' },
    { title: 'Cricket & Cross Country (Term 3)', category: 'Sports', url: 'school-life.html#sports', snippet: 'Mini-cricket (Grades 1–3), hardball league (Grades 4–7), and endurance running.' },
    { title: 'School Choir & Public Speaking', category: 'Culture', url: 'school-life.html#culture', snippet: 'Award-winning senior choir, English and Afrikaans eisteddfod, and debate competitions.' },
    { title: 'Term Dates & Academic Calendar', category: 'Calendar', url: 'school-life.html#calendar', snippet: 'Official 4-term 2026 school calendar, examination periods, and public holidays.' },

    // Community, Sustainability & Aquaponics
    { title: 'Campus Aquaponics Farm & Greenhouse', category: 'Community', url: 'about.html#sustainability', snippet: 'Closed-loop aquaculture farming: tilapia fish tanks and organic hydroponic vegetable growbeds.' },
    { title: 'Daily Feeding Scheme (1,150 Learners)', category: 'Community', url: 'about.html#sustainability', snippet: 'Nutritional food security program ensuring warm breakfast and lunch for learners.' },
    { title: '120-Year Heritage (Established 1903)', category: 'Heritage', url: 'about.html#heritage', snippet: 'Founded during the post-Boer War reconstruction era, evolving into a modern English-medium powerhouse.' },

    // SMT Leadership & Administrative Directory
    { title: 'Mrs. P. Pillay — School Principal', category: 'Leadership', url: 'about.html#smt', snippet: 'Leading Laerskool Kempton Park with an ethos of academic distinction, safe haven sanctuary, and inclusive care.' },
    { title: 'Mrs. Y. Raspal — Deputy Principal (Academic & Operations)', category: 'Leadership', url: 'about.html#smt', snippet: 'Campus operations, administrative compliance, and academic curriculum delivery.' },
    { title: 'Ms. A. Weideman — Deputy Principal (Pastoral)', category: 'Leadership', url: 'about.html#smt', snippet: 'Learner discipline, values formation, pastoral care, and co-curricular programs.' },
    { title: 'Front Desk & Admissions (Ms. P. Moyaha)', category: 'Contact', url: 'contact.html#officers', snippet: 'General campus enquiries, admissions applications, Grade R enrolment: Ext 105 / 011 394 6421.' },
    { title: 'GDE Subsidies & Fee Exemptions (Ms. N. Zikhali & Ms. H. Ash)', category: 'Contact', url: 'contact.html#officers', snippet: 'SASA Section 39 fee exemption processing, GDE subsidies, and institutional assistance: Ext 107.' },
    { title: 'Finance & School Accounts (Ms. Y. Smith)', category: 'Contact', url: 'contact.html#officers', snippet: 'School fee invoices, debit orders, and payment receipting: Ext 106.' },

    // Transit & Physical Campus
    { title: 'Directions: 450m from Rhodesfield Gautrain', category: 'Location', url: 'contact.html#transit', snippet: 'Kittyhawk Street, Rhodesfield. 5-minute pedestrian walk from Rhodesfield Gautrain East Exit.' },
    { title: 'Campus Office Hours: 07:15 – 15:00', category: 'Contact', url: 'contact.html#hours', snippet: 'Administrative offices open Monday to Friday. Dedicated visitor parking inside Main Gate 1.' },

    // Statutory Compliance & Governance
    { title: 'PAIA Manual (Section 14 Statutory Compliance)', category: 'Governance', url: 'admissions.html#statutory', snippet: 'Promotion of Access to Information Act public manual and records request procedure.' },
    { title: 'POPIA Child Protection & Privacy Notice', category: 'Governance', url: 'index.html#statutory', snippet: 'Protection of Personal Information Act adherence: parental consent and child safeguarding.' },
    { title: 'Learner Code of Conduct & Values', category: 'Governance', url: 'about.html#values', snippet: 'Integrity, Respect, Discipline, Empathy, Diligence, Honesty, Responsibility, Compassion, Courage.' }
  ];

  // Inject Command Palette Modal into DOM
  const modalHTML = `
    <div id="search-modal" class="search-modal" aria-hidden="true" role="dialog" aria-modal="true" aria-label="Quick Search">
      <div class="search-modal-backdrop"></div>
      <div class="search-modal-container">
        <div class="search-modal-header">
          <div class="search-input-wrapper">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input 
              type="text" 
              id="search-input" 
              class="search-input" 
              placeholder="Search anything: fees, Grade R, term dates, therapy, staff, uniforms..." 
              autocomplete="off" 
              spellcheck="false"
            />
            <button type="button" id="search-clear-btn" class="search-clear-btn" aria-label="Clear search" style="display: none;">&times;</button>
          </div>
          <div class="search-kbd-hint">
            <kbd>ESC</kbd> to close
          </div>
        </div>
        <div class="search-modal-body">
          <div id="search-suggestions" class="search-section">
            <div class="search-section-label">Popular Institutional Shortcuts</div>
            <div class="search-quick-tags">
              <button type="button" class="quick-tag-btn" data-query="Grade R">Grade R Intake</button>
              <button type="button" class="quick-tag-btn" data-query="Fees">School Fees</button>
              <button type="button" class="quick-tag-btn" data-query="Term Dates">Term Dates</button>
              <button type="button" class="quick-tag-btn" data-query="Therapy">Therapy Clinic</button>
              <button type="button" class="quick-tag-btn" data-query="Stationery">Stationery</button>
              <button type="button" class="quick-tag-btn" data-query="Gautrain">Gautrain Directions</button>
            </div>
          </div>
          <div id="search-results-wrapper" class="search-results-list" role="listbox">
            <!-- Dynamic search results populated here -->
          </div>
        </div>
        <div class="search-modal-footer">
          <div class="search-footer-hint">
            <span><kbd>&uarr;</kbd> <kbd>&darr;</kbd> Navigate</span>
            <span><kbd>&crarr;</kbd> Open</span>
            <span><kbd>ESC</kbd> Close</span>
          </div>
          <div class="search-footer-brand">Laerskool Kempton Park • 100% English Medium</div>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHTML);

  const modal = document.getElementById('search-modal');
  const input = document.getElementById('search-input');
  const resultsWrapper = document.getElementById('search-results-wrapper');
  const suggestions = document.getElementById('search-suggestions');
  const clearBtn = document.getElementById('search-clear-btn');
  const backdrop = modal.querySelector('.search-modal-backdrop');

  let selectedIndex = -1;

  function openSearch() {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(() => {
      input.focus();
      if (!input.value.trim()) {
        renderResults('');
      }
    }, 50);
  }

  function closeSearch() {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    input.value = '';
    selectedIndex = -1;
    clearBtn.style.display = 'none';
  }

  // Keyboard shortcut listener (Cmd+K / Ctrl+K / / key)
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (modal.classList.contains('active')) {
        closeSearch();
      } else {
        openSearch();
      }
    } else if (e.key === 'Escape' && modal.classList.contains('active')) {
      closeSearch();
    } else if (modal.classList.contains('active')) {
      handleModalKeydown(e);
    }
  });

  // Open triggers across the UI (desktop header buttons & mobile drawer)
  document.querySelectorAll('.btn-search-trigger, [data-action="open-search"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      openSearch();
    });
  });

  backdrop.addEventListener('click', closeSearch);

  input.addEventListener('input', () => {
    const val = input.value.trim();
    clearBtn.style.display = val ? 'block' : 'none';
    renderResults(val);
  });

  clearBtn.addEventListener('click', () => {
    input.value = '';
    clearBtn.style.display = 'none';
    renderResults('');
    input.focus();
  });

  // Quick tag buttons
  modal.querySelectorAll('.quick-tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.query;
      input.value = q;
      clearBtn.style.display = 'block';
      renderResults(q);
      input.focus();
    });
  });

  function renderResults(query) {
    selectedIndex = -1;
    if (!query) {
      suggestions.style.display = 'block';
      resultsWrapper.innerHTML = `
        <div class="search-empty-state">
          <p>Type keywords to search across admissions, fees, therapies, term dates, and campus policies.</p>
        </div>
      `;
      return;
    }

    suggestions.style.display = 'none';
    const lowerQ = query.toLowerCase();
    const matches = searchIndex.filter(item => {
      return item.title.toLowerCase().includes(lowerQ) ||
             item.snippet.toLowerCase().includes(lowerQ) ||
             item.category.toLowerCase().includes(lowerQ);
    });

    if (matches.length === 0) {
      resultsWrapper.innerHTML = `
        <div class="search-empty-state">
          <div style="font-size: 1.5rem; margin-bottom: 0.5rem; color: var(--color-accent-gold);">&empty;</div>
          <h4>No direct matching topics found</h4>
          <p>Try searching for "fees", "Grade R", "uniform", "term", "therapy", or "stationery".</p>
        </div>
      `;
      return;
    }

    resultsWrapper.innerHTML = matches.map((item, idx) => `
      <a href="${item.url}" class="search-result-item" role="option" data-index="${idx}">
        <div class="search-result-left">
          <span class="search-result-category">${item.category}</span>
          <div class="search-result-title">${highlightText(item.title, query)}</div>
          <div class="search-result-snippet">${highlightText(item.snippet, query)}</div>
        </div>
        <div class="search-result-arrow">&rarr;</div>
      </a>
    `).join('');
  }

  function highlightText(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  function handleModalKeydown(e) {
    const items = resultsWrapper.querySelectorAll('.search-result-item');
    if (items.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      selectedIndex = (selectedIndex + 1) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      selectedIndex = (selectedIndex - 1 + items.length) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'Enter') {
      if (selectedIndex >= 0 && items[selectedIndex]) {
        e.preventDefault();
        items[selectedIndex].click();
      }
    }
  }

  function updateActiveItem(items) {
    items.forEach((item, i) => {
      if (i === selectedIndex) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }
}
