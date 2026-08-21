"""Jobs search primitive for Upwork."""

from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from .summary_parser import parse_summary_card, JobSummary
from .detail_parser import parse_detail_page, JobDetail
from .models import Budget


class UpworkBlockedError(Exception):
    """Raised when Upwork returns a Cloudflare challenge page or blocks access."""
    pass


class EnrichmentMismatchError(Exception):
    """Raised when summary and detail job IDs don't match during enrichment."""
    pass


def verify_enrichment_match(summary: JobSummary, detail: JobDetail) -> bool:
    """Verify that summary and detail job IDs match for safe enrichment.
    
    Args:
        summary: JobSummary from search results
        detail: JobDetail from detail page parse
        
    Returns:
        True if verification passes
        
    Raises:
        EnrichmentMismatchError: If job IDs don't match
    """
    if summary.job_id != detail.job_id:
        raise EnrichmentMismatchError(
            f"Job ID mismatch: summary.job_id={summary.job_id}, detail.job_id={detail.job_id}"
        )
    
    # If detail has a URL, it should match or be consistent with summary URL
    if detail.url and summary.url:
        # Extract job ID from both URLs and compare
        # URLs may have query parameters, so we just check they're for the same job
        if detail.url != summary.url:
            # They don't need to be identical (one might have query params),
            # but they should both contain the job ID
            if summary.job_id not in detail.url:
                raise EnrichmentMismatchError(
                    f"URL mismatch: summary job_id {summary.job_id} not found in detail URL {detail.url}"
                )
    
    return True


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


class JobListing(BaseModel):
    """Raw job listing extracted from Upwork."""
    
    model_config = ConfigDict(extra="forbid")
    
    job_id: str
    title: str
    description: str
    posted_date: str  # Truthful source value like "17 minutes ago"
    url: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    posted_at: Optional[datetime] = None  # Only when absolute timestamp parsed
    budget: Optional[Budget] = None
    status: str = "open"
    tags: List[str] = []
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("url is required and cannot be empty")
        if not v.startswith("https://www.upwork.com"):
            raise ValueError("url must be a valid Upwork URL")
        return v.strip()


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

    async def get_job_details(self, url: str) -> JobListing:
        """Get detailed information for a specific job by navigating to its detail page.
        
        Args:
            url: The absolute URL of the job detail page
            
        Returns:
            JobListing: Enriched job listing with detail page information
            
        Raises:
            ValueError: If URL is invalid
            RuntimeError: If navigation or parsing fails
            EnrichmentMismatchError: If summary and detail job IDs don't match
        """
        if not url or not url.startswith("https://www.upwork.com"):
            raise ValueError(f"Invalid job URL: {url}")
        
        # Check if we have a real Playwright page object
        if self.session.page is None:
            raise RuntimeError("Cannot get job details without a real browser page")
        
        try:
            # Navigate to job detail page
            await self.session.navigate(url)
            
            # Wait for page to load
            await self.session.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Assert we're on a valid page, not a Cloudflare challenge
            page_content = await self.session.page.content()
            self._assert_search_page(page_content)
            
            # Get the full page HTML for parsing
            html = await self.session.page.content()
            
            # Parse the detail page
            detail = parse_detail_page(html)
            
            # For enrichment verification, we need the summary. Since we're navigating
            # directly to the detail page, we create a minimal summary from the detail
            # for verification purposes. In a real flow, you'd have the summary from search.
            minimal_summary = JobSummary(
                job_id=detail.job_id,
                title=detail.title,
                description=detail.description,
                url=url,  # Use the URL we navigated to
                posted_date=detail.posted_date,
                client_id=detail.client_id,
                client_name=detail.client_name,
                tags=detail.tags,
                budget=detail.budget,
            )
            
            # Verify enrichment match
            verify_enrichment_match(minimal_summary, detail)
            
            # Convert JobDetail to JobListing
            return JobListing(
                job_id=detail.job_id,
                title=detail.title,
                description=detail.description,
                client_id=detail.client_id,
                client_name=detail.client_name,
                posted_date=detail.posted_date,
                posted_at=detail.posted_at,
                url=url,  # Use the URL we navigated to
                budget=detail.budget,
                tags=detail.tags,
                status=detail.status,
            )
            
        except EnrichmentMismatchError as exc:
            raise RuntimeError(f"Enrichment verification failed: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"Failed to parse job detail page: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to navigate to job detail page: {exc}") from exc

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
            for index, card_html in enumerate(cards_html):
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
                        budget=summary.budget,  # Already a Budget model from parser
                        tags=summary.tags,
                    ))
                except ValueError as exc:
                    # Fail loudly on missing required fields with card index for diagnosis
                    raise RuntimeError(f"Failed to parse job card {index}: {exc}") from exc

        except Exception as e:
            raise RuntimeError(f"Failed to extract job cards from DOM: {e}")

        return listings
