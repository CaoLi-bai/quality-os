from __future__ import annotations

import os

from playwright.sync_api import Error


def launch_browser(playwright):
    channel = os.getenv("QUALITY_OS_BROWSER_CHANNEL")
    if channel:
        return playwright.chromium.launch(headless=True, channel=channel)
    try:
        return playwright.chromium.launch(headless=True)
    except Error:
        if os.name == "nt":
            return playwright.chromium.launch(headless=True, channel="msedge")
        raise
