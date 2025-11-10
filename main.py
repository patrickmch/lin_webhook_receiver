import logging
from datetime import datetime
from typing import Optional
import json

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import ValidationError

import config
import database
from database import get_db, init_db
from models import (
    HeyreachWebhook,
    HealthResponse,
    StatsResponse,
    ProspectsListResponse,
    ProspectDetailResponse,
    EventsListResponse,
    ProspectResponse,
    EventResponse,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LinkedIn Webhook Tracker",
    description="Receives and tracks Heyreach webhooks for LinkedIn outreach",
    version="1.0.0",
)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Application started")


# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "LinkedIn Webhook Tracker API",
        "docs": "/docs",
        "health": "/health",
    }


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Check if system is running and database is accessible"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        database_status = "error"

    return HealthResponse(
        status="ok",
        database=database_status,
        timestamp=datetime.utcnow(),
    )


# Webhook receiver endpoint
@app.post("/webhooks/heyreach")
async def receive_heyreach_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Receive webhooks from Heyreach and process them.
    Always returns 200 OK, even if there's an error (errors are logged).
    """
    try:
        # Get raw body first
        raw_body = await request.body()
        body_str = raw_body.decode('utf-8')

        # Log the raw payload for debugging
        logger.info(f"Received webhook - Raw body: {body_str}")

        # Parse JSON
        try:
            body_json = json.loads(body_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {"status": "error", "message": "Invalid JSON"}

        # Validate against our model
        try:
            webhook = HeyreachWebhook(**body_json)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            logger.error(f"Received data: {json.dumps(body_json, indent=2)}")
            return {"status": "error", "message": "Validation failed", "details": str(e)}

        logger.info(f"Webhook validated: {webhook.event_type} for lead {webhook.lead.id}")

        # Get or create prospect (use profile_url if available, otherwise use lead id)
        linkedin_url = webhook.lead.profile_url or f"heyreach_lead_{webhook.lead.id}"

        prospect = database.get_or_create_prospect(
            db=db,
            linkedin_url=linkedin_url,
            heyreach_lead_id=webhook.lead.id,
            first_name=webhook.lead.first_name,
            last_name=webhook.lead.last_name,
            company=webhook.lead.company_name,
            title=webhook.lead.position,
            email=webhook.lead.email_address,
        )

        # Create event record
        database.create_event(
            db=db,
            prospect_id=prospect.id,
            event_type=webhook.event_type,
            heyreach_lead_id=webhook.lead.id,
            raw_payload=body_str,
        )

        # Update prospect status based on event type
        database.update_prospect_status(
            db=db,
            prospect=prospect,
            event_type=webhook.event_type,
        )

        logger.info(f"Successfully processed webhook: {webhook.event_type}")

        return {"status": "success", "message": "Webhook processed"}

    except Exception as e:
        # Log error but still return 200 OK
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": "Webhook logged with error"}


# Stats endpoint
@app.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get overall statistics"""
    stats = database.get_stats(db)
    return StatsResponse(**stats)


# List prospects endpoint
@app.get("/prospects", response_model=ProspectsListResponse)
def list_prospects(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """List all prospects with optional filtering"""
    prospects, total = database.get_prospects(db, status=status, limit=limit, offset=offset)

    return ProspectsListResponse(
        prospects=[ProspectResponse.model_validate(p) for p in prospects],
        total=total,
    )


# Get single prospect endpoint
@app.get("/prospects/{prospect_id}", response_model=ProspectDetailResponse)
def get_prospect(prospect_id: int, db: Session = Depends(get_db)):
    """Get single prospect with all their events"""
    prospect = database.get_prospect_by_id(db, prospect_id)

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    events = database.get_events_for_prospect(db, prospect_id)

    return ProspectDetailResponse(
        prospect=ProspectResponse.model_validate(prospect),
        events=[EventResponse.model_validate(e) for e in events],
    )


# List events endpoint
@app.get("/events", response_model=EventsListResponse)
def list_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=500, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
):
    """List recent events with optional filtering"""
    events, total = database.get_events(db, event_type=event_type, limit=limit, offset=offset)

    return EventsListResponse(
        events=[EventResponse.model_validate(e) for e in events],
        total=total,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
