# Acinonyx Design System & Visual Identity Specification

**Author:** `design_lead`  
**Deliverable for:** `UX-01` (`MAS-18`)  
**Scope:** `portal/css/`, `docs/`  
**Status:** Approved & Implemented

---

## 1. Visual Identity & Design Principles

Acinonyx is an autonomous enterprise multi-agent system. Its interface must project precision, operational velocity, and high-trust transparency.

1. **Information Density with Breathing Room**: Avoid oversized toy UI elements; prioritize scannable telemetry, real-time status pills, and dense tabular data.
2. **Curated Dark Modern Aesthetic**: High-contrast, warm dark surfaces (`#101211`, `#151816`, `#1b211d`) paired with crisp emerald and mint accents (`#a6d7b6`, `#87d3a4`).
3. **Anti-Slop Guardrails**: Zero AI-generated decorative filler, zero generic stock layouts, zero unstyled fallback components. Every element has purposeful visual weight.
4. **State Transparency**: Every agent action, FSM transition, circuit breaker, and empirical test log has an explicit visual state indicator.

---

## 2. Core Token Specification (`portal/css/tokens.css`)

### Color Palette

| Token | CSS Variable | Hex / Value | Semantic Role |
| :--- | :--- | :--- | :--- |
| **Canvas Background** | `--bg` | `#101211` | Primary screen canvas |
| **Panel Surface** | `--panel` | `#151816` | Sidebar, drawers, containers |
| **Card Surface** | `--card` | `#1b211d` | Kanban cards, metric panels |
| **Border / Rule** | `--line` | `#303a32` | Subtle dividing lines |
| **Primary Text** | `--text` | `#e2ede5` | High-contrast readable body |
| **Muted Text** | `--muted` | `#a9b7ac` | Secondary metadata and labels |
| **Emerald Accent** | `--green` | `#a6d7b6` | Active states, successful verification |
| **Critical Red** | `--red` | `#f5a99d` | P0 blockers, circuit trips |
| **Warning Gold** | `--gold` | `#e4c28c` | Rework required, WIP warnings |

### Typography

- **Headings & Badges**: Outfit / Inter (`font-weight: 600` / `700`), uppercase tracking on stage tags.
- **Body & Data**: Inter (`font-size: 14px`, `line-height: 1.5`).
- **Telemetry & Hashes**: JetBrains Mono (`font-size: 12px`, tabular numerals).

---

## 3. Component Standards

### Kanban & Scrum Board (`board.css`)
- **Column Header**: Displays column stage name, saturated color indicator, and WIP ratio `[Count / WIP Limit]`.
- **Ticket Card**:
  - Displays Allocation ID, Title, Priority tag, and Assignee avatar pill.
  - Interactive hover state: `transform: translateY(-2px)` with subtle border highlight.
  - Drawer inspector modal provides full immutable audit trail and verifiable evidence links.

### Sprints View
- Grid layout with responsive auto-fit cards displaying Sprint Goal, Active status pill, date window, and assigned issue count.

---

## 4. Verification & Testing

- Automated regression coverage via `tests/test_visual_diff.py` and `tests/test_portal_web.py`.
- Automated anti-slop audit via `scripts/audit_web_anti_slop.py`.
