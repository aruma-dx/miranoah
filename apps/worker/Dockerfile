FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY apps/worker/pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir .
COPY apps/api/app /app/app
CMD ["dramatiq", "app.jobs.slack", "--processes", "1", "--threads", "4"]
