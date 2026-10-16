"""Command line entry point.

``python -m checker``              run the checker with the web UI (default)
``python -m checker --no-ui``      run only the check loop (headless, configured via .env)
``python -m checker --once``       run a single check and exit
``python -m checker --login-test`` log in once and print the auth state
``python -m checker --test-notification``
``python -m checker --status``
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys

from .checker import Checker
from .config import Settings
from .db import Database
from .notify import Notifier
from .service import Service

log = logging.getLogger("checker")


def _configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _describe(settings: Settings) -> None:
    log.info("Data directory: %s (config: %s)", settings.data_dir, "yes" if settings.config_path.exists() else "no")
    log.info("Search URL: %s", settings.search_url)
    log.info("Filter: %s | sort: %s", json.dumps(settings.search_filter()), json.dumps(settings.search_sort()))
    log.info("Notification channels: %s", ", ".join(settings.channels) or "none")
    if settings.has_credentials:
        log.info("Login: automatic via Stadt Wien Konto as %s", settings.username)
    elif settings.session_cookie:
        log.info("Login: using a fixed session cookie (no automatic re-login possible)")
    else:
        log.warning("Not configured yet (no credentials)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="checker",
        description="Watch meinwohnticket.wien for new apartments and send notifications.",
    )
    parser.add_argument("--no-ui", action="store_true", help="run the check loop without the web UI")
    parser.add_argument("--host", help="web UI bind address (default: UI_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, help="web UI port (default: UI_PORT or 8080)")
    parser.add_argument("--once", action="store_true", help="run a single check and exit")
    parser.add_argument("--login-test", action="store_true", help="log in once and print the auth state")
    parser.add_argument("--test-notification", action="store_true", help="send a test message to all channels")
    parser.add_argument("--status", action="store_true", help="print the last runs and exit")
    args = parser.parse_args(argv)

    settings = Settings.load()
    _configure_logging(settings)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _describe(settings)

    one_off = args.once or args.login_test or args.test_notification or args.status
    if one_off:
        db = Database(settings.db_path)
        notifier = Notifier(settings)
        checker = Checker(settings, db, notifier)
        try:
            if args.status:
                for run in db.last_runs(15):
                    print(
                        f"{run['started_at']}  {run['status']:5}  total={run['total_hits']}  "
                        f"new={run['new_count']}  gone={run['removed_count']}  {run['error'] or ''}"
                    )
                print(f"{db.active_count()} listing(s) currently stored as active")
                return 0
            if args.test_notification:
                ok = notifier.send(
                    "Wohn-Ticket checker: test",
                    "If you can read this, notifications are configured correctly.",
                    url=settings.search_url,
                    tags=["white_check_mark"],
                )
                print("sent" if ok else "FAILED (see log)")
                return 0 if ok else 1
            if args.login_test:
                print(f"login ok, auth state: {checker.login_test()}")
                return 0
            result = checker.run_once()
            summary = {k: v for k, v in result.items() if k not in ("new", "removed")}
            summary["new"] = len(result.get("new") or [])
            print(json.dumps(summary))
            return 0 if result["status"] == "ok" else 1
        finally:
            db.close()

    service = Service(settings)
    if args.no_ui:
        if not settings.is_configured:
            log.error("Nothing to do: configure MWT_USERNAME/MWT_PASSWORD or start without --no-ui to use the web UI")
            return 2

        def _handle_signal(signum: int, _frame: object) -> None:
            log.info("Received signal %s, shutting down", signum)
            service.stop()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)
        log.info("Checking every %d minute(s)", settings.interval_minutes)
        service.run_loop()
        return 0

    import uvicorn

    from .web import create_app

    host = args.host or settings.ui_host
    port = args.port or settings.ui_port
    service.start()
    log.info("Web UI listening on http://%s:%d", host, port)
    try:
        uvicorn.run(create_app(service), host=host, port=port, log_level="warning")
    finally:
        service.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
