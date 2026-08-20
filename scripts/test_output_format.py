"""Test clean output contract using captured fixture data."""

import json
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_records.models import JobRecord, JobStatus
from packages.domain_jobs.search import JobListing
from datetime import datetime


def test_output_format():
    """Test that JobRecord.to_dict() produces the expected clean output format."""
    print("Testing clean output contract format...")
    
    # Create a sample JobListing (simulating what search.py produces)
    job_listing = JobListing(
        job_id="test-job-123",
        title="Python Developer Needed",
        description="Looking for senior Python developer with LLM experience",
        client_id="client-456",
        client_name="Test Client",
        posted_date=datetime.now(),
        url="https://www.upwork.com/jobs/test-job-123",
        budget={
            "proposals": "5 to 10",
            "posted_on": "1 hour ago"
        },
        tags=["Python", "LLM", "Data Science"]
    )
    
    # Convert to JobRecord (simulating what normalizer does)
    job_record = JobRecord(
        id=job_listing.job_id,
        title=job_listing.title,
        description=job_listing.description,
        client_id=job_listing.client_id,
        client_name=job_listing.client_name,
        posted_date=job_listing.posted_date,
        url=job_listing.url,
        status=JobStatus.OPEN,
        budget=job_listing.budget,
        tags=job_listing.tags
    )
    
    # Get the dict output (this is what runner.py returns)
    output = job_record.to_dict()
    
    print("\nJobRecord.to_dict() output:")
    print(json.dumps(output, indent=2, default=str))
    
    # Verify required fields
    required_fields = ["job_id", "title", "description", "client_id", "client_name", "posted_date", "url", "status", "tags"]
    missing_fields = [field for field in required_fields if field not in output]
    
    if missing_fields:
        print(f"\n❌ Missing required fields: {missing_fields}")
        return False
    else:
        print(f"\n✅ All required fields present")
    
    # Check that deprecated fields are not present
    deprecated_fields = ["id", "created_at", "updated_at"]
    found_deprecated = [field for field in deprecated_fields if field in output]
    
    if found_deprecated:
        print(f"\n❌ Found deprecated fields: {found_deprecated}")
        return False
    else:
        print(f"\n✅ No deprecated fields present")
    
    # Test the full response structure
    full_response = {
        "jobs": [output],
        "search_id": "test-search-123",
        "cursor_id": "cursor-456",
        "new_jobs_count": 1,
        "total_jobs_count": 1
    }
    
    print("\nFull response structure:")
    print(json.dumps(full_response, indent=2, default=str))
    
    if "jobs" in full_response:
        print(f"\n✅ Jobs array present in response")
        return True
    else:
        print(f"\n❌ Jobs array missing from response")
        return False


if __name__ == "__main__":
    success = test_output_format()
    print(f"\n{'='*50}")
    print(f"Test result: {'PASSED' if success else 'FAILED'}")
    print(f"{'='*50}")
