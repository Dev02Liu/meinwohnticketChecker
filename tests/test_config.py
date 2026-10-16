import json

from checker.config import DEFAULT_SORT, Settings, build_filter, build_sort, is_search_url, parse_range

EMPTY_LISTS = {
    "wohnungsarten": [],
    "bezirke": [],
    "ausstattung": [],
    "foerderungen": [],
    "freiflaechen": [],
    "nutzung": [],
}
SMART_URL = "https://www.meinwohnticket.wien/wohnungen?anzahlRaeume=2-3&foerderungen=SMART_ZUSICHERUNG"


def test_filter_from_smart_search_url():
    assert build_filter(SMART_URL) == {
        **EMPTY_LISTS,
        "foerderungen": ["SMART_ZUSICHERUNG"],
        "anzahlRaeume": {"min": 2, "max": 3},
    }


def test_filter_lists_and_open_ranges():
    url = (
        "https://www.meinwohnticket.wien/wohnungen?bezirke=10~12~23&monatlicheKosten=-700"
        "&flaeche=40-&wohnungsarten=GEMEINDEWOHNUNG&ausstattung=LIFT~BALKON&einmaligeKosten=0-6000.5"
    )
    flt = build_filter(url)
    assert flt["bezirke"] == ["10", "12", "23"]
    assert flt["mieteGesamt"] == {"min": None, "max": 700}
    assert flt["qmZinsflaeche"] == {"min": 40, "max": None}
    assert flt["wohnungsarten"] == ["GEMEINDEWOHNUNG"]
    assert flt["ausstattung"] == ["LIFT", "BALKON"]
    assert flt["einmaligeKosten"] == {"min": 0, "max": 6000.5}
    assert "anzahlRaeume" not in flt


def test_filter_without_query_has_all_mandatory_lists():
    assert build_filter("https://www.meinwohnticket.wien/wohnungen") == EMPTY_LISTS


def test_parse_range_edge_cases():
    assert parse_range("") is None
    assert parse_range("-") is None
    assert parse_range("2") == {"min": 2, "max": 2}
    assert parse_range("1,5-2") == {"min": 1.5, "max": 2}


def test_sort_parsing():
    base = "https://www.meinwohnticket.wien/wohnungen"
    assert build_sort(base) == DEFAULT_SORT
    assert build_sort(base + "?sortierung=_MIETE_GESAMT") == {"field": "MIETE_GESAMT", "direction": "ASC"}
    assert build_sort(base + "?sortierung=PLZ") == {"field": "PLZ", "direction": "DESC"}
    assert build_sort(base + "?sortierung=BOGUS") == DEFAULT_SORT


def test_is_search_url():
    assert is_search_url(SMART_URL)
    assert is_search_url("https://meinwohnticket.wien/wohnungen")
    assert not is_search_url("http://www.meinwohnticket.wien/wohnungen")
    assert not is_search_url("https://example.com/wohnungen")
    assert not is_search_url("not a url")


def test_settings_layering_file_over_env_over_defaults(tmp_path):
    (tmp_path / "config.json").write_text(
        json.dumps({"username": "from-file", "interval_minutes": "15", "notify_on_start": False, "ntfy_topic": ""})
    )
    env = {
        "MWT_USERNAME": "from-env",
        "MWT_PASSWORD": "pw",
        "CHECK_INTERVAL_MINUTES": "99",
        "NTFY_TOPIC": "env-topic",
        "UI_PASSWORD": "secret",
        "LOG_LEVEL": "debug",
    }
    settings = Settings.load(tmp_path, env=env)
    assert settings.username == "from-file"  # file wins
    assert settings.password == "pw"  # env fills what the file lacks
    assert settings.interval_minutes == 15  # file wins, coerced to int
    assert settings.notify_on_start is False
    assert settings.ntfy_topic == "env-topic"  # blank file value falls back to env
    assert settings.ui_password == "secret"  # env-only field
    assert settings.log_level == "DEBUG"
    assert settings.data_dir == tmp_path
    assert settings.search_url.endswith("/wohnungen")  # default


def test_settings_save_roundtrip_and_public_dict(tmp_path):
    settings = Settings(data_dir=tmp_path).with_updates(
        username="me", password="pw", search_url=SMART_URL, ntfy_topic="topic", interval_minutes="5"
    )
    path = settings.save()
    assert path == tmp_path / "config.json"
    reloaded = Settings.load(tmp_path, env={})
    assert reloaded.username == "me" and reloaded.password == "pw"
    assert reloaded.interval_minutes == 5
    assert reloaded.search_url == SMART_URL

    public = settings.public_dict()
    assert public["password"] == "" and public["password_set"] is True
    assert public["ntfy_token_set"] is False
    assert public["channels"] == ["ntfy"]
    assert public["configured"] is True
    assert "pw" not in json.dumps(public)


def test_settings_with_updates_blank_clears_optional_and_restores_default():
    settings = Settings(username="x", password="y", ntfy_topic="t", interval_minutes=30)
    updated = settings.with_updates(ntfy_topic="", interval_minutes="")
    assert updated.ntfy_topic is None
    assert updated.interval_minutes == 10


def test_validate_reports_problems():
    problems = Settings(search_url="https://example.com", interval_minutes=0, language="en").validate()
    assert any("username and password" in p for p in problems)
    assert any("search URL" in p for p in problems)
    assert any("interval" in p for p in problems)
    assert any("notification channel" in p for p in problems)

    ok = Settings(username="u", password="p", search_url=SMART_URL, ntfy_topic="abc-123", language="en")
    assert ok.validate() == []

    bad_topic = ok.with_updates(ntfy_topic="has space")
    assert any("ntfy topic" in p for p in bad_topic.validate())

    half_telegram = ok.with_updates(telegram_bot_token="tok")
    assert any("Telegram" in p for p in half_telegram.validate())


def test_language_setting_normalizes_and_translates_validation():
    assert Settings(language="DE").language == "de"
    assert Settings(language="fr").language == "de"  # unknown -> default
    assert Settings.load("/nonexistent", env={"LANGUAGE": "en"}).language == "en"
    german = Settings(search_url="https://example.com").validate()
    assert any("Such-URL" in p for p in german)
