"""Process real captured data using truthful selectolax parser."""

import json
import sys
from pathlib import Path
from selectolax.parser import HTMLParser

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_jobs.summary_parser import parse_summary_card
from packages.domain_jobs.search import JobListing
from packages.domain_records.models import JobRecord, JobStatus


def process_captured_html():
    """Process the captured HTML to extract real job data using selectolax parser."""
    print("Processing real captured job data with truthful parser...")
    
    # Load the captured HTML
    html_path = Path(__file__).parent.parent / "tests" / "fixtures" / "upwork_authenticated_search.html"
    html_content = html_path.read_text(encoding="utf-8")
    
    # Use selectolax to extract job cards
    parser = HTMLParser(html_content)
    job_cards = parser.css('[data-test="JobTile"]')
    
    print(f"Found {len(job_cards)} job cards in captured HTML")
    
    successful_parses = []
    rejected_cards = []
    
    for idx, card in enumerate(job_cards):
        card_html = card.html
        try:
            summary = parse_summary_card(card_html)
            
            # Convert JobSummary to JobListing (preserve truthful data)
            listing = JobListing(
                job_id=summary.job_id,
                title=summary.title,
                description=summary.description,
                client_id=summary.client_id,
                client_name=summary.client_name,
                posted_date=summary.posted_date,
                posted_at=None,
                url=summary.url,
                budget=summary.budget,
                tags=summary.tags,
            )
            successful_parses.append(listing)
            
        except ValueError as e:
            rejected_cards.append({
                "index": idx,
                "reason": str(e),
                "card_preview": card_html[:200] + "..." if len(card_html) > 200 else card_html
            })
    
    print(f"\n✅ Successfully parsed: {len(successful_parses)} cards")
    print(f"❌ Rejected: {len(rejected_cards)} cards")
    
    if rejected_cards:
        print(f"\n{'='*60}")
        print("REJECTED CARDS")
        print(f"{'='*60}")
        for rejection in rejected_cards:
            print(f"\nCard {rejection['index']}: {rejection['reason']}")
            print(f"Preview: {rejection['card_preview']}")
    
    # Convert successful parses to JobRecord objects
    job_records = []
    for listing in successful_parses:
        job_record = JobRecord(
            id=listing.job_id,
            title=listing.title,
            description=listing.description,
            client_id=listing.client_id,
            client_name=listing.client_name,
            posted_date=listing.posted_at,
            posted_date_text=listing.posted_date,
            url=listing.url,
            status=JobStatus.OPEN,
            budget=listing.budget,
            tags=listing.tags
        )
        job_records.append(job_record)
    
    # Create the clean output response using truthful data
    response = {
        "jobs": [record.to_dict() for record in job_records],
        "search_id": "real-capture-test",
        "cursor_id": "cursor-123",
        "new_jobs_count": len(job_records),
        "total_jobs_count": len(job_records)
    }
    
    print(f"\n{'='*60}")
    print(f"CLEAN OUTPUT CONTRACT - TRUTHFUL JOB DATA")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2, default=str))
    print(f"{'='*60}")
    
    # Save to file
    output_path = Path(__file__).parent.parent / "tests" / "fixtures" / "clean_output_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=2, default=str)
    print(f"\n✅ Saved clean output to: {output_path}")
    
    # Save rejected cards for inspection
    if rejected_cards:
        rejected_path = Path(__file__).parent.parent / "tests" / "fixtures" / "rejected_cards.json"
        with open(rejected_path, 'w', encoding='utf-8') as f:
            json.dump(rejected_cards, f, indent=2, default=str)
        print(f"✅ Saved rejected cards to: {rejected_path}")
    
    # Verify the output format
    if response["jobs"]:
        first_job = response["jobs"][0]
        required_fields = ["job_id", "title", "description", "client_id", "client_name", "posted_date", "posted_date_text", "url", "status", "tags"]
        missing_fields = [field for field in required_fields if field not in first_job]
        
        if missing_fields:
            print(f"\n❌ Missing required fields: {missing_fields}")
        else:
            print(f"\n✅ All required fields present")
        
        # Check for fabricated data
        issues = []
        if first_job.get("job_id", "").startswith("job_"):
            issues.append("job_id starts with 'job_' (fabricated)")
        if first_job.get("client_name") == "Unknown Client":
            issues.append("client_name is 'Unknown Client' (fabricated)")
        if "Just not interested" in first_job.get("description", ""):
            issues.append("description contains feedback menu text")
        
        if issues:
            print(f"\n❌ Found fabricated data: {issues}")
        else:
            print(f"\n✅ No fabricated data detected")


if __name__ == "__main__":
    process_captured_html()
