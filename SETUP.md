
# Setup Instructions :

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- [Git](https://git-scm.com/)

### 🔧 Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/ShinichiShi/CreditApproval.git
   cd CreditApproval
   ```

2. **Environment Configuration**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit the environment variables as needed
   nano .env
   ```

3. **Build and Start Services**
   ```bash
   # Build and start all services
   docker-compose up --build

   ```

5. **Access the Application**
   - **API Base URL**: `http://localhost:8000/`
   - **Swagger Documentation**: `http://localhost:8000/swagger/`
   - **ReDoc Documentation**: `http://localhost:8000/redoc/`

### 🐳 Docker Services

The application consists of the following containerized services:

- **web**: Django application server
- **db**: PostgreSQL database
- **redis**: Redis server for Celery task queue
- **celery**: Celery worker for background tasks

---