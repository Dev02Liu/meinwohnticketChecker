from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from checker.api import AuthRequired
from checker.config import Settings
from checker.service import Service
from checker.web import create_app
from tests.test_checker import FakeClient, FakeNotifier, hit

SMART_URL = "https://www.meinwohnticket.wien/wohnungen?anzahlRaeume=2-3&foerderungen=SMART_ZUSICHERUNG"
FETCH = {"X-Requested-With": "fetch"}


class Harness:
    def __init__(self, tmp_path, settings: Settings | None = None):
        self.notifier = FakeNotifier()
        self.client = FakeClient([hit("a")])
        self.logins: list[tuple[str, str]] = []

        def fake_login(username, password, data_dir):
            self.logins.append((username, password))
            if password == "wrong":
                raise RuntimeError("The login page says: Benutzername oder Passwort falsch")
            return [{"name": "c", "value": "fresh", "domain": "www.meinwohnticket.wien", "path": "/"}]

        self.service = Service(
            settings or Settings(data_dir=tmp_path),
            login_fn=fake_login,
            client_factory=lambda cookies: self.client,
            notifier_factory=lambda s: self.notifier,
        )
        self.http = TestClient(create_app(self.service))


@pytest.fixture
def unconfigured(tmp_path):
    h = Harness(tmp_path)
    yield h
    h.service.stop()


@pytest.fixture
def configured(tmp_path):
    settings = Settings(data_dir=tmp_path, username="me", password="pw", search_url=SMART_URL, ntfy_topic="t")
    h = Harness(tmp_path, settings)
    yield h
    h.service.stop()


def test_unconfigured_redirects_to_setup(unconfigured):
    response = unconfigured.http.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/settings"
    page = unconfigured.http.get("/settings")
    assert page.status_code == 200
    assert "set up your checker" in page.text


def test_setup_saves_config_and_triggers_first_check(unconfigured, tmp_path):
    payload = {
        "username": "me",
        "password": "pw",
        "search_url": SMART_URL,
        "ntfy_topic": "wohnticket-abc",
        "interval_minutes": "5",
        "notify_on_start": True,
        "notify_on_removed": False,
        "failure_threshold": "3",
    }
    response = unconfigured.http.post("/api/settings", json=payload, headers=FETCH)
    assert response.status_code == 200, response.text
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["username"] == "me" and saved["password"] == "pw"
    assert saved["interval_minutes"] == 5
    assert unconfigured.service.settings.is_configured

    # a check can now run with the new settings (the loop is not running in tests)
    result = unconfigured.service.check_now()
    assert result["status"] == "ok" and result["first_run"] is True
    assert unconfigured.notifier.sent[0]["title"].startswith("Wohn-Ticket checker is running")

    dashboard = unconfigured.http.get("/")
    assert dashboard.status_code == 200
    assert "Meischlgasse 50/3/15" in dashboard.text


def test_settings_validation_errors(unconfigured):
    response = unconfigured.http.post(
        "/api/settings", json={"username": "me", "password": "pw", "search_url": "https://example.com"}, headers=FETCH
    )
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert any("search URL" in e for e in errors)
    assert any("notification channel" in e for e in errors)


def test_blank_secret_keeps_stored_value(configured, tmp_path):
    response = configured.http.post(
        "/api/settings",
        json={"username": "me", "password": "", "search_url": SMART_URL, "ntfy_topic": "t", "interval_minutes": 20},
        headers=FETCH,
    )
    assert response.status_code == 200
    assert configured.service.settings.password == "pw"
    assert configured.service.settings.interval_minutes == 20


def test_changing_search_url_resets_baseline(configured):
    configured.service.check_now()
    assert configured.service.db.get_meta("initialized") is not None
    new_url = SMART_URL + "&bezirke=23"
    configured.http.post(
        "/api/settings", json={"username": "me", "search_url": new_url, "ntfy_topic": "t"}, headers=FETCH
    )
    assert configured.service.db.get_meta("initialized") is None


def test_changing_credentials_resets_session(configured, tmp_path):
    configured.service.check_now()
    assert configured.service.settings.cookie_path.exists()
    configured.http.post(
        "/api/settings", json={"username": "other", "password": "pw2", "search_url": SMART_URL, "ntfy_topic": "t"},
        headers=FETCH,
    )
    assert not configured.service.settings.cookie_path.exists()


def test_post_without_fetch_header_is_rejected(configured):
    response = configured.http.post("/api/check", json={})
    assert response.status_code == 403


def test_login_test_success_and_failure(unconfigured):
    ok = unconfigured.http.post("/api/test/login", json={"username": "me", "password": "pw"}, headers=FETCH)
    assert ok.status_code == 200 and ok.json()["state"] == "REGISTERED"
    assert unconfigured.logins == [("me", "pw")]
    assert unconfigured.service.settings.cookie_path.exists()

    bad = unconfigured.http.post("/api/test/login", json={"username": "me", "password": "wrong"}, headers=FETCH)
    assert bad.status_code == 502
    assert "Passwort falsch" in bad.json()["error"]

    missing = unconfigured.http.post("/api/test/login", json={"username": "me"}, headers=FETCH)
    assert missing.status_code == 400


def test_search_test_returns_preview(configured):
    response = configured.http.post("/api/test/search", json={"search_url": SMART_URL}, headers=FETCH)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["listings"][0]["title"] == "Meischlgasse 50/3/15"
    assert data["listings"][0]["url"].endswith("/wohnungen/a")

    bad = configured.http.post("/api/test/search", json={"search_url": "https://example.com"}, headers=FETCH)
    assert bad.status_code == 400


def test_search_test_reports_auth_problems(unconfigured):
    unconfigured.client.fail_auth = True
    response = unconfigured.http.post("/api/test/search", json={"search_url": SMART_URL}, headers=FETCH)
    assert response.status_code == 502
    assert "No valid session" in response.json()["error"]


def test_notification_test_uses_form_values(unconfigured):
    response = unconfigured.http.post(
        "/api/test/notification", json={"ntfy_topic": "from-form", "search_url": SMART_URL}, headers=FETCH
    )
    assert response.status_code == 200
    assert unconfigured.notifier.sent[-1]["title"] == "Wohn-Ticket checker: test"

    none = unconfigured.http.post("/api/test/notification", json={}, headers=FETCH)
    assert none.status_code == 400


def test_status_and_check_endpoints(configured):
    status = configured.http.get("/api/status").json()
    assert status["configured"] is True
    assert status["channels"] == ["ntfy"]
    assert status["listing_count"] == 0
    triggered = configured.http.post("/api/check", json={}, headers=FETCH)
    assert triggered.status_code == 200


def test_basic_auth_when_ui_password_set(tmp_path):
    settings = Settings(data_dir=tmp_path, username="me", password="pw", search_url=SMART_URL, ntfy_topic="t",
                        ui_password="hunter2")
    h = Harness(tmp_path, settings)
    try:
        assert h.http.get("/").status_code == 401
        assert h.http.get("/healthz").status_code == 200  # health check stays open
        token = base64.b64encode(b"anyone:hunter2").decode()
        assert h.http.get("/", headers={"Authorization": f"Basic {token}"}).status_code == 200
        wrong = base64.b64encode(b"anyone:nope").decode()
        assert h.http.get("/", headers={"Authorization": f"Basic {wrong}"}).status_code == 401
    finally:
        h.service.stop()


def test_notifier_does_not_leak_secrets_in_public_settings_page(configured):
    page = configured.http.get("/settings")
    assert page.status_code == 200
    assert '"password": ""' in page.text or '"password":""' in page.text
    assert "pw" not in page.text.split("const current =")[1].split(";")[0]
