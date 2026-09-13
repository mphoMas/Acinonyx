/**
 * Accessible Modal Dialog Component for Laerskool Kempton Park
 * Replaces unstyled browser alerts with elegant, WCAG-compliant institutional dialogs.
 */
class KempieModal {
  constructor() {
    this.activeModal = null;
    this.previousActiveElement = null;
    this.init();
  }

  init() {
    // Listen for trigger buttons
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-modal-target]');
      if (trigger) {
        e.preventDefault();
        const targetId = trigger.getAttribute('data-modal-target');
        this.open(targetId, trigger);
        return;
      }

      // Close button
      const closeBtn = e.target.closest('[data-modal-close]');
      if (closeBtn) {
        e.preventDefault();
        this.close();
        return;
      }

      // Backdrop click
      if (e.target.classList.contains('kempie-modal-backdrop')) {
        this.close();
      }
    });

    // Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.activeModal) {
        this.close();
      }
    });
  }

  open(modalId, triggerElement = null) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    this.previousActiveElement = triggerElement || document.activeElement;
    this.activeModal = modal;

    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Focus first focusable element or close button
    const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable) {
      focusable.focus();
    }
  }

  close() {
    if (!this.activeModal) return;

    this.activeModal.classList.remove('is-open');
    this.activeModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';

    if (this.previousActiveElement && typeof this.previousActiveElement.focus === 'function') {
      this.previousActiveElement.focus();
    }

    this.activeModal = null;
    this.previousActiveElement = null;
  }
}

// Global instance
window.kempieModal = new KempieModal();
