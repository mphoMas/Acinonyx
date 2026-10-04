# MAS-Core runtime image (demo / staged dispatch by default)
FROM python:3.12-slim

WORKDIR /app
COPY mas/ mas/
COPY main.py pyproject.toml README.md MANDATE.md ./
COPY docs/ docs/

ENV PYTHONPATH=/app
ENV MAS_WORKSPACE=/app
ENV MAS_ENABLE_LIVE_DISPATCH=false
ENV MAS_SANDBOX_PYTHON=true
ENV MAS_TOOL_ACL=true
ENV MAS_AUDIT_LOG=/app/workspace/audit/events.jsonl

RUN mkdir -p /app/workspace/audit /app/workspace/projects \
    && pip install --no-cache-dir -e .

EXPOSE 8080
CMD ["python3", "main.py", "--mode", "dashboard", "--port", "8080"]
