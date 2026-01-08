# Jira Microlab Automation

**In collaboration with Prodius Enterprise**

A full-stack application for automated Jira issue analysis and feedback, powered by DSPy and AI. The system evaluates Jira issues against customizable rubrics and provides actionable, AI-powered feedback to improve issue quality.

**Author:** Cristian Prodius

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
  - [System Architecture](#system-architecture)
  - [Authentication Flow](#authentication-flow)
  - [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start with Docker](#quick-start-with-docker)
  - [Manual Setup](#manual-setup)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Jira Microlab Automation is a production-ready platform that helps development teams improve their Jira issue quality through:

- **Automated Analysis**: Evaluates issues against customizable rubric criteria
- **AI-Powered Feedback**: Uses DSPy with LLMs (GPT-4, Claude) for intelligent suggestions
- **Real-time Updates**: WebSocket-based progress tracking for analysis jobs
- **Multi-channel Notifications**: Telegram bot integration for alerts
- **Secure Authentication**: HTTP-only cookie-based JWT authentication

---

## Features

| Feature | Description |
|---------|-------------|
| **Rubric-Based Scoring** | Deterministic evaluation across 7+ criteria with customizable weights |
| **AI Critique** | DSPy-powered analysis with GPT-4 or Claude |
| **Batch Analysis** | Process multiple issues with real-time progress updates |
| **Custom Rubrics** | Create and customize evaluation rules per user |
| **Telegram Notifications** | Receive analysis results via Telegram bot |
| **WebSocket Updates** | Real-time progress tracking during analysis |
| **Feedback History** | Track all previous analyses with full audit trail |
| **Secure Auth** | HTTP-only cookies, encrypted credential storage |

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Jira Microlab Automation                                │
│                      In collaboration with Prodius Enterprise                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Browser      │     │   Next.js       │     │    FastAPI      │
│    Client       │◄───►│   Frontend      │◄───►│    Backend      │
│                 │     │   (Port 3000)   │     │   (Port 8000)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               │   API Proxy Route      │
                               │   (Cookie Forwarding)  │
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  HTTP-only      │     │   PostgreSQL    │
                        │  Cookies        │     │   Database      │
                        │  (JWT Tokens)   │     │   (Port 5432)   │
                        └─────────────────┘     └─────────────────┘
                                                       │
                                                       │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Jira Cloud    │◄────│   DSPy +        │◄────│     Redis       │
│   REST API      │     │   LLM Provider  │     │   (Jobs Queue)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Telegram      │
                        │   Bot API       │
                        └─────────────────┘
```

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (Next.js 16)                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │   Auth Pages    │  │   Dashboard     │  │   Settings      │                 │
│  │   - Login       │  │   - Overview    │  │   - Profile     │                 │
│  │   - Register    │  │   - Analytics   │  │   - Rubrics     │                 │
│  │                 │  │   - Issues      │  │   - Jira Creds  │                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                          │
│           └────────────────────┼────────────────────┘                          │
│                                │                                               │
│                    ┌───────────┴───────────┐                                   │
│                    │   API Proxy Route     │                                   │
│                    │   /api/[...path]      │                                   │
│                    │   (Cookie Forwarding) │                                   │
│                    └───────────┬───────────┘                                   │
│                                │                                               │
└────────────────────────────────┼───────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Backend (FastAPI)                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │   Auth Router   │  │  Issues Router  │  │ Feedback Router │                 │
│  │   /api/v1/auth  │  │  /api/v1/issues │  │ /api/v1/feedback│                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                          │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐                 │
│  │ Rubrics Router  │  │Telegram Router  │  │ WebSocket Router│                 │
│  │ /api/v1/rubrics │  │/api/v1/telegram │  │   /api/v1/ws    │                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                          │
│           └────────────────────┼────────────────────┘                          │
│                                │                                               │
│                    ┌───────────┴───────────┐                                   │
│                    │      Services         │                                   │
│                    │  - AuthService        │                                   │
│                    │  - IssuesService      │                                   │
│                    │  - FeedbackPipeline   │                                   │
│                    │  - RubricEvaluator    │                                   │
│                    └───────────────────────┘                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        Secure Cookie-Based Authentication                       │
└─────────────────────────────────────────────────────────────────────────────────┘

  Browser                    Next.js Frontend              FastAPI Backend
     │                              │                              │
     │  1. POST /auth/login         │                              │
     │  {email, password}           │                              │
     ├─────────────────────────────►│                              │
     │                              │  2. Proxy to backend         │
     │                              │  (forward cookies)           │
     │                              ├─────────────────────────────►│
     │                              │                              │
     │                              │  3. Validate credentials     │
     │                              │     Generate JWT tokens      │
     │                              │                              │
     │                              │  4. Set-Cookie:              │
     │                              │     access_token=xxx         │
     │                              │     refresh_token=xxx        │
     │                              │     (HttpOnly, Secure)       │
     │                              │◄─────────────────────────────┤
     │                              │                              │
     │  5. Set-Cookie forwarded     │                              │
     │     to browser               │                              │
     │◄─────────────────────────────┤                              │
     │                              │                              │
     │  6. Subsequent requests      │                              │
     │     include cookies          │                              │
     │     automatically            │                              │
     ├─────────────────────────────►│                              │
     │                              │  7. Forward with Cookie      │
     │                              │     header                   │
     │                              ├─────────────────────────────►│
     │                              │                              │
     │                              │  8. Validate JWT from cookie │
     │                              │     Return protected data    │
     │                              │◄─────────────────────────────┤
     │◄─────────────────────────────┤                              │
     │                              │                              │

Security Features:
┌────────────────────────────────────────────────────────────────────────────────┐
│  • HTTP-only cookies: Cannot be accessed by JavaScript (XSS protection)        │
│  • Secure flag: Only sent over HTTPS in production                            │
│  • SameSite=Lax: CSRF protection                                              │
│  • Server-side proxy: Backend URL never exposed to browser                     │
│  • No localStorage: Tokens never stored in browser-accessible storage          │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow - Issue Analysis

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Issue Analysis Pipeline                                │
└─────────────────────────────────────────────────────────────────────────────────┘

User Request                     Processing                          Output
────────────                     ──────────                          ──────

POST /api/v1/feedback/analyze
     │
     ▼
┌───────────────────┐
│ 1. Validate User  │
│    & Credentials  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐    ┌─────────────────┐
│ 2. Fetch Issues   │───►│   Jira Cloud    │
│    from Jira      │    │   REST API      │
└─────────┬─────────┘    └─────────────────┘
          │
          ▼
┌───────────────────┐
│ 3. For Each Issue │
└─────────┬─────────┘
          │
          ├──────────────────────────────────────────┐
          │                                          │
          ▼                                          ▼
┌───────────────────┐                    ┌───────────────────┐
│ 4. Rubric         │                    │ 5. AI Analysis    │
│    Evaluation     │                    │    (DSPy + LLM)   │
│                   │                    │                   │
│ • Title Clarity   │                    │ • Critique        │
│ • Description     │                    │ • Suggestions     │
│ • Acceptance Crit │                    │ • Improved AC     │
│ • Ambiguous Terms │                    │                   │
│ • Estimate        │                    │                   │
│ • Labels          │                    │                   │
│ • Scope Clarity   │                    │                   │
└─────────┬─────────┘                    └─────────┬─────────┘
          │                                        │
          └──────────────────┬─────────────────────┘
                             │
                             ▼
                  ┌───────────────────┐
                  │ 6. Combine Scores │
                  │    Build Feedback │
                  └─────────┬─────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Save to DB     │ │  WebSocket      │ │  Telegram       │
│  (History)      │ │  Progress       │ │  Notification   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Database Schema (PostgreSQL)                          │
└─────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────┐
│          users            │
├───────────────────────────┤
│ id              PK        │
│ email           UNIQUE    │───────────────────────────────────────┐
│ hashed_password           │                                       │
│ full_name                 │                                       │
│ is_active                 │                                       │
│ is_superuser              │                                       │
│ created_at                │                                       │
│ updated_at                │                                       │
└───────────────────────────┘                                       │
         │                                                          │
         │ 1:1                                                      │
         ▼                                                          │
┌───────────────────────────┐                                       │
│    jira_credentials       │                                       │
├───────────────────────────┤                                       │
│ id              PK        │                                       │
│ user_id         FK ───────┼───────────────────────────────────────┤
│ base_url                  │                                       │
│ email                     │                                       │
│ encrypted_api_token       │  (Fernet encrypted)                   │
│ is_valid                  │                                       │
│ last_tested_at            │                                       │
│ created_at                │                                       │
│ updated_at                │                                       │
└───────────────────────────┘                                       │
                                                                    │
┌───────────────────────────┐                                       │
│   telegram_user_links     │                                       │
├───────────────────────────┤                                       │
│ id              PK        │                                       │
│ user_id         FK ───────┼───────────────────────────────────────┤
│ telegram_chat_id UNIQUE   │                                       │
│ telegram_username         │                                       │
│ is_verified               │                                       │
│ verification_code         │                                       │
│ verification_expires_at   │                                       │
│ notifications_enabled     │                                       │
│ created_at                │                                       │
└───────────────────────────┘                                       │
                                                                    │
┌───────────────────────────┐                                       │
│     refresh_tokens        │                                       │
├───────────────────────────┤                                       │
│ id              PK        │                                       │
│ user_id         FK ───────┼───────────────────────────────────────┤
│ token           UNIQUE    │                                       │
│ expires_at                │                                       │
│ revoked                   │                                       │
│ created_at                │                                       │
└───────────────────────────┘                                       │
                                                                    │
┌───────────────────────────┐                                       │
│   user_rubric_configs     │                                       │
├───────────────────────────┤                                       │
│ id              PK        │◄──────────────────────────────────────┤
│ user_id         FK ───────┼───────────────────────────────────────┤
│ name                      │                                       │
│ is_default                │                                       │
│ min_description_words     │                                       │
│ require_acceptance_criteria│                                      │
│ allowed_labels   JSON     │                                       │
│ created_at                │                                       │
│ updated_at                │                                       │
└───────────────────────────┘                                       │
         │                                                          │
         │ 1:N                                                      │
         ▼                                                          │
┌───────────────────────────┐     ┌───────────────────────────┐     │
│      rubric_rules         │     │    ambiguous_terms        │     │
├───────────────────────────┤     ├───────────────────────────┤     │
│ id              PK        │     │ id              PK        │     │
│ config_id       FK        │     │ config_id       FK        │     │
│ rule_id                   │     │ term                      │     │
│ weight                    │     └───────────────────────────┘     │
│ is_enabled                │                                       │
│ thresholds      JSON      │                                       │
└───────────────────────────┘                                       │
                                                                    │
┌───────────────────────────┐                                       │
│    feedback_history       │                                       │
├───────────────────────────┤                                       │
│ id              PK        │                                       │
│ user_id         FK ───────┼───────────────────────────────────────┤
│ issue_key       INDEX     │                                       │
│ content_hash              │  (SHA256 for idempotency)             │
│ score                     │                                       │
│ emoji                     │                                       │
│ overall_assessment TEXT   │                                       │
│ strengths       JSON      │                                       │
│ improvements    JSON      │                                       │
│ suggestions     JSON      │                                       │
│ rubric_breakdown JSON     │                                       │
│ improved_ac     TEXT      │                                       │
│ resources       JSON      │                                       │
│ issue_summary             │                                       │
│ issue_type                │                                       │
│ issue_status              │                                       │
│ assignee                  │                                       │
│ labels          JSON      │                                       │
│ was_posted_to_jira        │                                       │
│ jira_comment_id           │                                       │
│ was_sent_to_telegram      │                                       │
│ was_sent_to_slack         │                                       │
│ created_at      INDEX     │                                       │
└───────────────────────────┘                                       │
                                                                    │
┌───────────────────────────┐                                       │
│      analysis_jobs        │                                       │
├───────────────────────────┤                                       │
│ id              PK        │                                       │
│ job_id          UNIQUE    │  (UUID)                               │
│ user_id         FK ───────┼───────────────────────────────────────┘
│ jql             TEXT      │
│ max_issues                │
│ dry_run                   │
│ post_to_jira              │
│ send_telegram             │
│ rubric_config_id FK       │
│ status          INDEX     │  (pending/running/completed/failed)
│ total_issues              │
│ processed_issues          │
│ failed_issues             │
│ current_issue_key         │
│ average_score             │
│ lowest_score              │
│ highest_score             │
│ started_at                │
│ completed_at              │
│ error_message   TEXT      │
│ created_at                │
└───────────────────────────┘
```

### Table Details

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | email, hashed_password, is_active |
| `jira_credentials` | Encrypted Jira API tokens | encrypted_api_token (Fernet) |
| `telegram_user_links` | Telegram bot linking | telegram_chat_id, verification_code |
| `refresh_tokens` | JWT refresh tokens | token, expires_at, revoked |
| `user_rubric_configs` | Custom rubric configurations | name, min_description_words |
| `rubric_rules` | Individual rule weights/thresholds | rule_id, weight, thresholds |
| `ambiguous_terms` | User-defined vague terms | term |
| `feedback_history` | Analysis results audit trail | issue_key, score, rubric_breakdown |
| `analysis_jobs` | Batch job tracking | job_id, status, progress counts |

---

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login (sets HTTP-only cookies) |
| `POST` | `/api/v1/auth/logout` | Logout (clears cookies) |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Get current user profile |
| `PUT` | `/api/v1/auth/me` | Update user profile |
| `PUT` | `/api/v1/auth/password` | Change password |
| `GET` | `/api/v1/auth/ws-token` | Get WebSocket auth token |

### Jira Credentials

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/auth/jira/credentials` | Get credentials status |
| `POST` | `/api/v1/auth/jira/credentials` | Set Jira credentials |
| `DELETE` | `/api/v1/auth/jira/credentials` | Delete credentials |
| `POST` | `/api/v1/auth/jira/test` | Test Jira connection |

### Telegram Integration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/telegram/link` | Get verification code |
| `GET` | `/api/v1/auth/telegram/status` | Get link status |
| `DELETE` | `/api/v1/auth/telegram/link` | Unlink Telegram |
| `PUT` | `/api/v1/auth/telegram/settings` | Update notification settings |

### Issues

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/issues` | Search Jira issues |
| `GET` | `/api/v1/issues/{key}` | Get single issue |

### Feedback & Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/feedback/analyze` | Start analysis job |
| `GET` | `/api/v1/feedback/jobs` | List analysis jobs |
| `GET` | `/api/v1/feedback/jobs/{id}` | Get job status |
| `GET` | `/api/v1/feedback/history` | Get feedback history |

### Rubrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/rubrics` | List user's rubric configs |
| `POST` | `/api/v1/rubrics` | Create rubric config |
| `GET` | `/api/v1/rubrics/{id}` | Get rubric details |
| `PUT` | `/api/v1/rubrics/{id}` | Update rubric |
| `DELETE` | `/api/v1/rubrics/{id}` | Delete rubric |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `WS /api/v1/ws/jobs/{job_id}` | Real-time job progress |

---

## Tech Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API framework |
| **SQLAlchemy** | ORM and database access |
| **PostgreSQL** | Primary database |
| **Redis** | Job queue and caching |
| **Alembic** | Database migrations |
| **Pydantic** | Data validation |
| **python-jose** | JWT handling |
| **cryptography** | Fernet encryption |
| **DSPy** | LLM orchestration |
| **httpx** | Async HTTP client |

### Frontend

| Technology | Purpose |
|------------|---------|
| **Next.js 16** | React framework (App Router) |
| **TypeScript** | Type safety |
| **Tailwind CSS v4** | Styling |
| **shadcn/ui** | UI components |
| **Zustand** | State management |
| **React Hook Form** | Form handling |
| **TanStack Table** | Data tables |
| **Biome** | Linting and formatting |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Multi-container orchestration |
| **Nginx** | Reverse proxy (production) |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Jira Cloud account with API access
- OpenAI or Anthropic API key

### Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone https://github.com/cristianprodius/jira-microlab-automation.git
   cd jira-microlab-automation
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables**
   ```env
   # Database
   DB_USER=jira_feedback
   DB_PASSWORD=your_secure_password
   DB_NAME=jira_feedback

   # Security
   SECRET_KEY=your-super-secret-key-change-in-production
   ENCRYPTION_KEY=your-32-byte-encryption-key

   # Jira (can also be configured per-user in the app)
   JIRA_BASE_URL=https://yourcompany.atlassian.net
   JIRA_EMAIL=your.email@example.com
   JIRA_API_TOKEN=your_api_token

   # LLM
   OPENAI_API_KEY=sk-your-openai-key
   MODEL=gpt-4o-mini

   # Optional: Telegram
   TELEGRAM_BOT_TOKEN=your-bot-token
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/v1/telegram/webhook
   ```

4. **Start the application**
   ```bash
   docker compose up -d
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start server
uvicorn api.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `SECRET_KEY` | JWT signing key | - |
| `ENCRYPTION_KEY` | Fernet key for credential encryption | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |
| `MODEL` | LLM model to use | `gpt-4o-mini` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token expiry | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token expiry | `7` |

### Rubric Criteria

The default rubric evaluates issues across these criteria:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Title Clarity | 1.0x | Clear, actionable, appropriately sized |
| Description Length | 1.2x | Meets minimum word count (default: 20) |
| Acceptance Criteria | 1.5x | Present and testable |
| Ambiguous Terms | 1.0x | Avoids vague language |
| Estimate Present | 0.8x | Has story points or time estimate |
| Labels | 0.7x | Appropriate labeling |
| Scope Clarity | 1.0x | Well-defined boundaries |

---

## Project Structure

```
jiraMicroLabAutomation/
├── backend/
│   ├── api/
│   │   ├── auth/           # Authentication module
│   │   │   ├── models.py   # User, JiraCredential, TelegramLink models
│   │   │   ├── router.py   # Auth endpoints
│   │   │   ├── schemas.py  # Pydantic schemas
│   │   │   ├── security.py # JWT utilities
│   │   │   └── service.py  # Business logic
│   │   ├── db/             # Database configuration
│   │   ├── feedback/       # Feedback history module
│   │   ├── issues/         # Jira issues module
│   │   ├── rubrics/        # Rubric configuration module
│   │   ├── telegram/       # Telegram bot integration
│   │   ├── websocket/      # WebSocket handlers
│   │   ├── config.py       # Settings management
│   │   ├── dependencies.py # FastAPI dependencies
│   │   └── main.py         # Application entry point
│   ├── alembic/            # Database migrations
│   ├── src/                # Core analysis modules
│   │   ├── pipeline.py     # Feedback pipeline
│   │   ├── rubric.py       # Rubric evaluator
│   │   ├── signatures.py   # DSPy signatures
│   │   └── jira_client.py  # Jira API client
│   ├── tests/              # Backend tests
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   │   ├── api/        # API route handlers (proxy)
│   │   │   └── (main)/     # Main app routes
│   │   │       ├── auth/   # Auth pages (login, register)
│   │   │       └── dashboard/  # Dashboard pages
│   │   ├── components/     # Reusable UI components
│   │   ├── lib/            # Utilities and API client
│   │   ├── stores/         # Zustand stores
│   │   └── config/         # App configuration
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

---

## Security

### Authentication Security

- **HTTP-only cookies**: JWT tokens stored in HTTP-only cookies, inaccessible to JavaScript
- **Secure flag**: Cookies only sent over HTTPS in production
- **SameSite=Lax**: CSRF protection
- **Token rotation**: Refresh tokens are single-use

### Credential Storage

- **Fernet encryption**: Jira API tokens encrypted at rest using Fernet symmetric encryption
- **No plaintext storage**: API tokens never stored in plaintext
- **Per-user keys**: Each user's credentials encrypted independently

### Input Validation

- **Pydantic validation**: All API inputs validated with Pydantic schemas
- **SQL injection protection**: SQLAlchemy ORM prevents SQL injection
- **XSS protection**: React's JSX escaping prevents XSS

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Backend
cd backend
pip install -e ".[dev]"
pytest -v

# Frontend
cd frontend
npm install
npm run lint
npm run build
```

---

## License

MIT License - see [LICENSE](LICENSE) file

---

## Support

- **Issues**: https://github.com/cristianprodius/jira-microlab-automation/issues
- **Author**: Cristian Prodius
- **Collaboration**: Prodius Enterprise
