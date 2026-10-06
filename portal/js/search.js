/**
 * portal/js/search.js: Sub-millisecond Client-Side Fuzzy Search Engine.
 * Filters across all 66 documents, titles, headings, tags, and full content.
 * 
 * Architect: data_architect_ai / MAS Swarm
 */

class ResearchSearchEngine {
  constructor(catalog) {
    this.catalog = catalog || window.RESEARCH_CATALOG || { documents: [] };
    this.documents = this.catalog.documents || [];
    this.activeFilter = 'ALL';
  }

  setFilter(filterCategory) {
    this.activeFilter = filterCategory;
  }

  search(query, maxResults = 12) {
    if (!query || !query.trim()) {
      return this.getDefaultResults(maxResults);
    }

    const q = query.trim().toLowerCase();
    const terms = q.split(/\s+/).filter(t => t.length > 0);
    const scoredResults = [];

    for (const doc of this.documents) {
      // Filter by volume category if set
      if (this.activeFilter !== 'ALL' && doc.volumeKey !== this.activeFilter) {
        continue;
      }

      let score = 0;
      const titleLower = doc.title.toLowerCase();
      const summaryLower = (doc.summary || '').toLowerCase();
      const tagsLower = (doc.tags || []).join(' ').toLowerCase();
      const categoryLower = (doc.category || '').toLowerCase();
      const contentLower = doc.content ? doc.content.toLowerCase() : '';

      // Exact title match gets massive weight
      if (titleLower.includes(q)) {
        score += 100;
        if (titleLower.startsWith(q)) score += 50;
      }

      // Check all terms
      let allTermsFound = true;
      let matchedSnippet = '';

      for (const term of terms) {
        let termInDoc = false;

        if (titleLower.includes(term)) {
          score += 40;
          termInDoc = true;
        }
        if (tagsLower.includes(term)) {
          score += 25;
          termInDoc = true;
        }
        if (categoryLower.includes(term)) {
          score += 20;
          termInDoc = true;
        }
        if (summaryLower.includes(term)) {
          score += 15;
          termInDoc = true;
          if (!matchedSnippet) {
            matchedSnippet = this.extractSnippet(doc.summary, term);
          }
        }
        if (contentLower.includes(term)) {
          score += 5;
          termInDoc = true;
          if (!matchedSnippet) {
            matchedSnippet = this.extractSnippet(doc.content, term);
          }
        }

        if (!termInDoc) {
          allTermsFound = false;
        }
      }

      if (score > 0) {
        if (allTermsFound) score += 30; // Bonus for multi-term conjunction
        scoredResults.push({
          doc,
          score,
          snippet: matchedSnippet || this.cleanSnippet(doc.summary || '')
        });
      }
    }

    // Sort descending by score
    scoredResults.sort((a, b) => b.score - a.score);
    return scoredResults.slice(0, maxResults);
  }

  getDefaultResults(limit = 8) {
    return this.documents.slice(0, limit).map(doc => ({
      doc,
      score: 1,
      snippet: this.cleanSnippet(doc.summary || '')
    }));
  }

  extractSnippet(text, term) {
    if (!text) return '';
    const lower = text.toLowerCase();
    const idx = lower.indexOf(term.toLowerCase());
    if (idx === -1) return this.cleanSnippet(text);

    const start = Math.max(0, idx - 60);
    const end = Math.min(text.length, idx + term.length + 80);
    let snippet = text.substring(start, end);
    if (start > 0) snippet = '...' + snippet;
    if (end < text.length) snippet = snippet + '...';
    return this.cleanSnippet(snippet);
  }

  cleanSnippet(str) {
    return str
      .replace(/#+\s*/g, '')
      .replace(/!\[.*?\]\(.*?\)/g, '')
      .replace(/\[([^\]]+)\]\(.*?\)/g, '$1')
      .replace(/```.*?```/gs, '')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/>\s*/g, '')
      .trim();
  }

  highlightMatch(text, query) {
    if (!query) return text;
    const terms = query.trim().split(/\s+/).filter(t => t.length > 1);
    if (!terms.length) return text;

    const regex = new RegExp(`(${terms.map(t => this.escapeRegex(t)).join('|')})`, 'gi');
    return text.replace(regex, '<span class="highlight-match">$1</span>');
  }

  escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}

window.ResearchSearchEngine = ResearchSearchEngine;
