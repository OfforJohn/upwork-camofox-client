"""Integration tests for real Camoufox session (opt-in, requires browser binary)."""

import pytest
from packages.domain_camofox.session import CamofoxSession, SessionConfig, CAMOUFOX_AVAILABLE
from packages.domain_camofox.interface import PageInfo, FakeBrowser
from packages.domain_jobs.search import JobsSearch, JobSearchParams


@pytest.mark.integration
@pytest.mark.skipif(not CAMOUFOX_AVAILABLE, reason="Camoufox SDK not available")
class TestCamoufoxIntegration:
    """Integration tests for real Camoufox browser sessions."""

    @pytest.mark.asyncio
    async def test_launch_and_navigate_to_upwork(self):
        """Test that a real Camoufox session can launch and navigate to Upwork."""
        # Create session config
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )

        # Launch session
        session = CamofoxSession(config)
        await session.launch()

        try:
            assert session.is_active
            assert session.camofox is not None
            assert session.browser_context is not None
            assert session.page is not None

            # Navigate to Upwork
            await session.navigate("https://www.upwork.com")

            # Get page info
            page_info = await session.get_page_info()

            assert page_info is not None
            assert "upwork.com" in page_info.url.lower()
            assert page_info.title is not None
        finally:
            # Close session even if navigation fails
            await session.close()

        assert not session.is_active
        assert session.browser_context is None
        assert session.page is None

    @pytest.mark.asyncio
    async def test_get_cookies_from_real_browser(self):
        """Test that cookies can be extracted from a browser session using fake browser."""
        fake_browser = FakeBrowser()
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )

        session = CamofoxSession(config, browser=fake_browser)
        await session.launch()

        try:
            # Navigate to a site
            await session.navigate("https://www.upwork.com")

            # Get cookies (returns config cookies since fake browser doesn't set cookies)
            cookies = await session.get_cookies()

            assert isinstance(cookies, list)
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle: launch, navigate, close using fake browser."""
        fake_browser = FakeBrowser()
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )

        session = CamofoxSession(config, browser=fake_browser)

        # Initially inactive
        assert not session.is_active

        await session.launch()
        assert session.is_active

        try:
            # Navigate
            await session.navigate("https://www.upwork.com")
            page_info = await session.get_page_info()
            assert "upwork.com" in page_info.url.lower()
        finally:
            # Close
            await session.close()

        assert not session.is_active

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Upwork blocks automated access with Cloudflare - requires manual authentication")
    async def test_live_job_extraction_with_query(self):
        """Test that real Upwork job extraction works with a query parameter."""
        # Create session config
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )

        # Launch session
        session = CamofoxSession(config)
        await session.launch()

        try:
            # Check for Cloudflare challenge before attempting search
            html = await session.get_page_content()
            assert html, "Expected HTML content from page"
            assert "Just a moment..." not in html, "Cloudflare challenge page detected - blocked"
            assert "cf-chl-" not in html, "Cloudflare challenge markers detected - blocked"

            # Create JobsSearch instance
            jobs_search = JobsSearch(session)

            # Search with a query
            params = JobSearchParams(query="python")
            listings = await jobs_search.search(params)

            # Assert we got meaningful job listings from real Upwork HTML
            assert listings, "Expected at least one job parsed from Upwork HTML"

            first = listings[0]
            assert first.title.strip(), "Job title should not be empty"
            assert first.url.startswith("https://"), "Job URL should start with https://"
            assert first.description.strip(), "Job description should not be empty"
        finally:
            await session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
