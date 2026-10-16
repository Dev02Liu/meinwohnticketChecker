"""Notification channels (ntfy, Telegram, Discord) and message formatting."""
from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import BASE_URL, Settings
from .i18n import translate

log = logging.getLogger(__name__)

VIENNA = ZoneInfo("Europe/Vienna")

# Proper names used by the City of Vienna; kept in German in both languages.
KIND_LABELS = {
    "GEMEINDEWOHNUNG": "Gemeindewohnung",
    "GEFOERDERTE_WOHNUNG": "Geförderte Wohnung",
    "GEFOERDERTE_EIGENTUMSWOHNUNG": "Geförderte Eigentumswohnung",
    "WBI_WOHNUNG": "WBI-Wohnung",
}
NTFY_PRIORITY = {"low": 2, "default": 3, "high": 4, "urgent": 5}


def _kind_label(value: str | None) -> str:
    if not value:
        return ""
    return KIND_LABELS.get(value, value.replace("_", " ").title())


def _feature_label(value: str, lang: str) -> str:
    text = translate(lang, f"f_{value}")
    return text if text != f"f_{value}" else value.replace("_", " ").title()


def _euro(value: Any, lang: str) -> str:
    if value is None:
        return "–"
    text = f"{float(value):,.2f}"
    if lang != "en":
        text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {text}"


def listing_url(hit: dict[str, Any]) -> str:
    return f"{BASE_URL}/wohnungen/{hit['angebotUuid']}"


def format_listing(hit: dict[str, Any], lang: str = "de") -> tuple[str, str, str]:
    """Return ``(title, body, url)`` for one apartment listing."""
    street = " ".join(part for part in [hit.get("strasse"), hit.get("orientierungsnummer")] if part)
    door = "/".join(str(part) for part in [hit.get("stiege"), hit.get("tuernummer")] if part)
    address = f"{street}/{door}" if door else street
    kind = _kind_label(hit.get("wohnungsart") or hit.get("vergabetyp"))
    if hit.get("smartZusicherung"):
        kind = f"SMART · {kind}" if kind else "SMART"

    rooms = hit.get("raumanzahl")
    size = hit.get("qmZinsflaeche")
    facts = []
    if rooms is not None:
        facts.append(translate(lang, "l_rooms", n=rooms))
    if size is not None:
        size_text = f"{size:g}"
        if lang != "en":
            size_text = size_text.replace(".", ",")
        facts.append(f"{size_text} m²")
    lines = [f"{hit.get('plz', '')} {hit.get('ort', '')}".strip(), " · ".join(facts)]
    if kind:
        lines.append(kind)
    if hit.get("mieteGesamt") is not None:
        lines.append(f"{translate(lang, 'l_monthly')} {_euro(hit['mieteGesamt'], lang)}")
    if hit.get("eigenmittelGesamt"):
        lines.append(f"{translate(lang, 'l_own_funds')} {_euro(hit['eigenmittelGesamt'], lang)}")
    if hit.get("gefoerderterKaufpreis"):
        lines.append(f"{translate(lang, 'l_price')} {_euro(hit['gefoerderterKaufpreis'], lang)}")
    features = [_feature_label(f, lang) for f in hit.get("ausstattung") or []]
    if features:
        lines.append(f"{translate(lang, 'l_equipment')} " + ", ".join(features))
    published = hit.get("erstellungszeitpunkt")
    if published:
        try:
            stamp = datetime.fromisoformat(published).astimezone(VIENNA)
            lines.append(f"{translate(lang, 'l_since')} {stamp:%d.%m.%Y %H:%M}")
        except ValueError:
            pass
    body = "\n".join(line for line in lines if line)
    return address or translate(lang, "l_new_apartment"), body, listing_url(hit)


class Notifier:
    def __init__(self, settings: Settings, http: httpx.Client | None = None):
        self._settings = settings
        self._http = http or httpx.Client(timeout=20)
        self.lang = settings.language
        self.channels: list[str] = []
        if settings.ntfy_topic:
            self.channels.append("ntfy")
        if settings.telegram_bot_token and settings.telegram_chat_id:
            self.channels.append("telegram")
        if settings.discord_webhook_url:
            self.channels.append("discord")

    @property
    def enabled(self) -> bool:
        return bool(self.channels)

    def send(
        self,
        title: str,
        body: str,
        url: str | None = None,
        priority: str = "default",
        tags: list[str] | None = None,
    ) -> bool:
        """Send to every configured channel; returns True if at least one succeeded."""
        if not self.channels:
            log.warning("No notification channel configured; message dropped: %s", title)
            return False
        ok = False
        for channel in self.channels:
            try:
                getattr(self, f"_send_{channel}")(title, body, url, priority, tags or [])
                ok = True
                log.info("Notification sent via %s: %s", channel, title)
            except Exception as exc:  # noqa: BLE001 - one failing channel must not break the others
                log.error("Sending via %s failed: %s", channel, exc)
        return ok

    def _send_ntfy(self, title: str, body: str, url: str | None, priority: str, tags: list[str]) -> None:
        payload: dict[str, Any] = {
            "topic": self._settings.ntfy_topic,
            "title": title,
            "message": body,
            "priority": NTFY_PRIORITY.get(priority, 3),
            "tags": tags,
        }
        if url:
            payload["click"] = url
            payload["actions"] = [{"action": "view", "label": translate(self.lang, "open").capitalize(), "url": url}]
        headers = {}
        if self._settings.ntfy_token:
            headers["Authorization"] = f"Bearer {self._settings.ntfy_token}"
        response = self._http.post(self._settings.ntfy_server, json=payload, headers=headers)
        response.raise_for_status()

    def _send_telegram(self, title: str, body: str, url: str | None, priority: str, tags: list[str]) -> None:
        text = f"<b>{html.escape(title)}</b>\n{html.escape(body)}"
        if url:
            text += f'\n<a href="{html.escape(url)}">{html.escape(translate(self.lang, "l_open"))}</a>'
        response = self._http.post(
            f"https://api.telegram.org/bot{self._settings.telegram_bot_token}/sendMessage",
            json={
                "chat_id": self._settings.telegram_chat_id,
                "text": text[:4000],
                "parse_mode": "HTML",
                "disable_notification": priority == "low",
            },
        )
        response.raise_for_status()

    def _send_discord(self, title: str, body: str, url: str | None, priority: str, tags: list[str]) -> None:
        content = f"**{title}**\n{body}"
        if url:
            content += f"\n{url}"
        response = self._http.post(self._settings.discord_webhook_url, json={"content": content[:1900]})
        response.raise_for_status()
