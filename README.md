# Analytical Platform for an Online Store with Sales Forecasting

## Project Description

A comprehensive analytical platform for retail stores that provides sales forecasting, performance analytics, and inventory insights. The platform leverages machine learning to predict future sales based on historical data, store characteristics, and seasonal patterns, enabling data-driven decision making for inventory management and promotional planning.

## Thesis Modules

- **Data Engineering**: ETL pipelines for Rossmann Store Sales dataset, data quality validation, and preprocessing
- **Machine Learning**: Time series forecasting models (ARIMA, Prophet, XGBoost), feature engineering, and model evaluation
- **Backend Development**: REST API for data access, forecast generation, and analytics queries
- **Frontend Development**: Interactive dashboard for visualizing forecasts, trends, and store performance

## Dataset

**Rossmann Store Sales** - A popular Kaggle dataset containing historical sales data for 1,115 Rossmann stores with features including:
- Store types and assortments
- Competitor information
- Holidays and promotional events
- Seasonal and temporal patterns

## High-Level Architecture

The platform follows a **headless modular monolith** architecture:

```
┌─────────────┐
│   Frontend  │  (React/Next.js - Presentation Layer)
└──────┬──────┘
       │ REST API
┌──────▼─────────────────────────────────┐
│            Backend                     │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │ Auth    │ │ Sales   │ │ Forecast │ │
│  │ Module  │ │ Service │ │ Service  │ │
│  └─────────┘ └─────────┘ └──────────┘ │
└──────┬────────────────────────────────┘
       │
┌──────▼──────────┐    ┌──────────────────┐
│     Supabase    │    │   ML Services    │
│  (PostgreSQL +  │◄───┤  (Model Inference)│
│   Auth + RLS)   │    └──────────────────┘
└─────────────────┘
```

## Planned Stack

| Layer | Technology |
|-------|-----------|
| Database | Supabase (PostgreSQL + Auth + RLS) |
| Backend | FastAPI (Python) |
| ML/Data | Python (pandas, scikit-learn, prophet, xgboost) |
| Frontend | Next.js 14+ with TypeScript |
| Infrastructure | Docker, GitHub Actions |

## Development Phases

1. **Phase 1** — Repository Foundation (Current)
2. **Phase 2** — Data Ingestion & Processing
3. **Phase 3** — Database & Authentication Setup
4. **Phase 4** — Core Backend API
5. **Phase 5** — ML Model Development
6. **Phase 6** — ML Model Integration
7. **Phase 7** — Frontend Dashboard
8. **Phase 8** — Production Deployment

## Repository Structure

```
DIPLOMA/
├── frontend/           # Next.js frontend application
├── backend/            # FastAPI backend services
├── data/               # Data pipelines and ETL scripts
├── ml/                 # ML models, training, and inference
├── docs/               # Architecture and technical documentation
├── infra/              # Infrastructure as code (Docker, CI/CD)
├── specs/              # Feature specifications and scope
├── supabase/           # Supabase migrations and functions
├── .github/workflows/  # CI/CD pipelines
├── README.md
├── AGENTS.md
└── .gitignore
```

## Getting Started

*See individual module READMEs for setup instructions (coming in Phase 2+).*

---

**Status**: Phase 1 — Repository Foundation (In Progress)
