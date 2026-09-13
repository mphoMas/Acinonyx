/**
 * Accessibility Controls for Laerskool Kempton Park
 * Supports: High Contrast Mode, Text Scaling, and Local Storage Persistence
 */
document.addEventListener('DOMContentLoaded', () => {
  initAccessibility();
});

function initAccessibility() {
  const btnContrast = document.getElementById('btn-contrast');
  const btnFontIncrease = document.getElementById('btn-font-increase');
  const btnFontReset = document.getElementById('btn-font-reset');

  // Load saved preferences
  const savedContrast = localStorage.getItem('lkp-contrast');
  const savedFontSize = localStorage.getItem('lkp-font-size');

  if (savedContrast === 'high') {
    document.body.classList.add('high-contrast');
  }

  if (savedFontSize) {
    document.body.classList.add(savedFontSize);
  }

  // Toggle Contrast
  if (btnContrast) {
    btnContrast.addEventListener('click', () => {
      const isHigh = document.body.classList.toggle('high-contrast');
      localStorage.setItem('lkp-contrast', isHigh ? 'high' : 'normal');
      btnContrast.setAttribute('aria-pressed', isHigh);
    });
  }

  // Increase Font Size
  if (btnFontIncrease) {
    btnFontIncrease.addEventListener('click', () => {
      if (document.body.classList.contains('font-lg')) {
        document.body.classList.remove('font-lg');
        document.body.classList.add('font-xl');
        localStorage.setItem('lkp-font-size', 'font-xl');
      } else if (!document.body.classList.contains('font-xl')) {
        document.body.classList.add('font-lg');
        localStorage.setItem('lkp-font-size', 'font-lg');
      }
    });
  }

  // Reset Font Size
  if (btnFontReset) {
    btnFontReset.addEventListener('click', () => {
      document.body.classList.remove('font-lg', 'font-xl');
      localStorage.removeItem('lkp-font-size');
    });
  }
}
