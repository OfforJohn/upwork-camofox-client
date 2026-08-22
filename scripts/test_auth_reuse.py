"""Test script to verify manual authentication and automatic credential reuse."""

import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_camofox.session import CamofoxSession, SessionExpiredError


async def test_auth_reuse():
    """Test automatic credential reuse with persisted session."""
    print("=" * 60)
    print("TESTING AUTOMATIC CREDENTIAL REUSE")
    print("=" * 60)
    
    # Load persisted credentials
    credentials = CamofoxSession.load_persisted_credentials()
    
    if not credentials:
        print("\n❌ No persisted credentials found.")
        print("Please run: python scripts/manual_auth.py")
        print("to complete manual authentication first.")
        return False
    
    print(f"\n✅ Found persisted credentials (saved: {credentials.get('saved_at', 'unknown')})")
    print(f"   - {len(credentials.get('cookies', []))} cookies")
    print(f"   - {len(credentials.get('local_storage', {}))} localStorage items")
    print(f"   - {len(credentials.get('session_storage', {}))} sessionStorage items")
    
    # Create session config from credentials
    config = CamofoxSession.create_config_from_credentials(
        account_id="upwork_test",
        credentials=credentials
    )
    
    print("\nLaunching session with persisted credentials...")
    
    # Launch session
    session = CamofoxSession(config)
    
    try:
        await session.launch()
        print("✅ Session launched successfully")
        
        # Test navigation
        print("\nTesting navigation to Upwork...")
        await session.navigate("https://www.upwork.com/nx/search/jobs/?q=python")
        print("✅ Navigation successful")
        
        # Get page info
        page_info = await session.get_page_info()
        print(f"\n✅ Current page:")
        print(f"   - Title: {page_info.title}")
        print(f"   - URL: {page_info.url}")
        
        # Check if we're on the search page
        if "search" in page_info.url.lower() and "jobs" in page_info.url.lower():
            print("\n✅ SUCCESS: Session is authenticated and can access job search")
            print("\n" + "=" * 60)
            print("AUTOMATIC CREDENTIAL REUSE WORKING")
            print("=" * 60)
            return True
        else:
            print("\n⚠️  WARNING: Not on expected search page")
            print(f"   Current URL: {page_info.url}")
            return False
            
    except SessionExpiredError as e:
        print(f"\n❌ Session expired: {e}")
        print("Please run: python scripts/manual_auth.py")
        print("to re-authenticate.")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        await session.close()


if __name__ == "__main__":
    success = asyncio.run(test_auth_reuse())
    sys.exit(0 if success else 1)
