FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/api/pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir .

COPY apps/api/app /app/app

COPY apps/api/alembic.ini /app/alembic.ini
COPY apps/api/alembic /app/alembic

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
