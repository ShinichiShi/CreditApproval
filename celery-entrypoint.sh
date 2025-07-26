#!/bin/bash
# celery-entrypoint.sh
echo "⏳ Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done

echo "⏳ Waiting for web service to complete migrations..."
# Wait a bit longer to ensure web service has completed its setup
sleep 10

echo "🚀 Starting Celery worker..."
exec celery -A credit_system worker --loglevel=info