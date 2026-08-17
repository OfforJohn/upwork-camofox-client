"""Job normalizer for normalizing raw job listings to job records."""

from typing import List, Set
from datetime import datetime
from .models import JobRecord, JobStatus
from ..domain_jobs.search import JobListing


class JobNormalizer:
    """Normalizes raw job listings to job records."""

    def normalize(self, listing: JobListing) -> JobRecord:
        """Normalize a single job listing to a job record."""
        # Parse status
        status = self._parse_status(listing.status)
        
        return JobRecord(
            id=listing.job_id,
            title=listing.title,
            description=listing.description,
            client_id=listing.client_id,
            client_name=listing.client_name,
            posted_date=listing.posted_date,
            url=listing.url,
            status=status,
            budget=listing.budget,
            tags=listing.tags or [],
        )

    def normalize_batch(self, listings: List[JobListing]) -> List[JobRecord]:
        """Normalize a batch of job listings."""
        return [self.normalize(listing) for listing in listings]

    def deduplicate(self, records: List[JobRecord], existing_ids: Set[str]) -> List[JobRecord]:
        """Deduplicate job records against existing IDs."""
        return [record for record in records if record.id not in existing_ids]

    def _parse_status(self, status: str) -> JobStatus:
        """Parse status string to JobStatus enum."""
        status_lower = status.lower()
        if status_lower == "open":
            return JobStatus.OPEN
        elif status_lower == "closed":
            return JobStatus.CLOSED
        elif status_lower == "filled":
            return JobStatus.FILLED
        elif status_lower == "expired":
            return JobStatus.EXPIRED
        else:
            return JobStatus.OPEN
