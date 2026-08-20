"""Jobs search primitive for Upwork."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from .summary_parser import parse_summary_card


class UpworkBlockedError(Exception):
    """Raised when Upwork returns a Cloudflare challenge page or blocks access."""
    pass


@dataclass
class JobSearchParams:
    """Parameters for job search."""
    query: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    job_type: Optional[str] = None  # fixed, hourly, etc.
    experience_level: Optional[str] = None  # entry, intermediate, expert
    duration: Optional[str] = None  # less_than_month, 1_to_3_months, etc.
    hourly_rate_min: Optional[int] = None
    hourly_rate_max: Optional[int] = None
    fixed_budget_min: Optional[int] = None
    fixed_budget_max: Optional[int] = None


@dataclass
class JobListing:
    """Raw job listing extracted from Upwork."""
    job_id: str
    title: str
    description: str
    posted_date: str  # Truthful source value like "17 minutes ago"
    url: str
    client_id: str | None = None
    client_name: str | None = None
    posted_at: datetime | None = None  # Only when absolute timestamp parsed
    budget: Optional[Dict[str, Any]] = None
    status: str = "open"
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class JobsSearch:
    """Jobs search primitive using Camofox session."""

    def __init__(self, session):
        self.session = session
        self.job_card_locator = "[data-test*='job-tile']"

    def _assert_search_page(self, html: str) -> None:
        """Assert that the HTML is a valid search page, not a Cloudflare challenge."""
        lowered = html.lower()
        if "just a moment..." in lowered or "cf-chl-" in lowered:
            raise UpworkBlockedError("Upwork returned a Cloudflare challenge page")

    async def search(self, params: JobSearchParams, limit: int = 50) -> List[JobListing]:
        """Search for jobs on Upwork."""
        # Build search URL from parameters
        search_url = self._build_search_url(params)

        # Navigate to search URL
        await self.session.navigate(search_url)

        # Wait for page to load (only if real Playwright page is available)
        if self.session.page is not None:
            await self.session.page.wait_for_load_state('networkidle', timeout=10000)

        # Assert we're on a valid search page, not a Cloudflare challenge
        if self.session.page is not None:
            page_content = await self.session.page.content()
            self._assert_search_page(page_content)

        # Extract job cards using DOM evaluation
        job_cards = await self._extract_job_cards_from_dom()

        if not job_cards and self.session.page is not None:
            # Fail loudly with diagnostics only if we have a real page but no cards
            final_url = self.session.page.url if self.session.page else "unknown"
            final_title = await self.session.page.title() if self.session.page else "unknown"
            raise RuntimeError(
                f"No job cards found on page. "
                f"URL: {final_url}, Title: {final_title}, "
                f"Locator: {self.job_card_locator}"
            )

        return job_cards[:limit]

    async def get_job_details(self, job_id: str) -> JobListing:
        """Get detailed information for a specific job."""
        # TODO: Implement job detail extraction
        # Navigate to job page and extract full details
        
        # Placeholder
        raise NotImplementedError("Job details extraction not yet implemented")

    def _build_search_url(self, params: JobSearchParams) -> str:
        """Build Upwork search URL from parameters."""
        base_url = "https://www.upwork.com/nx/search/jobs/"
        query_params = {}

        if params.query:
            query_params["q"] = params.query

        if query_params:
            return f"{base_url}?{urlencode(query_params)}"

        return base_url

    async def _extract_job_cards_from_dom(self) -> List[JobListing]:
        """Extract job cards from DOM using outerHTML and parse with selectolax."""
        listings = []

        # Check if we have a real Playwright page object
        if self.session.page is None:
            # For testing with FakeBrowser, return empty list
            return []

        try:
            # Use the identified job card locator
            job_cards_locator = self.session.page.locator(self.job_card_locator)
            card_count = await job_cards_locator.count()

            if card_count == 0:
                return []

            # Extract outerHTML from all job cards
            cards_html = await job_cards_locator.evaluate_all(
                "elements => elements.map(element => element.outerHTML)"
            )

            # Parse each card using selectolax parser
            for card_html in cards_html:
                try:
                    summary = parse_summary_card(card_html)
                    
                    # Convert JobSummary to JobListing
                    # No fallback values - fail loudly if required fields are missing
                    listings.append(JobListing(
                        job_id=summary.job_id,
                        title=summary.title,
                        description=summary.description,
                        client_id=summary.client_id,  # Optional, no fallback
                        client_name=summary.client_name,  # Optional, no fallback
                        posted_date=summary.posted_date,  # Truthful source value
                        posted_at=None,  # No absolute timestamp from card
                        url=summary.url,  # Already normalized by parser
                        budget=summary.budget,
                        tags=summary.tags,
                    ))
                except ValueError as e:
                    # Fail loudly on missing required fields
                    raise RuntimeError(f"Failed to parse job card: {e}")

        except Exception as e:
            raise RuntimeError(f"Failed to extract job cards from DOM: {e}")

        return listings
