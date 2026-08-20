"""Test script to validate summary_parser against real HTML fixture."""

import sys
from pathlib import Path
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_jobs.summary_parser import parse_summary_card

# Load the authenticated fixture HTML
fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "upwork_authenticated_search.html"
html_content = fixture_path.read_text(encoding='utf-8')

# Use selectolax to extract job cards directly
from selectolax.parser import HTMLParser
parser = HTMLParser(html_content)
job_cards = parser.css('[data-test="JobTile"]')

print(f"Found {len(job_cards)} job cards in fixture")

# Test parsing the first job card
if job_cards:
    first_card_html = job_cards[0].html
    
    # Debug: check what elements are in the card
    print(f"\nFirst card HTML length: {len(first_card_html)}")
    print(f"First card preview: {first_card_html[:300]}...")
    
    # Check if job-tile-title-link exists
    from selectolax.parser import HTMLParser as Parser
    card_parser = Parser(first_card_html)
    title_link = card_parser.css_first('[data-test="job-tile-title-link"]')
    print(f"Found job-tile-title-link: {title_link is not None}")
    
    # Try finding all links
    all_links = card_parser.css('a')
    print(f"Found {len(all_links)} links in card")
    for i, link in enumerate(all_links[:3]):
        print(f"  Link {i}: {link.attrs.get('href', 'no href')}")
    
    # Check for client info elements
    client_info = card_parser.css_first('[data-test="JobInfoClient"]')
    print(f"Found JobInfoClient: {client_info is not None}")
    if client_info:
        print(f"JobInfoClient content: {client_info.text(strip=True)[:100]}...")
    
    try:
        summary = parse_summary_card(first_card_html)
        print("\n✅ Successfully parsed first job card:")
        print(f"  job_id: {summary.job_id}")
        print(f"  title: {summary.title}")
        print(f"  url: {summary.url}")
        print(f"  description: {summary.description[:100]}...")
        print(f"  posted_date: {summary.posted_date}")
        print(f"  client_id: {summary.client_id}")
        print(f"  client_name: {summary.client_name}")
        print(f"  tags: {summary.tags}")
        print(f"  budget: {summary.budget}")
    except ValueError as e:
        print(f"\n❌ Failed to parse first job card: {e}")
        print(f"Card HTML preview: {first_card_html[:500]}...")
else:
    print("❌ No job cards found in fixture")
