"""Shared Playwright fixtures for E2E tests.

Provides session-scoped browser, function-scoped pages, screenshot helpers,
and config loading.  All E2E tests require the frontend running on
``http://localhost:8080`` — launch it with ``python -m src.frontend``.

Non-fixture helpers (send_query, select_agent_engine, etc.) live in
``tests/e2e_helpers.py`` so test files can import them directly.
"""

from __future__ import annotations

import pytest
import yaml

from e2e_helpers import BASE_URL, SCREENSHOT_DIR, SETTINGS_PATH

VIEWPORT = {"width": 1920, "height": 1080}
DEVICE_SCALE = 2


def _get_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        pytest.skip("playwright not installed (pip install playwright)")


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def config():
    with open(SETTINGS_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def screenshot_dir():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOT_DIR


@pytest.fixture(scope="session")
def browser():
    sync_playwright = _get_sync_playwright()
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        yield b
        b.close()


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def browser_context(browser):
    ctx = browser.new_context(
        viewport=VIEWPORT,
        device_scale_factor=DEVICE_SCALE,
    )
    yield ctx
    ctx.close()


@pytest.fixture()
def page(browser_context):
    pg = browser_context.new_page()
    console_log: list[str] = []
    pg.on("console", lambda msg: console_log.append(f"[{msg.type}] {msg.text}"))
    pg.console_log = console_log  # type: ignore[attr-defined]
    yield pg
    pg.close()


@pytest.fixture()
def live_page(page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("#brand-name", state="visible", timeout=10_000)
    page.wait_for_selector("#chat-input", state="visible", timeout=10_000)
    page.wait_for_timeout(1500)
    return page


@pytest.fixture()
def take_screenshot(screenshot_dir):
    def _capture(page, name: str, *, selector: str | None = None, full_page: bool = False):
        path = screenshot_dir / f"{name}.png"
        if selector:
            el = page.locator(selector).first
            el.screenshot(path=str(path))
        else:
            page.screenshot(path=str(path), full_page=full_page)
        return path
    return _capture
