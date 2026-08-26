# Cloud Run image.
#
# The package is installed editable and the working directory stays /app, so
# schema/, seed/ and dashboard/ resolve to the copies in the image rather than to
# site-packages. GRANTLOOP_ROOT makes that explicit rather than implied.
FROM python:3.12-slim

WORKDIR /app

# Dependencies first, so source edits do not invalidate the pip layer.
COPY pyproject.toml README.md ./
COPY grantloop/__init__.py ./grantloop/
RUN pip install --no-cache-dir -e ".[deploy]"

COPY grantloop/ ./grantloop/
COPY schema/ ./schema/
COPY seed/ ./seed/
COPY dashboard/ ./dashboard/

# Cloud Run injects PORT. Project, model and location are set at deploy time;
# none of them is baked into the image, because both the project and the model
# have already moved once.
ENV PORT=8080 \
    GRANTLOOP_ROOT=/app \
    PYTHONUNBUFFERED=1
EXPOSE 8080

CMD exec uvicorn --factory grantloop.api.app:create_app --host 0.0.0.0 --port ${PORT}
