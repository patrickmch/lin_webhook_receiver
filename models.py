from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# Webhook payload models
class HeyreachList(BaseModel):
    id: int
    name: str
    custom_fields: Optional[Dict] = None


class HeyreachLead(BaseModel):
    id: str
    profile_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    position: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    about: Optional[str] = None
    email_address: Optional[str] = None
    tags: Optional[List[str]] = None
    lists: Optional[List[HeyreachList]] = None


class HeyreachSender(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email_address: Optional[str] = None
    profile_url: Optional[str] = None


class HeyreachCampaign(BaseModel):
    id: int
    name: str
    status: Optional[str] = None


class HeyreachWebhook(BaseModel):
    event_type: str
    lead: HeyreachLead
    campaign: Optional[HeyreachCampaign] = None
    sender: Optional[HeyreachSender] = None
    connection_message: Optional[str] = None
    timestamp: str
    correlation_id: Optional[str] = None


# API response models
class ProspectResponse(BaseModel):
    id: int
    linkedin_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    heyreach_lead_id: Optional[str] = None
    status: str
    connection_sent_at: Optional[datetime] = None
    connection_accepted_at: Optional[datetime] = None
    blacklisted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: int
    prospect_id: Optional[int] = None
    event_type: str
    heyreach_lead_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProspectsListResponse(BaseModel):
    prospects: List[ProspectResponse]
    total: int


class ProspectDetailResponse(BaseModel):
    prospect: ProspectResponse
    events: List[EventResponse]


class EventsListResponse(BaseModel):
    events: List[EventResponse]
    total: int


class StatsResponse(BaseModel):
    total_prospects: int
    by_status: Dict[str, int]
    total_events: int
    acceptance_rate: float
    last_webhook_received: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
