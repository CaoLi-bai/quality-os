from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from quality_os.browser import launch_browser


def test_refund_main_flow_with_browser_evidence():
    urllib.request.urlopen(urllib.request.Request(os.environ["QUALITY_OS_BASE_URL"] + "/reset", method="POST"), timeout=5).close()
    evidence = Path(os.environ.get("QUALITY_OS_EVIDENCE_DIR", "artifacts/browser-test"))
    evidence.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        context = browser.new_context()
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(5000)
        try:
            page.goto(os.environ["QUALITY_OS_BASE_URL"])
            page.get_by_test_id("order-select").select_option("order-1001")
            page.get_by_test_id("refund-amount").fill("100")
            page.get_by_test_id("idempotency-key").fill("browser-main-001")
            page.get_by_test_id("refund-submit").click()
            expect(page.get_by_test_id("refund-result")).to_contain_text("退款成功")
            expect(page.get_by_test_id("order-summary")).to_contain_text("已退 100 分")
            page.screenshot(path=str(evidence / "refund-success.png"), full_page=True)
        finally:
            page.screenshot(path=str(evidence / "final-state.png"), full_page=True)
            context.tracing.stop(path=str(evidence / "playwright-trace.zip"))
            browser.close()
