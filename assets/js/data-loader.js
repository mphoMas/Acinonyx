/**
 * Data Loader & UI Interactions (Tabs, Accordions, Search)
 */
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initAccordions();
  initDownloadFilter();
});

/* Tabs Switching */
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  if (!tabButtons.length) return;

  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetId = button.getAttribute('data-tab');
      
      // Update buttons
      tabButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');

      // Update contents
      const tabContents = document.querySelectorAll('.tab-content');
      tabContents.forEach(content => {
        if (content.id === targetId) {
          content.classList.add('active');
        } else {
          content.classList.remove('active');
        }
      });
    });
  });
}

/* Accordion Logic */
function initAccordions() {
  const accordionHeaders = document.querySelectorAll('.accordion-header');
  accordionHeaders.forEach(header => {
    header.addEventListener('click', () => {
      const item = header.parentElement;
      const isOpen = item.classList.contains('open');
      
      // Close peers if desired
      const parent = item.parentElement;
      if (parent) {
        parent.querySelectorAll('.accordion-item').forEach(peer => peer.classList.remove('open'));
      }

      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });
}

/* Filter Downloads Hub */
function initDownloadFilter() {
  const searchInput = document.getElementById('download-search');
  const items = document.querySelectorAll('.download-item');

  if (!searchInput || !items.length) return;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    items.forEach(item => {
      const title = item.querySelector('.download-meta h4')?.textContent.toLowerCase() || '';
      const desc = item.querySelector('.download-meta p')?.textContent.toLowerCase() || '';
      if (title.includes(query) || desc.includes(query)) {
        item.style.display = 'flex';
      } else {
        item.style.display = 'none';
      }
    });
  });
}
