"""One check cycle: fetch the current listings, diff them against the database, notify."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from . import auth
from .api import SESSION_COOKIE_NAME, AuthRequired, MwtClient
from .config import Settings, build_filter, build_sort
from .db import Database
from .notify import Notifier, format_listing

log = logging.getLogger(__name__)

# Above this many new listings in one check, send one summary instead of single messages.
MAX_INDIVIDUAL_NOTIFICATIONS = 8
# After the first problem notification, remind again every N further failures.
FAILURE_REMINDER_EVERY = 50


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Checker:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        notifier: Notifier,
        login_fn: Callable[..., list[dict[str, Any]]] = auth.login,
        client_factory: Callable[[list[dict[str, Any]]], MwtClient] = MwtClient,
    ):
        self.settings = settings
        self.db = db
        self.notifier = notifier
        self._login_fn = login_fn
        self._client_factory = client_factory
        self._cookies = auth.CookieStore(settings.cookie_path)
        self._client: MwtClient | None = None
        self._lock = threading.RLock()
        self._failures = int(db.get_meta("consecutive_failures", "0") or 0)

    # -- session handling ---------------------------------------------------------
    def _candidate_cookie_sets(self) -> list[tuple[str, list[dict[str, Any]]]]:
        candidates: list[tuple[str, list[dict[str, Any]]]] = []
        saved = self._cookies.load()
        if saved:
            candidates.append(("saved", saved))
        if self.settings.session_cookie:
            manual = {
                "name": SESSION_COOKIE_NAME,
                "value": self.settings.session_cookie,
                "domain": "www.meinwohnticket.wien",
                "path": "/",
            }
            candidates.append(("MWT_SESSION_COOKIE", [manual]))
        return candidates

    def _drop_client(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        self._cookies.clear()

    def reset_session(self) -> None:
        """Forget the current session (e.g. after the credentials changed)."""
        with self._lock:
            self._drop_client()

    def _login(self) -> MwtClient:
        if not self.settings.has_credentials:
            raise auth.LoginError(
                "No valid session: set MWT_USERNAME and MWT_PASSWORD for automatic login, "
                "or provide a fresh MWT_SESSION_COOKIE."
            )
        self._drop_client()
        cookies = self._login_fn(self.settings.username, self.settings.password, self.settings.data_dir)
        self._cookies.save(cookies)
        self._client = self._client_factory(cookies)
        return self._client

    def _fetch(self, search_filter: dict[str, Any], sort: dict[str, str]) -> tuple[int, list[dict[str, Any]]]:
        if self._client is not None:
            try:
                return self._client.search_listings(search_filter, sort)
            except AuthRequired:
                log.warning("Session expired")
                self._drop_client()

        for source, cookies in self._candidate_cookie_sets():
            client = self._client_factory(cookies)
            try:
                result = client.search_listings(search_filter, sort)
            except AuthRequired:
                log.info("Cookies from %s are not valid (anymore)", source)
                client.close()
                continue
            log.info("Using session from %s cookies", source)
            self._client = client
            return result

        client = self._login()
        return client.search_listings(search_filter, sort)

    # -- public API -------------------------------------------------------------------
    def login_test(self) -> str:
        """Force a fresh login and return the resulting auth state."""
        with self._lock:
            client = self._login()
            return client.auth_state()

    def search_preview(self, search_url: str) -> tuple[int, list[dict[str, Any]]]:
        """Run a search for an arbitrary URL without touching the database."""
        with self._lock:
            return self._fetch(build_filter(search_url), build_sort(search_url))

    def run_once(self) -> dict[str, Any]:
        with self._lock:
            return self._run_once()

    def _run_once(self) -> dict[str, Any]:
        started = _now()
        try:
            total, hits = self._fetch(self.settings.search_filter(), self.settings.search_sort())
        except Exception as exc:  # noqa: BLE001 - every failure is recorded and reported
            log.error("Check failed: %s", exc)
            self.db.record_run(started, _now(), "error", error=str(exc)[:1000])
            self._register_failure(exc)
            return {"status": "error", "error": str(exc), "finished_at": _now()}

        now = _now()
        new, reappeared, removed = self.db.record_listings(hits, now)
        if self._client is not None:
            self._cookies.save(self._client.export_cookies())

        first_run = self.db.get_meta("initialized") is None
        if first_run:
            self.db.set_meta("initialized", now)
            log.info("First run: %d listing(s) match right now; they are stored, not reported as new", len(hits))
            if self.settings.notify_on_start:
                self.notifier.send(
                    "Wohn-Ticket checker is running",
                    f"Watching your search. {len(hits)} apartment(s) match right now. "
                    "You will be notified as soon as a new one appears.",
                    url=self.settings.search_url,
                    tags=["house"],
                )
            self.db.mark_notified([hit["angebotUuid"] for hit in hits], now)
        else:
            self._notify_new(new + reappeared, now)
            if removed:
                log.info("%d listing(s) disappeared from the search", len(removed))
                if self.settings.notify_on_removed:
                    names = [format_listing(hit)[0] for hit in removed]
                    self.notifier.send(
                        f"{len(removed)} apartment(s) no longer listed",
                        "\n".join(f"• {name}" for name in names),
                        url=self.settings.search_url,
                        priority="low",
                    )

        self._register_success()
        self.db.record_run(
            started,
            now,
            "ok",
            total_hits=total,
            new_count=len(new) + len(reappeared),
            removed_count=len(removed),
        )
        log.info("Check done: %d matching, %d new, %d gone", len(hits), len(new) + len(reappeared), len(removed))
        return {
            "status": "ok",
            "total": total,
            "new": new + reappeared,
            "removed": removed,
            "first_run": first_run,
            "finished_at": now,
        }

    # -- helpers ---------------------------------------------------------------------------
    def _notify_new(self, hits: list[dict[str, Any]], now: str) -> None:
        if not hits:
            return
        if len(hits) > MAX_INDIVIDUAL_NOTIFICATIONS:
            lines = []
            for hit in hits:
                title, body, _ = format_listing(hit)
                lines.append(f"• {title} – {body.splitlines()[0]}")
            self.notifier.send(
                f"{len(hits)} new apartments",
                "\n".join(lines),
                url=self.settings.search_url,
                priority="high",
                tags=["house"],
            )
        else:
            for hit in hits:
                title, body, url = format_listing(hit)
                self.notifier.send(f"Neue Wohnung: {title}", body, url=url, priority="high", tags=["house"])
        self.db.mark_notified([hit["angebotUuid"] for hit in hits], now)

    def _register_failure(self, exc: Exception) -> None:
        self._failures += 1
        self.db.set_meta("consecutive_failures", str(self._failures))
        threshold = self.settings.failure_threshold
        if self._failures == threshold or (
            self._failures > threshold and (self._failures - threshold) % FAILURE_REMINDER_EVERY == 0
        ):
            self.notifier.send(
                "Wohn-Ticket checker: problem",
                f"The last {self._failures} checks failed. Latest error:\n{str(exc)[:600]}",
                priority="high",
                tags=["warning"],
            )

    def _register_success(self) -> None:
        if self._failures >= self.settings.failure_threshold:
            self.notifier.send("Wohn-Ticket checker: recovered", "Checks are working again.", tags=["white_check_mark"])
        if self._failures:
            self._failures = 0
            self.db.set_meta("consecutive_failures", "0")
