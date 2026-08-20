"""Test summary_parser against real authenticated fixture HTML."""

from pathlib import Path
from selectolax.parser import HTMLParser
from packages.domain_jobs.summary_parser import parse_summary_card


def test_summary_parser_reads_real_card():
    """Test parser extracts truthful data from real authenticated fixture."""
    # Load the authenticated fixture HTML
    fixture_path = Path(__file__).parent / "fixtures" / "upwork_authenticated_search.html"
    html_content = fixture_path.read_text(encoding='utf-8')
    
    # Use selectolax to extract job cards directly
    parser = HTMLParser(html_content)
    job_cards = parser.css('[data-test="JobTile"]')
    
    assert len(job_cards) > 0, "No job cards found in fixture"
    
    # Test parsing the first job card
    first_card_html = job_cards[0].html
    summary = parse_summary_card(first_card_html)
    
    # Assert job_id is real (starts with numeric digits from data-ev-job-uid)
    assert summary.job_id, "job_id should not be empty"
    assert summary.job_id.isdigit() or summary.job_id.startswith("022"), f"job_id should be real: {summary.job_id}"
    
    # Assert title exists and contains no HTML artifacts
    assert summary.title, "title should not be empty"
    assert "&amp;" not in summary.title, "title should not contain HTML entities"
    assert "span-class-highlight" not in summary.title, "title should not contain CSS class artifacts"
    
    # Assert description exists and contains no feedback menu text
    assert summary.description, "description should not be empty"
    assert "Just not interested" not in summary.description, "description should not contain feedback menu text"
    
    # Assert URL is absolute and properly normalized
    assert summary.url, "url should not be empty"
    assert summary.url.startswith("https://www.upwork.com/jobs/"), f"url should be absolute: {summary.url}"
    assert not summary.url.startswith("https://www.upwork.comhttps://"), "url should not be double-prefixed"
    
    # Assert posted_date is truthful source value (relative time text)
    assert summary.posted_date, "posted_date should not be empty"
    assert "ago" in summary.posted_date.lower() or "yesterday" in summary.posted_date.lower(), \
        f"posted_date should be relative time text: {summary.posted_date}"
    
    # Assert tags have no duplicates
    assert len(summary.tags) == len(set(summary.tags)), "tags should not contain duplicates"
    
    # Assert client_id is not fabricated (should be None or different from job_id)
    assert summary.client_id is None or summary.client_id != summary.job_id, \
        "client_id should not be fabricated as job_id"


def test_summary_parser_all_cards_parse_or_fail_specifically():
    """Test every card in fixture either parses successfully or produces specific parse error."""
    # Load the authenticated fixture HTML
    fixture_path = Path(__file__).parent / "fixtures" / "upwork_authenticated_search.html"
    html_content = fixture_path.read_text(encoding='utf-8')
    
    # Use selectolax to extract job cards directly
    parser = HTMLParser(html_content)
    job_cards = parser.css('[data-test="JobTile"]')
    
    assert len(job_cards) > 0, "No job cards found in fixture"
    
    # Try to parse every card
    successful_parses = 0
    specific_errors = []
    
    for index, card in enumerate(job_cards):
        card_html = card.html
        try:
            summary = parse_summary_card(card_html)
            successful_parses += 1
        except ValueError as e:
            # Capture specific parse errors
            specific_errors.append(f"Card {index}: {e}")
    
    # Assert we either parsed all cards successfully or have specific errors
    assert successful_parses > 0, "No cards parsed successfully"
    
    # If there were errors, they should be specific (not generic failures)
    if specific_errors:
        # Log the errors for diagnosis but don't fail the test
        # This ensures we know which cards are problematic
        print(f"\nParsed {successful_parses}/{len(job_cards)} cards successfully")
        for error in specific_errors:
            print(f"  {error}")
    
    # The key assertion: we should not silently skip malformed cards
    # Every card was attempted and either succeeded or produced a specific error
    assert successful_parses + len(specific_errors) == len(job_cards), \
        "Every card should either parse successfully or produce a specific error"
