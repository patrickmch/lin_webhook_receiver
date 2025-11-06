# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI application that receives webhooks from Heyreach (LinkedIn outreach tool) and tracks prospect interactions. The system maintains a SQLite database of prospects and events, tracking the lifecycle from initial connection request through acceptance and messaging.

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database (creates prospects.db)
python -c "from database import init_db; init_db()"

# Run development server
uvicorn main:app --reload --port 8000

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Health check
curl http://localhost:8000/health

# Test webhook endpoint
curl -X POST http://localhost:8000/webhooks/heyreach \
  -H "Content-Type: application/json" \
  -d '{"event": "connection_request_sent", "lead": {"id": "test_123", "firstName": "Test", "lastName": "User", "linkedInProfileUrl": "https://linkedin.com/in/test"}, "timestamp": "2025-11-05T10:00:00Z"}'

# View stats
curl http://localhost:8000/stats

# View prospects
curl http://localhost:8000/prospects

# View events
curl http://localhost:8000/events
```

## Architecture

### Core Components

**main.py** - FastAPI application with endpoints:
- `/webhooks/heyreach` (POST) - Webhook receiver that processes Heyreach events
- `/stats` (GET) - Returns aggregated statistics
- `/prospects` (GET) - Lists prospects with filtering and pagination
- `/prospects/{id}` (GET) - Returns single prospect with all events
- `/events` (GET) - Lists events with filtering and pagination
- `/health` (GET) - Health check with database connectivity test

**database.py** - SQLAlchemy models and query functions:
- `Prospect` model - Stores LinkedIn prospects with status tracking
- `Event` model - Stores webhook events linked to prospects
- Query functions handle prospect creation/updates and event logging
- Implements get-or-create pattern for prospect upserts
- Status transitions: qualified → connection_sent → connected

**models.py** - Pydantic models for request/response validation:
- `HeyreachWebhook` - Incoming webhook payload schema
- Response models for API endpoints with proper serialization

**config.py** - Environment configuration using python-dotenv:
- `DATABASE_URL` - SQLite connection string (default: sqlite:///./prospects.db)
- `DEBUG` - Debug mode flag
- `LOG_LEVEL` - Logging verbosity
- `PORT` - Server port (default: 8000)

### Data Flow

1. Heyreach sends webhook → `/webhooks/heyreach` endpoint
2. Webhook validated against `HeyreachWebhook` schema
3. `get_or_create_prospect()` finds or creates prospect by LinkedIn URL
4. `create_event()` logs the webhook event
5. `update_prospect_status()` updates prospect status based on event type
6. Response always returns 200 OK (errors logged but not returned to Heyreach)

### Database Schema

**prospects table:**
- Unique constraint on `linkedin_url` (used for upsert operations)
- Indexed on `status`, `heyreach_lead_id`, `linkedin_url`
- Tracks timestamps for connection_sent and connection_accepted
- Status field: qualified, connection_sent, connected, expired, blacklisted

**events table:**
- Foreign key to prospects table
- Stores raw webhook payload as JSON in `raw_payload`
- Indexed on `event_type`, `prospect_id`, `created_at`

### Key Design Patterns

**Error Handling:** Webhook endpoint returns 200 OK even on errors to prevent Heyreach retries. Errors logged with full stack traces.

**Idempotency:** Prospects identified by LinkedIn URL. Multiple webhooks for same prospect update existing record rather than creating duplicates.

**Audit Trail:** All webhook payloads stored in `raw_payload` field for debugging and historical analysis.

**Status Management:** Prospect status automatically updated based on event types:
- `connection_request_sent` → status: connection_sent
- `connection_request_accepted` → status: connected

## Environment Setup

Copy `.env.example` to `.env` for local development. Defaults are suitable for local use. Railway deployment auto-sets `PORT` environment variable.

## Deployment Notes

Designed for Railway deployment. SQLite database persists in Railway's ephemeral filesystem (consider upgrading to PostgreSQL for production). Application auto-initializes database on startup via the `@app.on_event("startup")` handler.
