"""Jobs search primitive for Upwork."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup


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

    async def search(self, params: JobSearchParams, limit: int = 50) -> List[JobListing]:
        """Search for jobs on Upwork."""
        # Build search URL from parameters
        search_url = self._build_search_url(params)

        # Navigate to search URL
        await self.session.navigate(search_url)

        # Get page HTML content from session (either fake browser fixture or real browser)
        html = await self.session.get_page_content()

        if html:
            return self._extract_listings_from_dom(html)

        # Placeholder return if no content available
        return []

    async def get_job_details(self, job_id: str) -> JobListing:
        """Get detailed information for a specific job."""
        # TODO: Implement job detail extraction
        # Navigate to job page and extract full details
        
        # Placeholder
        raise NotImplementedError("Job details extraction not yet implemented")

    def _build_search_url(self, params: JobSearchParams) -> str:
        """Build Upwork search URL from parameters."""
        base_url = "https://www.upwork.com/jobs/search/"
        query_parts = []

        if params.query:
            query_parts.append(f"q={params.query}")

        if query_parts:
            return f"{base_url}?{'&'.join(query_parts)}"

        return base_url

    def _extract_listings_from_dom(self, html: str) -> List[JobListing]:
        """Extract job listings from HTML DOM."""
        listings = []

        soup = BeautifulSoup(html, 'html.parser')

        # Try to find job tiles (fixture format)
        job_tiles = soup.find_all('div', class_='job-tile')

        for idx, tile in enumerate(job_tiles):
            title_elem = tile.find('h3', class_='job-title')
            desc_elem = tile.find('div', class_='job-description')
            budget_elem = tile.find('span', class_='budget')
            link_elem = tile.find('a', class_='job-link')

            if title_elem and desc_elem and link_elem:
                title = title_elem.get_text(strip=True)
                description = desc_elem.get_text(strip=True)
                budget = budget_elem.get_text(strip=True) if budget_elem else "Unknown"
                url = link_elem.get('href', '')

                # Extract job ID from URL
                job_id_match = re.search(r'/jobs/([a-z0-9-]+)', url)
                job_id = job_id_match.group(1) if job_id_match else f"job_{idx}"

                listings.append(JobListing(
                    job_id=job_id,
                    title=title,
                    description=description,
                    client_id="unknown",
                    client_name="Unknown Client",
                    posted_date=datetime.now(),
                    url=f"https://www.upwork.com{url}",
                    budget={"amount": budget},
                ))

        return listings
