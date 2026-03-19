# Research: Sales Forecasting Platform

**Feature**: Sales Forecasting Platform
**Branch**: `001-sales-forecasting-platform`
**Date**: 2026-03-06

## Overview

This document captures research findings and technology decisions for the Sales Forecasting Platform. All decisions are made with the following priorities:
1. Thesis-readiness (academic rigor, documentation quality)
2. Production-minded (maintainable, testable, observable)
3. Small team friendly (minimal operational overhead)
4. MVP-focused (avoid over-engineering)

## Frontend Framework Decision

### Research Question: Next.js App Router vs React + Vite for MVP

| Criterion | Next.js 14+ (App Router) | React + Vite | Winner |
|-----------|----------------------------|---------------|---------|
| **Initial Setup** | Requires more configuration (app router structure) | Simple, fast startup | Vite |
| **Routing** | Built-in file-based routing | Requires React Router | Next.js |
| **API Integration** | Server components reduce client-side complexity | All client-side | Next.js |
| **Type Safety** | Built-in TypeScript support | Requires setup | Tie |
| **Deployment** | Vercel (optimized), or Node.js | Any static hosting | Tie |
| **Learning Curve** | Steeper (server components, app router) | Gentler (standard React) | Vite |
| **Thesis Presentation** | More impressive (full-stack framework) | Appears as basic SPA | Next.js |
| **SEO** | Server-side rendering built-in | Limited (requires SSR setup) | Next.js |
| **Performance** | Server components reduce bundle size | Client-side only | Next.js |
| **Ecosystem** | Rich ecosystem, industry standard | Standard React ecosystem | Next.js |

### Analysis

**Next.js Advantages for This Project**:
- Server Components allow API calls on server, reducing client-side complexity
- Built-in routing eliminates need for additional routing library
- Server-side rendering improves initial load and SEO
- More impressive for thesis presentation (modern, production-grade)
- Stronger industry adoption (Meta, Vercel backing)
- Better long-term viability and skill investment

**React + Vite Advantages for This Project**:
- Faster initial development speed
- Simpler mental model (all client-side)
- Lower learning curve
- Less abstraction overhead

### Decision

**CHOSEN**: Next.js 14+ with App Router

**Rationale**:
1. **Thesis Impact**: Next.js demonstrates fuller-stack knowledge and industry relevance
2. **API Integration**: Server Components simplify backend API calls (authentication header management)
3. **Future-Proof**: Stronger ecosystem and career investment
4. **Performance**: Server-side rendering improves dashboard load times
5. **Headless Alignment**: Server components naturally enforce headless pattern (API calls happen server-side)

**Mitigated Concerns**:
- **Learning Curve**: Well-documented, ample examples for App Router patterns
- **Initial Complexity**: Templates and best practices widely available
- **Deployment**: Vercel provides free tier for academic projects

**Alternative Considered**: React + Vite (rejected for weaker thesis impact and missing server-side benefits)

## Backend Framework Decision

### Research Question: Python Backend Framework

| Criterion | FastAPI | Flask | Django REST | Django Ninja | Winner |
|-----------|----------|--------|--------------|---------------|---------|
| **Type Safety** | Native Pydantic | None | DRF serializers | Native Pydantic | FastAPI/Django Ninja |
| **Async Support** | Native | Via extensions | DRF async limited | Native | FastAPI/Django Ninja |
| **API Documentation** | Auto OpenAPI | Manual | DRF manual | Auto OpenAPI | FastAPI/Django Ninja |
| **Performance** | High (Starlette) | Medium | Medium | High | FastAPI/Django Ninja |
| **Ecosystem** | Growing | Mature | Mature | Newer | Flask/Django |
| **Learning Curve** | Moderate | Low | High | Moderate | Flask |
| **Constitution Requirement** | Specified | No | No | No | FastAPI |

### Decision

**CHOSEN**: FastAPI

**Rationale**:
1. **Constitution Compliance**: Specified in constitution as required technology
2. **Async Native**: Better performance for concurrent forecast requests
3. **Auto Documentation**: OpenAPI/Swagger generation reduces manual work
4. **Type Safety**: Pydantic models align with TypeScript frontend types
5. **Industry Trend**: Modern, gaining adoption for ML backends

**Alternative Considered**: Flask (rejected - no async native, less type-safe), Django REST (rejected - more complexity than needed)

## Database & ORM Decision

### Research Question: Python ORM for FastAPI

| Criterion | SQLAlchemy 2.0 (Async) | Tortoise ORM | Piccolo ORM | Winner |
|-----------|-------------------------|--------------|--------------|---------|
| **Async Native** | Yes | Yes | Yes | Tie |
| **Type Hints** | Full 2.0 | Full | Full | Tie |
| **Maturity** | Very mature | Medium | New | SQLAlchemy |
| **Ecosystem** | Largest | Medium | Small | SQLAlchemy |
| **Alembic Support** | Native | Via extension | Built-in | Tie |
| **Supabase Compatibility** | Via connection pool | Has Supabase client | Built-in Supabase | Piccolo/SQLAlchemy |
| **Learning Curve** | Moderate | Gentle | Gentle | Piccolo/Tortoise |

### Decision

**CHOSEN**: SQLAlchemy 2.0 (Async)

**Rationale**:
1. **Constitution Compliance**: Specified in constitution
2. **Maturity**: Most battle-tested, best long-term investment
3. **Alembic Integration**: Robust migration tooling
4. **Ecosystem**: Largest community, most resources for learning
5. **Future Flexibility**: Can migrate to sync or async as needed

**Supabase Integration**: Use SQLAlchemy async with Supabase connection string (via asyncpg driver)

**Alternative Considered**: Piccolo ORM (rejected - newer, less ecosystem), Tortoise ORM (rejected - less mature)

## ML Framework Decision

### Research Question: Time Series Forecasting Frameworks

| Criterion | Prophet | XGBoost | ARIMA (statsmodels) | Ensemble | Winner |
|-----------|----------|-----------|----------------------|-----------|---------|
| **Ease of Use** | High | Medium | Low | High | Prophet |
| **Seasonality** | Excellent | Manual | Manual | Excellent | Prophet |
| **Trend Handling** | Automatic | Manual | Manual | Automatic | Prophet |
| **Interpretability** | High | Medium | High | Medium | Prophet |
| **Performance** | Medium | High | Medium | High | XGBoost |
| **Features** | Time series only | Any features | Time series only | Time series + features | XGBoost |
| **Thesis Impact** | Industry standard | Industry standard | Academic standard | Industry standard | Ensemble |

### Decision

**CHOSEN**: Ensemble Approach (Prophet + XGBoost)

**Rationale**:
1. **Prophet**: Strong baseline, handles seasonality automatically, high interpretability (good for thesis)
2. **XGBoost**: Feature-based approach, captures complex patterns, high accuracy potential
3. **Ensemble**: Best of both worlds, demonstrates ML sophistication for thesis
4. **Fallback**: Prophet alone if XGBoost fails or overfits
5. **Academic Value**: Comparing multiple methods is thesis-worthy

**Implementation Approach**:
- **Primary Model**: Prophet (Facebook) - automatic trend/seasonality
- **Secondary Model**: XGBoost - feature-based predictions
- **Ensemble**: Weighted average or model selection based on validation performance
- **Baseline**: Historical average for data-insufficient stores

**Alternative Considered**: Single model approach (rejected - less thesis value), LSTM/Deep Learning (rejected - overkill for 6-week forecasts)

## Authentication Strategy

### Research Question: Supabase Auth Integration Pattern

| Pattern | Description | Complexity | Security | Winner |
|----------|---------------|--------------|----------|---------|
| **Client-Side JWT** | Frontend gets JWT from Supabase, passes to backend | Low | Medium | |
| **Server-Side Flow** | Backend validates JWT with Supabase Admin API | Medium | High | Winner |
| **RLS-Only** | Rely entirely on Supabase RLS, backend with service key | Low | High | |
| **Hybrid** | Backend validates JWT, enforces role-based access | Medium | High | |

### Decision

**CHOSEN**: Hybrid Approach (JWT Validation + Role-Based Access Control)

**Rationale**:
1. **Security**: Backend validates every JWT (no trusted client tokens)
2. **Authorization**: Role-based enforcement at backend (admin/analyst/viewer)
3. **RLS Defense**: Row-level security as database layer protection
4. **Audit Logging**: Backend logs all data access with user context
5. **Separation**: Clear separation between client authentication (Supabase) and backend authorization

**Implementation**:
- Frontend: Uses Supabase client for authentication (get JWT)
- Backend: Validates JWT with Supabase, extracts user ID and role
- Database: RLS policies ensure row-level filtering as defense in depth
- Admin Operations: Use Supabase service role key (never exposed to frontend)

## CI/CD Strategy

### Research Question: Graduation Project CI/CD

| Option | Description | Complexity | MVP Fit | Winner |
|---------|---------------|--------------|-----------|---------|
| **Full CD to Production** | Automated deployment on merge | High | Overkill | |
| **Manual Deployment** | Deploy manually when ready | Low | Underkill | |
| **CI + Manual CD** | Tests pass on merge, deploy manually | Medium | Perfect | Winner |
| **Staging + Production** | Two environments, auto-promote | High | Overkill | |

### Decision

**CHOSEN**: CI + Manual CD (Continuous Integration, Manual Continuous Deployment)

**Rationale**:
1. **Academic Context**: Graduation project doesn't need full production automation
2. **Focus on Development**: CI ensures quality, manual CD allows control
3. **Simpler Setup**: One environment reduces complexity
4. **Thesis Documentation**: Manual steps are easier to document for thesis
5. **Risk Mitigation**: Manual approval prevents accidental production changes

**CI Pipeline**:
- On every push: Run linting, formatting checks
- On every PR: Run unit tests, integration tests
- On merge to main: Full test suite, security scan, build artifacts

**CD Process**:
- Developer runs deployment script locally
- Script validates environment, runs migrations
- Docker containers built and pushed (or deployed to Vercel/Render)
- Health checks performed before considering deployment complete

**Alternative Considered**: Full automation (rejected - overkill for graduation project)

## Data Pipeline Strategy

### Research Question: ETL Pattern for Rossmann Dataset

| Pattern | Description | Reproducibility | Performance | Winner |
|----------|---------------|------------------|--------------|---------|
| **One-Time Script** | Script runs once to ingest data | Low | N/A | |
| **Idempotent Pipeline** | Can run multiple times safely | High | Medium | |
| **Streaming Pipeline** | Processes data as it arrives | High | High | |
| **Batch with Checkpoints** | Processes in batches, saves progress | High | High | Winner |

### Decision

**CHOSEN**: Idempotent Pipeline with Checkpoints

**Rationale**:
1. **Reproducibility**: Can re-run pipeline without duplicating data
2. **Thesis Quality**: Documentable, testable pipeline
3. **Error Recovery**: Checkpoints allow resumption from failure
4. **Debugging**: Clear stages with logging at each checkpoint
5. **Quality Control**: Validation at each stage before proceeding

**Pipeline Stages**:
1. **Ingestion**: Load CSV files, validate structure
2. **Quality Check**: Identify missing values, outliers, inconsistencies
3. **Cleaning**: Impute or exclude problematic records
4. **Transformation**: Create derived features, normalize formats
5. **Loading**: Insert into Supabase with batch operations
6. **Verification**: Query back loaded data for integrity checks

**Alternative Considered**: One-time script (rejected - not reproducible, not thesis-worthy)

## KPI Mart Strategy

### Research Question: KPI Calculation and Storage

| Approach | Description | Query Performance | Freshness | Winner |
|-----------|---------------|-------------------|-----------|---------|
| **On-Demand Calculation** | Calculate when requested | Slow | Always fresh | |
| **Pre-Aggregated Tables** | Materialized views or separate tables | Fast | Stale | Winner |
| **Cached On-Demand** | Calculate once, cache results | Fast | TTL-based | |

### Decision

**CHOSEN**: Pre-Aggregated Tables with Refresh Triggers

**Rationale**:
1. **Performance**: Meets NFR-001 (dashboard load < 3s)
2. **Freshness**: Refresh on data update or scheduled refresh
3. **Simplicity**: No caching infrastructure required
4. **Predictability**: Consistent query performance
5. **Thesis Documentability**: Clear data flow to explain

**KPI Tables**:
- `kpi_daily_sales`: Daily aggregations by store
- `kpi_weekly_sales`: Weekly aggregations by store
- `kpi_monthly_sales`: Monthly aggregations by store
- `kpi_store_comparison`: Cross-store metrics for comparison views

**Refresh Strategy**:
- Trigger-based: Refresh when new data ingested
- Scheduled: Nightly refresh for any missed triggers
- Manual: Admin-triggered refresh for corrections

**Alternative Considered**: On-demand calculation (rejected - too slow), Caching (rejected - adds infrastructure complexity)

## Observability Strategy

### Research Question: Logging and Monitoring for Graduation Project

| Aspect | Option | Complexity | MVP Fit | Winner |
|---------|----------|--------------|-----------|---------|
| **Structured Logging** | JSON logs with correlation IDs | Medium | Perfect | Winner |
| **File Logs** | Simple text files | Low | Underkill | |
| **Cloud Monitoring** | Datadog, New Relic | High | Overkill | |
| **Dashboard** | Grafana/Prometheus | Medium | Overkill | |

### Decision

**CHOSEN**: Structured Logging + Simple Metrics Dashboard

**Rationale**:
1. **Constitution Compliance**: Structured logging required
2. **Thesis Quality**: Correlation IDs enable request tracing
3. **Simplicity**: No external services needed
4. **Documentation**: Logs are self-documenting for thesis
5. **Debugging**: Queryable JSON logs vs parsing text

**Implementation**:
- Logging: Python `structlog` or `loguru` with JSON formatting
- Correlation IDs: Generated at API gateway, propagated through all calls
- Metrics: Simple endpoint that returns system health and basic metrics
- Dashboard: Optional - can use Supabase dashboard for simple monitoring

**Alternative Considered**: Full observability stack (rejected - overkill for graduation project)

## Rapidly Changing Tools

### Version-Conscious Decisions

| Tool | Version | Rationale |
|------|---------|------------|
| **Next.js** | 14+ (App Router) | App Router is current stable, Pages Router deprecated |
| **React** | 18+ | Concurrent features, automatic batching |
| **TypeScript** | 5.3+ | Recent type improvements |
| **FastAPI** | 0.104+ | Stable async support |
| **SQLAlchemy** | 2.0+ | Async support is breaking change from 1.x |
| **Pydantic** | 2.0+ | Breaking changes from 1.x, V2 required for FastAPI |
| **Python** | 3.11+ | Modern type hints, performance improvements |
| **Node.js** | 20+ | LTS with modern features |

## Summary of Technology Choices

| Layer | Technology | Version | Rationale |
|--------|-------------|----------|------------|
| **Frontend** | Next.js | 14+ | Server components, SSR, thesis impact |
| **Backend** | FastAPI | 0.104+ | Async, auto docs, type-safe |
| **Database** | PostgreSQL | 15+ | Via Supabase, constitution requirement |
| **ORM** | SQLAlchemy | 2.0+ | Async, mature, constitution requirement |
| **Auth** | Supabase Auth | Current | Constitution requirement, JWT validation |
| **ML Models** | Prophet + XGBoost | Latest | Ensemble approach, thesis value |
| **Data Processing** | pandas | 2.0+ | Industry standard for tabular data |
| **Testing** | pytest + pytest-asyncio | Latest | Async test support |
| **CI** | GitHub Actions | Current | Free, integrated, simple |
| **Deployment** | Docker | Latest | Consistency, reproducibility |

## Unresolved Risks

1. **Model Training Time**: XGBoost on full dataset may exceed 10-minute target. Mitigation: Use sample for development, full dataset for production training.
2. **Supabase Free Tier Limits**: 500MB database limit may be exceeded. Mitigation: Clean test data, optimize indexes, monitor storage.
3. **Forecast Accuracy**: MAPE < 15% target may not be achievable. Mitigation: Document best effort, use ensemble to improve.

## Alternative Research Not Required

Based on project constraints and constitution, the following do not require additional research:
- **Microservices vs Monolith**: Constitution explicitly requires modular monolith
- **Database Choice**: Constitution explicitly requires Supabase/PostgreSQL
- **Authentication Provider**: Constitution explicitly requires Supabase Auth
- **API Style**: Specification and constitution require REST
