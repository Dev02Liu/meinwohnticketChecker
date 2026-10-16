"""Thin GraphQL client for the apartment search service of meinwohnticket.wien.

The site is a React app talking to several GraphQL services behind a login gateway
("PVP Standardportal"). When the session is missing or expired, the gateway answers
with an HTML page and the header ``x-stdportal-error: AUTHENTICATION_REQUIRED``.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import BASE_URL

log = logging.getLogger(__name__)

SEARCH_SERVICE = "/api/was"  # "wohnungAngebotSuche"
SESSION_COOKIE_NAME = "wswinteressentenportalSessionCookiewwwmeinwohnticketwien"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# Identical to the query the web app sends (extracted from its JS bundle).
SEARCH_QUERY = """
query searchWohnungen($sort: WohnungSearchSort, $filter: WohnungSearchFilter, $page: Page!) {
  searchWohnungen(sort: $sort, filter: $filter, page: $page) {
    totalHits
    hits {
      angebotUuid
      suchbild { mediaId typ }
      mieteGesamt
      eigenmittelGesamt
      gefoerderterKaufpreis
      qmZinsflaeche
      nutzung
      raumanzahl
      plz
      ort
      strasse
      orientierungsnummer
      stiege
      tuernummer
      ausstattung
      erstellungszeitpunkt
      vergabetyp
      wohnungsart
      smartZusicherung
    }
  }
}
"""


class AuthRequired(Exception):
    """The session cookie is missing, invalid or expired."""


class ApiError(Exception):
    """The API answered, but with an error."""


class MwtClient:
    def __init__(self, cookies: list[dict[str, Any]], base_url: str = BASE_URL, timeout: float = 30.0):
        self.base_url = base_url
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            follow_redirects=False,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Origin": base_url,
                "Referer": f"{base_url}/wohnungen",
            },
        )
        host = httpx.URL(base_url).host
        for cookie in cookies:
            domain = (cookie.get("domain") or host).lstrip(".")
            self._http.cookies.set(cookie["name"], cookie["value"], domain=domain, path=cookie.get("path") or "/")

    def close(self) -> None:
        self._http.close()

    def export_cookies(self) -> list[dict[str, Any]]:
        """Current cookies (the server may rotate the session cookie)."""
        return [
            {"name": c.name, "value": c.value, "domain": (c.domain or "").lstrip("."), "path": c.path or "/"}
            for c in self._http.cookies.jar
        ]

    @staticmethod
    def _is_auth_wall(response: httpx.Response) -> bool:
        if response.headers.get("x-stdportal-error") == "AUTHENTICATION_REQUIRED":
            return True
        return "text/html" in response.headers.get("content-type", "")

    def auth_state(self) -> str:
        """``ANONYMOUS``, ``AUTHENTICATED``, ``REGISTERED``, ``IDENTIFIED`` ..."""
        response = self._http.get("/auth/state")
        if self._is_auth_wall(response):
            return "ANONYMOUS"
        response.raise_for_status()
        return str(response.json().get("state", "UNKNOWN"))

    def _graphql(self, service: str, query: str, variables: dict[str, Any], operation_name: str) -> dict[str, Any]:
        response = self._http.post(
            f"{service}/graphql",
            json={"operationName": operation_name, "query": query, "variables": variables},
            headers={"Content-Type": "application/json"},
        )
        if self._is_auth_wall(response):
            raise AuthRequired("The site asked for a login (session missing or expired).")
        if response.status_code >= 400:
            raise ApiError(f"HTTP {response.status_code} from {service}: {response.text[:300]}")
        payload = response.json()
        if payload.get("errors"):
            messages = "; ".join(str(err.get("message", "?")) for err in payload["errors"])
            raise ApiError(f"GraphQL error from {service}: {messages}")
        return payload["data"]

    def search_listings(
        self,
        search_filter: dict[str, Any],
        sort: dict[str, str] | None,
        page_size: int = 24,
        max_results: int = 1000,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Return ``(totalHits, hits)`` across all result pages."""
        hits: list[dict[str, Any]] = []
        seen: set[str] = set()
        offset = 0
        total = 0
        while True:
            variables = {
                "filter": search_filter,
                "sort": sort,
                "page": {"size": page_size, "offset": offset},
            }
            data = self._graphql(SEARCH_SERVICE, SEARCH_QUERY, variables, "searchWohnungen")
            result = data["searchWohnungen"]
            total = int(result.get("totalHits") or 0)
            batch = result.get("hits") or []
            for hit in batch:
                if hit["angebotUuid"] not in seen:
                    seen.add(hit["angebotUuid"])
                    hits.append(hit)
            offset += len(batch)
            if not batch or offset >= total or offset >= max_results:
                break
        log.debug("search returned %d hits (totalHits=%d)", len(hits), total)
        return total, hits
