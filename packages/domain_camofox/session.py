"""Camofox session manager for account-scoped browser sessions."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Protocol
import asyncio
from datetime import datetime, UTC
import json
from pathlib import Path
from .interface import BrowserInterface

try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False


class SessionExpiredError(Exception):
    """Raised when session has expired and requires manual re-authentication."""
    pass


class BrowserSessionPort(Protocol):
    """The small browser interface the session manager actually needs."""

    async def launch(self, config: "SessionConfig") -> None: ...

    async def navigate(self, url: str) -> None: ...

    async def get_cookies(self) -> List["Cookie"]: ...

    async def get_session_state(self) -> "SessionState": ...

    async def close(self) -> None: ...


class SessionStore(Protocol):
    """Persistence interface for account session data."""

    async def save(
        self,
        account_id: str,
        cookies: List["Cookie"],
        session_state: "SessionState",
    ) -> None: ...


@dataclass
class ProxyConfig:
    """Proxy configuration for session launch."""
    protocol: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.protocol:
            raise ValueError("ProxyConfig.protocol is required")
        if not self.host:
            raise ValueError("ProxyConfig.host is required")
        if not (1 <= self.port <= 65535):
            raise ValueError(f"ProxyConfig.port must be between 1 and 65535, got {self.port}")

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

    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Cookie.name is required")
        if self.value is None:
            raise ValueError("Cookie.value is required")
        if not self.domain:
            raise ValueError("Cookie.domain is required")

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

    def __init__(
        self,
        config: SessionConfig,
        browser: Optional[BrowserSessionPort] = None,
        store: Optional[SessionStore] = None,
    ):
        self.config = config
        self.browser = browser
        self.store = store
        self.camofox: Optional[AsyncCamoufox] = None
        self.browser_context = None
        self.page = None
        self.is_active = False
        self.created_at = datetime.now(UTC)

    @staticmethod
    def load_persisted_credentials(credentials_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Load persisted credentials from file.
        
        Args:
            credentials_path: Path to credentials file. If None, uses default path.
            
        Returns:
            Credentials dict if file exists, None otherwise.
        """
        if credentials_path is None:
            credentials_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "auth_credentials.json"
        
        if not credentials_path.exists():
            return None
        
        with open(credentials_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def create_config_from_credentials(
        account_id: str,
        credentials: Dict[str, Any]
    ) -> SessionConfig:
        """Create SessionConfig from persisted credentials.
        
        Args:
            account_id: Account ID for the session
            credentials: Credentials dict with cookies, local_storage, session_storage
            
        Returns:
            SessionConfig with loaded credentials
        """
        cookies = [
            Cookie(
                name=cookie["name"],
                value=cookie["value"],
                domain=cookie["domain"],
                path=cookie.get("path", "/"),
                expires=cookie.get("expires")
            )
            for cookie in credentials.get("cookies", [])
        ]
        
        session_state = SessionState(
            local_storage=credentials.get("local_storage", {}),
            session_storage=credentials.get("session_storage", {})
        )
        
        return SessionConfig(
            account_id=account_id,
            cookies=cookies,
            session_state=session_state
        )

    async def launch(self) -> None:
        """Launch browser session with cookies, proxy, and humanization."""
        if self.is_active:
            return

        if self.browser:
            await self.browser.launch(self.config)
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
        """Navigate to URL within the session.
        
        Raises:
            SessionExpiredError: If session has expired (redirected to login, etc.)
        """
        self._require_active()

        if self.browser:
            await self.browser.navigate(url)
        elif self.page:
            await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            # Check for session expiry after navigation
            await self._check_session_expiry(url)
        else:
            raise RuntimeError("Browser page is not available")

    async def _check_session_expiry(self, expected_url: str) -> None:
        """Check if session has expired by examining current page.
        
        Raises:
            SessionExpiredError: If session has expired
        """
        if not self.page:
            return
        
        current_url = self.page.url
        
        # Check for login page redirect
        if "login" in current_url.lower() or "signin" in current_url.lower():
            raise SessionExpiredError(
                f"Session expired: redirected to login page ({current_url}). "
                f"Please run manual authentication script to re-authenticate."
            )
        
        # Check if we're still on the expected domain
        from urllib.parse import urlparse
        expected_domain = urlparse(expected_url).netloc
        current_domain = urlparse(current_url).netloc
        
        if current_domain != expected_domain:
            raise SessionExpiredError(
                f"Session expired: redirected from {expected_domain} to {current_domain}. "
                f"Please run manual authentication script to re-authenticate."
            )

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
            return PageInfo(title="", url="")

    async def get_page_content(self) -> str:
        """Get current page HTML content."""
        if self.browser:
            return await self.browser.get_page_content()
        elif self.page:
            return await self.page.content()
        else:
            return ""

    async def get_cookies(self) -> List[Cookie]:
        """Get current cookies from the session."""
        self._require_active()

        if self.browser:
            return await self.browser.get_cookies()
        elif self.browser_context:
            cookies = await self.browser_context.cookies()
            return [Cookie.from_dict(cookie) for cookie in cookies]
        return self.config.cookies

    async def get_session_state(self) -> SessionState:
        """Get current session state from the browser."""
        self._require_active()

        if self.browser:
            return await self.browser.get_session_state()
        elif self.page:
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
            if self.browser:
                cookies = await self.browser.get_cookies()
                state = await self.browser.get_session_state()
                if self.store:
                    await self.store.save(self.config.account_id, cookies, state)
                await self.browser.close()
            elif self.browser_context:
                cookies = await self.browser_context.cookies()
                self.config.cookies = [Cookie.from_dict(cookie) for cookie in cookies]
                # TODO: Extract session state
                if self.store:
                    await self.store.save(
                        self.config.account_id,
                        self.config.cookies,
                        self.config.session_state,
                    )
                await self.browser_context.close()
                if self.camofox:
                    await self.camofox.__aexit__(None, None, None)
        finally:
            self.browser_context = None
            self.page = None
            self.camofox = None
            self.is_active = False

    def _require_active(self) -> None:
        if not self.is_active:
            raise RuntimeError("Session is not active")


class SessionManager:
    """Manages account-scoped Camofox sessions."""

    def __init__(
        self,
        browser_factory: Optional[callable] = None,
        store: Optional[SessionStore] = None,
    ):
        self.sessions: Dict[str, CamofoxSession] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self.browser_factory = browser_factory
        self.store = store

    async def get_session(self, account_id: str, config: SessionConfig) -> CamofoxSession:
        """Get or create a session for the given account."""
        if account_id != config.account_id:
            raise ValueError("account_id must match config.account_id")

        lock = self._locks.setdefault(account_id, asyncio.Lock())
        async with lock:
            existing = self.sessions.get(account_id)
            if existing and existing.is_active:
                return existing

            browser = self.browser_factory(config) if self.browser_factory else None
            session = CamofoxSession(
                config=config,
                browser=browser,
                store=self.store,
            )
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
