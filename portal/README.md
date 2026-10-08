# Acinonyx primary delivery board

**The canonical interface for planning, assigning, tracking, verifying, and reviewing all Acinonyx work is [`scrum.html`](scrum.html).** Use the MAS-PM backend as the source of truth; do not maintain competing local-only task boards. All initiatives, epics, tasks, defects, sprints, agent assignments, evidence, and judicial-review status belong in MAS-PM.

Start the integrated server from the repository root:

```bash
python3 main.py --mode dashboard --port 8080
```

Open **http://127.0.0.1:8080/portal/scrum.html**. Check **http://127.0.0.1:8080/api/pm/projects** to verify API connectivity. The standalone `python3 -m http.server` command serves static files but does **not** provide the MAS-PM APIs required for live board operation.

The research portal at [`index.html`](index.html) remains a separate knowledge/research interface, **not** the project-management source of truth. Respect server-side workflow guards, WIP limits, authenticated roles, evidence requirements, and independent judicial review; UI status alone is not evidence of completion. Do not claim production-readiness solely because the board loads.

---

# Active research portal

`index.html` is the active entry point. `css/` contains styles; `js/` contains application code and the generated research catalog in `js/data/`.

The active entry point remains the same version used before the folder reorganization. The separate upgraded variant formerly nested at `portal/portal/` is preserved under [archives/portal_snapshot/](../archives/portal_snapshot/). Choosing between versions is a separate product decision.

Reference screenshots are under [docs/demos/portal/](../docs/demos/portal/). Exported ZIP files are under [archives/exports/](../archives/exports/). Keep future generated captures outside the live application folder.

To serve locally from the repository root, run `python3 -m http.server 8080 --bind 127.0.0.1`, then request `/portal/`. This server is for local development and serves the checkout; it is not a production deployment.
