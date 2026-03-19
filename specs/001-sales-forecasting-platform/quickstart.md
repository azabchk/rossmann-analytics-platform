# Quick Start: Sales Forecasting Platform

**Feature**: Sales Forecasting Platform
**Branch**: `001-sales-forecasting-platform`
**Date**: 2026-03-06

## Overview

This guide helps you set up the Sales Forecasting Platform for local development. Follow these steps to get a running development environment with backend, database, and frontend (optional).

## Prerequisites

### Required Software

| Tool | Version | Purpose | Install |
|-------|----------|---------|---------|
| **Python** | 3.11+ | Backend, data, ML | [python.org](https://python.org) |
| **Node.js** | 20+ | Frontend | [nodejs.org](https://nodejs.org) |
| **Docker** | Latest | Local Supabase | [docker.com](https://docker.com) |
| **Docker Compose** | Latest | Local Supabase | [docs.docker.com/compose](https://docs.docker.com/compose) |
| **Git** | Latest | Version control | [git-scm.com](https://git-scm.com) |

### Optional Software

| Tool | Purpose |
|-------|---------|
| **Postman** | API testing |
| **pgAdmin** | Database browser (alternative to Supabase dashboard) |
| **VS Code** | Recommended IDE |

## Environment Variables

### Required Variables

Create a `.env` file in the project root (this file is already in `.gitignore`):

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_DB_URL=postgresql://postgres:password@localhost:5432/postgres

# Backend Configuration
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# ML Configuration
MODEL_PATH=./ml/models
MAX_FORECAST_WEEKS=6
FORECAST_CONFIDENCE_LEVEL=0.95

# Application Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Getting Supabase Credentials

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Navigate to Project Settings → API
4. Copy the following values:
   - `SUPABASE_URL`: Project URL
   - `SUPABASE_ANON_KEY`: anon/public key
   - `SUPABASE_SERVICE_KEY`: service_role key (keep secret)

### Getting Supabase DB URL (Local Development)

When using local Supabase via Docker:
```bash
SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

For production Supabase:
```bash
# Found in Project Settings → Database → Connection String
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

## Project Structure

```
DIPLOMA/
├── backend/              # FastAPI backend
│   ├── src/
│   │   ├── api/        # API routes
│   │   ├── models/      # SQLAlchemy models
│   │   ├── services/    # Business logic
│   │   └── schemas/     # Pydantic schemas
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/        # App Router pages
│   │   ├── components/  # React components
│   │   └── lib/         # API client, utilities
│   ├── package.json
│   └── Dockerfile
├── data/                # Data pipelines
│   ├── ingest.py
│   ├── validate.py
│   └── transform.py
├── ml/                  # ML models
│   ├── train.py
│   ├── models/
│   └── inference.py
├── supabase/            # Database migrations
│   └── migrations/
├── .env                 # Environment variables (NOT in git)
├── docker-compose.yml     # Local Supabase
└── README.md
```

## Setup Steps

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd DIPLOMA
git checkout 001-sales-forecasting-platform
```

### Step 2: Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

### Step 3: Set Up Supabase (Local Development)

**Option A: Use Local Supabase (Recommended for Development)**

```bash
# Start local Supabase with Docker Compose
docker-compose up -d

# Verify it's running
docker-compose ps

# Access local Supabase dashboard
open http://localhost:8000
```

**Option B: Use Cloud Supabase (Production-like)**

Skip local Supabase setup and use your cloud Supabase project credentials in `.env`.

### Step 4: Run Database Migrations

```bash
# From project root
cd supabase/migrations

# Run all migrations (using local Supabase)
psql -h localhost -U postgres -d postgres -f 20260306_001_create_stores_table.sql
psql -h localhost -U postgres -d postgres -f 20260306_002_create_sales_records_table.sql
# ... continue with all migration files

# Or use a migration script (to be created)
python backend/scripts/run_migrations.py
```

### Step 5: Set Up Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations (alternative method)
python scripts/run_migrations.py

# Start backend server
uvicorn src.main:app --reload --port 8000
```

Verify backend is running:
```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-03-06T12:00:00Z"
}
```

### Step 6: Set Up Data Pipeline

```bash
# Navigate to data directory
cd data

# Create virtual environment (if not using shared venv)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download Rossmann dataset (if not already present)
# Place train.csv and store.csv in data/raw/

# Run ingestion
python ingest.py --input raw/train.csv --input-raw raw/store.csv

# Run validation
python validate.py

# Run transformation and KPI calculation
python transform.py
```

### Step 7: Set Up ML Models

```bash
# Navigate to ml directory
cd ml

# Create virtual environment (if not using shared venv)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Train models (using cleaned data from database)
python train.py --store-id 1 --model-type prophet

# Evaluate models
python evaluate.py --model-id prophet_v1.0

# Generate forecast
python inference.py --store-id 1 --weeks 6
```

### Step 8: Set Up Frontend (Optional)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with backend URL: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Start development server
npm run dev
```

Access frontend at: http://localhost:3000

## Development Workflow

### Backend Development

```bash
# Activate virtual environment
cd backend && source venv/bin/activate

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Start development server (with auto-reload)
uvicorn src.main:app --reload
```

### Frontend Development

```bash
cd frontend

# Run linter
npm run lint

# Run type checking
npm run type-check

# Start dev server
npm run dev

# Build for production
npm run build
```

### Data Pipeline Development

```bash
cd data && source venv/bin/activate

# Test data quality
python validate.py --verbose

# Re-run pipeline after changes
python ingest.py && python transform.py
```

### ML Model Development

```bash
cd ml && source venv/bin/activate

# Train new model
python train.py --store-id 1 --model-type xgboost

# Compare models
python compare_models.py --store-ids 1,2,3

# Retrain with new data
python train.py --retrain --model-id prophet_v1.0
```

## Common Tasks

### Add New API Endpoint

1. Define route in `backend/src/api/`
2. Create Pydantic schema in `backend/src/schemas/`
3. Implement business logic in `backend/src/services/`
4. Write tests in `backend/tests/`
5. Update API documentation (auto-generated via FastAPI)

### Add New KPI

1. Update KPI calculation in `backend/src/services/kpi_service.py`
2. Add aggregation query in `supabase/migrations/`
3. Run migration
4. Add endpoint in `backend/src/api/kpis.py`
5. Update frontend to display new KPI

### Train New Forecast Model

1. Add model parameters to `ml/train.py`
2. Update hyperparameter search space
3. Run training: `python train.py --model-type your-model`
4. Evaluate: `python evaluate.py --model-id your-model_v1.0`
5. Update `ml/models/active_model.json` if best performer

### Debug Database Issues

```bash
# Connect to local Supabase database
psql -h localhost -U postgres -d postgres

# Useful queries
\dt                          # List tables
SELECT COUNT(*) FROM sales_records;  # Check data loaded
SELECT * FROM stores LIMIT 5;          # Preview stores
```

### Debug Authentication Issues

1. Check JWT token in browser DevTools → Application
2. Verify token is being sent in Authorization header
3. Check backend logs for validation errors
4. Verify user has store_access record for requested store

## Testing

### Run All Tests

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# Integration tests (end-to-end)
pytest tests/integration/
```

### Run Specific Test

```bash
# Backend specific test
cd backend
pytest tests/test_api_stores.py -v

# Test with database (requires test database)
pytest tests/integration/ --test-db-url=postgresql://...
```

## Troubleshooting

### Backend Won't Start

- Check if port 8000 is in use: `lsof -i :8000` (Mac) or `netstat -ano | findstr :8000` (Windows)
- Verify `.env` file exists and has correct values
- Check Python version: `python --version` (must be 3.11+)
- Verify dependencies installed: `pip list`

### Frontend Can't Connect to Backend

- Check backend is running: `curl http://localhost:8000/api/v1/health`
- Verify CORS settings in `.env`: `CORS_ORIGINS=http://localhost:3000`
- Check browser console for CORS errors
- Verify `NEXT_PUBLIC_API_URL` in `.env.local`

### Data Ingestion Fails

- Verify CSV files exist in `data/raw/`
- Check file encoding (must be UTF-8)
- Validate CSV structure: `head data/raw/train.csv`
- Check database connection: `echo $SUPABASE_DB_URL`

### Model Training Fails

- Verify data exists in database for training
- Check if enough historical data (minimum 30 days)
- Verify required Python packages installed: `pip list`
- Check available memory: `python train.py --small-sample` for testing

### Supabase Connection Issues

**Local Supabase**:
- Check Docker is running: `docker ps`
- View logs: `docker-compose logs supabase`
- Restart: `docker-compose restart`

**Cloud Supabase**:
- Verify credentials in `.env`
- Check connection from browser: [Supabase Dashboard](https://supabase.com/dashboard)
- Check service key has admin permissions

## Next Steps

After successful setup:

1. **Explore the API**: Open `http://localhost:8000/docs` for interactive API documentation
2. **Load Sample Data**: Run data ingestion with Rossmann dataset
3. **Train First Model**: Train a Prophet model for a sample store
4. **Generate Forecast**: Use API to generate a 6-week forecast
5. **Build Dashboard**: Develop frontend to visualize forecasts and KPIs

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Supabase Documentation](https://supabase.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [Prophet Documentation](https://facebook.github.io/prophet)
- [XGBoost Documentation](https://xgboost.readthedocs.io)
