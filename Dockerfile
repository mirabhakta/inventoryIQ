FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# LightGBM needs the OpenMP runtime, which slim images omit.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser main.py ./
COPY --chown=appuser:appuser api ./api
COPY --chown=appuser:appuser models ./models
COPY --chown=appuser:appuser services ./services
COPY --chown=appuser:appuser utils ./utils

USER appuser

EXPOSE 8000

# One worker keeps the in-process cache coherent and fits the free tier.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
