#!/usr/bin/env python3
"""
Backfill script to sync connection acceptances from Heyreach to local database.

This script:
1. Fetches all leads from a Heyreach campaign
2. Filters for leads with accepted connections
3. Creates/updates prospect records in our database
4. Adds connection_accepted events for tracking
5. Prints a summary of backfilled records

Usage:
    python backfill_heyreach.py [--campaign-id CAMPAIGN_ID] [--dry-run]

Environment variables required:
    HEYREACH_API_KEY - Your Heyreach API key
    HEYREACH_CAMPAIGN_ID - Default campaign ID (can be overridden with --campaign-id)
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

import requests
from sqlalchemy.orm import Session

import config
import database
from database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HeyreachClient:
    """Client for interacting with the Heyreach API"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def get_campaign_leads(self, campaign_id: str, page: int = 1, limit: int = 100) -> Dict[str, Any]:
        """
        Get leads from a campaign with pagination.

        Args:
            campaign_id: The campaign ID
            page: Page number (default: 1)
            limit: Results per page (default: 100)

        Returns:
            Dict containing leads and pagination info
        """
        url = f"{self.base_url}/campaign/GetLeadsForCampaign"
        params = {
            "campaignId": campaign_id,
            "page": page,
            "limit": limit,
        }

        logger.info(f"Fetching leads from campaign {campaign_id}, page {page}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch leads from Heyreach: {e}")
            raise

    def get_all_campaign_leads(self, campaign_id: str) -> List[Dict[str, Any]]:
        """
        Get all leads from a campaign (handles pagination automatically).

        Args:
            campaign_id: The campaign ID

        Returns:
            List of all leads
        """
        all_leads = []
        page = 1

        while True:
            result = self.get_campaign_leads(campaign_id, page=page, limit=100)

            # Handle different possible response structures
            leads = result.get("leads", result.get("data", []))

            if not leads:
                break

            all_leads.extend(leads)
            logger.info(f"Fetched {len(leads)} leads from page {page}")

            # Check if there are more pages
            total_pages = result.get("totalPages", result.get("total_pages", 0))
            if total_pages and page >= total_pages:
                break

            # If no pagination info, check if we got less than requested
            if len(leads) < 100:
                break

            page += 1

        logger.info(f"Fetched total of {len(all_leads)} leads")
        return all_leads


def is_connection_accepted(lead: Dict[str, Any]) -> bool:
    """
    Check if a lead has accepted the connection request.

    Args:
        lead: Lead data from Heyreach

    Returns:
        True if connection was accepted, False otherwise
    """
    # Check various possible field names that indicate connection acceptance
    status = lead.get("status", "").lower()
    connection_status = lead.get("connectionStatus", lead.get("connection_status", "")).lower()

    # Common indicators of accepted connection
    accepted_indicators = ["accepted", "connected", "connection_accepted"]

    return (
        status in accepted_indicators or
        connection_status in accepted_indicators or
        lead.get("isConnected", False) or
        lead.get("is_connected", False)
    )


def backfill_lead(db: Session, lead: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Backfill a single lead into our database.

    Args:
        db: Database session
        lead: Lead data from Heyreach
        dry_run: If True, don't actually write to database

    Returns:
        True if lead was backfilled, False if it already existed
    """
    lead_id = lead.get("id", lead.get("leadId"))
    profile_url = lead.get("profileUrl", lead.get("profile_url", lead.get("linkedInProfileUrl", "")))

    if not profile_url:
        profile_url = f"heyreach_lead_{lead_id}"

    # Check if prospect already exists
    existing = database.get_prospect_by_linkedin_url(db, profile_url)

    if existing and existing.status == "connected":
        logger.debug(f"Lead {lead_id} already exists with connected status, skipping")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would backfill lead: {lead.get('firstName')} {lead.get('lastName')} ({profile_url})")
        return True

    # Create or update prospect
    prospect = database.get_or_create_prospect(
        db=db,
        linkedin_url=profile_url,
        heyreach_lead_id=lead_id,
        first_name=lead.get("firstName", lead.get("first_name")),
        last_name=lead.get("lastName", lead.get("last_name")),
        company=lead.get("companyName", lead.get("company_name")),
        title=lead.get("position"),
        email=lead.get("emailAddress", lead.get("email_address")),
    )

    # Create connection_accepted event
    database.create_event(
        db=db,
        prospect_id=prospect.id,
        event_type="connection_request_accepted",
        heyreach_lead_id=lead_id,
        raw_payload=str(lead),
    )

    # Update prospect status
    database.update_prospect_status(
        db=db,
        prospect=prospect,
        event_type="connection_request_accepted",
    )

    logger.info(f"Backfilled lead: {lead.get('firstName')} {lead.get('lastName')} ({profile_url})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill Heyreach connection acceptances")
    parser.add_argument(
        "--campaign-id",
        help="Campaign ID to backfill from (overrides env var)",
        default=config.HEYREACH_CAMPAIGN_ID,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be backfilled without writing to database",
    )

    args = parser.parse_args()

    # Validate required config
    if not config.HEYREACH_API_KEY:
        logger.error("HEYREACH_API_KEY not set in environment")
        sys.exit(1)

    if not args.campaign_id:
        logger.error("Campaign ID not provided (use --campaign-id or set HEYREACH_CAMPAIGN_ID)")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Heyreach Connection Acceptance Backfill")
    logger.info("=" * 60)
    logger.info(f"Campaign ID: {args.campaign_id}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("")

    # Initialize database
    init_db()
    db = next(database.get_db())

    try:
        # Create Heyreach client
        client = HeyreachClient(config.HEYREACH_API_KEY, config.HEYREACH_API_BASE_URL)

        # Fetch all leads from campaign
        logger.info("Fetching leads from Heyreach...")
        leads = client.get_all_campaign_leads(args.campaign_id)

        # Filter for accepted connections
        accepted_leads = [lead for lead in leads if is_connection_accepted(lead)]

        logger.info(f"Found {len(leads)} total leads")
        logger.info(f"Found {len(accepted_leads)} leads with accepted connections")
        logger.info("")

        if not accepted_leads:
            logger.info("No accepted connections to backfill")
            return

        # Backfill each accepted lead
        logger.info("Backfilling accepted connections...")
        backfilled_count = 0

        for lead in accepted_leads:
            if backfill_lead(db, lead, dry_run=args.dry_run):
                backfilled_count += 1

        if not args.dry_run:
            db.commit()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Backfill Summary")
        logger.info("=" * 60)
        logger.info(f"Total leads in campaign: {len(leads)}")
        logger.info(f"Leads with accepted connections: {len(accepted_leads)}")
        logger.info(f"New leads backfilled: {backfilled_count}")
        logger.info(f"Already existed: {len(accepted_leads) - backfilled_count}")

        if args.dry_run:
            logger.info("")
            logger.info("DRY RUN - No changes were made to the database")

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
