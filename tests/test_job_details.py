"""Test job details extraction with mock page."""

import asyncio
from packages.domain_jobs.search import JobsSearch
from unittest.mock import AsyncMock, MagicMock


def test_get_job_details_with_mock_page():
    """Test get_job_details navigates to URL and parses detail page."""
    async def _run_test():
        # Create fake session with mock page
        fake_session = MagicMock()
        fake_session.page = AsyncMock()
        
        # Mock navigate to do nothing
        fake_session.navigate = AsyncMock()
        
        # Mock wait_for_load_state to do nothing
        fake_session.page.wait_for_load_state = AsyncMock()
        
        # Mock page.content to return minimal detail page HTML
        detail_html = """
        <html>
        <body>
            <div data-ev-job-uid="022090361778369164301">
                <h1 data-test="job-title">Python Developer Needed</h1>
                <div data-test="job-description">Looking for experienced Python developer for web scraping project.</div>
                <div data-test="job-published-date">Posted 2 hours ago</div>
                <div data-test="client-name">Test Client</div>
                <div data-client-uid="client123"></div>
                <div data-test="skill">Python</div>
                <div data-test="skill">Web Scraping</div>
                <div data-test="job-budget">$50-100</div>
                <div data-test="proposal-count">5 proposals</div>
            </div>
        </body>
        </html>
        """
        fake_session.page.content = AsyncMock(return_value=detail_html)
        
        # Create JobsSearch instance
        jobs_search = JobsSearch(fake_session)
        
        # Execute get_job_details
        job_url = "https://www.upwork.com/jobs/test-job"
        listing = await jobs_search.get_job_details(job_url)
        
        # Assert navigation was called
        fake_session.navigate.assert_called_once_with(job_url)
        
        # Assert listing was returned
        assert listing is not None
        assert listing.job_id == "022090361778369164301"
        assert listing.title == "Python Developer Needed"
        assert "web scraping" in listing.description.lower()
        assert listing.client_id == "client123"
        assert listing.client_name == "Test Client"
        assert listing.posted_date == "Posted 2 hours ago"
        assert listing.url == job_url
        assert "Python" in listing.tags
        assert "Web Scraping" in listing.tags
        assert listing.budget.text == "$50-100"
        assert listing.budget.proposals == "5"
    
    asyncio.run(_run_test())


def test_get_job_details_invalid_url():
    """Test get_job_details raises ValueError for invalid URL."""
    async def _run_test():
        fake_session = MagicMock()
        fake_session.page = AsyncMock()
        
        jobs_search = JobsSearch(fake_session)
        
        # Test with invalid URL
        try:
            await jobs_search.get_job_details("invalid-url")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid job URL" in str(e)
    
    asyncio.run(_run_test())


def test_get_job_details_no_page():
    """Test get_job_details raises RuntimeError when no page available."""
    async def _run_test():
        fake_session = MagicMock()
        fake_session.page = None  # No page available
        
        jobs_search = JobsSearch(fake_session)
        
        try:
            await jobs_search.get_job_details("https://www.upwork.com/jobs/test")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Cannot get job details without a real browser page" in str(e)
    
    asyncio.run(_run_test())
