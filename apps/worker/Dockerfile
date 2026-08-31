FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY apps/worker/pyproject.toml /app/pyproject.toml

RUN pip install --no-cache-dir .

COPY apps/api/app /app/app

CMD [
  "dramatiq",
  "app.jobs.slack",
  "app.jobs.slack_actions",
  "--processes",
  "1",
  "--threads",
  "4"
]
