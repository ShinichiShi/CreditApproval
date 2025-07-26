# 💳 Credit Approval System

<p align="center">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/DRF-ff1709?style=for-the-badge&logo=django&logoColor=white" alt="Django REST Framework">
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white" alt="GitHub Actions">
</p>

<p align="center">
  A robust <strong>Credit Approval System</strong> built with Django REST Framework that evaluates loan eligibility based on historical data and implements intelligent credit scoring algorithms.
</p>

---

## 📌 Overview

This **Credit Approval System** is designed to assess loan applications by analyzing customer credit history, calculating dynamic credit scores, and making intelligent approval decisions. The system processes historical customer and loan data to provide real-time credit evaluations with appropriate interest rate corrections.

## 🛠️ Features

- **Customer Management** - Register and manage customer profiles
- **Credit Scoring Algorithm** - Intelligent scoring based on payment history, loan volume, and current activity
- **Loan Eligibility Check** - Real-time eligibility assessment with interest rate corrections
- **Loan Processing** - Create and manage approved loans
- **Comprehensive Loan Views** - Individual and customer-wise loan details
- **Background Data Ingestion** - Automated processing of historical data
- **RESTful API Design** - Well-structured endpoints with proper error handling
- **Interactive API Documentation** - Swagger/OpenAPI integration
- **Dockerized Deployment** - Complete containerization with Docker Compose
- **CI/CD Pipeline** - GitHub Actions for automated testing and deployment

## 📦 Tech Stack

- **Backend Framework**: [Django 4+](https://www.djangoproject.com/) with [Django REST Framework](https://www.django-rest-framework.org/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **Task Queue**: [Celery](https://celery.readthedocs.io/) with Redis for background processing
- **API Documentation**: [Swagger/OpenAPI](https://swagger.io/) via drf-spectacular
- **Containerization**: [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
- **CI/CD**: [GitHub Actions](https://github.com/features/actions)
- **Code Quality**: Pre-commit hooks, linting, and automated testing

---
## SETUP: 

 ### Follow the setup instructions mentioned [here](SETUP.md) to setup this project locally

---
## 📌 API Endpoints

### Customer Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register/` | Register a new customer |

### Loan Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/check-eligibility/` | Check loan eligibility and get credit assessment |
| `POST` | `/create-loan/` | Process and create a new loan |
| `GET` | `/view-loan/<loan_id>/` | View specific loan details |
| `GET` | `/view-loans/<customer_id>/` | View all loans for a customer |

### 📝 API Usage Examples

#### Register a New Customer
```bash
curl -X POST http://localhost:8000/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": "9876543210"
  }'
```

#### Check Loan Eligibility
```bash
curl -X POST http://localhost:8000/check-eligibility/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 87,
    "loan_amount": 4000,
    "interest_rate": 10.5,
    "tenure": 12
  }'
```

#### Create a Loan
```bash
curl -X POST http://localhost:8000/create-loan/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 87,
    "loan_amount": 4000,
    "interest_rate": 12.0,
    "tenure": 12
  }'
```


#### View specific loan
```bash
curl -X GET http://localhost:8000/view-loan/123/ \
  -H "Content-Type: application/json"
```

#### View loans of specific customer
```bash
curl -X GET http://localhost:8000/view-loans/87/ \
  -H "Content-Type: application/json"
```
---

## 🧮 Credit Scoring Algorithm

The system implements a sophisticated credit scoring mechanism based on the following components:

### Scoring Components and calculations

1. Payment History (Up to 25 points)

        Formula: min(25, on_time_ratio * 25)
        Calculation: on_time_ratio = sum(emis_paid_on_time) / sum(tenure) for all existing loans.
        For new customers: Assigned 10 points as baseline

2. Loan Count Impact (Up to 20 points)

        Formula: `max(0, 20 - len(existing_loans) * 2)`
        Logic: Each existing loan reduces score by 2 points

3. Current Year Activity (Up to 20 points)

        Formula: `max(0, 20 - len(current_year_loans) * 5)`
        Logic: Each loan taken in current year reduces score by 5 points

4. Credit Utilization (Up to 20 points)

        Formula: `max(0, 20 - (total_loan_volume / approved_limit) * 20)`   
        Logic: Higher utilization of approved credit limit reduces score

### Approval Rules & Interest Rate Corrections

    Credit Score > 50: ✅ Loan approved at requested interest rate

    30 < Credit Score ≤ 50: ⚠️ Loan approved with minimum 12% interest rate

    10 < Credit Score ≤ 30: ⚠️ Loan approved with minimum 16% interest rate

    Credit Score ≤ 10: ❌ Loan rejected

### Additional Safeguards

1. Credit Limit Breach:  If current_debt > approved_limit, credit score is set to 0 (automatic rejection)

2. Debt-to-Income Ratio Check

    Rule: (new_loan_emi + total_existing_emis) ≤ 50% of monthly_salary
    EMI Calculation:
    monthly_rate = `corrected_interest_rate / (12 * 100)`
    emi = `loan_amount * monthly_rate * ((1 + monthly_rate)^tenure) / (((1 + monthly_rate)^tenure) - 1)`


3. Interest Rate Correction Logic
    ```python
    if score <= 10:
        corrected_rate = 16  # Minimum for very low scores
    elif score <= 30:
        corrected_rate = max(requested_rate, 16)  # At least 16%
    elif score <= 50:
        corrected_rate = max(requested_rate, 12)  # At least 12%
    else:
        corrected_rate = requested_rate  # No correction needed
    ```
    The system implements a sophisticated credit scoring mechanism based on:


---

## 🏗️ Project Structure

```
Credit Approval System
├── core/                      # Main Django app containing business logic
│   ├── admin.py               # Django admin configurations for models
│   ├── apps.py                # App configuration class for 'core'
│   ├── migrations/            # Auto-generated DB migration files
│   ├── models.py              # Database models (Customer, Loan)
│   ├── serializers.py         # DRF serializers for request/response validation
│   ├── tasks.py               # Celery tasks (for background data import)
│   ├── tests.py               # Unit tests for all API endpoints
│   ├── urls.py                # URL routes specific to 'core' app
│   ├── utils.py               # Helper functions (e.g., credit scoring logic)
│   └── views.py               # API views (business logic for endpoints)
├── credit_system/             # Django project configuration
│   ├── asgi.py                # ASGI configuration (for async servers)
│   ├── celery.py              # Celery app configuration & broker setup
│   ├── settings.py            # Main project settings (DB, Redis, etc.)
│   ├── urls.py                # Global URL routing (includes core.urls)
│   └── wsgi.py                # WSGI entry point (for production servers)
├── manage.py                  # Django CLI utility for migrations, server, etc.
├── docker-compose.yml         # Docker Compose config (Web, DB, Redis, Celery)
├── Dockerfile                 # Docker image definition for the Django app
├── celery-entrypoint.sh       # Entrypoint script for Celery worker container
├── entrypoint.sh              # Entrypoint script to run Django in the container
├── loan_data.xlsx             # Sample dataset for loans (used in Celery tasks)
├── customer_data.xlsx         # Sample dataset for customers (used in Celery tasks)
└── requirements.txt           # Python dependencies for the project

```

---

## 🧪 Testing

Run the test suite using Docker:

```bash
# Run all tests
docker-compose exec web python manage.py test

```

---

## 🚢 Deployment

The project includes GitHub Actions workflows for:

- **Continuous Integration**: Automated testing on pull requests
- **Code Quality Checks**: Linting, formatting, and security scanning
- **Automated Deployment**: Deploy to staging/production environments

### Manual Deployment

1. **Production Build**
   ```bash
   docker-compose -f docker-compose.prod.yml up --build -d
   ```

2. **Environment Variables**
   Ensure all production environment variables are properly set in your deployment environment.

---

## Contributing :
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
