"""Notification channels (ntfy, Telegram, Discord) and message formatting."""
from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import BASE_URL, Settings

log = logging.getLogger(__name__)

VIENNA = ZoneInfo("Europe/Vienna")

KIND_LABELS = {
    "GEMEINDEWOHNUNG": "Gemeindewohnung",
    "GEFOERDERTE_WOHNUNG": "Geförderte Wohnung",
    "GEFOERDERTE_EIGENTUMSWOHNUNG": "Geförderte Eigentumswohnung",
    "WBI_WOHNUNG": "WBI-Wohnung",
}
FEATURE_LABELS = {
    "LIFT": "Lift",
    "BALKON": "Balkon",
    "LOGGIA": "Loggia",
    "TERRASSE": "Terrasse",
    "GARTEN": "Garten",
    "BADEWANNE": "Badewanne",
    "DUSCHE": "Dusche",
    "STUFENLOS": "stufenlos",
    "ROLLSTUHLGERECHT": "rollstuhlgerecht",
}
NTFY_PRIORITY = {"low": 2, "default": 3, "high": 4, "urgent": 5}


def _label(value: str | None, table: dict[str, str]) -> str:
    if not value:
        return ""
    return table.get(value, value.replace("_", " ").title())


def _euro(value: Any) -> str:
    if value is None:
        return "–"
    text = f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {text}"


def listing_url(hit: dict[str, Any]) -> str:
    return f"{BASE_URL}/wohnungen/{hit['angebotUuid']}"


def format_listing(hit: dict[str, Any]) -> tuple[str, str, str]:
    """Return ``(title, body, url)`` for one apartment listing."""
    street = " ".join(part for part in [hit.get("strasse"), hit.get("orientierungsnummer")] if part)
    door = "/".join(str(part) for part in [hit.get("stiege"), hit.get("tuernummer")] if part)
    address = f"{street}/{door}" if door else street
    kind = _label(hit.get("wohnungsart") or hit.get("vergabetyp"), KIND_LABELS)
    if hit.get("smartZusicherung"):
        kind = f"SMART · {kind}" if kind else "SMART"

    rooms = hit.get("raumanzahl")
    size = hit.get("qmZinsflaeche")
    facts = []
    if rooms is not None:
        facts.append(f"{rooms} Zi.")
    if size is not None:
        facts.append(f"{size:g} m²".replace(".", ","))
    lines = [f"{hit.get('plz', '')} {hit.get('ort', '')}".strip(), " · ".join(facts)]
    if kind:
        lines.append(kind)
    if hit.get("mieteGesamt") is not None:
        lines.append(f"Monatlich: {_euro(hit['mieteGesamt'])}")
    if hit.get("eigenmittelGesamt"):
        lines.append(f"Eigenmittel: {_euro(hit['eigenmittelGesamt'])}")
    if hit.get("gefoerderterKaufpreis"):
        lines.append(f"Kaufpreis: {_euro(hit['gefoerderterKaufpreis'])}")
    features = [_label(f, FEATURE_LABELS) for f in hit.get("ausstattung") or []]
    if features:
        lines.append("Ausstattung: " + ", ".join(features))
    published = hit.get("erstellungszeitpunkt")
    if published:
        try:
            stamp = datetime.fromisoformat(published).astimezone(VIENNA)
            lines.append(f"Online seit: {stamp:%d.%m.%Y %H:%M}")
        except ValueError:
            pass
    body = "\n".join(line for line in lines if line)
    return address or "Neue Wohnung", body, listing_url(hit)


class Notifier:
    def __init__(self, settings: Settings, http: httpx.Client | None = None):
        self._settings = settings
        self._http = http or httpx.Client(timeout=20)
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
            payload["actions"] = [{"action": "view", "label": "Öffnen", "url": url}]
        headers = {}
        if self._settings.ntfy_token:
            headers["Authorization"] = f"Bearer {self._settings.ntfy_token}"
        response = self._http.post(self._settings.ntfy_server, json=payload, headers=headers)
        response.raise_for_status()

    def _send_telegram(self, title: str, body: str, url: str | None, priority: str, tags: list[str]) -> None:
        text = f"<b>{html.escape(title)}</b>\n{html.escape(body)}"
        if url:
            text += f'\n<a href="{html.escape(url)}">Wohnung öffnen</a>'
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
