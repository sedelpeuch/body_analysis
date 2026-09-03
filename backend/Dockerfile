FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

# Installé hors de /app : le bind mount de développement (compose.yaml)
# recouvre /app avec le code de l'hôte, mais pas /opt/venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

COPY pyproject.toml uv.lock ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./

RUN uv sync --frozen

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
