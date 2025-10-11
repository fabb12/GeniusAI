import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Connect to the running application. We need to find the window by its title.
        # This is a bit of a workaround for desktop apps.
        try:
            app = await p.chromium.launch(executable_path="/usr/bin/python3", args=["src/TGeniusAI.py"], headless=False)

            # Wait for the main window to appear.
            page = await app.new_page()
            await page.wait_for_timeout(5000) # Give the app time to load

            # Find the summary tab widget and click the "Riassunto" tab
            await page.get_by_role("tab", name="Riassunto").click()

            # Verify the new tabs exist
            await page.get_by_role("tab", name="Dettagliato Combinato").is_visible()
            await page.get_by_role("tab", name="Note Riunione Combinato").is_visible()

            # Click on the new combined tab
            await page.get_by_role("tab", name="Dettagliato Combinato").click()

            # Take a screenshot
            await page.screenshot(path="jules-scratch/verification/verification.png")

            await app.close()
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())