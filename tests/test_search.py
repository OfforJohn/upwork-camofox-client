"""Test JobsSearch pipeline with fake page to prevent fabricated data."""

import asyncio
from pathlib import Path
from selectolax.parser import HTMLParser
from packages.domain_jobs.search import JobsSearch, JobSearchParams
from unittest.mock import AsyncMock, MagicMock


def test_search_pipeline_no_fabricated_data():
    """Test JobsSearch pipeline does not reintroduce datetime.now() or double-prefix URLs."""
    async def _run_test():
        # Load the authenticated fixture HTML
        fixture_path = Path(__file__).parent / "fixtures" / "upwork_authenticated_search.html"
        html_content = fixture_path.read_text(encoding='utf-8')
        
        # Extract one real job card outerHTML
        parser = HTMLParser(html_content)
        job_cards = parser.css('[data-test="JobTile"]')
        assert len(job_cards) > 0, "No job cards found in fixture"
        
        card_outerhtml = job_cards[0].html
        
        # Create fake session with mock page
        fake_session = MagicMock()
        fake_session.page = AsyncMock()
        
        # Mock navigate to do nothing
        fake_session.navigate = AsyncMock()
        
        # Mock wait_for_load_state to do nothing
        fake_session.page.wait_for_load_state = AsyncMock()
        
        # Mock page.content to return minimal HTML
        fake_session.page.content = AsyncMock(return_value="<html><body>Search page</body></html>")
        
        # Mock locator to return the fixture card outerHTML
        mock_locator = AsyncMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.evaluate_all = AsyncMock(return_value=[card_outerhtml])
        fake_session.page.locator = MagicMock(return_value=mock_locator)
        
        # Create JobsSearch instance
        jobs_search = JobsSearch(fake_session)
        
        # Execute search
        search_params = JobSearchParams(query="python")
        listings = await jobs_search.search(search_params)
        
        # Assert we got one listing
        assert len(listings) == 1, "Should extract one job card"
        
        listing = listings[0]
        
        # Assert no datetime.now() was used - posted_date should be string
        assert isinstance(listing.posted_date, str), "posted_date should be string, not datetime"
        assert "ago" in listing.posted_date.lower() or "yesterday" in listing.posted_date.lower(), \
            f"posted_date should be relative time text, not datetime: {listing.posted_date}"
        
        # Assert posted_at is None (no absolute timestamp from card)
        assert listing.posted_at is None, "posted_at should be None for card data"
        
        # Assert URL is absolute and not double-prefixed
        assert listing.url.startswith("https://www.upwork.com/jobs/"), \
            f"url should be absolute: {listing.url}"
        assert not listing.url.startswith("https://www.upwork.comhttps://"), \
            f"url should not be double-prefixed: {listing.url}"
        
        # Assert client_id is not fabricated (None or different from job_id)
        assert listing.client_id is None or listing.client_id != listing.job_id, \
            "client_id should not be fabricated as job_id"
        
        # Assert client_name is optional (can be None)
        # No assertion needed - just ensure it doesn't crash
    
    asyncio.run(_run_test())
