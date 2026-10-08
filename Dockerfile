# MAS-Core runtime image (demo / staged dispatch by default)
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

WORKDIR /app

ENV PYTHONPATH=/app \
    MAS_WORKSPACE=/app \
    MAS_PM_DB_PATH=/app/workspace/mas_pm.db \
    MAS_ENABLE_LIVE_DISPATCH=false \
    MAS_SANDBOX_PYTHON=true \
    MAS_TOOL_ACL=true \
    MAS_AUDIT_LOG=/app/workspace/audit/events.jsonl \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PIP_NO_CACHE_DIR=1

# Node.js + pinned Playwright 1.49.1 (package-lock.json) with browser binaries baked in at build time
COPY package.json package-lock.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    apt-get update && apt-get install -y --no-install-recommends nodejs npm bubblewrap xvfb xdotool \
    && npm ci \
    && npx playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* \
    && chmod -R a+rX /ms-playwright

COPY mas/ mas/
COPY main.py pyproject.toml README.md ./
COPY company/MANDATE.md company/MANDATE.md
COPY docs/ docs/
COPY portal/ portal/
COPY work_queue/ work_queue/

# Run as an unprivileged user
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    useradd --create-home --uid 10001 mas \
    && mkdir -p /app/workspace/audit /app/workspace/projects \
    && pip install -e ".[browser]" \
    && chown -R mas:mas /app
USER mas

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/status', timeout=3)" || exit 1
CMD ["python3", "main.py", "--mode", "dashboard", "--port", "8080"]
