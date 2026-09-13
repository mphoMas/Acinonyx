/**
 * Campus Contact & Message Dispatch Module
 * Laerskool Kempton Park Full Service School
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('contact-form');
  const successCard = document.getElementById('contact-success-card');
  const resetBtn = document.getElementById('btn-reset-form');

  if (!form || !successCard) return;

  const DEPT_OFFICERS = {
    'admissions-gr-r': { officer: 'Ms. P. Moyaha (Admissions Lead)', ext: 'Ext. 105', email: 'admissions@laerskoolkempton.co.za' },
    'admissions-gr-1-7': { officer: 'Ms. P. Moyaha (Front Desk & Admissions)', ext: 'Ext. 105', email: 'admissions@laerskoolkempton.co.za' },
    'full-service': { officer: 'Ms. D. Opperman (Head of Inclusion & SBST)', ext: 'Ext. 108', email: 'support@laerskoolkempton.co.za' },
    'subsidies': { officer: 'Ms. N. Zikhali & Ms. H. Ash (SASA Subsidies)', ext: 'Ext. 107', email: 'subsidies@laerskoolkempton.co.za' },
    'finance': { officer: 'Ms. Y. Smith (Finance & Fee Accounts)', ext: 'Ext. 106', email: 'finance@laerskoolkempton.co.za' }
  };

  // URL query parameter parsing to automatically select inquiry category
  const urlParams = new URLSearchParams(window.location.search);
  const queryParam = urlParams.get('query');
  if (queryParam) {
    const select = document.getElementById('query-type');
    if (select) {
      if (queryParam === 'fee-subsidy' || queryParam === 'subsidies') {
        select.value = 'subsidies';
      } else if (queryParam === 'full-service' || queryParam === 'therapy') {
        select.value = 'full-service';
      } else if (queryParam === 'admissions' || queryParam === 'admissions-gr-r' || queryParam === 'gr-r') {
        select.value = 'admissions-gr-r';
      } else if (queryParam === 'finance') {
        select.value = 'finance';
      }
      setTimeout(() => {
        form.scrollIntoView({ behavior: 'smooth', block: 'center' });
        select.focus();
      }, 200);
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    const parentName = document.getElementById('parent-name').value.trim();
    const parentEmail = document.getElementById('parent-email').value.trim();
    const parentPhone = document.getElementById('parent-phone').value.trim();
    const queryType = document.getElementById('query-type').value;
    const message = document.getElementById('message').value.trim();

    if (!parentName || !parentEmail || !parentPhone || !queryType || !message) {
      return;
    }

    const deptInfo = DEPT_OFFICERS[queryType] || { officer: 'Administrative Operations Team', ext: 'Ext. 101', email: 'admin@laerskoolkempton.co.za' };
    const randomRef = 'LKP-' + new Date().getFullYear() + '-' + Math.floor(1000 + Math.random() * 9000);

    const refEl = document.getElementById('success-ref-num');
    const nameEl = document.getElementById('success-parent-name');
    const officerEl = document.getElementById('success-officer-name');
    const channelEl = document.getElementById('success-contact-channel');

    if (refEl) refEl.textContent = randomRef;
    if (nameEl) nameEl.textContent = parentName;
    if (officerEl) officerEl.textContent = deptInfo.officer;
    if (channelEl) channelEl.textContent = deptInfo.ext + ' • ' + deptInfo.email;

    form.style.display = 'none';
    successCard.style.display = 'block';
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      form.reset();
      successCard.style.display = 'none';
      form.style.display = 'block';
    });
  }
});
