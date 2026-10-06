# MAS-Core runtime image (demo / staged dispatch by default)
FROM python:3.12-slim

WORKDIR /app
COPY mas/ mas/
COPY main.py pyproject.toml README.md MANDATE.md ./
COPY docs/ docs/

COPY package.json ./

ENV PYTHONPATH=/app
ENV MAS_WORKSPACE=/app
ENV MAS_ENABLE_LIVE_DISPATCH=false
ENV MAS_SANDBOX_PYTHON=true
ENV MAS_TOOL_ACL=true
ENV MAS_AUDIT_LOG=/app/workspace/audit/events.jsonl
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Node.js, Playwright 1.49.1, and pre-bake browser binaries during build time
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && npm install \
    && npx playwright install --with-deps chromium \
    && mkdir -p /app/workspace/audit /app/workspace/projects \
    && pip install --no-cache-dir -e .

EXPOSE 8080
CMD ["python3", "main.py", "--mode", "dashboard", "--port", "8080"]
