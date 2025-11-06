from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# Webhook payload models
class HeyreachLead(BaseModel):
    id: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    linkedInProfileUrl: str
    email: Optional[str] = None


class HeyreachCampaign(BaseModel):
    id: str
    name: str


class HeyreachWebhook(BaseModel):
    event: str
    lead: HeyreachLead
    campaign: Optional[HeyreachCampaign] = None
    timestamp: str


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
