from checker.config import build_filter
from checker.filters import FILTER_CATALOG, describe_search, filters_to_url, url_to_filters

BASE = "https://www.meinwohnticket.wien/wohnungen"
SMART_URL = BASE + "?anzahlRaeume=2-3&foerderungen=SMART_ZUSICHERUNG"


def test_catalog_covers_every_url_parameter_the_config_understands():
    params = {entry["param"] for entry in FILTER_CATALOG}
    assert params == {
        "wohnungsarten", "bezirke", "anzahlRaeume", "flaeche", "monatlicheKosten",
        "einmaligeKosten", "foerderungen", "nutzung", "ausstattung", "freiflaechen",
    }
    for entry in FILTER_CATALOG:
        if entry["type"] == "multi":
            assert entry["options"], entry["param"]
        else:
            assert entry["min"] < entry["max"], entry["param"]


def test_url_to_filters_reads_the_users_search():
    assert url_to_filters(SMART_URL) == {
        "anzahlRaeume": {"min": 2, "max": 3},
        "foerderungen": ["SMART_ZUSICHERUNG"],
    }


def test_filters_to_url_matches_site_encoding():
    url = filters_to_url(
        {
            "bezirke": ["10", "23"],
            "anzahlRaeume": {"min": 2, "max": 3},
            "monatlicheKosten": {"min": None, "max": 700},
            "flaeche": {"min": 40, "max": None},
            "freiflaechen": ["BALKON", "LOGGIA"],
            "foerderungen": [],
            "nutzung": None,
        }
    )
    assert url == (
        BASE + "?bezirke=10~23&anzahlRaeume=2-3&flaeche=40-&monatlicheKosten=-700&freiflaechen=BALKON~LOGGIA"
    )
    # and the checker's GraphQL filter builder understands the result
    flt = build_filter(url)
    assert flt["bezirke"] == ["10", "23"]
    assert flt["mieteGesamt"] == {"min": None, "max": 700}
    assert flt["qmZinsflaeche"] == {"min": 40, "max": None}


def test_round_trip_and_passthrough_of_unknown_params():
    values = {
        "wohnungsarten": ["GEMEINDEWOHNUNG"],
        "einmaligeKosten": {"min": 0, "max": 6000},
        "ausstattung": ["LIFT"],
        "sortierung": "_MIETE_GESAMT",
    }
    url = filters_to_url(values)
    assert "sortierung=_MIETE_GESAMT" in url
    assert url_to_filters(url) == values
    assert filters_to_url({}) == BASE


def test_describe_search():
    assert describe_search(SMART_URL) == ["2–3 Wohnräume", "SMART-Wohnungen"]
    assert describe_search(BASE) == []
    assert describe_search(BASE + "?bezirke=10~23&monatlicheKosten=-700&flaeche=40-&freiflaechen=BALKON~GARTEN") == [
        "10., 23. Bezirk",
        "ab 40 m² Größe",
        "Monatliche Kosten bis € 700",
        "Balkon, Garten",
    ]
    assert describe_search(BASE + "?einmaligeKosten=-6000&anzahlRaeume=3-3") == [
        "3 Wohnräume",
        "Einmalige Kosten bis € 6.000",
    ]
