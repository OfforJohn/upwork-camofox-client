import asyncio
from pathlib import Path

from packages.domain_camofox.session import CamofoxSession, SessionConfig


async def main():
    session = CamofoxSession(
        SessionConfig(account_id="manual_capture", cookies=[])
    )
    await session.launch()

    try:
        await session.navigate("https://www.upwork.com/nx/search/jobs/?q=python")

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
