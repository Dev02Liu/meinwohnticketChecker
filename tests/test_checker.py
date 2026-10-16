from __future__ import annotations

from pathlib import Path

import pytest

from checker.api import AuthRequired
from checker.checker import Checker
from checker.config import Settings
from checker.db import Database
from checker.notify import format_listing


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = dict(
        username="user",
        password="secret",
        session_cookie=None,
        search_url="https://www.meinwohnticket.wien/wohnungen?anzahlRaeume=2-3&foerderungen=SMART_ZUSICHERUNG",
        interval_minutes=10,
        data_dir=tmp_path,
        notify_on_start=True,
        notify_on_removed=False,
        failure_threshold=2,
        ntfy_server="https://ntfy.sh",
        ntfy_topic="test",
        ntfy_token=None,
        telegram_bot_token=None,
        telegram_chat_id=None,
        discord_webhook_url=None,
        log_level="INFO",
    )
    values.update(overrides)
    return Settings(**values)


def hit(uuid: str, **extra) -> dict:
    base = {
        "angebotUuid": uuid,
        "suchbild": {"mediaId": "x.jpg", "typ": "STIEGE"},
        "mieteGesamt": 599.34,
        "eigenmittelGesamt": 0,
        "gefoerderterKaufpreis": None,
        "qmZinsflaeche": 54.99,
        "nutzung": "WOHNUNG",
        "raumanzahl": 2,
        "plz": "1230",
        "ort": "Wien",
        "strasse": "Meischlgasse",
        "orientierungsnummer": "50",
        "stiege": "3",
        "tuernummer": "15",
        "ausstattung": ["LIFT", "BADEWANNE"],
        "erstellungszeitpunkt": "2026-10-16T06:38:16.014+02:00",
        "vergabetyp": "ANBOTSWOHNUNG",
        "wohnungsart": "GEFOERDERTE_WOHNUNG",
        "smartZusicherung": True,
    }
    base.update(extra)
    return base


class FakeClient:
    def __init__(self, hits: list[dict] | None = None, fail_auth: bool = False):
        self.hits = hits or []
        self.fail_auth = fail_auth
        self.closed = False
        self.calls = 0

    def search_listings(self, search_filter, sort, **_):
        self.calls += 1
        if self.fail_auth:
            raise AuthRequired("expired")
        return len(self.hits), list(self.hits)

    def export_cookies(self):
        return [{"name": "c", "value": "v", "domain": "www.meinwohnticket.wien", "path": "/"}]

    def auth_state(self):
        return "REGISTERED"

    def close(self):
        self.closed = True


class FakeNotifier:
    channels = ["fake"]
    enabled = True

    def __init__(self):
        self.sent: list[dict] = []

    def send(self, title, body, url=None, priority="default", tags=None):
        self.sent.append({"title": title, "body": body, "url": url, "priority": priority})
        return True


@pytest.fixture
def env(tmp_path):
    settings = make_settings(tmp_path)
    db = Database(settings.db_path)
    notifier = FakeNotifier()
    yield settings, db, notifier
    db.close()


def build_checker(settings, db, notifier, client: FakeClient, login_fn=None):
    calls = {"login": 0}

    def fake_login(username, password, data_dir):
        calls["login"] += 1
        return [{"name": "c", "value": "fresh", "domain": "www.meinwohnticket.wien", "path": "/"}]

    checker = Checker(
        settings, db, notifier, login_fn=login_fn or fake_login, client_factory=lambda cookies: client
    )
    return checker, calls


def test_first_run_stores_without_per_listing_notifications(env):
    settings, db, notifier = env
    client = FakeClient([hit("a"), hit("b")])
    checker, calls = build_checker(settings, db, notifier, client)

    result = checker.run_once()

    assert result["status"] == "ok"
    assert calls["login"] == 1  # no cookies yet -> login
    assert db.active_count() == 2
    assert len(notifier.sent) == 1
    assert "2 apartment(s)" in notifier.sent[0]["body"]
    assert settings.cookie_path.exists()


def test_new_listing_triggers_one_notification(env):
    settings, db, notifier = env
    client = FakeClient([hit("a")])
    checker, _ = build_checker(settings, db, notifier, client)
    checker.run_once()
    notifier.sent.clear()

    client.hits = [hit("a"), hit("b", strasse="Neue Gasse", orientierungsnummer="1")]
    result = checker.run_once()

    assert result["status"] == "ok"
    assert [h["angebotUuid"] for h in result["new"]] == ["b"]
    assert len(notifier.sent) == 1
    assert notifier.sent[0]["title"] == "Neue Wohnung: Neue Gasse 1/3/15"
    assert notifier.sent[0]["url"] == "https://www.meinwohnticket.wien/wohnungen/b"
    assert "SMART" in notifier.sent[0]["body"]
    assert "€ 599,34" in notifier.sent[0]["body"]


def test_removed_listing_is_tracked_and_reappearance_notifies_again(env):
    settings, db, notifier = env
    client = FakeClient([hit("a"), hit("b")])
    checker, _ = build_checker(settings, db, notifier, client)
    checker.run_once()
    notifier.sent.clear()

    client.hits = [hit("a")]
    result = checker.run_once()
    assert [h["angebotUuid"] for h in result["removed"]] == ["b"]
    assert db.active_count() == 1
    assert notifier.sent == []  # NOTIFY_ON_REMOVED is off

    client.hits = [hit("a"), hit("b")]
    result = checker.run_once()
    assert [h["angebotUuid"] for h in result["new"]] == ["b"]
    assert len(notifier.sent) == 1


def test_many_new_listings_are_summarised(env):
    settings, db, notifier = env
    client = FakeClient([])
    checker, _ = build_checker(settings, db, notifier, client)
    checker.run_once()
    notifier.sent.clear()

    client.hits = [hit(f"u{i}") for i in range(12)]
    checker.run_once()

    assert len(notifier.sent) == 1
    assert notifier.sent[0]["title"] == "12 new apartments"
    assert notifier.sent[0]["body"].count("•") == 12


def test_expired_session_triggers_relogin(env):
    settings, db, notifier = env
    settings.cookie_path.write_text('[{"name":"c","value":"old","domain":"www.meinwohnticket.wien","path":"/"}]')
    good = FakeClient([hit("a")])
    bad = FakeClient(fail_auth=True)
    clients = iter([bad, good])
    logins = {"n": 0}

    def fake_login(username, password, data_dir):
        logins["n"] += 1
        return [{"name": "c", "value": "fresh", "domain": "www.meinwohnticket.wien", "path": "/"}]

    checker = Checker(settings, db, notifier, login_fn=fake_login, client_factory=lambda cookies: next(clients))
    result = checker.run_once()

    assert result["status"] == "ok"
    assert logins["n"] == 1
    assert bad.closed is True
    assert good.calls == 1


def test_failures_notify_once_at_threshold_and_recovery(env):
    settings, db, notifier = env
    client = FakeClient(fail_auth=True)
    checker, _ = build_checker(
        settings, db, notifier, client, login_fn=lambda *a: (_ for _ in ()).throw(RuntimeError("login broken"))
    )

    assert checker.run_once()["status"] == "error"
    assert notifier.sent == []
    assert checker.run_once()["status"] == "error"
    assert len(notifier.sent) == 1 and "problem" in notifier.sent[0]["title"]
    assert checker.run_once()["status"] == "error"
    assert len(notifier.sent) == 1

    client.fail_auth = False
    client.hits = []
    checker._client = client  # pretend the stored session became valid again
    assert checker.run_once()["status"] == "ok"
    assert notifier.sent[-1]["title"].endswith("recovered")
    assert db.get_meta("consecutive_failures") == "0"


def test_format_listing_matches_site_layout():
    title, body, url = format_listing(hit("abc"))
    assert title == "Meischlgasse 50/3/15"
    assert body.splitlines()[0] == "1230 Wien"
    assert "2 Zi. · 54,99 m²" in body
    assert "SMART · Geförderte Wohnung" in body
    assert "Monatlich: € 599,34" in body
    assert "Ausstattung: Lift, Badewanne" in body
    assert "Online seit: 16.10.2026 06:38" in body
    assert url == "https://www.meinwohnticket.wien/wohnungen/abc"
