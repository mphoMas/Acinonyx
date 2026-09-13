/**
 * Interactive Filterable Calendar with 1-Click iCal Export
 * Laerskool Kempton Park Designated Full Service School
 */

document.addEventListener('DOMContentLoaded', () => {
  initSchoolCalendar();
});

function initSchoolCalendar() {
  const container = document.getElementById('school-calendar-app');
  if (!container) return;

  const eventsData = [
    // Term 1
    {
      id: 't1-start',
      title: 'Term 1 School Commences (All Grades)',
      term: '1',
      category: 'academic',
      startDate: '2026-01-14',
      endDate: '2026-01-14',
      time: '07:30 – 14:00',
      location: 'Laerskool Kempton Park Campus',
      description: 'Official start of the 2026 academic year. All Grade R to Grade 7 learners report in full summer uniform by 07:25.'
    },
    {
      id: 't1-athletics-house',
      title: 'Inter-House Athletics Championship Meet',
      term: '1',
      category: 'sports',
      startDate: '2026-01-23',
      endDate: '2026-01-23',
      time: '08:00 – 15:00',
      location: 'Main Sports Grounds',
      description: 'Annual inter-house track and field championship. Parents are warmly invited to cheer from the pavilion.'
    },
    {
      id: 't1-agm',
      title: 'Annual General Meeting (AGM) & SGB Financial Presentation',
      term: '1',
      category: 'community',
      startDate: '2026-02-12',
      endDate: '2026-02-12',
      time: '18:00 – 19:30',
      location: 'School Hall',
      description: 'Statutory SGB presentation of audited 2025 financial accounts and approval of 2026 school fee schedules.'
    },
    {
      id: 't1-athletics-interschools',
      title: 'Inter-School Athletics Championship (Interschools)',
      term: '1',
      category: 'sports',
      startDate: '2026-02-27',
      endDate: '2026-02-27',
      time: '08:00 – 16:00',
      location: 'Barnard Stadium, Kempton Park',
      description: 'Kempie track & field athletes compete in regional inter-primary athletic divisionals.'
    },
    {
      id: 't1-close',
      title: 'Term 1 Concludes & Holiday Commences',
      term: '1',
      category: 'academic',
      startDate: '2026-03-27',
      endDate: '2026-03-27',
      time: '07:30 – 11:00',
      location: 'All Classrooms',
      description: 'End of Term 1. Progress reports distributed to parents. School dismisses promptly at 11:00.'
    },

    // Term 2
    {
      id: 't2-start',
      title: 'Term 2 School Reopens',
      term: '2',
      category: 'academic',
      startDate: '2026-04-14',
      endDate: '2026-04-14',
      time: '07:30 – 14:00',
      location: 'Laerskool Kempton Park Campus',
      description: 'All learners return for Term 2 in winter uniform. Winter sports practices commence.'
    },
    {
      id: 't2-rugby-netball',
      title: 'Winter Sports League Derby (Rugby & Netball vs Birchleigh)',
      term: '2',
      category: 'sports',
      startDate: '2026-04-25',
      endDate: '2026-04-25',
      time: '08:00 – 13:00',
      location: 'Home Fields & Netball Courts',
      description: 'U/9 to U/13 Rugby and Netball teams host Laerskool Birchleigh. Refreshments sold at the clubhouse.'
    },
    {
      id: 't2-grade-r-open',
      title: 'Grade R 2027 Open Morning & Campus Quad Walk',
      term: '2',
      category: 'community',
      startDate: '2026-05-15',
      endDate: '2026-05-15',
      time: '09:00 – 11:30',
      location: 'Grade R Center & Main Quad',
      description: 'Dedicated prospective parent morning. Guided tours of classroom facilities, sensory room, and clinic.'
    },
    {
      id: 't2-exams',
      title: 'Mid-Year Examinations (Grades 4–7)',
      term: '2',
      category: 'academic',
      startDate: '2026-06-05',
      endDate: '2026-06-19',
      time: '08:00 – 13:00',
      location: 'Senior Classrooms & Hall',
      description: 'Formal mid-year assessment window for Intermediate and Senior Phase learners.'
    },
    {
      id: 't2-close',
      title: 'Term 2 Concludes (Mid-Year Reports Issued)',
      term: '2',
      category: 'academic',
      startDate: '2026-06-26',
      endDate: '2026-06-26',
      time: '07:30 – 11:00',
      location: 'All Classrooms',
      description: 'Distribution of Term 2 academic reports. School closes for 3-week winter vacation.'
    },

    // Term 3
    {
      id: 't3-start',
      title: 'Term 3 School Reopens',
      term: '3',
      category: 'academic',
      startDate: '2026-07-21',
      endDate: '2026-07-21',
      time: '07:30 – 14:00',
      location: 'Campus Classrooms',
      description: 'Commencement of Term 3. Cricket, cross country, and choir eisteddfod preparations begin.'
    },
    {
      id: 't3-aquaponics',
      title: 'Aquaponics Spring Harvest & Community Market',
      term: '3',
      category: 'community',
      startDate: '2026-08-07',
      endDate: '2026-08-07',
      time: '12:00 – 16:00',
      location: 'Campus Aquaponics Greenhouse',
      description: 'Fresh organic spinach, lettuce, and herbs harvested from school farm available to parents.'
    },
    {
      id: 't3-eisteddfod',
      title: 'East Rand Eisteddfod & Senior Choir Gala',
      term: '3',
      category: 'cultural',
      startDate: '2026-08-21',
      endDate: '2026-08-21',
      time: '18:00 – 20:30',
      location: 'School Hall',
      description: 'Celebration of vocal music, poetry recitations, and instrumental solo performances.'
    },
    {
      id: 't3-heritage',
      title: '120-Year Heritage Day & Multicultural Food Fair',
      term: '3',
      category: 'cultural',
      startDate: '2026-09-23',
      endDate: '2026-09-23',
      time: '09:00 – 14:00',
      location: 'Main Quadrangle',
      description: 'Learners celebrate South African cultural diversity and 120 years of school history (Est. 1903).'
    },
    {
      id: 't3-close',
      title: 'Term 3 Concludes',
      term: '3',
      category: 'academic',
      startDate: '2026-10-02',
      endDate: '2026-10-02',
      time: '07:30 – 11:00',
      location: 'All Classrooms',
      description: 'End of Term 3. School closes for short spring holiday break.'
    },

    // Term 4
    {
      id: 't4-start',
      title: 'Term 4 School Reopens',
      term: '4',
      category: 'academic',
      startDate: '2026-10-13',
      endDate: '2026-10-13',
      time: '07:30 – 14:00',
      location: 'Campus Classrooms',
      description: 'Final term of the academic year begins. Year-end revision and final examination schedules commence.'
    },
    {
      id: 't4-grade-r-deadline',
      title: 'Grade R 2027 Admissions Deadline (Strict 14:00)',
      term: '4',
      category: 'community',
      startDate: '2026-10-09',
      endDate: '2026-10-09',
      time: '14:00 Deadline',
      location: 'Admissions Office (Ms. P. Moyaha)',
      description: 'Official closing deadline for physical submission of Grade R 2027 enrolment files.'
    },
    {
      id: 't4-valedictory',
      title: 'Senior Awards Evening & Grade 7 Valedictory',
      term: '4',
      category: 'academic',
      startDate: '2026-11-27',
      endDate: '2026-11-27',
      time: '18:00 – 20:30',
      location: 'School Hall',
      description: 'Conferring of academic Dux Scholar, sports trophies, leadership blazers, and Grade 7 graduation.'
    },
    {
      id: 't4-close',
      title: 'Term 4 Concludes (2026 School Year Ends)',
      term: '4',
      category: 'academic',
      startDate: '2026-12-09',
      endDate: '2026-12-09',
      time: '07:30 – 10:30',
      location: 'All Classrooms',
      description: 'Final promotion reports distributed. Summer holidays commence.'
    }
  ];

  let currentCategory = 'all';
  let currentTerm = 'all';

  function renderCalendar() {
    const filtered = eventsData.filter(ev => {
      const matchCat = currentCategory === 'all' || ev.category === currentCategory;
      const matchTerm = currentTerm === 'all' || ev.term === currentTerm;
      return matchCat && matchTerm;
    });

    const markup = `
      <div class="calendar-controls-bar">
        <div class="calendar-filter-group">
          <span class="filter-label">Filter Category:</span>
          <div class="filter-pills">
            <button type="button" class="filter-pill ${currentCategory === 'all' ? 'active' : ''}" data-cat="all">All Events</button>
            <button type="button" class="filter-pill ${currentCategory === 'academic' ? 'active' : ''}" data-cat="academic">Academic &amp; Terms</button>
            <button type="button" class="filter-pill ${currentCategory === 'sports' ? 'active' : ''}" data-cat="sports">Interschool Sports</button>
            <button type="button" class="filter-pill ${currentCategory === 'cultural' ? 'active' : ''}" data-cat="cultural">Culture &amp; Arts</button>
            <button type="button" class="filter-pill ${currentCategory === 'community' ? 'active' : ''}" data-cat="community">Parent &amp; Community</button>
          </div>
        </div>

        <div class="calendar-filter-group">
          <span class="filter-label">Filter Term:</span>
          <div class="filter-pills">
            <button type="button" class="filter-pill ${currentTerm === 'all' ? 'active' : ''}" data-term="all">Full Year 2026</button>
            <button type="button" class="filter-pill ${currentTerm === '1' ? 'active' : ''}" data-term="1">Term 1</button>
            <button type="button" class="filter-pill ${currentTerm === '2' ? 'active' : ''}" data-term="2">Term 2</button>
            <button type="button" class="filter-pill ${currentTerm === '3' ? 'active' : ''}" data-term="3">Term 3</button>
            <button type="button" class="filter-pill ${currentTerm === '4' ? 'active' : ''}" data-term="4">Term 4</button>
          </div>
        </div>

        <div style="margin-left: auto;">
          <button type="button" id="btn-export-full-ics" class="btn btn-outline-gold btn-sm">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Sync Full 2026 Calendar (.ics)
          </button>
        </div>
      </div>

      <div class="calendar-events-grid">
        ${filtered.length === 0 ? `
          <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: #FFF; border-radius: var(--radius-xs); border: 1px solid var(--color-border);">
            <h4>No scheduled events match your selected filters.</h4>
            <p class="text-muted" style="font-size: var(--text-xs);">Try selecting "All Events" or "Full Year 2026" above.</p>
          </div>
        ` : filtered.map(ev => {
          const dateObj = new Date(ev.startDate + 'T00:00:00');
          const dayName = dateObj.toLocaleDateString('en-ZA', { weekday: 'short' });
          const dayNum = dateObj.getDate();
          const monthName = dateObj.toLocaleDateString('en-ZA', { month: 'short' });

          const googleUrl = generateGoogleCalendarUrl(ev);

          return `
            <div class="calendar-event-card category-${ev.category}">
              <div class="event-date-badge">
                <span class="event-day-num">${dayNum}</span>
                <span class="event-month">${monthName}</span>
                <span class="event-day-name">${dayName}</span>
              </div>
              <div class="event-details">
                <div class="event-top-meta">
                  <span class="event-tag-term">Term ${ev.term}</span>
                  <span class="event-tag-cat cat-${ev.category}">${ev.category}</span>
                </div>
                <h4 class="event-title">${ev.title}</h4>
                <p class="event-time-loc">
                  <span>&#128337; ${ev.time}</span> &bull; 
                  <span>&#128205; ${ev.location}</span>
                </p>
                <p class="event-desc">${ev.description}</p>
                <div class="event-action-strip">
                  <a href="${googleUrl}" target="_blank" rel="noopener noreferrer" class="btn-event-action" title="Add to Google Calendar">
                    + Google Cal
                  </a>
                  <button type="button" class="btn-event-action btn-download-single-ics" data-event-id="${ev.id}" title="Download Apple / Outlook iCal (.ics)">
                    &darr; iCal (.ics)
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.innerHTML = markup;

    // Attach Category Filter Listeners
    container.querySelectorAll('[data-cat]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentCategory = btn.dataset.cat;
        renderCalendar();
      });
    });

    // Attach Term Filter Listeners
    container.querySelectorAll('[data-term]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentTerm = btn.dataset.term;
        renderCalendar();
      });
    });

    // Single iCal Download Listener
    container.querySelectorAll('.btn-download-single-ics').forEach(btn => {
      btn.addEventListener('click', () => {
        const evId = btn.dataset.eventId;
        const targetEv = eventsData.find(e => e.id === evId);
        if (targetEv) {
          downloadIcsFile([targetEv], `${targetEv.id}-lkp-event.ics`);
        }
      });
    });

    // Full iCal Sync Download Listener
    const exportFullBtn = container.querySelector('#btn-export-full-ics');
    if (exportFullBtn) {
      exportFullBtn.addEventListener('click', () => {
        downloadIcsFile(eventsData, 'laerskool-kempton-park-2026-calendar.ics');
      });
    }
  }

  function generateGoogleCalendarUrl(ev) {
    const startIso = ev.startDate.replace(/-/g, '') + 'T073000Z';
    const endIso = ev.endDate.replace(/-/g, '') + 'T150000Z';
    const title = encodeURIComponent(ev.title + ' | Laerskool Kempton Park');
    const details = encodeURIComponent(ev.description + '\n\nLocation: ' + ev.location + '\nContact: 011 394 6421');
    const loc = encodeURIComponent(ev.location + ', Kittyhawk St, Rhodesfield');
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${title}&dates=${startIso}/${endIso}&details=${details}&location=${loc}`;
  }

  function downloadIcsFile(events, filename) {
    let icsContent = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Laerskool Kempton Park//Institutional Calendar//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'X-WR-CALNAME:Laerskool Kempton Park 2026 Calendar',
      'X-WR-TIMEZONE:Africa/Johannesburg'
    ];

    events.forEach(ev => {
      const dtStart = ev.startDate.replace(/-/g, '') + 'T073000Z';
      const dtEnd = ev.endDate.replace(/-/g, '') + 'T150000Z';
      const now = new Date().toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

      icsContent.push('BEGIN:VEVENT');
      icsContent.push(`UID:${ev.id}-2026@laerskoolkempton.co.za`);
      icsContent.push(`DTSTAMP:${now}`);
      icsContent.push(`DTSTART:${dtStart}`);
      icsContent.push(`DTEND:${dtEnd}`);
      icsContent.push(`SUMMARY:${ev.title}`);
      icsContent.push(`DESCRIPTION:${ev.description.replace(/\n/g, '\\n')}`);
      icsContent.push(`LOCATION:${ev.location}, Kittyhawk Street, Rhodesfield, Kempton Park`);
      icsContent.push('STATUS:CONFIRMED');
      icsContent.push('END:VEVENT');
    });

    icsContent.push('END:VCALENDAR');

    const blob = new Blob([icsContent.join('\r\n')], { type: 'text/calendar;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  renderCalendar();
}
