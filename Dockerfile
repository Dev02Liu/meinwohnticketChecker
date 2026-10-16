FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DATA_DIR=/data \
    UI_HOST=0.0.0.0 \
    UI_PORT=8080 \
    TZ=Europe/Vienna

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt \
    && playwright install --with-deps chromium-headless-shell \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data && chown app:app /data \
    && chmod -R a+rX /ms-playwright

COPY checker ./checker

USER app
VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import httpx, os; httpx.get(f\"http://127.0.0.1:{os.environ.get('UI_PORT', '8080')}/healthz\", timeout=4).raise_for_status()" || exit 1

ENTRYPOINT ["python", "-m", "checker"]
