"""Process real captured data through clean output pipeline using regex."""

import json
import sys
import re
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_records.models import JobRecord, JobStatus
from packages.domain_jobs.search import JobListing
from datetime import datetime


def process_captured_html():
    """Process the captured HTML to extract real job data using regex."""
    print("Processing real captured job data...")
    
    # Load the captured HTML
    html_path = Path(__file__).parent.parent / "tests" / "fixtures" / "upwork_authenticated_search.html"
    html_content = html_path.read_text(encoding="utf-8")
    
    # Extract job cards using regex patterns
    # Find all job card elements
    job_card_pattern = r'<article[^>]*data-test="JobTile"[^>]*>(.*?)</article>'
    job_cards = re.findall(job_card_pattern, html_content, re.DOTALL)
    
    print(f"Found {len(job_cards)} job cards in captured HTML")
    
    listings = []
    
    for idx, card_html in enumerate(job_cards):
        # Extract title
        title_match = re.search(r'<h[23][^>]*class="[^"]*job-tile-title[^"]*"[^>]*>\s*<a[^>]*>(.*?)</a>', card_html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Unknown"
        # Clean HTML tags from title
        title = re.sub(r'<[^>]+>', '', title).strip()
        
        # Extract URL
        url_match = re.search(r'href="(/jobs/[^"]+)"', card_html)
        url = url_match.group(1) if url_match else None
        
        if not url:
            continue
        
        # Extract job ID from URL
        job_id_match = re.search(r'/jobs/([a-z0-9-]+)', url)
        job_id = job_id_match.group(1) if job_id_match else f"job_{idx}"
        
        # Extract client ID
        client_id_match = re.search(r'data-ev-job-uid="([^"]+)"', card_html)
        client_id = client_id_match.group(1) if client_id_match else 'unknown'
        
        # Extract proposals
        proposals_match = re.search(r'<span[^>]*data-test="proposals-tier"[^>]*>(.*?)</span>', card_html, re.DOTALL)
        proposals = proposals_match.group(1).strip() if proposals_match else None
        proposals = re.sub(r'<[^>]+>', '', proposals).strip() if proposals else None
        
        # Extract posted date
        posted_match = re.search(r'<span[^>]*data-test="job-pubilshed-date"[^>]*>(.*?)</span>', card_html, re.DOTALL)
        posted_on = posted_match.group(1).strip() if posted_match else None
        posted_on = re.sub(r'<[^>]+>', '', posted_on).strip() if posted_on else None
        
        # Extract tags
        tags = []
        tag_matches = re.findall(r'<span[^>]*class="[^"]*highlight[^"]*"[^>]*>(.*?)</span>', card_html, re.DOTALL)
        for tag in tag_matches:
            clean_tag = re.sub(r'<[^>]+>', '', tag).strip()
            if clean_tag:
                tags.append(clean_tag)
        
        # Extract description (first paragraph or text content)
        desc_match = re.search(r'<p[^>]*>(.*?)</p>', card_html, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ''
        description = re.sub(r'<[^>]+>', '', description).strip()
        # Limit description length
        if len(description) > 500:
            description = description[:500] + "..."
        
        listings.append(JobListing(
            job_id=job_id,
            title=title,
            description=description,
            client_id=client_id,
            client_name="Unknown Client",  # Not easily extractable from current HTML structure
            posted_date=datetime.now(),
            url=f"https://www.upwork.com{url}",
            budget={
                "proposals": proposals,
                "posted_on": posted_on
            },
            tags=tags,
        ))
    
    # Convert to JobRecord objects
    job_records = []
    for listing in listings:
        job_record = JobRecord(
            id=listing.job_id,
            title=listing.title,
            description=listing.description,
            client_id=listing.client_id,
            client_name=listing.client_name,
            posted_date=listing.posted_date,
            url=listing.url,
            status=JobStatus.OPEN,
            budget=listing.budget,
            tags=listing.tags
        )
        job_records.append(job_record)
    
    # Create the clean output response
    response = {
        "jobs": [record.to_dict() for record in job_records],
        "search_id": "real-capture-test",
        "cursor_id": "cursor-123",
        "new_jobs_count": len(job_records),
        "total_jobs_count": len(job_records)
    }
    
    print(f"\n{'='*60}")
    print(f"CLEAN OUTPUT CONTRACT - REAL JOB DATA")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2, default=str))
    print(f"{'='*60}")
    
    # Save to file
    output_path = Path(__file__).parent.parent / "tests" / "fixtures" / "clean_output_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=2, default=str)
    print(f"\n✅ Saved clean output to: {output_path}")
    
    # Verify the output format
    if response["jobs"]:
        first_job = response["jobs"][0]
        required_fields = ["job_id", "title", "description", "client_id", "client_name", "posted_date", "url", "status", "tags"]
        missing_fields = [field for field in required_fields if field not in first_job]
        
        if missing_fields:
            print(f"\n❌ Missing required fields: {missing_fields}")
        else:
            print(f"\n✅ All required fields present")
        
        deprecated_fields = ["id", "created_at", "updated_at"]
        found_deprecated = [field for field in deprecated_fields if field in first_job]
        
        if found_deprecated:
            print(f"\n❌ Found deprecated fields: {found_deprecated}")
        else:
            print(f"\n✅ No deprecated fields present")


if __name__ == "__main__":
    process_captured_html()
