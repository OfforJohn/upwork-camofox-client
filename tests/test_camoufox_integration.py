"""Integration tests for real Camoufox session (opt-in, requires browser binary)."""

import pytest
from packages.domain_camofox.session import CamofoxSession, SessionConfig, CAMOUFOX_AVAILABLE
from packages.domain_camofox.interface import PageInfo


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
        
        # Close session
        await session.close()
        
        assert not session.is_active
        assert session.browser_context is None
        assert session.page is None

    @pytest.mark.asyncio
    async def test_get_cookies_from_real_browser(self):
        """Test that cookies can be extracted from a real browser session."""
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )
        
        session = CamofoxSession(config)
        await session.launch()
        
        # Navigate to a site that sets cookies
        await session.navigate("https://www.upwork.com")
        
        # Get cookies
        cookies = await session.get_cookies()
        
        assert isinstance(cookies, list)
        # Upwork should set some cookies
        # (exact count depends on the site's behavior)
        
        await session.close()

    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """Test complete session lifecycle: launch, navigate, close."""
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )
        
        session = CamofoxSession(config)
        
        # Initially inactive
        assert not session.is_active
        assert session.browser_context is None
        assert session.page is None
        
        # Launch
        await session.launch()
        assert session.is_active
        assert session.browser_context is not None
        assert session.page is not None
        
        # Navigate
        await session.navigate("https://www.upwork.com")
        page_info = await session.get_page_info()
        assert page_info.url == "https://www.upwork.com"
        
        # Close
        await session.close()
        assert not session.is_active

    @pytest.mark.asyncio
    async def test_real_async_lifecycle(self):
        """Test real async lifecycle: context manager, context, page creation."""
        config = SessionConfig(
            account_id="test_account",
            cookies=[],
        )
        
        session = CamofoxSession(config)
        
        # Launch should create context manager, browser context, and page
        await session.launch()
        assert session.camofox is not None
        assert session.browser_context is not None
        assert session.page is not None
        
        # Navigate should use page.goto()
        await session.navigate("https://www.upwork.com")
        
        # Get page info should use page.title() and page.url
        page_info = await session.get_page_info()
        assert page_info.title is not None
        assert page_info.url is not None
        
        # Get cookies should use context.cookies()
        cookies = await session.get_cookies()
        assert isinstance(cookies, list)
        
        # Close should properly exit context manager
        await session.close()
        assert session.browser_context is None
        assert session.page is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
