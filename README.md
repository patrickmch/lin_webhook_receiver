# LinkedIn Webhook Tracker

Simple system to receive and track Heyreach webhooks for LinkedIn outreach.

## Overview

This FastAPI application receives webhooks from Heyreach (LinkedIn outreach tool) and tracks:
- Connection requests sent
- Connection requests accepted
- Message replies received
- Prospect status changes

## Local Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create environment file

```bash
cp .env.example .env
```

Edit `.env` if you want to customize settings (defaults work fine for local development).

### 3. Create database

```bash
python -c "from database import init_db; init_db()"
```

This creates a `prospects.db` SQLite file in your project directory.

### 4. Run locally

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### 5. Test it

```bash
# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

## Deploy to Railway

Railway is a simple platform-as-a-service that auto-deploys from GitHub (~$5/month).

### 1. Push code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Sign up/login (can use GitHub account)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Railway auto-detects Python and deploys
6. Wait for deployment to complete (~2 minutes)

### 3. Get your Railway URL

1. In Railway dashboard, click on your project
2. Go to "Settings" → "Domains"
3. Click "Generate Domain"
4. Copy the URL (e.g., `https://your-app.up.railway.app`)

### 4. Test your deployed app

```bash
curl https://your-app.up.railway.app/health
curl https://your-app.up.railway.app/stats
```

## Configure Heyreach

### 1. Set up webhook in Heyreach

1. Log into Heyreach
2. Go to **Settings** → **Integrations** → **Webhooks**
3. Click "Add New Webhook"
4. Configure:
   - **Webhook URL**: `https://your-app.up.railway.app/webhooks/heyreach`
   - **Events to send**:
     - Connection Request Sent
     - Connection Request Accepted
     - Message Reply Received
     - (Select any other events you want to track)
5. Click "Save"

### 2. Test the webhook

Send a test connection request through Heyreach, then check:

```bash
curl https://your-app.up.railway.app/stats
curl https://your-app.up.railway.app/events
```

You should see the webhook event logged!

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/docs` | GET | Interactive API documentation |

### Webhook Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/heyreach` | POST | Receives webhooks from Heyreach |

### Data Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats` | GET | Overall statistics |
| `/prospects` | GET | List all prospects (supports filtering) |
| `/prospects/{id}` | GET | Get single prospect with events |
| `/events` | GET | List recent events (supports filtering) |

## Usage Examples

### View overall statistics

```bash
curl https://your-app.up.railway.app/stats
```

Response:
```json
{
  "total_prospects": 50,
  "by_status": {
    "qualified": 10,
    "connection_sent": 20,
    "connected": 15,
    "expired": 3,
    "blacklisted": 2
  },
  "total_events": 120,
  "acceptance_rate": 0.75,
  "last_webhook_received": "2025-11-05T10:30:00Z"
}
```

### List all prospects

```bash
# All prospects
curl https://your-app.up.railway.app/prospects

# Filter by status
curl https://your-app.up.railway.app/prospects?status=connected

# Pagination
curl https://your-app.up.railway.app/prospects?limit=10&offset=20
```

### Get single prospect details

```bash
curl https://your-app.up.railway.app/prospects/1
```

Response includes prospect info and all their events:
```json
{
  "prospect": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "company": "Acme Corp",
    "title": "VP of Operations",
    "linkedin_url": "https://linkedin.com/in/johndoe",
    "status": "connected",
    "connection_sent_at": "2025-11-01T10:00:00Z",
    "connection_accepted_at": "2025-11-02T14:30:00Z"
  },
  "events": [
    {
      "id": 1,
      "event_type": "connection_request_sent",
      "created_at": "2025-11-01T10:00:00Z"
    },
    {
      "id": 2,
      "event_type": "connection_request_accepted",
      "created_at": "2025-11-02T14:30:00Z"
    }
  ]
}
```

### List recent events

```bash
# All events
curl https://your-app.up.railway.app/events

# Filter by event type
curl https://your-app.up.railway.app/events?event_type=connection_request_accepted

# Pagination
curl https://your-app.up.railway.app/events?limit=50&offset=100
```

## Testing the Webhook Locally

You can test the webhook endpoint locally with a fake webhook:

```bash
curl -X POST http://localhost:8000/webhooks/heyreach \
  -H "Content-Type: application/json" \
  -d '{
    "event": "connection_request_accepted",
    "lead": {
      "id": "test_123",
      "firstName": "John",
      "lastName": "Doe",
      "company": "Test Corp",
      "title": "CEO",
      "linkedInProfileUrl": "https://linkedin.com/in/test",
      "email": "john@test.com"
    },
    "timestamp": "2025-11-05T10:30:00Z"
  }'
```

Then check if it worked:

```bash
curl http://localhost:8000/stats
curl http://localhost:8000/prospects
curl http://localhost:8000/events
```

## Database Schema

### prospects table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| linkedin_url | TEXT | LinkedIn profile URL (unique) |
| first_name | TEXT | First name |
| last_name | TEXT | Last name |
| company | TEXT | Company name |
| title | TEXT | Job title |
| email | TEXT | Email address |
| heyreach_lead_id | TEXT | Heyreach lead ID |
| status | TEXT | Current status (qualified, connection_sent, connected, expired, blacklisted) |
| connection_sent_at | DATETIME | When connection request was sent |
| connection_accepted_at | DATETIME | When connection was accepted |
| blacklisted | BOOLEAN | Whether prospect is blacklisted |
| created_at | DATETIME | When record was created |
| updated_at | DATETIME | When record was last updated |

### events table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| prospect_id | INTEGER | Foreign key to prospects table |
| event_type | TEXT | Type of event |
| heyreach_lead_id | TEXT | Heyreach lead ID |
| raw_payload | TEXT | Full webhook payload as JSON |
| created_at | DATETIME | When event was received |

## Monitoring Your System

### Check if webhooks are being received

```bash
curl https://your-app.up.railway.app/stats | jq '.last_webhook_received'
```

### View recent activity

```bash
curl https://your-app.up.railway.app/events?limit=10
```

### Check acceptance rate

```bash
curl https://your-app.up.railway.app/stats | jq '.acceptance_rate'
```

### View Railway logs

1. Go to Railway dashboard
2. Click on your project
3. Go to "Deployments" → Select latest deployment
4. Click "View Logs"

You'll see all webhook events being logged in real-time!

## Troubleshooting

### Webhook not being received

1. Check Heyreach webhook configuration
2. Verify the URL is correct
3. Check Railway logs for errors
4. Test with `curl` to ensure endpoint is accessible

### Database errors

Railway auto-creates SQLite database on first run. If you see database errors:

1. Check Railway logs
2. Ensure database is initialized (happens automatically on startup)
3. Try redeploying on Railway

### Connection issues

Railway apps go to sleep after inactivity. First request may be slow. Subsequent requests will be fast.

## Project Structure

```
linkedin-webhook-tracker/
├── main.py              # FastAPI app with all endpoints
├── database.py          # Database setup and queries
├── models.py            # Pydantic models for requests/responses
├── config.py            # Configuration from environment variables
├── requirements.txt     # Dependencies
├── .env.example         # Template for environment variables
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./prospects.db | Database connection string |
| DEBUG | false | Enable debug mode |
| LOG_LEVEL | info | Logging level (debug, info, warning, error) |
| PORT | 8000 | Port to run on (Railway sets this automatically) |

## What's Next?

This is a foundation for your LinkedIn outreach system. Future enhancements could include:

- Message generation with AI
- Sending messages via Heyreach API
- Cron jobs for expired connection requests
- Blacklist management
- Integration with Claude API for prospect qualification
- Email notifications for important events
- Dashboard UI for viewing prospects

But for now, you have a working webhook receiver and tracking system!

## Support

For issues with:
- **Heyreach**: See [Heyreach webhook docs](https://help.heyreach.io/en/articles/9877965-webhooks)
- **Railway**: See [Railway docs](https://docs.railway.app/)
- **FastAPI**: See [FastAPI docs](https://fastapi.tiangolo.com/)

## License

MIT
