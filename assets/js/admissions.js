/**
 * Admissions Interactive Module for GDE Guidelines & Checklists
 */
document.addEventListener('DOMContentLoaded', () => {
  initChecklist();
});

function initChecklist() {
  const checkboxes = document.querySelectorAll('.checklist-input');
  const countBadge = document.getElementById('checklist-count');
  const totalCount = checkboxes.length;
  const printBtn = document.getElementById('btn-print-checklist');

  function updateChecklistProgress() {
    let checkedCount = 0;
    checkboxes.forEach(cb => {
      const item = cb.closest('.checklist-item');
      if (cb.checked) {
        checkedCount++;
        if (item) item.classList.add('checked');
      } else {
        if (item) item.classList.remove('checked');
      }
    });

    if (countBadge) {
      countBadge.textContent = `${checkedCount} of ${totalCount} Ready`;
      if (checkedCount === totalCount) {
        countBadge.style.backgroundColor = '#10B981';
        countBadge.style.color = '#FFFFFF';
      } else {
        countBadge.style.backgroundColor = '';
        countBadge.style.color = '';
      }
    }
  }

  checkboxes.forEach(cb => {
    cb.addEventListener('change', updateChecklistProgress);
  });

  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }

  updateChecklistProgress();
}
