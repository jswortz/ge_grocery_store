"""Shared constants and helpers for E2E tests.

Fixtures are in tests/conftest.py (auto-discovered by pytest).
This module provides importable helpers and constants.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
SCREENSHOT_DIR = ROOT / "tests" / "screenshots"
BASE_URL = "http://localhost:8080"
VIEWPORT = {"width": 1920, "height": 1080}
DEVICE_SCALE = 2
RESPONSE_TIMEOUT = 90_000

FORBIDDEN_RETAILER_NAMES = ["Kroger", "HEB", "H-E-B", "Walmart", "Albertsons"]


def check_frontend() -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


frontend_running = pytest.mark.skipif(
    not check_frontend(), reason="Frontend not running on localhost:8080"
)
e2e = pytest.mark.e2e


def send_query(page, text: str, *, timeout: int = RESPONSE_TIMEOUT):
    """Type a query, click send, wait for assistant response, return last message element."""
    page.locator("#chat-input").fill(text)
    page.locator("#send-btn").click()
    page.wait_for_selector(
        ".message.assistant .msg-bubble",
        state="visible",
        timeout=timeout,
    )
    page.wait_for_selector(".typing-indicator", state="hidden", timeout=timeout)
    return page.locator(".message.assistant").last


def select_agent_engine(page, agent_name: str) -> str:
    """Switch to Agent Engine tab and select an agent by name substring."""
    page.locator('button[data-backend="agent-engine"]').click()
    page.wait_for_timeout(500)
    selector = page.locator("#agent-selector")
    options = selector.locator("option").all()
    for opt in options:
        text = opt.text_content() or ""
        if agent_name.lower() in text.lower():
            selector.select_option(opt.get_attribute("value"))
            page.wait_for_timeout(300)
            return text
    pytest.skip(f"Agent '{agent_name}' not found in selector")
    return ""


def wait_for_a2ui(page, *, timeout: int = RESPONSE_TIMEOUT):
    """Wait for an A2UI surface to render and animations to settle."""
    page.wait_for_selector(".a2ui-surface", state="visible", timeout=timeout)
    page.wait_for_timeout(500)
