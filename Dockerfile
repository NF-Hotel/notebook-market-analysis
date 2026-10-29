# Image of the market analysis service: the HTTP API the NFHotel web application calls.
# The notebook libraries are not installed. Build context is the repository root:
#   docker build -t market-analysis:local .
# Dependencies come from requirements.lock (hash-locked, wheels only); the code runs from
# PYTHONPATH, so no build backend and no setup script runs. Regenerate the lock as README.md says.
# Settings come from the environment (deploy/market-analysis.env.example); no secret is in the image.
FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.lock ./
RUN pip install --require-hashes --only-binary :all: --no-deps -r requirements.lock
COPY src ./src

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app /data
USER app

ENV OUTPUT_DIRECTORY=/data
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "--factory", "app.infrastructure.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
