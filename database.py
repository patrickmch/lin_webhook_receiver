from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import config
import logging

logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database models
class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    linkedin_url = Column(Text, unique=True, nullable=False)
    first_name = Column(Text)
    last_name = Column(Text)
    company = Column(Text)
    title = Column(Text)
    email = Column(Text)
    heyreach_lead_id = Column(Text)
    status = Column(Text, default="qualified")
    connection_sent_at = Column(DateTime)
    connection_accepted_at = Column(DateTime)
    blacklisted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_status", "status"),
        Index("idx_heyreach_lead_id", "heyreach_lead_id"),
        Index("idx_linkedin_url", "linkedin_url"),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id"))
    event_type = Column(Text, nullable=False)
    heyreach_lead_id = Column(Text)
    raw_payload = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_event_type", "event_type"),
        Index("idx_prospect_id", "prospect_id"),
        Index("idx_created_at", "created_at"),
    )


def init_db():
    """Create database tables if they don't exist"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database query functions
def get_or_create_prospect(
    db: Session,
    linkedin_url: str,
    heyreach_lead_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    email: Optional[str] = None,
) -> Prospect:
    """Get existing prospect or create new one"""
    prospect = db.query(Prospect).filter(Prospect.linkedin_url == linkedin_url).first()

    if not prospect:
        prospect = Prospect(
            linkedin_url=linkedin_url,
            heyreach_lead_id=heyreach_lead_id,
            first_name=first_name,
            last_name=last_name,
            company=company,
            title=title,
            email=email,
            status="qualified",
        )
        db.add(prospect)
        db.commit()
        db.refresh(prospect)
        logger.info(f"Created new prospect: {linkedin_url}")
    else:
        # Update prospect info if it changed
        updated = False
        if heyreach_lead_id and prospect.heyreach_lead_id != heyreach_lead_id:
            prospect.heyreach_lead_id = heyreach_lead_id
            updated = True
        if first_name and prospect.first_name != first_name:
            prospect.first_name = first_name
            updated = True
        if last_name and prospect.last_name != last_name:
            prospect.last_name = last_name
            updated = True
        if company and prospect.company != company:
            prospect.company = company
            updated = True
        if title and prospect.title != title:
            prospect.title = title
            updated = True
        if email and prospect.email != email:
            prospect.email = email
            updated = True

        if updated:
            prospect.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(prospect)
            logger.info(f"Updated prospect info: {linkedin_url}")

    return prospect


def update_prospect_status(
    db: Session,
    prospect: Prospect,
    event_type: str,
) -> None:
    """Update prospect status based on event type"""
    now = datetime.utcnow()

    if event_type == "connection_request_sent":
        prospect.status = "connection_sent"
        prospect.connection_sent_at = now
        prospect.updated_at = now
        db.commit()
        logger.info(f"Updated prospect {prospect.id} status to connection_sent")

    elif event_type == "connection_request_accepted":
        prospect.status = "connected"
        prospect.connection_accepted_at = now
        prospect.updated_at = now
        db.commit()
        logger.info(f"Updated prospect {prospect.id} status to connected")


def create_event(
    db: Session,
    prospect_id: Optional[int],
    event_type: str,
    heyreach_lead_id: str,
    raw_payload: str,
) -> Event:
    """Create new event record"""
    event = Event(
        prospect_id=prospect_id,
        event_type=event_type,
        heyreach_lead_id=heyreach_lead_id,
        raw_payload=raw_payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"Created event: {event_type} for prospect {prospect_id}")
    return event


def get_prospects(
    db: Session,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[Prospect], int]:
    """Get prospects with optional filtering"""
    query = db.query(Prospect)

    if status:
        query = query.filter(Prospect.status == status)

    total = query.count()
    prospects = query.order_by(Prospect.created_at.desc()).offset(offset).limit(limit).all()

    return prospects, total


def get_prospect_by_id(db: Session, prospect_id: int) -> Optional[Prospect]:
    """Get single prospect by ID"""
    return db.query(Prospect).filter(Prospect.id == prospect_id).first()


def get_events_for_prospect(db: Session, prospect_id: int) -> List[Event]:
    """Get all events for a prospect"""
    return db.query(Event).filter(Event.prospect_id == prospect_id).order_by(Event.created_at.asc()).all()


def get_events(
    db: Session,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[List[Event], int]:
    """Get events with optional filtering"""
    query = db.query(Event)

    if event_type:
        query = query.filter(Event.event_type == event_type)

    total = query.count()
    events = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()

    return events, total


def get_stats(db: Session) -> dict:
    """Calculate statistics"""
    total_prospects = db.query(Prospect).count()

    # Count by status
    status_counts = {}
    for status in ["qualified", "connection_sent", "connected", "expired", "blacklisted"]:
        count = db.query(Prospect).filter(Prospect.status == status).count()
        status_counts[status] = count

    total_events = db.query(Event).count()

    # Calculate acceptance rate
    connection_sent = status_counts.get("connection_sent", 0) + status_counts.get("connected", 0)
    connected = status_counts.get("connected", 0)
    acceptance_rate = connected / connection_sent if connection_sent > 0 else 0.0

    # Get last webhook timestamp
    last_event = db.query(Event).order_by(Event.created_at.desc()).first()
    last_webhook_received = last_event.created_at if last_event else None

    return {
        "total_prospects": total_prospects,
        "by_status": status_counts,
        "total_events": total_events,
        "acceptance_rate": acceptance_rate,
        "last_webhook_received": last_webhook_received,
    }
