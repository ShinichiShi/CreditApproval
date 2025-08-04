#!/bin/bash
echo "⏳ Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done

echo "⏳ Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done

echo "🔧 Making and applying migrations..."
python manage.py makemigrations
python manage.py migrate

echo "🧹 Collecting static files..."
python manage.py collectstatic --noinput

echo "📋 Checking if data files exist..."
ls -la *.xlsx || echo "⚠️  No Excel files found!"

echo "📊 Checking current database state..."
python manage.py shell -c "
from core.models import Customer, Loan
print(f'Current customers: {Customer.objects.count()}')
print(f'Current loans: {Loan.objects.count()}')
"

echo "📦 Triggering sequential data import via Celery..."
python manage.py shell -c "
from core.tasks import import_customer_data, import_loan_data, check_data_status
import time

print('🔍 Checking initial data status...')
try:
    initial_status = check_data_status.delay()
    initial_result = initial_status.get(timeout=30)
    print('Initial status result:', initial_result)
except Exception as e:
    print('Error checking initial status:', str(e))

print('📥 Starting customer data import...')
try:
    result1 = import_customer_data.delay()
    customer_result = result1.get(timeout=300)  # 5 minute timeout
    print('Customer import result:', customer_result)
except Exception as e:
    print('Error importing customer data:', str(e))

print('📥 Starting loan data import...')
try:
    result2 = import_loan_data.delay()
    loan_result = result2.get(timeout=300)  # 5 minute timeout
    print('Loan import result:', loan_result)
except Exception as e:
    print('Error importing loan data:', str(e))

print('🔍 Checking final data status...')
try:
    final_status = check_data_status.delay()
    final_result = final_status.get(timeout=30)
    print('Final status result:', final_result)
except Exception as e:
    print('Error checking final status:', str(e))

print('✅ All imports complete!')
"

echo "📊 Final database check..."
python manage.py shell -c "
from core.models import Customer, Loan
print(f'Final customers: {Customer.objects.count()}')
print(f'Final loans: {Loan.objects.count()}')
if Customer.objects.exists():
    print('Sample customer:', Customer.objects.first().__dict__)
if Loan.objects.exists():
    print('Sample loan:', Loan.objects.first().__dict__)
"

echo "🚀 Starting Gunicorn with OpenTelemetry..."
exec opentelemetry-instrument \
    --traces_exporter otlp \
    --metrics_exporter none \
    --service_name credit-approval-api \
    gunicorn credit_system.wsgi:application --bind 0.0.0.0:8000