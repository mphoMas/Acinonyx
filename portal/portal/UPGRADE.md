# Acinonyx Research Workspace — upgrade

## Install

Back up your existing `portal` directory, then extract this archive into your MAS project directory. The archive contains a top-level `portal/` folder.

Open `portal/index.html` directly, or serve it from your MAS directory:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000/portal/`.

Keep the existing sibling `research/` directory. PDF and diagram links in the Vault point there; those assets were not part of the uploaded portal archive. Existing relative paths are preserved.

## What's changed

- A coordinated graphite, sage and warm-paper workspace design, with a clear two-row navigation header and responsive collection grid.
- A new home view with catalogue-derived counts, collection filtering, a continue-reading panel, recent documents and saved-document access.
- The seven navigation destinations remain reachable on small screens using a horizontally scrollable navigation strip.
- Search category filters now apply to empty queries. Search text is escaped before insertion into result markup. Results are keyboard-focusable buttons.
- Reader chapter titles use the specific chapter name; save controls expose their pressed state.
- Dialog focus wrapping, return-to-opener behavior, keyboard activation for button-role controls, backdrop dismissal and Escape handling.
- Reader sidebar toggle state fixed, mobile drawer behavior corrected, improved text colors and reduced-motion support.
- Research assist is labelled as a local passage finder. Hardcoded verification scores are replaced with catalogue metadata; recorded roots are not represented as independently verified.
- FinOps and benchmark views identify their bundled assumptions. Existing calculator and simulator logic and source data are preserved.
- Remote font dependency removed. Mermaid remains an optional, asynchronously loaded external dependency; without connectivity, its diagram source remains available as text.

## Data and privacy

All 82 supplied documents are retained without changing the catalogue files. Bookmarks, reader preferences and recent-document IDs use browser-local storage. They are not synchronised between browsers or devices. The research assistant does not call an AI service.

Existing PNG screenshots in the archive predate this upgrade. They are reference captures, not previews or evidence of the upgraded layout.

## Verification

Run the included dependency-free logic checks from the portal directory:

```bash
node tests/workspace.test.cjs
```

Checks cover home catalogue counts, category filtering with and without a query, query escaping, history deduplication, corrupt history recovery, saved-document lookup, Markdown rendering, and duplicate IDs in the entry HTML.

All JavaScript files were syntax-checked, and local script and stylesheet references were checked. The two research catalogue files were verified unchanged against the uploaded archive.

Browser rendering, interactive end-to-end testing and a full accessibility audit were not performed in the available environment. Before replacing a production copy, check desktop and mobile layouts, keyboard focus, search, chapter navigation, the four tools and your local Vault links in a browser. No claim of WCAG conformance is made.

## Implementation

`css/workspace.css` owns the upgraded theme and responsive layout. `js/workspace.js` implements the catalogue home and extends the existing app before initialisation. `js/app.js`, `js/search.js` and `js/copilot.js` include the related navigation, filtering and presentation fixes. No build process or package installation is required.
