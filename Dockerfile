FROM python:3.12-slim AS base

# Bleak's BlueZ backend talks to the bluetoothd D-Bus service; the client
# library itself is pure Python, so no extra system packages are required.
RUN pip install --no-cache-dir uv==0.7.13

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ src/
COPY README.md ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["vick"]
CMD ["--config", "/config/config.toml"]
