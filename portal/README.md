# Active research portal

`index.html` is the active entry point. `css/` contains styles; `js/` contains application code and the generated research catalog in `js/data/`.

The active entry point remains the same version used before the folder reorganization. The separate upgraded variant formerly nested at `portal/portal/` is preserved under [archives/portal_snapshot/](../archives/portal_snapshot/). Choosing between versions is a separate product decision.

Reference screenshots are under [docs/demos/portal/](../docs/demos/portal/). Exported ZIP files are under [archives/exports/](../archives/exports/). Keep future generated captures outside the live application folder.

To serve locally from the repository root, run `python3 -m http.server 8080 --bind 127.0.0.1`, then request `/portal/`. This server is for local development and serves the checkout; it is not a production deployment.
