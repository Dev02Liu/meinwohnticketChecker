"""Login via Stadt Wien Konto using a headless browser, and cookie persistence.

The login is a SAML single sign-on: meinwohnticket.wien -> mein.wien.gv.at (login form)
-> back to meinwohnticket.wien, which then sets its session cookie. A real browser
(Playwright / Chromium) handles the redirects and auto-submitted forms reliably;
afterwards only the cookies are kept and used with a plain HTTP client.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .api import USER_AGENT
from .config import BASE_URL

log = logging.getLogger(__name__)

FALLBACK_LOGIN_URL = (
    "https://mein.wien.gv.at/login/?branding=WbWWbis"
    "&redirect=https://www.meinwohnticket.wien/loginredirect"
)
OK_STATES = {"AUTHENTICATED", "REGISTERED", "IDENTIFIED", "IDENTIFICATION_FAILED"}


class LoginError(Exception):
    """Logging in did not result in an authenticated session."""


def _is_portal_url(url: str) -> bool:
    """True when the browser is back on meinwohnticket.wien (the login URL merely *mentions* it)."""
    host = urlparse(url).hostname or ""
    return host == "meinwohnticket.wien" or host.endswith(".meinwohnticket.wien")


class CookieStore:
    """Cookies persisted as JSON so restarts do not need a fresh login."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[dict[str, Any]] | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as exc:
            log.warning("Ignoring unreadable cookie file %s: %s", self.path, exc)
            return None
        return data if isinstance(data, list) and data else None

    def save(self, cookies: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def discover_login_url() -> str:
    """The app publishes its login URL in configuration.json; fall back to the known one."""
    try:
        response = httpx.get(f"{BASE_URL}/configuration.json", timeout=15, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        url = response.json()["anwendungsportal"]["loginWithPasswordUrl"]
        if isinstance(url, str) and url.startswith("https://"):
            return url
    except Exception as exc:  # noqa: BLE001 - any failure just means "use the fallback"
        log.warning("Could not read login URL from configuration.json (%s); using fallback", exc)
    return FALLBACK_LOGIN_URL


def login(username: str, password: str, data_dir: Path, timeout_s: int = 90) -> list[dict[str, Any]]:
    """Log in with a headless Chromium and return the meinwohnticket.wien cookies."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    login_url = discover_login_url()
    log.info("Logging in via Stadt Wien Konto (headless browser) ...")
    trace: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=USER_AGENT, locale="de-AT")
            page = context.new_page()
            _record_navigation(page, trace)
            page.goto(login_url, wait_until="domcontentloaded", timeout=timeout_s * 1000)

            # An existing single-sign-on session would skip the form entirely.
            if not _is_portal_url(page.url):
                page.wait_for_selector("#auth_uid", state="visible", timeout=30_000)
                page.fill("#auth_uid", username)
                page.fill("#auth_pwd", password)
                submit = page.locator("#auth_submit")
                if submit.count():
                    submit.first.click()
                else:
                    page.press("#auth_pwd", "Enter")

                deadline = time.monotonic() + timeout_s
                while not _is_portal_url(page.url):
                    site_error = _visible_error(page)
                    if site_error:
                        raise LoginError(_describe_failure(page, data_dir, trace, f"the login page says: {site_error}"))
                    if time.monotonic() > deadline:
                        raise LoginError(_describe_failure(page, data_dir, trace, "timed out waiting for the redirect"))
                    try:
                        page.wait_for_timeout(500)
                    except PlaywrightTimeout:
                        pass

            state = _wait_for_auth_state(page, timeout_s=30)
            if state not in OK_STATES:
                raise LoginError(_describe_failure(page, data_dir, trace, f"auth state is {state!r}"))

            cookies = [c for c in context.cookies() if "meinwohnticket.wien" in (c.get("domain") or "")]
            if not cookies:
                raise LoginError("Login looked successful but no meinwohnticket.wien cookies were set.")
            log.info("Login successful (auth state %s, %d cookie(s))", state, len(cookies))
            return [
                {"name": c["name"], "value": c["value"], "domain": c.get("domain", ""), "path": c.get("path", "/")}
                for c in cookies
            ]
        finally:
            browser.close()


def _wait_for_auth_state(page: Any, timeout_s: int) -> str:
    deadline = time.monotonic() + timeout_s
    state = "UNKNOWN"
    while time.monotonic() < deadline:
        try:
            response = page.request.get(f"{BASE_URL}/auth/state", headers={"Accept": "application/json"})
            if "application/json" in response.headers.get("content-type", ""):
                state = str(response.json().get("state", "UNKNOWN"))
                if state in OK_STATES:
                    return state
            else:
                state = "ANONYMOUS"
        except Exception as exc:  # noqa: BLE001
            log.debug("auth/state probe failed: %s", exc)
        page.wait_for_timeout(2000)
    return state


def _visible_error(page: Any) -> str | None:
    """Text of the login page's error box, if it is shown."""
    try:
        error_box = page.locator("#fehler")
        if error_box.count() and error_box.first.is_visible():
            text = " ".join(error_box.first.inner_text().split())
            return text[:300] or None
    except Exception:  # noqa: BLE001 - the page may be mid-navigation
        pass
    return None


def _record_navigation(page: Any, trace: list[dict[str, Any]]) -> None:
    """Collect top-level document requests/responses for diagnostics (no form values, no cookies)."""

    def on_request(request: Any) -> None:
        if request.resource_type != "document":
            return
        entry: dict[str, Any] = {"t": round(time.time(), 2), "request": request.method, "url": request.url[:200]}
        if request.method == "POST":
            data = request.post_data or ""
            entry["post_fields"] = sorted({part.split("=", 1)[0] for part in data.split("&") if part})
        trace.append(entry)

    def on_response(response: Any) -> None:
        if response.request.resource_type != "document":
            return
        headers = response.headers
        trace.append(
            {
                "t": round(time.time(), 2),
                "response": response.status,
                "url": response.url[:200],
                "location": (headers.get("location") or "")[:200],
                "set_cookie": "set-cookie" in headers,
                "content_type": headers.get("content-type", ""),
            }
        )

    page.on("request", on_request)
    page.on("response", on_response)


def _describe_failure(page: Any, data_dir: Path, trace: list[dict[str, Any]], detail: str | None = None) -> str:
    message = "Login did not produce a session on meinwohnticket.wien."
    if detail:
        message += f" ({detail})"
    try:
        message += f" Browser ended up at: {page.url}"
    except Exception:  # noqa: BLE001
        pass
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        shot = data_dir / "login-failure.png"
        page.screenshot(path=str(shot), full_page=True)
        (data_dir / "login-failure.html").write_text(page.content(), encoding="utf-8")
        (data_dir / "login-trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
        message += f" Diagnostics saved to {data_dir} (login-failure.png/.html, login-trace.json)."
    except Exception:  # noqa: BLE001
        pass
    return message
