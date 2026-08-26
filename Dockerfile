# Cloud Run image. The offline path needs nothing installed; only the served
# API pulls dependencies, so the build stays small and the replay fallback keeps
# working even if a dependency breaks.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY grantloop/ ./grantloop/
COPY schema/ ./schema/
COPY seed/ ./seed/
COPY dashboard/ ./dashboard/

RUN pip install --no-cache-dir ".[serve]"

# Cloud Run injects PORT. GOOGLE_CLOUD_PROJECT and MODEL_ID are set at deploy
# time; neither is baked into the image.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn --factory grantloop.api.app:create_app --host 0.0.0.0 --port ${PORT}
