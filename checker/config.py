"""Settings and search-URL parsing.

Settings come from three layers, each overriding the previous one:

1. built-in defaults,
2. environment variables (``.env`` / ``docker compose``),
3. ``config.json`` in the data directory, written by the web UI.

The website encodes the active filters in the URL query string, e.g.
``/wohnungen?anzahlRaeume=2-3&foerderungen=SMART_ZUSICHERUNG&bezirke=10~12``.
We translate that into the GraphQL ``WohnungSearchFilter`` the site itself sends.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse

from .i18n import DEFAULT_LANGUAGE, normalize_language, translate

log = logging.getLogger(__name__)

BASE_URL = "https://www.meinwohnticket.wien"
DEFAULT_SEARCH_URL = f"{BASE_URL}/wohnungen"
CONFIG_FILENAME = "config.json"

# URL parameter -> GraphQL field for list-valued filters (values joined with "~").
LIST_PARAMS: dict[str, str] = {
    "wohnungsarten": "wohnungsarten",
    "bezirke": "bezirke",
    "ausstattung": "ausstattung",
    "foerderungen": "foerderungen",
    "freiflaechen": "freiflaechen",
    "nutzung": "nutzung",
}
# URL parameter -> GraphQL field for range filters ("min-max", either side optional).
RANGE_PARAMS: dict[str, str] = {
    "anzahlRaeume": "anzahlRaeume",
    "einmaligeKosten": "einmaligeKosten",
    "monatlicheKosten": "mieteGesamt",
    "flaeche": "qmZinsflaeche",
}
SORT_FIELDS = {
    "BEZUGSDATUM",
    "EIGENMITTEL_GESAMT",
    "ERSTELLUNGSZEITPUNKT",
    "MIETE_GESAMT",
    "PLZ",
    "QM_ZINSFLAECHE",
    "STRASSE",
}
DEFAULT_SORT: dict[str, str] = {"field": "ERSTELLUNGSZEITPUNKT", "direction": "DESC"}

# Settings field -> environment variable.
ENV_MAP: dict[str, str] = {
    "username": "MWT_USERNAME",
    "password": "MWT_PASSWORD",
    "session_cookie": "MWT_SESSION_COOKIE",
    "search_url": "MWT_SEARCH_URL",
    "interval_minutes": "CHECK_INTERVAL_MINUTES",
    "notify_on_start": "NOTIFY_ON_START",
    "notify_on_removed": "NOTIFY_ON_REMOVED",
    "failure_threshold": "FAILURE_NOTIFY_THRESHOLD",
    "ntfy_server": "NTFY_SERVER",
    "ntfy_topic": "NTFY_TOPIC",
    "ntfy_token": "NTFY_TOKEN",
    "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
    "telegram_chat_id": "TELEGRAM_CHAT_ID",
    "discord_webhook_url": "DISCORD_WEBHOOK_URL",
    "language": "LANGUAGE",
    "log_level": "LOG_LEVEL",
    "ui_host": "UI_HOST",
    "ui_port": "UI_PORT",
    "ui_password": "UI_PASSWORD",
}
# Fields the web UI may change; these are stored in config.json.
PERSISTED_FIELDS: tuple[str, ...] = (
    "username",
    "password",
    "session_cookie",
    "search_url",
    "interval_minutes",
    "notify_on_start",
    "notify_on_removed",
    "failure_threshold",
    "ntfy_server",
    "ntfy_topic",
    "ntfy_token",
    "telegram_bot_token",
    "telegram_chat_id",
    "discord_webhook_url",
    "language",
)
SECRET_FIELDS: tuple[str, ...] = (
    "password",
    "session_cookie",
    "ntfy_token",
    "telegram_bot_token",
    "discord_webhook_url",
    "ui_password",
)
NTFY_TOPIC_RE = re.compile(r"^[-_A-Za-z0-9]{1,64}$")


# --- search URL parsing -----------------------------------------------------------


def _num(raw: str) -> int | float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return float(raw.replace(",", "."))


def parse_range(value: str) -> dict[str, Any] | None:
    """``"2-3"`` -> ``{"min": 2, "max": 3}``; ``"-700"`` -> ``{"min": None, "max": 700}``."""
    if "-" not in value:
        single = _num(value)
        return None if single is None else {"min": single, "max": single}
    low, high = value.split("-", 1)
    rng = {"min": _num(low), "max": _num(high)}
    if rng["min"] is None and rng["max"] is None:
        return None
    return rng


def parse_list(value: str) -> list[str]:
    return [part.strip() for part in value.split("~") if part.strip()]


def build_filter(search_url: str) -> dict[str, Any]:
    """Build the GraphQL ``WohnungSearchFilter`` from a search URL.

    All list fields are mandatory in the schema (``[X!]!``), so they are always present.
    """
    params = parse_qs(urlparse(search_url).query)
    flt: dict[str, Any] = {field: [] for field in LIST_PARAMS.values()}
    for param, field in LIST_PARAMS.items():
        for raw in params.get(param, []):
            flt[field].extend(parse_list(raw))
    for param, field in RANGE_PARAMS.items():
        raw = params.get(param)
        if raw:
            rng = parse_range(raw[-1])
            if rng:
                flt[field] = rng
    return flt


def build_sort(search_url: str) -> dict[str, str]:
    """``sortierung=_MIETE_GESAMT`` means ascending, ``sortierung=MIETE_GESAMT`` descending."""
    params = parse_qs(urlparse(search_url).query)
    raw = params.get("sortierung")
    if not raw:
        return dict(DEFAULT_SORT)
    value = raw[-1]
    ascending = value.startswith("_")
    field = value.lstrip("_").upper()
    if field not in SORT_FIELDS:
        return dict(DEFAULT_SORT)
    return {"field": field, "direction": "ASC" if ascending else "DESC"}


def is_search_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in {"www.meinwohnticket.wien", "meinwohnticket.wien"}


# --- value coercion ----------------------------------------------------------------


def _to_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _coerce(field: dataclasses.Field, raw: Any) -> Any:
    kind = str(field.type)
    optional = "None" in kind
    if isinstance(raw, str):
        raw = raw.strip()
        if raw == "" and optional:
            return None
    if kind.startswith("bool"):
        return _to_bool(raw)
    if kind.startswith("int"):
        return int(raw)
    if kind.startswith("Path"):
        return Path(raw)
    return str(raw)


def _is_blank(raw: Any) -> bool:
    return raw is None or (isinstance(raw, str) and raw.strip() == "")


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path("/data")
    username: str | None = None
    password: str | None = None
    session_cookie: str | None = None
    search_url: str = DEFAULT_SEARCH_URL
    interval_minutes: int = 10
    notify_on_start: bool = True
    notify_on_removed: bool = False
    failure_threshold: int = 3
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str | None = None
    ntfy_token: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None
    language: str = DEFAULT_LANGUAGE
    log_level: str = "INFO"
    ui_host: str = "127.0.0.1"
    ui_port: int = 8080
    ui_password: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", normalize_language(self.language))

    # -- construction -----------------------------------------------------------------
    @classmethod
    def load(cls, data_dir: Path | str | None = None, env: Mapping[str, str] | None = None) -> "Settings":
        """Defaults <- environment <- config.json."""
        env = os.environ if env is None else env
        directory = Path(data_dir or env.get("DATA_DIR") or "/data")
        return cls.from_sources(directory, env, cls.read_config_file(directory / CONFIG_FILENAME))

    @classmethod
    def from_env(cls) -> "Settings":
        return cls.load()

    @classmethod
    def from_sources(cls, data_dir: Path, env: Mapping[str, str], file_values: Mapping[str, Any]) -> "Settings":
        values: dict[str, Any] = {"data_dir": Path(data_dir)}
        for field in dataclasses.fields(cls):
            if field.name == "data_dir":
                continue
            raw: Any = file_values.get(field.name) if field.name in PERSISTED_FIELDS else None
            if _is_blank(raw):
                env_name = ENV_MAP.get(field.name)
                raw = env.get(env_name) if env_name else None
            if _is_blank(raw):
                continue
            try:
                values[field.name] = _coerce(field, raw)
            except (TypeError, ValueError) as exc:
                log.warning("Ignoring invalid value for %s (%s)", field.name, exc)
        return cls(**values).normalized()

    @staticmethod
    def read_config_file(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            log.warning("Ignoring unreadable %s: %s", path, exc)
            return {}
        return data if isinstance(data, dict) else {}

    def normalized(self) -> "Settings":
        return dataclasses.replace(
            self,
            interval_minutes=max(1, int(self.interval_minutes)),
            failure_threshold=max(1, int(self.failure_threshold)),
            ntfy_server=(self.ntfy_server or "https://ntfy.sh").rstrip("/"),
            search_url=(self.search_url or DEFAULT_SEARCH_URL).strip(),
            language=normalize_language(self.language),
            log_level=(self.log_level or "INFO").upper(),
        )

    def with_updates(self, **changes: Any) -> "Settings":
        """Return a copy with the given fields changed (strings are coerced like env values)."""
        fields = {f.name: f for f in dataclasses.fields(self)}
        coerced: dict[str, Any] = {}
        for name, raw in changes.items():
            if name not in fields or name == "data_dir":
                raise ValueError(f"unknown setting: {name}")
            field = fields[name]
            if _is_blank(raw):
                coerced[name] = None if "None" in str(field.type) else field.default
            else:
                coerced[name] = _coerce(field, raw)
        return dataclasses.replace(self, **coerced).normalized()

    # -- persistence --------------------------------------------------------------------
    @property
    def config_path(self) -> Path:
        return self.data_dir / CONFIG_FILENAME

    def save(self) -> Path:
        """Write the UI-editable fields to config.json (owner-readable only where supported)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = {name: getattr(self, name) for name in PERSISTED_FIELDS}
        tmp = self.config_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.config_path)
        try:
            os.chmod(self.config_path, 0o600)
        except OSError:
            pass
        return self.config_path

    def public_dict(self) -> dict[str, Any]:
        """Settings for the UI: secrets are blanked and reported as ``<field>_set``."""
        data: dict[str, Any] = {}
        for name in PERSISTED_FIELDS:
            value = getattr(self, name)
            if name in SECRET_FIELDS:
                data[name] = ""
                data[f"{name}_set"] = bool(value)
            else:
                data[name] = value
        data["ui_password_set"] = bool(self.ui_password)
        data["configured"] = self.is_configured
        data["channels"] = self.channels
        return data

    # -- derived -----------------------------------------------------------------------------
    @property
    def db_path(self) -> Path:
        return self.data_dir / "checker.sqlite3"

    @property
    def cookie_path(self) -> Path:
        return self.data_dir / "cookies.json"

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    @property
    def is_configured(self) -> bool:
        return self.has_credentials or bool(self.session_cookie)

    @property
    def channels(self) -> list[str]:
        channels = []
        if self.ntfy_topic:
            channels.append("ntfy")
        if self.telegram_bot_token and self.telegram_chat_id:
            channels.append("telegram")
        if self.discord_webhook_url:
            channels.append("discord")
        return channels

    def search_filter(self) -> dict[str, Any]:
        return build_filter(self.search_url)

    def search_sort(self) -> dict[str, str]:
        return build_sort(self.search_url)

    def validate(self, lang: str | None = None) -> list[str]:
        """Human-readable problems that make the configuration unusable."""
        lang = lang or self.language
        problems: list[str] = []
        if not self.is_configured:
            problems.append(translate(lang, "v_credentials"))
        if not is_search_url(self.search_url):
            problems.append(translate(lang, "v_search_url"))
        if not 1 <= self.interval_minutes <= 7 * 24 * 60:
            problems.append(translate(lang, "v_interval"))
        if self.ntfy_topic and not NTFY_TOPIC_RE.match(self.ntfy_topic):
            problems.append(translate(lang, "v_ntfy_topic"))
        if self.ntfy_topic and not self.ntfy_server.startswith(("http://", "https://")):
            problems.append(translate(lang, "v_ntfy_server"))
        if bool(self.telegram_bot_token) != bool(self.telegram_chat_id):
            problems.append(translate(lang, "v_telegram"))
        if self.discord_webhook_url and not self.discord_webhook_url.startswith("https://"):
            problems.append(translate(lang, "v_discord"))
        if not self.channels:
            problems.append(translate(lang, "v_channel"))
        return problems
