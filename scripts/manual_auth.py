"""Manual authentication script for Upwork.

Launches a visible Camoufox browser for one-time manual login and Cloudflare verification,
then extracts and saves cookies and session state for automatic reuse.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camoufox.async_api import AsyncCamoufox


async def manual_auth():
    """Launch visible browser for manual authentication and save credentials."""
    print("=" * 60)
    print("MANUAL AUTHENTICATION FOR UPWORK")
    print("=" * 60)
    print("\nThis will launch a visible Camoufox browser.")
    print("Please complete the following steps:")
    print("1. Login to your Upwork account")
    print("2. Complete any Cloudflare verification")
    print("3. Navigate to the jobs search page")
    print("4. Return here and press Enter when authenticated")
    print("\n" + "=" * 60)
    
    input("\nPress Enter to launch browser...")
    
    # Launch Camoufox with visible browser
    async with AsyncCamoufox(headless=False) as browser:
        # Create browser context
        context = await browser.new_context()
        
        # Create page
        page = await context.new_page()
        
        # Navigate to Upwork
        print("\nNavigating to https://www.upwork.com...")
        await page.goto("https://www.upwork.com", wait_until="domcontentloaded")
        
        print("\nBrowser launched. Please complete authentication.")
        input("\nPress Enter when you have successfully logged in and can see the jobs page...")
        
        # Extract cookies
        print("\nExtracting cookies...")
        cookies = await context.cookies()
        
        # Extract localStorage
        print("Extracting localStorage...")
        local_storage = await page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }
        """)
        
        # Extract sessionStorage
        print("Extracting sessionStorage...")
        session_storage = await page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            }
        """)
        
        # Prepare credentials data
        credentials = {
            "cookies": cookies,
            "local_storage": local_storage,
            "session_storage": session_storage,
            "saved_at": "2026-08-22T12:00:00Z",
            "account_id": "upwork_account"
        }
        
        # Save to file
        output_path = Path(__file__).parent.parent / "tests" / "fixtures" / "auth_credentials.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2)
        
        print(f"\n✅ Credentials saved to: {output_path}")
        print(f"   - {len(cookies)} cookies")
        print(f"   - {len(local_storage)} localStorage items")
        print(f"   - {len(session_storage)} sessionStorage items")
        
        print("\n" + "=" * 60)
        print("AUTHENTICATION COMPLETE")
        print("=" * 60)
        print("\nYou can now use these credentials for automated runs.")
        print("The browser will close in 5 seconds...")
        
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(manual_auth())
