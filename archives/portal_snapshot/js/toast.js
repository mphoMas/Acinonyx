/**
 * portal/js/toast.js: Lightweight Accessible Toast Notification Engine.
 * 
 * Architect: frontend_engineer / MAS Swarm
 */

class ToastManager {
  constructor() {
    this.container = null;
    this.init();
  }

  init() {
    let el = document.getElementById('toast-container');
    if (!el) {
      el = document.createElement('div');
      el.id = 'toast-container';
      el.className = 'toast-container';
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      document.body.appendChild(el);
    }
    this.container = el;
  }

  show(message, type = 'info', durationMs = 3200) {
    if (!this.container) this.init();

    const icons = {
      success: '✓',
      info: '✦',
      warning: '⚠️',
      error: '✕'
    };

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.setAttribute('role', 'status');

    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || '✦'}</span>
      <span class="toast-message">${this.escapeHtml(message)}</span>
    `;

    this.container.appendChild(toast);

    // Trigger entrance animation
    requestAnimationFrame(() => {
      toast.classList.add('toast-visible');
    });

    setTimeout(() => {
      toast.classList.remove('toast-visible');
      toast.classList.add('toast-hiding');
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }, durationMs);
  }

  escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

window.toast = new ToastManager();
