"""Camofox session manager for account-scoped browser sessions."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import asyncio
from datetime import datetime, UTC
import json
from .interface import BrowserInterface

try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False


@dataclass
class ProxyConfig:
    """Proxy configuration for session launch."""
    protocol: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "protocol": self.protocol,
            "host": self.host,
            "port": self.port,
        }
        if self.username:
            result["username"] = self.username
        if self.password:
            result["password"] = self.password
        return result


@dataclass
class HumanizationConfig:
    """Launch-time humanization configuration."""
    user_agent: Optional[str] = None
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    fonts: Optional[List[str]] = None
    webgl_fingerprint: Optional[Dict[str, Any]] = None
    canvas_fingerprint: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.user_agent:
            result["user_agent"] = self.user_agent
        if self.screen_resolution:
            result["screen_resolution"] = self.screen_resolution
        if self.timezone:
            result["timezone"] = self.timezone
        if self.language:
            result["language"] = self.language
        if self.fonts:
            result["fonts"] = self.fonts
        if self.webgl_fingerprint:
            result["webgl_fingerprint"] = self.webgl_fingerprint
        if self.canvas_fingerprint:
            result["canvas_fingerprint"] = self.canvas_fingerprint
        return result


@dataclass
class Cookie:
    """Cookie representation for session loading."""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path,
        }
        if self.expires:
            result["expires"] = self.expires
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cookie":
        return cls(
            name=data["name"],
            value=data["value"],
            domain=data["domain"],
            path=data.get("path", "/"),
            expires=data.get("expires"),
        )


@dataclass
class SessionState:
    """Session state (localStorage, sessionStorage)."""
    local_storage: Dict[str, str] = field(default_factory=dict)
    session_storage: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        return cls(
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
        )


@dataclass
class SessionConfig:
    """Configuration for launching a Camofox session."""
    account_id: str
    cookies: List[Cookie] = field(default_factory=list)
    session_state: SessionState = field(default_factory=SessionState)
    proxy: Optional[ProxyConfig] = None
    humanization: Optional[HumanizationConfig] = None


class CamofoxSession:
    """Account-scoped Camofox session manager."""

    def __init__(self, config: SessionConfig, browser: Optional[BrowserInterface] = None):
        self.config = config
        self.browser: Optional[BrowserInterface] = browser
        self.camofox: Optional[AsyncCamoufox] = None
        self.browser_context = None
        self.page = None
        self.is_active = False
        self.created_at = datetime.now(UTC)

    async def launch(self) -> None:
        """Launch browser session with cookies, proxy, and humanization."""
        # If fake browser is provided, skip real Camoufox launch
        if self.browser:
            self.is_active = True
            return

        if not CAMOUFOX_AVAILABLE:
            raise RuntimeError("Camoufox SDK is not available. Install camoufox package.")

        # Build Camoufox launch options
        launch_options: Dict[str, Any] = {}

        # Configure proxy if provided
        if self.config.proxy:
            proxy_dict = self.config.proxy.to_dict()
            launch_options["proxy"] = proxy_dict

        # Configure humanization if provided
        if self.config.humanization:
            humanization_dict = self.config.humanization.to_dict()
            launch_options.update(humanization_dict)

        # Launch Camoufox browser as async context manager
        self.camofox = AsyncCamoufox(**launch_options)
        browser = await self.camofox.__aenter__()

        # Create browser context
        self.browser_context = await browser.new_context()

        # Load cookies if provided (after context creation)
        if self.config.cookies:
            cookies_list = [cookie.to_dict() for cookie in self.config.cookies]
            await self.browser_context.add_cookies(cookies_list)

        # Create page
        self.page = await self.browser_context.new_page()

        # Restore session state if provided
        if self.config.session_state.local_storage:
            await self._restore_local_storage(self.config.session_state.local_storage)

        if self.config.session_state.session_storage:
            await self._restore_session_storage(self.config.session_state.session_storage)

        self.is_active = True

    async def _restore_local_storage(self, local_storage: Dict[str, str]) -> None:
        """Restore localStorage from session state."""
        if not self.page:
            return
        # TODO: Implement localStorage restoration via Camoufox
        # This depends on Camoufox's specific API for localStorage manipulation
        # Example: await self.page.evaluate(f"""localStorage.setItem(...)""")

    async def _restore_session_storage(self, session_storage: Dict[str, str]) -> None:
        """Restore sessionStorage from session state."""
        if not self.page:
            return
        # TODO: Implement sessionStorage restoration via Camoufox
        # This depends on Camoufox's specific API for sessionStorage manipulation
        # Example: await self.page.evaluate(f"""sessionStorage.setItem(...)""")

    async def navigate(self, url: str) -> None:
        """Navigate to URL within the session."""
        if not self.is_active:
            raise RuntimeError("Session is not active")

        if self.browser:
            # Use injected browser interface (for testing)
            await self.browser.navigate(url)
        elif self.page:
            # Use real Camoufox page with domcontentloaded and 60s timeout
            await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )
        else:
            raise RuntimeError("Browser page is not available")

    async def get_page_info(self):
        """Get current page title and URL."""
        if self.browser:
            return await self.browser.get_page_info()
        elif self.page:
            from .interface import PageInfo
            title = await self.page.title()
            url = self.page.url
            return PageInfo(title=title, url=url)
        else:
            # Fallback for placeholder implementation
            from .interface import PageInfo
            return PageInfo(title="Upwork", url="https://www.upwork.com")

    async def get_cookies(self) -> List[Cookie]:
        """Get current cookies from the session."""
        if self.browser_context:
            cookies = await self.browser_context.cookies()
            return [Cookie.from_dict(cookie) for cookie in cookies]
        return self.config.cookies

    async def get_session_state(self) -> SessionState:
        """Get current session state from the browser."""
        if self.page:
            # TODO: Implement session state extraction via Camoufox
            # This depends on Camoufox's specific API for localStorage/sessionStorage
            # Example: local_storage = await self.page.evaluate("Object.entries(localStorage)")
            pass
        return self.config.session_state

    async def close(self) -> None:
        """Close session and persist cookies/session-state."""
        if not self.is_active:
            return

        try:
            # Extract cookies from browser
            if self.browser_context:
                cookies = await self.browser_context.cookies()
                self.config.cookies = [Cookie.from_dict(cookie) for cookie in cookies]

                # Extract session state
                # TODO: Implement session state extraction
        finally:
            # Always cleanup browser resources, even if cookie extraction fails
            if self.browser_context:
                # Close browser context
                await self.browser_context.close()

                # Exit Camoufox context manager
                if self.camofox:
                    await self.camofox.__aexit__(None, None, None)

            # Clear references
            self.browser_context = None
            self.page = None
            self.camofox = None
            self.is_active = False


class SessionManager:
    """Manages account-scoped Camofox sessions."""

    def __init__(self, browser_factory: Optional[callable] = None):
        self.sessions: Dict[str, CamofoxSession] = {}
        self.browser_factory = browser_factory

    async def get_session(self, account_id: str, config: SessionConfig) -> CamofoxSession:
        """Get or create a session for the given account."""
        if account_id in self.sessions:
            session = self.sessions[account_id]
            if session.is_active:
                return session
            else:
                del self.sessions[account_id]

        browser = self.browser_factory() if self.browser_factory else None
        session = CamofoxSession(config, browser=browser)
        await session.launch()
        self.sessions[account_id] = session
        return session

    async def close_session(self, account_id: str) -> None:
        """Close and cleanup a session."""
        if account_id in self.sessions:
            session = self.sessions[account_id]
            await session.close()
            del self.sessions[account_id]

    async def close_all(self) -> None:
        """Close all active sessions."""
        for account_id in list(self.sessions.keys()):
            await self.close_session(account_id)
