"""Long-running service: the periodic check loop plus everything the web UI needs.

Settings can be replaced at runtime (the UI writes ``config.json``); the loop picks
them up immediately and runs a check right away.
"""
from __future__ import annotations

import logging
import random
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from . import __version__, auth
from .api import MwtClient
from .checker import Checker
from .config import Settings
from .db import Database
from .filters import describe_search
from .notify import Notifier, format_listing

log = logging.getLogger(__name__)

UNCONFIGURED_POLL_SECONDS = 30


class Service:
    def __init__(
        self,
        settings: Settings,
        login_fn: Callable[..., list[dict[str, Any]]] = auth.login,
        client_factory: Callable[[list[dict[str, Any]]], MwtClient] = MwtClient,
        notifier_factory: Callable[[Settings], Notifier] = Notifier,
    ):
        self.settings = settings
        self.db = Database(settings.db_path)
        self._login_fn = login_fn
        self._client_factory = client_factory
        self._notifier_factory = notifier_factory
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.checker = self._build_checker(settings)
        self.started_at = datetime.now(timezone.utc)
        self.last_result: dict[str, Any] | None = None
        self.next_check_at: datetime | None = None
        self.checking = False

    def _build_checker(self, settings: Settings) -> Checker:
        return Checker(
            settings,
            self.db,
            self._notifier_factory(settings),
            login_fn=self._login_fn,
            client_factory=self._client_factory,
        )

    # -- lifecycle ----------------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self.run_loop, name="check-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        self.db.close()

    def run_loop(self) -> None:
        """Blocking loop; ``start()`` runs it in a background thread."""
        warned = False
        while not self._stop.is_set():
            if self.settings.is_configured:
                warned = False
                try:
                    self.check_now()
                except Exception:  # noqa: BLE001 - the loop must survive anything
                    log.exception("Unexpected error in check cycle")
                delay = self.settings.interval_minutes * 60 + random.uniform(0, 30)
            else:
                if not warned:
                    log.warning("Not configured yet: open the web UI to finish the setup")
                    warned = True
                delay = UNCONFIGURED_POLL_SECONDS
            self.next_check_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            self._wake.wait(delay)
            self._wake.clear()
        log.info("Check loop stopped")

    # -- actions -------------------------------------------------------------------------
    def check_now(self) -> dict[str, Any]:
        """Run one check synchronously (used by the loop and by the UI's 'check now')."""
        self.checking = True
        try:
            result = self.checker.run_once()
        finally:
            self.checking = False
        self.last_result = result
        return result

    def trigger_check(self) -> None:
        """Ask the loop to run a check as soon as possible."""
        self._wake.set()

    def update_settings(self, new: Settings) -> None:
        with self._lock:
            old = self.settings
            new.save()
            self.settings = new
            self.checker = self._build_checker(new)
            credentials_changed = (old.username, old.password, old.session_cookie) != (
                new.username,
                new.password,
                new.session_cookie,
            )
            if credentials_changed:
                self.checker.reset_session()
            if old.search_url != new.search_url:
                log.info("Search URL changed; the next check stores the new baseline without notifying")
                self.db.reset_baseline()
            log.info("Settings saved to %s", new.config_path)
        self.trigger_check()

    def test_login(self, username: str, password: str) -> str:
        """Log in with the given credentials; on success the session is kept for the checker."""
        with self._lock:
            cookies = self._login_fn(username, password, self.settings.data_dir)
            auth.CookieStore(self.settings.cookie_path).save(cookies)
            client = self._client_factory(cookies)
            try:
                return client.auth_state()
            finally:
                client.close()

    def test_search(self, search_url: str) -> tuple[int, list[dict[str, Any]]]:
        return self.checker.search_preview(search_url)

    def test_notification(self, settings: Settings) -> bool:
        if not settings.channels:
            raise ValueError("No notification channel configured.")
        notifier = self._notifier_factory(settings)
        if not notifier.enabled:
            raise ValueError("No notification channel configured.")
        return notifier.send(
            "Wohn-Ticket checker: test",
            "If you can read this, notifications are configured correctly.",
            url=settings.search_url,
            tags=["white_check_mark"],
        )

    # -- status ------------------------------------------------------------------------------
    def status(self) -> dict[str, Any]:
        settings = self.settings
        runs = self.db.last_runs(15)
        listings = [self._listing_view(hit) for hit in self.db.active_listings()]
        return {
            "version": __version__,
            "configured": settings.is_configured,
            "username": settings.username,
            "search_url": settings.search_url,
            "search_summary": describe_search(settings.search_url),
            "interval_minutes": settings.interval_minutes,
            "channels": settings.channels,
            "checking": self.checking,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "next_check_at": self.next_check_at.isoformat(timespec="seconds") if self.next_check_at else None,
            "last_result": _summarise(self.last_result),
            "consecutive_failures": int(self.db.get_meta("consecutive_failures", "0") or 0),
            "initialized": self.db.get_meta("initialized") is not None,
            "runs": runs,
            "listings": listings,
            "listing_count": len(listings),
        }

    @staticmethod
    def _listing_view(hit: dict[str, Any]) -> dict[str, Any]:
        title, body, url = format_listing(hit)
        return {
            "uuid": hit.get("angebotUuid"),
            "title": title,
            "lines": body.splitlines(),
            "url": url,
            "first_seen": hit.get("_first_seen"),
            "smart": bool(hit.get("smartZusicherung")),
        }


def _summarise(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if result is None:
        return None
    if result.get("status") != "ok":
        return {"status": "error", "error": result.get("error"), "finished_at": result.get("finished_at")}
    return {
        "status": "ok",
        "total": result.get("total"),
        "new": len(result.get("new") or []),
        "removed": len(result.get("removed") or []),
        "first_run": result.get("first_run", False),
        "finished_at": result.get("finished_at"),
    }
