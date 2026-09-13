# 🏫 Laerskool Kempton Park — Official School Portal

> **Branch:** `school-website`  
> **Repository:** [mphoMas/Acinonyx](https://github.com/mphoMas/Acinonyx/tree/school-website)  
> **Hosting Target:** Firebase Hosting (`laerskool-kempton-park`)  
> **Institution:** Laerskool Kempton Park (English-Medium Primary & Full-Service School, Est. 1903)  
> **Location:** Kittyhawk St, Rhodesfield, Kempton Park, Gauteng, South Africa

---

## 📌 Project Overview
This branch houses the production-grade, responsive digital web portal for **Laerskool Kempton Park**, a premier English-medium public primary and full-service school in Rhodesfield. The portal delivers an accessible, high-performance community interface designed for parents, learners, educators, and the Gauteng Department of Education (GDE) ecosystem.

---

## ✨ Key Features & Architectural Modules

### 1. Site-Wide Search & Quick Palette (`search-palette.js`)
- Instant keyboard shortcut trigger (`Ctrl/Cmd + K` or search button).
- Live filtering across admissions, curriculum, clinical therapies, staff, calendar, and downloadable documents.
- Keyboard navigation (arrow keys, Enter to navigate, Escape to dismiss).

### 2. Admissions & Tuition Fee Calculator (`fee-calculator.js`, `grade-r-checker.js`)
- Dynamic annual and monthly fee estimation based on grade level and sibling discounts.
- Grade R eligibility age calculator aligned with South African statutory entry requirements.
- Full GDE admissions timeline guidance and certified documentation checklist.

### 3. Full-Service & Inclusive Therapy Navigator (`therapy-navigator.js`)
- Comprehensive overview of on-site multidisciplinary therapies:
  - Speech & Language Therapy
  - Occupational Therapy (sensory integration & fine-motor development)
  - Remedial & Learning Support
  - School Social Work & Counseling
- SIAS (Screening, Identification, Assessment and Support) protocol explainer.

### 4. Interactive School Calendar & News Hub (`calendar-module.js`)
- Term-by-term academic, sporting, and cultural event calendar.
- Category filtering (Academics, Athletics, Netball, Cultural, Assemblies, Holidays).
- Official school circulars and downloadable newsletters.

### 5. Institutional & Campus Portals
- **`index.html`**: Institutional landing page, leadership welcome, core value pillars, key metrics, and campus highlights.
- **`about.html`**: 120+ year institutional heritage (1903–present), mission, vision, school governing body (SGB), and staff directory.
- **`admissions.html`**: Admissions policies, GDE online application links, fee schedules, and requirements.
- **`full-service.html`**: Dedicated full-service education wing, special needs support, and therapy facilities.
- **`school-life.html`**: Academic phases (Foundation, Intermediate, Senior), sporting codes, choir, and the aquaponics agriculture project.
- **`news.html`**: Announcements, press releases, and calendar.
- **`contact.html`**: Direct departmental contacts, interactive enquiry form, directions from Rhodesfield Gautrain station, and emergency lines.

---

## 🎨 Design System & Accessibility
- **CSS Architecture:** Zero runtime framework dependencies. Engineered with native CSS Custom Properties (`variables.css`), semantic base resets (`base.css`), reusable components (`components.css`), and responsive layouts (`pages.css`).
- **Typography & Aesthetics:** High-contrast, institutional navy and gold palette, modern typography, glassmorphic utility bars, and subtle micro-animations.
- **Accessibility:** WCAG 2.1 AA compliant, skip-to-content links, ARIA labels on all modal dialogues and search widgets, and fully keyboard navigable.

---

## 🚀 Local Development & Preview

To preview the portal locally using Python or any static HTTP server:

```powershell
# Using Python's built-in HTTP server
python -m http.server 8080

# Or using Node http-server / serve
npx serve .
```
Then open `http://localhost:8080` in your web browser.

---

## ☁️ Deployment (Firebase Hosting)

The project is pre-configured for Firebase Hosting in `firebase.json` and `.firebaserc`:

```powershell
# Authenticate with Firebase (if not already logged in)
firebase login

# Deploy directly to live hosting
firebase deploy --only hosting
```

---

*Engineered within the Acinonyx Agentic Framework on Dell PowerEdge T340.*
