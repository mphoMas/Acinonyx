/**
 * Full-Service 3-Tier Support & Clinical Therapy Navigator
 * Laerskool Kempton Park Designated Full Service School
 */

document.addEventListener('DOMContentLoaded', () => {
  initTherapyNavigator();
});

function initTherapyNavigator() {
  const triageContainer = document.getElementById('therapy-triage-app');
  if (!triageContainer) return;

  const TRIAGE_CHANNELS = {
    'reading': {
      title: 'Reading, Literacy & Phonics Remediation',
      tier: 'Tier 2: Targeted Remedial (LSE Wing)',
      specialist: 'Ms. D. Opperman (Head of Inclusion) & Learner Support Educators',
      actions: [
        'Baseline phonological awareness diagnostic evaluation within 10 days of referral.',
        'Structured 45-minute pull-out sessions 3x weekly in the dedicated LSE Remedial Wing.',
        'Individualized Educational Plan (IEP) synchronized with the mainstream classroom teacher.',
        'Quarterly reading age progression benchmarks shared confidentially with parents.'
      ],
      concession: 'Eligible for GDE Extra Time & Reader/Scribe Concessions during formal exams.'
    },
    'sensory': {
      title: 'Sensory Integration & Attention Regulation',
      tier: 'Tier 2 & Tier 3: Occupational Therapy & Sensory Room',
      specialist: 'Campus Occupational Therapist & SMT Pastoral Lead',
      actions: [
        'Comprehensive sensory profiling assessment conducted in the on-site OT suite.',
        'Structured sensory diet: scheduled regulation breaks in the darkened sensory calm room.',
        'Classroom accommodations: wobble stools, sensory chews, and noise-dampening headphones.',
        'Bilateral coordination and core stability exercises to support sustained desk focus.'
      ],
      concession: 'Separate venue examination accommodation to prevent auditory distractibility.'
    },
    'speech': {
      title: 'Speech, Language & Articulation Pathology',
      tier: 'Tier 3: Clinical Speech-Language Pathology',
      specialist: 'Consulting Campus Speech-Language Pathologist',
      actions: [
        'Standardized articulation and receptive-expressive language clinical assessment.',
        'Weekly one-on-one speech therapy sessions in quiet clinical suite.',
        'Auditory processing exercises and tongue-placement reinforcement activities for home practice.',
        'Multi-lingual language support assisting children transitioning to 100% English medium.'
      ],
      concession: 'Oral exam accommodations and spelling concession where phonologically indicated.'
    },
    'motor': {
      title: 'Fine-Motor, Handwriting & Visual Perception',
      tier: 'Tier 2 & Tier 3: Occupational Therapy Clinic',
      specialist: 'On-Site Occupational Therapy Team',
      actions: [
        'Fine-motor grip and handwriting speed assessment (Pencil grip correction, wrist stability).',
        'Visual-motor integration and spatial planning therapy to prevent letter reversals (b/d).',
        'Adaptive pencil grips and slanted writing desk boards provided for classroom use.',
        'Targeted scissor skills, hand strength, and bilateral coordination development.'
      ],
      concession: 'Handwriting concession (digital typing or amanuensis scribe) if clinically indicated.'
    },
    'medical': {
      title: 'Primary Health, Chronic Illness & Medication',
      tier: 'Tier 3: Full-Time Campus Health Clinic',
      specialist: 'Sister Howe (Registered Professional Campus Nurse)',
      actions: [
        'Immediate medical record profiling upon admission; secure storage of chronic medications.',
        'Daily supervised administration of prescribed medications with certified medical logbook.',
        'Annual visual acuity, hearing screening, and routine developmental milestone checks.',
        'Direct emergency triage and rapid coordination with local paramedics and hospitals.'
      ],
      concession: 'Rest breaks and emergency medical concession during formal assessment sessions.'
    }
  };

  const buttons = triageContainer.querySelectorAll('.triage-selector-btn');
  const displayCard = triageContainer.querySelector('#triage-display-card');

  function renderTriage(key) {
    const data = TRIAGE_CHANNELS[key] || TRIAGE_CHANNELS['reading'];

    displayCard.innerHTML = `
      <div class="triage-result-header">
        <div>
          <span class="status-badge status-primary">${data.tier}</span>
          <h3 style="margin-top: 0.5rem; margin-bottom: 0.25rem;">${data.title}</h3>
          <p style="font-size: var(--text-xs); color: var(--color-text-muted); margin: 0;">
            <strong>Lead Specialist:</strong> ${data.specialist}
          </p>
        </div>
        <a href="contact.html" class="btn btn-gold btn-sm">Request SBST Consultation &rarr;</a>
      </div>

      <div class="triage-result-body">
        <h5 style="color: var(--color-primary-navy); margin-bottom: 0.75rem;">Structured Support Protocol:</h5>
        <ul class="triage-steps-list">
          ${data.actions.map(act => `<li>${act}</li>`).join('')}
        </ul>

        <div class="triage-concession-box">
          <div style="font-weight: 700; color: var(--color-primary-navy); margin-bottom: 0.2rem; font-size: var(--text-xs);">
            &#127891; Statutory Assessment Concession:
          </div>
          <div style="font-size: var(--text-xs); color: var(--color-text-main);">
            ${data.concession}
          </div>
        </div>
      </div>
    `;
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTriage(btn.dataset.concern);
    });
  });

  // Default render
  renderTriage('reading');
}
