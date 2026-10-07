/**
 * portal/js/reader.js: High-Performance Technical Markdown Renderer & Reader Engine.
 * Converts markdown, GitHub-style alerts, fenced code, tables & Mermaid diagrams.
 * Provides reader preferences (font size, reading density, bookmarks, share links).
 * 
 * Architect: frontend_engineer / MAS Swarm
 */

class MarkdownReaderEngine {
  constructor() {
    this.mermaidInitialized = false;
    this.fontSize = localStorage.getItem('acinonyx_font_size') || 'normal';
    this.density = localStorage.getItem('acinonyx_density') || 'comfortable';
    this.applyPreferences();
  }

  applyPreferences() {
    const root = document.documentElement;
    if (this.fontSize === 'small') {
      root.style.setProperty('--reader-font-size', '0.94rem');
      root.style.setProperty('--reader-line-height', '1.6');
    } else if (this.fontSize === 'large') {
      root.style.setProperty('--reader-font-size', '1.14rem');
      root.style.setProperty('--reader-line-height', '1.85');
    } else {
      root.style.setProperty('--reader-font-size', '1.02rem');
      root.style.setProperty('--reader-line-height', '1.7');
    }

    if (this.density === 'compact') {
      root.style.setProperty('--reader-para-spacing', '0.9rem');
    } else {
      root.style.setProperty('--reader-para-spacing', '1.4rem');
    }
  }

  setFontSize(size) {
    this.fontSize = size;
    localStorage.setItem('acinonyx_font_size', size);
    this.applyPreferences();
    if (window.toast) window.toast.show(`Font size set to ${size}`, 'info');
  }

  setDensity(density) {
    this.density = density;
    localStorage.setItem('acinonyx_density', density);
    this.applyPreferences();
    if (window.toast) window.toast.show(`Reading density: ${density}`, 'info');
  }

  isBookmarked(docId) {
    try {
      const marks = JSON.parse(localStorage.getItem('acinonyx_bookmarks') || '[]');
      return marks.includes(docId);
    } catch (e) {
      return false;
    }
  }

  toggleBookmark(docId) {
    try {
      let marks = JSON.parse(localStorage.getItem('acinonyx_bookmarks') || '[]');
      let bookmarked = false;
      if (marks.includes(docId)) {
        marks = marks.filter(id => id !== docId);
        bookmarked = false;
        if (window.toast) window.toast.show('Removed from favorites', 'info');
      } else {
        marks.push(docId);
        bookmarked = true;
        if (window.toast) window.toast.show('Saved to favorites ★', 'success');
      }
      localStorage.setItem('acinonyx_bookmarks', JSON.stringify(marks));

      // Update UI button state if present
      const starBtn = document.getElementById(`star-btn-${docId}`);
      if (starBtn) {
        starBtn.classList.toggle('active', bookmarked);
        starBtn.innerHTML = bookmarked ? '★ Saved' : '☆ Save';
      }

      // Update sidebar star badge
      const linkEl = document.getElementById(`link-${docId}`);
      if (linkEl) {
        let starBadge = linkEl.querySelector('.star-badge');
        if (bookmarked && !starBadge) {
          starBadge = document.createElement('span');
          starBadge.className = 'star-badge';
          starBadge.innerText = '★';
          linkEl.prepend(starBadge);
        } else if (!bookmarked && starBadge) {
          starBadge.remove();
        }
      }

      return bookmarked;
    } catch (e) {
      console.error(e);
      return false;
    }
  }

  render(markdownText) {
    if (!markdownText) return '';

    let md = markdownText;

    // 1. Pre-process Code Blocks (including Mermaid) to prevent internal markdown parsing
    const codeBlocks = [];
    md = md.replace(/```([a-zA-Z0-9_\-]+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      const id = `__CODE_BLOCK_${codeBlocks.length}__`;
      codeBlocks.push({ lang: (lang || 'text').toLowerCase(), code: code.trim() });
      return id;
    });

    // 2. Pre-process GitHub-style alert callouts: > [!NOTE], > [!TIP], etc.
    md = md.replace(/^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*\n((?:>.*(?:\n|$))*)/gim, (match, type, content) => {
      const cleanContent = content.replace(/^>\s?/gm, '').trim();
      const typeLower = type.toLowerCase();
      const icons = {
        note: 'ℹ️',
        tip: '💡',
        important: '⚡',
        warning: '⚠️',
        caution: '🛑'
      };
      return `<div class="callout-alert callout-${typeLower}">
        <div class="callout-title">${icons[typeLower] || '📌'} ${type}</div>
        <p>${this.escapeHtml(cleanContent)}</p>
      </div>\n\n`;
    });

    // 3. Regular blockquotes
    md = md.replace(/^>\s+(.*)$/gm, '<blockquote><p>$1</p></blockquote>');
    // Merge adjacent blockquotes
    md = md.replace(/<\/blockquote>\s*<blockquote>/g, '');

    // 4. Headers with auto anchors
    md = md.replace(/^####\s+(.*)$/gm, (m, title) => {
      const anchor = this.createAnchor(title);
      return `<h4 id="${anchor}">${title}</h4>`;
    });
    md = md.replace(/^###\s+(.*)$/gm, (m, title) => {
      const anchor = this.createAnchor(title);
      return `<h3 id="${anchor}">${title}</h3>`;
    });
    md = md.replace(/^##\s+(.*)$/gm, (m, title) => {
      const anchor = this.createAnchor(title);
      return `<h2 id="${anchor}">${title}</h2>`;
    });
    md = md.replace(/^#\s+(.*)$/gm, (m, title) => {
      const anchor = this.createAnchor(title);
      return `<h1 id="${anchor}">${title}</h1>`;
    });

    // 5. Horizontal rules
    md = md.replace(/^(?:---|\*\*\*|___)\s*$/gm, '<hr>');

    // 6. Tables
    md = this.parseTables(md);

    // 7. Lists: tag each item by type, then wrap contiguous runs separately
    md = md.replace(/^[ \t]*[-*+][ \t]+(.*)$/gm, '<li data-t="u">$1</li>');
    md = md.replace(/^[ \t]*\d+\.[ \t]+(.*)$/gm, '<li data-t="o">$1</li>');
    md = md.replace(/(?:<li data-t="u">.*<\/li>\n?)+/g, m => `<ul>${m.replace(/ data-t="u"/g, '')}</ul>\n`);
    md = md.replace(/(?:<li data-t="o">.*<\/li>\n?)+/g, m => `<ol>${m.replace(/ data-t="o"/g, '')}</ol>\n`);

    // 8. Inline formatting. Underscore emphasis only applies at word boundaries
    md = md.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    md = md.replace(/(^|[\s(>])__([^_\n]+)__(?=[\s).,;:<]|$)/gm, '$1<strong>$2</strong>');
    md = md.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
    md = md.replace(/(^|[\s(>])_([^_\s][^_\n]*)_(?=[\s).,;:<]|$)/gm, '$1<em>$2</em>');
    md = md.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 9. Links & Images
    md = md.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="reader-img" style="max-width:100%; border-radius:10px; margin:1.5rem 0;">');
    md = md.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // 10. Paragraphs for remaining naked lines
    const paragraphs = md.split(/\n\s*\n/);
    md = paragraphs.map(p => {
      p = p.trim();
      if (!p) return '';
      if (/^<(h[1-6]|ul|ol|blockquote|div|hr|table|pre)/.test(p)) {
        return p;
      }
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).join('\n\n');

    // 11. Restore Code Blocks & Mermaid
    for (let i = 0; i < codeBlocks.length; i++) {
      const block = codeBlocks[i];
      const placeholder = `__CODE_BLOCK_${i}__`;

      if (block.lang === 'mermaid') {
        const mermaidHtml = `
          <div class="mermaid-wrapper">
            <div class="mermaid-header">
              <span>📊 Architecture Diagram</span>
              <span>Mermaid.js</span>
            </div>
            <div class="mermaid">${block.code}</div>
          </div>`;
        md = md.replace(placeholder, mermaidHtml);
      } else {
        const escapedCode = this.escapeHtml(block.code);
        const codeBlockHtml = `
          <div class="code-block-wrapper">
            <div class="code-block-header">
              <span>${block.lang.toUpperCase()}</span>
              <button class="copy-code-btn" onclick="copyCodeSnippet(this)">Copy</button>
            </div>
            <pre><code class="language-${block.lang}">${escapedCode}</code></pre>
          </div>`;
        md = md.replace(placeholder, codeBlockHtml);
      }
    }

    return md;
  }

  parseTables(text) {
    const tableRegex = /\|(.+)\|\n\|([\s\-:|]+)\|\n((?:\|.+\|\n?)+)/g;
    return text.replace(tableRegex, (match, headerRow, separatorRow, bodyRows) => {
      const headers = headerRow.split('|').slice(1, -1).map(h => `<th>${h.trim()}</th>`).join('');
      const rows = bodyRows.trim().split('\n').map(row => {
        const cells = row.split('|').slice(1, -1).map(c => `<td>${c.trim()}</td>`).join('');
        return `<tr>${cells}</tr>`;
      }).join('');

      return `
        <div class="table-wrapper">
          <table>
            <thead><tr>${headers}</tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    });
  }

  createAnchor(title) {
    return title.toLowerCase().replace(/<[^>]*>/g, '').replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-');
  }

  escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  initMermaid() {
    if (typeof mermaid !== 'undefined') {
      try {
        mermaid.initialize({
          startOnLoad: false,
          theme: 'dark',
          themeVariables: {
            darkMode: true,
            background: '#0a0e17',
            primaryColor: '#00f0ff',
            primaryTextColor: '#f1f5f9',
            primaryBorderColor: '#00f0ff',
            lineColor: '#38bdf8',
            secondaryColor: '#1e293b',
            tertiaryColor: '#0f172a'
          }
        });
        mermaid.run();
      } catch (err) {
        console.warn('Mermaid rendering notice:', err);
      }
    }
  }
}

// Global copy helper
window.copyCodeSnippet = function(button) {
  const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
  if (codeBlock) {
    navigator.clipboard.writeText(codeBlock.innerText).then(() => {
      const orig = button.innerText;
      button.innerText = 'Copied!';
      button.style.borderColor = 'var(--accent-emerald)';
      button.style.color = 'var(--accent-emerald)';
      if (window.toast) window.toast.show('Code snippet copied to clipboard', 'success');
      setTimeout(() => {
        button.innerText = orig;
        button.style.borderColor = '';
        button.style.color = '';
      }, 2000);
    });
  }
};

window.MarkdownReaderEngine = MarkdownReaderEngine;
