"""Catalog of the search filters offered by meinwohnticket.wien, and URL round-tripping.

The values and German labels mirror the website's "Alle Filter" dialog (October 2026). The
website stores the active filters in the URL query string: lists are joined with ``~`` and
ranges are written as ``min-max`` with either side optional, e.g.
``/wohnungen?bezirke=10~23&anzahlRaeume=2-3&monatlicheKosten=-700``.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .config import DEFAULT_SEARCH_URL, parse_list, parse_range
from .i18n import normalize_language

# label = German (as on the website), label_en = English. Options keep the site's enum values.
FILTER_CATALOG: list[dict[str, Any]] = [
    {
        "param": "wohnungsarten",
        "label": "Art der Wohnung",
        "label_en": "Apartment type",
        "type": "multi",
        "options": [
            {"value": "GEMEINDEWOHNUNG", "label": "Gemeindewohnung", "label_en": "Municipal (Gemeindewohnung)"},
            {"value": "GEFOERDERTE_WOHNUNG", "label": "Geförderte Wohnung", "label_en": "Subsidised rental"},
            {
                "value": "GEFOERDERTE_EIGENTUMSWOHNUNG",
                "label": "Geförderte Eigentumswohnung",
                "label_en": "Subsidised owner-occupied",
            },
        ],
    },
    {
        "param": "bezirke",
        "label": "Bezirk",
        "label_en": "District",
        "type": "multi",
        "layout": "compact",
        "options": [{"value": str(n), "label": f"{n}.", "label_en": f"{n}."} for n in range(1, 24)],
        "help": "leer = alle Bezirke",
        "help_en": "empty = all districts",
    },
    {
        "param": "anzahlRaeume",
        "label": "Wohnräume",
        "label_en": "Rooms",
        "type": "range",
        "unit": "",
        "min": 1,
        "max": 7,
        "step": 1,
        "unbounded": False,
    },
    {
        "param": "flaeche",
        "label": "Größe",
        "label_en": "Size",
        "type": "range",
        "unit": "m²",
        "min": 0,
        "max": 160,
        "step": 1,
        "unbounded": True,
    },
    {
        "param": "monatlicheKosten",
        "label": "Monatliche Kosten",
        "label_en": "Monthly costs",
        "type": "range",
        "unit": "€",
        "min": 0,
        "max": 1600,
        "step": 10,
        "unbounded": True,
        "help": "Gesamtkosten inkl. Steuern und Betriebskosten",
        "help_en": "monthly total including taxes and operating costs",
    },
    {
        "param": "einmaligeKosten",
        "label": "Einmalige Kosten",
        "label_en": "One-time costs",
        "type": "range",
        "unit": "€",
        "min": 0,
        "max": 40000,
        "step": 100,
        "unbounded": True,
        "help": "Eigenmittel (Grund-/Baukosten oder geförderter Kaufpreis), ohne Kaution",
        "help_en": "own funds (Grundkosten, Baukosten or subsidised purchase price), without deposit",
    },
    {
        "param": "foerderungen",
        "label": "Förderung",
        "label_en": "Funding",
        "type": "multi",
        "options": [
            {"value": "SMART_ZUSICHERUNG", "label": "SMART-Wohnungen", "label_en": "SMART apartments"},
            {"value": "SUPER_FOERDERUNG", "label": "Superförderung", "label_en": "Superförderung (extra subsidy)"},
        ],
    },
    {
        "param": "nutzung",
        "label": "Nutzung",
        "label_en": "Type of home",
        "type": "multi",
        "options": [
            {"value": "WOHNUNG", "label": "Wohnung", "label_en": "Apartment"},
            {"value": "MAISONETTE", "label": "Maisonette", "label_en": "Maisonette"},
            {"value": "REIHENHAUS", "label": "Reihenhaus", "label_en": "Terraced house"},
        ],
    },
    {
        "param": "ausstattung",
        "label": "Ausstattung",
        "label_en": "Equipment",
        "type": "multi",
        "options": [
            {"value": "LIFT", "label": "Aufzug", "label_en": "Elevator"},
            {"value": "STUFENLOS", "label": "Stufenlos", "label_en": "Step-free"},
            {"value": "ROLLSTUHLGERECHT", "label": "Rollstuhlgerecht", "label_en": "Wheelchair accessible"},
            {"value": "BADEWANNE", "label": "Badewanne", "label_en": "Bathtub"},
            {"value": "DUSCHE", "label": "Dusche", "label_en": "Shower"},
        ],
    },
    {
        "param": "freiflaechen",
        "label": "Freifläche",
        "label_en": "Outdoor space",
        "type": "multi",
        "options": [
            {"value": "BALKON", "label": "Balkon", "label_en": "Balcony"},
            {"value": "LOGGIA", "label": "Loggia", "label_en": "Loggia"},
            {"value": "TERRASSE", "label": "Terrasse", "label_en": "Terrace"},
            {"value": "GARTEN", "label": "Garten", "label_en": "Garden"},
        ],
        "help": "mindestens eine davon",
        "help_en": "at least one of the selected",
    },
]

_BY_PARAM = {entry["param"]: entry for entry in FILTER_CATALOG}


def _localized(entry: dict[str, Any], key: str, lang: str) -> str:
    if lang == "en":
        return str(entry.get(f"{key}_en") or entry.get(key) or "")
    return str(entry.get(key) or "")


def catalog_for(lang: str) -> list[dict[str, Any]]:
    """The catalog with ``label``/``help`` resolved for one UI language."""
    lang = normalize_language(lang)
    result = []
    for entry in FILTER_CATALOG:
        item = {k: v for k, v in entry.items() if k not in ("label_en", "help_en", "options")}
        item["label"] = _localized(entry, "label", lang)
        help_text = _localized(entry, "help", lang)
        if help_text:
            item["help"] = help_text
        else:
            item.pop("help", None)
        if "options" in entry:
            item["options"] = [
                {"value": opt["value"], "label": _localized(opt, "label", lang)} for opt in entry["options"]
            ]
        result.append(item)
    return result


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def filters_to_url(values: dict[str, Any], base_url: str = DEFAULT_SEARCH_URL) -> str:
    """Build a search URL from ``{param: [values] | {"min": .., "max": ..}}``.

    Unknown parameters are passed through untouched so nothing the site understands gets lost.
    """
    parsed = urlparse(base_url)
    query: list[tuple[str, str]] = []
    ordered = [p for p in _BY_PARAM] + [p for p in values if p not in _BY_PARAM]
    for param in ordered:
        value = values.get(param)
        if value is None:
            continue
        if isinstance(value, dict):
            low, high = _format_number(value.get("min")), _format_number(value.get("max"))
            if low or high:
                query.append((param, f"{low}-{high}"))
        elif isinstance(value, (list, tuple, set)):
            items = [str(v).strip() for v in value if str(v).strip()]
            if items:
                query.append((param, "~".join(items)))
        elif str(value).strip():
            query.append((param, str(value).strip()))
    return urlunparse(parsed._replace(query=urlencode(query, safe="~")))


def url_to_filters(url: str) -> dict[str, Any]:
    """Inverse of :func:`filters_to_url` for the parameters in the catalog (plus ``sortierung``)."""
    params = parse_qs(urlparse(url).query)
    result: dict[str, Any] = {}
    for param, raw_values in params.items():
        raw = raw_values[-1]
        entry = _BY_PARAM.get(param)
        if entry is None:
            if param == "sortierung" and raw.strip():
                result[param] = raw.strip()
            continue
        if entry["type"] == "range":
            rng = parse_range(raw)
            if rng:
                result[param] = rng
        else:
            items = parse_list(raw)
            if items:
                result[param] = items
    return result


def _range_text(label: str, rng: dict[str, Any], unit: str, lang: str) -> str:
    low, high = rng.get("min"), rng.get("max")
    unit_suffix = f" {unit}" if unit and unit != "€" else ""
    prefix = "€ " if unit == "€" else ""
    word_from = "from" if lang == "en" else "ab"
    word_to = "up to" if lang == "en" else "bis"

    def fmt(value: Any) -> str:
        text = _format_number(value)
        if unit == "€" and text.isdigit() and len(text) > 3:
            text = f"{int(text):,}".replace(",", "." if lang != "en" else ",")
        return f"{prefix}{text}{unit_suffix}"

    if low is not None and high is not None:
        if low == high:
            core = fmt(low)
        else:
            core = f"{fmt(low)}–{fmt(high)}" if unit != "€" else f"{fmt(low)} – {fmt(high)}"
    elif low is not None:
        core = f"{word_from} {fmt(low)}"
    else:
        core = f"{word_to} {fmt(high)}"
    return f"{core} {label}" if unit != "€" else f"{label} {core}"


def describe_search(url: str, lang: str = "de") -> list[str]:
    """Human-readable summary of a search URL, e.g. ``["2–3 Wohnräume", "SMART-Wohnungen"]``."""
    lang = normalize_language(lang)
    values = url_to_filters(url)
    parts: list[str] = []
    for entry in FILTER_CATALOG:
        value = values.get(entry["param"])
        if not value:
            continue
        label = _localized(entry, "label", lang)
        if entry["type"] == "range":
            parts.append(_range_text(label, value, entry.get("unit", ""), lang))
        elif entry["param"] == "bezirke":
            parts.append(", ".join(f"{v}." for v in value) + (" district" if lang == "en" else " Bezirk"))
        else:
            labels = {opt["value"]: _localized(opt, "label", lang) for opt in entry["options"]}
            parts.append(", ".join(labels.get(v, v.replace("_", " ").title()) for v in value))
    return parts
