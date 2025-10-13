import asyncio
from playwright.async_api import async_playwright
import os
import psutil
import pygetwindow as gw
import time

async def main():
    async with async_playwright() as p:
        # Find the GeniusAI window PID
        pid = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower() and 'src/TGeniusAI.py' in proc.info['cmdline']:
                pid = proc.info['pid']
                break

        if not pid:
            raise Exception("GeniusAI process not found.")

        app = p.electron.connect_over_cdp(f"http://localhost:8315")

        # Get the main window
        main_window = app.windows[0]
        await main_window.screenshot(path="jules-scratch/verification/01_main_window.png")

        # Load a video
        await main_window.get_by_text("Open Video/Audio").click()

        # It's difficult to interact with native file dialogs with playwright.
        # So instead we will assume a video is loaded and proceed.
        # This is a limitation of the current testing setup.

        # Open the Add Media dialog
        await main_window.get_by_text("Insert").click()
        await main_window.get_by_text("Add Media/Text...").click()

        # Wait for the dialog to appear
        await main_window.wait_for_selector('text="Add Media/Text with Preview"')
        await main_window.screenshot(path="jules-scratch/verification/02_add_media_dialog.png")

        # Enter text
        await main_window.get_by_label("Text:").fill("Test Text Overlay")

        # Click OK
        await main_window.get_by_role("button", name="OK").click()
        await main_window.screenshot(path="jules-scratch/verification/03_text_added.png")

        # The overlay is applied in a thread, so we need to wait for it to complete.
        # We will wait for the output video to be loaded.
        # This is a bit of a hack, but it's the best we can do without more control over the app.
        time.sleep(10) # Wait 10 seconds for the video to be processed.

        await main_window.screenshot(path="jules-scratch/verification/verification.png")

        await app.close()

if __name__ == "__main__":
    asyncio.run(main())