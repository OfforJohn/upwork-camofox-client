import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.domain_camofox.session import CamofoxSession, SessionConfig


async def main():
    session = CamofoxSession(
        SessionConfig(account_id="manual_capture", cookies=[])
    )
    await session.launch()

    try:
        # Store all JSON responses for later review
        captured_responses = []

        # Temporary response logger to observe Upwork search API
        async def log_response(response):
            nonlocal captured_responses
            url = response.url
            status = response.status
            method = response.request.method if hasattr(response, 'request') else "unknown"
            content_type = response.headers.get("content-type", "unknown")

            # Only log JSON responses that might be search-related
            if "application/json" in content_type:
                print(f"[RESPONSE] Method: {method}")
                print(f"[RESPONSE] URL: {url}")
                print(f"[RESPONSE] Status: {status}")
                print(f"[RESPONSE] Content-Type: {content_type}")

                # Try to get top-level keys without printing payload values
                try:
                    import json
                    # Remove size limit - inspect all JSON responses
                    text = await response.text()
                    data = json.loads(text)
                    if isinstance(data, dict):
                        print(f"[RESPONSE] Top-level keys: {list(data.keys())}")
                    elif isinstance(data, list):
                        print(f"[RESPONSE] Array with {len(data)} items")

                    # Capture ALL JSON responses for review
                    captured_responses.append({
                        "method": method,
                        "url": url,
                        "status": status,
                        "content_type": content_type,
                        "data": data
                    })
                    print(f"[CAPTURED] Response #{len(captured_responses)}: {method} {url}")
                except Exception as e:
                    print(f"[RESPONSE] Could not parse JSON: {e}")

        # Attach response listener to the page
        if session.page:
            session.page.on("response", lambda r: asyncio.create_task(log_response(r)))

        # Navigate to search page (it may redirect to best-matches) with timeout
        try:
            await asyncio.wait_for(
                session.navigate("https://www.upwork.com/nx/search/jobs/?q=python"),
                timeout=30.0
            )
            
            # If redirected to best-matches, try to navigate to actual search results
            if "best-matches" in session.page.url:
                print("[INFO] Redirected to best-matches, attempting to navigate to search results")
                try:
                    # Try direct navigation to search results with different path
                    await asyncio.wait_for(
                        session.navigate("https://www.upwork.com/nx/search/jobs/?q=python"),
                        timeout=30.0
                    )
                except:
                    print("[INFO] Direct navigation still redirects, will try search on page")
        except asyncio.TimeoutError:
            print("[TIMEOUT] Navigation timed out after 30 seconds")
            # Log current state even if navigation timed out
            if session.page:
                current_url = session.page.url
                current_title = await session.page.title()
                print(f"[STATE] Current URL after timeout: {current_url}")
                print(f"[STATE] Current title after timeout: {current_title}")
            raise
        except Exception as e:
            print(f"[ERROR] Navigation failed: {e}")
            # Log current state even if navigation failed
            if session.page:
                current_url = session.page.url
                current_title = await session.page.title()
                print(f"[STATE] Current URL after error: {current_url}")
                print(f"[STATE] Current title after error: {current_title}")
            raise

        await asyncio.to_thread(
            input,
            "Log in and complete any challenge in the browser. Let it redirect if needed. If on best-matches page, try entering 'python' in the search box and pressing Enter to load actual job results. Wait for job cards to load, then press Enter to continue capturing: ",
        )

        print("Continuing to capture responses for 20 more seconds...")
        await asyncio.sleep(20)

        await asyncio.to_thread(
            input,
            "If job cards are visible, press Enter to save captured responses: ",
        )

        # Save all captured responses for review
        import json
        output = Path("tests/fixtures/upwork_search_response.json")
        result = {
            "metadata": {
                "total_responses": len(captured_responses),
                "captured_at": "manual_capture"
            },
            "responses": captured_responses
        }
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"saved {len(captured_responses)} captured responses to {output}")

        # Record final page state
        final_url = session.page.url
        final_title = await session.page.title()
        print(f"[FINAL STATE] URL: {final_url}")
        print(f"[FINAL STATE] Title: {final_title}")
        
        # Check for authentication markers with better selectors
        auth_markers = {}
        try:
            # Check for various authentication indicators
            auth_markers["has_user_avatar"] = await session.page.locator("header [data-test*='avatar'], header [data-test*='user'], .user-avatar").count() > 0
        except:
            auth_markers["has_user_avatar"] = False
        
        try:
            # Check for login button (indicates not logged in)
            auth_markers["has_login_button"] = await session.page.locator("a[href*='/ab/account-security/login'], a[href*='/login']").count() > 0
        except:
            auth_markers["has_login_button"] = False
            
        try:
            # Check for freelancer dashboard elements (indicates logged in)
            auth_markers["has_freelancer_dashboard"] = await session.page.locator("aside, .sidebar, [data-test='sidebar']").count() > 0
        except:
            auth_markers["has_freelancer_dashboard"] = False

        # Capture small DOM snapshot of job cards area
        dom_snapshot = None

        job_card_count = 0
        job_card_locator_used = None
        try:
            # Try multiple possible job card selectors in order of preference
            selectors = [
                "section[data-ev-sublocation='job_feed_tile']",  # Best matches feed tiles
                "section[data-test='job-tile-list']",
                "[data-test*='job-tile']",
                "[data-test*='JobTile']",
                "article[data-test*='job']"
            ]
            for selector in selectors:
                job_cards = session.page.locator(selector)
                count = await job_cards.count()
                if count > 0:
                    job_card_count = count
                    job_card_locator_used = selector
                    dom_snapshot = await job_cards.first.inner_html()
                    print(f"[INFO] Found {count} job cards using selector: {selector}")
                    break
        except Exception as e:
            print(f"[ERROR] Error finding job cards: {e}")
            job_card_count = 0

        # Classify page state (prioritize job cards over URL pattern)
        page_classification = "unknown"
        if "cloudflare" in final_title.lower() or "challenge" in final_title.lower():
            page_classification = "blocked"
        elif not auth_markers.get("has_user_avatar", False) and not auth_markers.get("has_freelancer_dashboard", False) and auth_markers.get("has_login_button", False):
            page_classification = "unauthenticated"
        elif job_card_count > 0:
            page_classification = "results"
        elif job_card_count == 0 and "/search/jobs/" in final_url:
            page_classification = "empty"
        elif "/nx/find-work/best-matches" in final_url:
            page_classification = "redirected"
        elif auth_markers.get("has_freelancer_dashboard", False):
            page_classification = "authenticated_redirect"
        else:
            page_classification = "unknown"

        # Save page state
        page_state = {
            "final_url": final_url,
            "final_title": final_title,
            "auth_markers": auth_markers,
            "dom_snapshot": dom_snapshot,
            "job_card_count": job_card_count,
            "job_card_locator_used": job_card_locator_used,
            "page_classification": page_classification,
            "captured_at": "manual_capture"
        }
        page_state_output = Path("tests/fixtures/upwork_page_state.json")
        page_state_output.write_text(json.dumps(page_state, indent=2), encoding="utf-8")
        print(f"saved page state to {page_state_output}")
        print(f"Final page URL: {final_url}")
        print(f"Final page title: {final_title}")
        print(f"Auth markers: {auth_markers}")

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
