"""Test JobNormalizer preserves truthful posted_date_text without fabricating datetime."""

from datetime import datetime
from packages.domain_jobs.search import JobListing
from packages.domain_records.normalizer import JobNormalizer
from packages.domain_records.models import JobRecord


def test_normalizer_preserves_posted_date_text():
    """Test JobNormalizer preserves relative posted_date text without fabricating datetime."""
    normalizer = JobNormalizer()
    
    # Create a JobListing with truthful relative posted_date
    listing = JobListing(
        job_id="022090361778369164301",
        title="Python Developer",
        description="Looking for Python developer",
        client_id=None,
        client_name=None,
        posted_date="17 minutes ago",  # Truthful source value
        posted_at=None,  # No absolute timestamp
        url="https://www.upwork.com/jobs/test-job",
        tags=["Python", "Django"],
    )
    
    # Normalize to JobRecord
    record = normalizer.normalize(listing)
    
    # Assert posted_date is None (not fabricated)
    assert record.posted_date is None, "posted_date should be None when no absolute timestamp available"
    
    # Assert posted_date_text preserves the truthful source value
    assert record.posted_date_text == "17 minutes ago", \
        f"posted_date_text should preserve source value, got: {record.posted_date_text}"
    
    # Assert other fields are preserved correctly
    assert record.id == listing.job_id
    assert record.title == listing.title
    assert record.description == listing.description
    assert record.client_id == listing.client_id
    assert record.client_name == listing.client_name
    assert record.url == listing.url
    assert record.tags == listing.tags


def test_normalizer_with_absolute_timestamp():
    """Test JobNormalizer uses absolute timestamp when available."""
    normalizer = JobNormalizer()
    
    absolute_time = datetime(2024, 1, 15, 10, 30, 0)
    
    # Create a JobListing with both relative text and absolute timestamp
    listing = JobListing(
        job_id="022090361778369164301",
        title="Python Developer",
        description="Looking for Python developer",
        client_id="client123",
        client_name="Test Client",
        posted_date="17 minutes ago",  # Truthful source value
        posted_at=absolute_time,  # Absolute timestamp from detail page
        url="https://www.upwork.com/jobs/test-job",
        tags=["Python", "Django"],
    )
    
    # Normalize to JobRecord
    record = normalizer.normalize(listing)
    
    # Assert posted_date uses the absolute timestamp
    assert record.posted_date == absolute_time, \
        f"posted_date should use absolute timestamp, got: {record.posted_date}"
    
    # Assert posted_date_text still preserves the source value
    assert record.posted_date_text == "17 minutes ago", \
        f"posted_date_text should preserve source value, got: {record.posted_date_text}"
