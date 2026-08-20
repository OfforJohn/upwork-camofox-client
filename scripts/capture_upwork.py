import asyncio
from pathlib import Path

from packages.domain_camofox.session import CamofoxSession, SessionConfig


async def main():
    session = CamofoxSession(
        SessionConfig(account_id="manual_capture", cookies=[])
    )
    await session.launch()

    try:
        # Temporary response logger to observe Upwork search API
        async def log_response(response):
            url = response.url
            status = response.status
            content_type = response.headers.get("content-type", "unknown")

            # Only log JSON responses that might be search-related
            if "application/json" in content_type:
                print(f"[RESPONSE] URL: {url}")
                print(f"[RESPONSE] Status: {status}")
                print(f"[RESPONSE] Content-Type: {content_type}")

                # Try to get top-level keys without printing payload values
                try:
                    import json
                    # Only peek at the first 5000 chars to avoid large payloads
                    text = await response.text()
                    if len(text) < 5000:  # Only parse small responses
                        data = json.loads(text)
                        if isinstance(data, dict):
                            print(f"[RESPONSE] Top-level keys: {list(data.keys())}")
                        elif isinstance(data, list):
                            print(f"[RESPONSE] Array with {len(data)} items")
                except Exception as e:
                    print(f"[RESPONSE] Could not parse JSON: {e}")

        # Attach response listener to the page
        if session.page:
            session.page.on("response", lambda r: asyncio.create_task(log_response(r)))

        # Navigate to search page
        await session.navigate("https://www.upwork.com/nx/search/jobs/?q=python")

        await asyncio.to_thread(
            input,
            "Log in and complete any challenge in the browser, wait for job cards, then press Enter here to reload and capture network response: ",
        )

        # Reload the page to capture the network response with the listener attached
        print("Reloading page to capture network response...")
        await session.page.reload()

        await asyncio.to_thread(
            input,
            "Log in and complete any challenge in the browser, wait for job cards, then press Enter here: ",
        )

        html = await session.get_page_content()
        page_info = await session.get_page_info()
        print(f"Final page URL: {page_info.url}")
        print(f"Final page title: {page_info.title}")

        output = Path("tests/fixtures/upwork_authenticated_search.html")
        output.write_text(html, encoding="utf-8")
        print(f"saved {len(html):,} characters to {output}")
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
