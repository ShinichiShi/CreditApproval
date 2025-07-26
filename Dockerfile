FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y netcat-openbsd gcc postgresql-client libpq-dev curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
COPY entrypoint.sh /app/entrypoint.sh
COPY celery-entrypoint.sh /app/celery-entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/celery-entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
