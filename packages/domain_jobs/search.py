"""Jobs search primitive for Upwork."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlencode


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
    client_id: str
    client_name: str
    posted_date: datetime
    url: str
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

        # Wait for page to load
        await self.session.page.wait_for_load_state('networkidle', timeout=10000)

        # Extract job cards using DOM evaluation
        job_cards = await self._extract_job_cards_from_dom()

        if not job_cards:
            # Fail loudly with diagnostics if no cards found
            final_url = self.session.page.url
            final_title = await self.session.page.title()
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
        """Extract job cards from DOM using Playwright locator.evaluate_all()."""
        listings = []

        try:
            # Use the identified job card locator
            job_cards_locator = self.session.page.locator(self.job_card_locator)
            card_count = await job_cards_locator.count()

            if card_count == 0:
                return []

            # Extract data from all job cards using evaluate_all
            cards_data = await job_cards_locator.evaluate_all("""
                (elements) => elements.map(el => {
                    const titleLink = el.querySelector('h2.job-tile-title a, h3.job-tile-title a');
                    const postedOn = el.querySelector('[data-test="posted-on"], [data-test="job-pubilshed-date"]');
                    const proposalsTier = el.querySelector('[data-test="proposals-tier"]');
                    const description = el.querySelector('.job-description, [data-test="job-description-text"]');
                    const clientInfo = el.querySelector('[data-test="client-name"]');
                    const tags = Array.from(el.querySelectorAll('[data-test="token"]')).map(t => t.textContent.trim());
                    
                    return {
                        title: titleLink ? titleLink.textContent.trim() : null,
                        url: titleLink ? titleLink.getAttribute('href') : null,
                        posted_on: postedOn ? postedOn.textContent.trim() : null,
                        proposals: proposalsTier ? proposalsTier.textContent.trim() : null,
                        description: description ? description.textContent.trim() : null,
                        client_name: clientInfo ? clientInfo.textContent.trim() : null,
                        client_id: el.getAttribute('data-ev-job-uid'),
                        tags: tags,
                        opening_uid: el.getAttribute('data-ev-opening_uid'),
                        position: el.getAttribute('data-ev-position'),
                        feed_name: el.getAttribute('data-ev-feed_name')
                    };
                })
            """)

            for idx, card_data in enumerate(cards_data):
                if not card_data.get('url'):
                    continue

                # Extract job ID from URL
                job_id_match = re.search(r'/jobs/([a-z0-9-]+)', card_data['url'])
                job_id = job_id_match.group(1) if job_id_match else card_data.get('opening_uid', f"job_{idx}")

                # Parse posted date from text (e.g., "Posted 1 hour ago")
                posted_date = datetime.now()  # Default to now if parsing fails
                posted_on_text = card_data.get('posted_on', '')
                if posted_on_text:
                    # Simple parsing - could be enhanced with proper date parsing
                    posted_date = datetime.now()  # Keep as now for now, can be improved

                listings.append(JobListing(
                    job_id=job_id,
                    title=card_data.get('title', 'Unknown'),
                    description=card_data.get('description', ''),
                    client_id=card_data.get('client_id') or 'unknown',
                    client_name=card_data.get('client_name') or 'Unknown Client',
                    posted_date=posted_date,
                    url=f"https://www.upwork.com{card_data['url']}",
                    budget={
                        "proposals": card_data.get('proposals'),
                        "posted_on": card_data.get('posted_on')
                    },
                    tags=card_data.get('tags', []),
                ))

        except Exception as e:
            raise RuntimeError(f"Failed to extract job cards from DOM: {e}")

        return listings
