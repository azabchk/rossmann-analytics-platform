# Architecture Overview

## Headless Architecture

This project uses a **headless** architecture pattern where the backend provides a clean REST API that serves multiple potential frontend clients. The backend contains all business logic, data processing, and integration with ML services, while the frontend is a pure presentation layer that consumes the API.

```
Frontend (Headless Client)          Other Clients (Future)
       │                                     │
       └──────────────┬──────────────────────┘
                      │
                 REST API
                      │
              ┌───────▼────────┐
              │    Backend     │
              │  (FastAPI)     │
              └───────┬────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   Supabase    Data Pipelines   ML Services
```

## Module Boundaries

### Frontend Module
- **Responsibility**: Presentation, user interaction, data visualization
- **Technology**: Next.js, React, TypeScript, Tailwind CSS
- **Interfaces**: REST API calls only
- **Constraints**: No business logic, no direct database access

### Backend Module
- **Responsibility**: Business logic, API endpoints, data orchestration
- **Technology**: FastAPI, Python, Pydantic
- **Interfaces**: REST API, Supabase, ML services
- **Sub-modules**:
  - Auth Module: Authentication and authorization
  - Sales Service: Sales data queries and aggregations
  - Forecast Service: Forecast generation and retrieval

### Data Module
- **Responsibility**: ETL pipelines, data validation, preprocessing
- **Technology**: Python, pandas, Great Expectations
- **Interfaces**: Raw data sources, Supabase database
- **Output**: Cleaned data ready for analysis and ML

### ML Module
- **Responsibility**: Model training, evaluation, inference
- **Technology**: Python, scikit-learn, Prophet, XGBoost
- **Interfaces**: Data module, Backend API
- **Output**: Trained models and prediction endpoints

### Supabase Module
- **Responsibility**: Data persistence, authentication, row-level security
- **Technology**: PostgreSQL, Supabase Auth, RLS policies
- **Interfaces**: Backend API, data ingestion scripts

### Infrastructure Module
- **Responsibility**: Deployment, CI/CD, containerization
- **Technology**: Docker, GitHub Actions
- **Interfaces**: All modules

## Why Modular Monolith

A **modular monolith** architecture is chosen over microservices for this project because:

1. **Thesis Context**: The scope is well-defined and manageable as a single deployable unit
2. **Development Speed**: Easier to develop, test, and debug without distributed system complexity
3. **Cost**: Lower operational overhead for a single-tenant application
4. **Maintainability**: Clear module boundaries provide the benefits of service-oriented design without the operational burden
5. **Evolution Ready**: Can be split into microservices later if scale demands it
6. **Data Integrity**: Single database simplifies transactions and consistency

The monolith is **modular** because:
- Each module (frontend, backend, data, ml) has well-defined interfaces
- Modules can be developed and tested independently
- Clear separation of concerns with minimal coupling
- Easy to reason about and navigate the codebase

## Role of Supabase

Supabase serves as the **foundation layer** providing:

- **PostgreSQL Database**: Persistent storage for all application data
- **Authentication**: User authentication and session management via Supabase Auth
- **Row-Level Security (RLS)**: Fine-grained access control at the database level
- **Real-time Capabilities**: (Optional future feature) Real-time data subscriptions
- **Type Safety**: Automatic TypeScript type generation from database schema

Supabase is used as a managed service rather than self-hosted PostgreSQL to:
- Reduce infrastructure setup time
- Leverage built-in authentication and RLS
- Enable rapid development with pre-built features
- Reduce maintenance burden

## Role of Backend REST API

The **FastAPI backend** serves as the central business logic hub:

- **API Gateway**: Single entry point for all frontend requests
- **Business Logic Enforcement**: Ensures all business rules are consistently applied
- **Orchestration**: Coordinates calls to database, ML services, and external APIs
- **Validation**: Input validation using Pydantic models
- **Authentication Integration**: Validates JWT tokens from Supabase Auth
- **Error Handling**: Centralized error handling and consistent error responses

Example API endpoints (to be implemented in Phase 4):
- `GET /api/v1/stores` - List all stores
- `GET /api/v1/sales` - Query sales data
- `POST /api/v1/forecasts` - Generate sales forecast
- `GET /api/v1/forecasts/{id}` - Retrieve forecast results

## Role of Data and ML Layers

### Data Layer (data/)

The data layer handles **ETL and data quality**:

1. **Ingestion**: Load Rossmann Store Sales dataset from source
2. **Validation**: Verify data quality (missing values, outliers, consistency)
3. **Preprocessing**: Clean and transform data for analysis and ML
4. **Loading**: Insert processed data into Supabase database

### ML Layer (ml/)

The ML layer handles **forecasting model development**:

1. **Feature Engineering**: Create features from raw data (lagged values, moving averages, seasonal indicators)
2. **Model Training**: Train and evaluate forecasting models (Prophet, XGBoost, ARIMA)
3. **Model Selection**: Choose best-performing model per store segment
4. **Inference**: Generate predictions via API endpoints
5. **Monitoring**: Track model performance and retrain as needed

The ML layer is **separated** from the backend to:
- Enable independent development and experimentation
- Keep model training pipelines separate from serving infrastructure
- Allow for A/B testing of different models
- Support offline batch training with online inference

## Data Flow

```
1. Data Ingestion (Phase 2)
   Raw Kaggle Data → Data Pipelines → Supabase

2. Model Training (Phase 5)
   Supabase → Feature Engineering → Model Training → Trained Models

3. API Request (Phase 6+)
   Frontend → Backend → ML Service → Supabase → Backend → Frontend
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Security Boundary                    │
│                                                          │
│  ┌──────────┐    JWT    ┌──────────────────────────┐   │
│  │ Frontend │ ────────► │       Backend API        │   │
│  └──────────┘           └──────────┬───────────────┘   │
│                                     │                   │
│                            ┌────────▼────────┐        │
│                            │  Supabase RLS   │        │
│                            └────────┬────────┘        │
│                                     │                  │
│                            ┌────────▼────────┐        │
│                            │   PostgreSQL    │        │
│                            └─────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

- All API requests are authenticated via Supabase JWT
- Row-Level Security ensures users only see their data
- No direct database access from frontend
- ML services called via internal, authenticated endpoints
