"""User-facing texts of the web UI and the notifications, in German and English."""
from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "de"
LANGUAGES: dict[str, str] = {"de": "Deutsch", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # navigation / layout
        "nav_dashboard": "Dashboard",
        "nav_settings": "Settings",
        "footer_disclaimer": "not affiliated with Wohnberatung Wien or the City of Vienna",
        "language": "Language",
        "working": "Working…",
        # dashboard
        "dash_title": "Dashboard",
        "alert_no_channel_1": "No notification channel is configured.",
        "alert_no_channel_link": "Add one in the settings",
        "alert_no_channel_2": ", otherwise new apartments are only logged.",
        "alert_failures": "The last {n} check(s) failed",
        "alert_first_check": (
            "The first check has not run yet. It stores what is currently listed and sends one "
            "confirmation message; from then on every new listing triggers a notification."
        ),
        "watching": "Watching",
        "account": "Account",
        "session_cookie": "session cookie",
        "search": "Search",
        "all_apartments": "all apartments offered to you",
        "open": "open",
        "interval": "Interval",
        "every_minutes": "every {n} min",
        "channels": "Channels",
        "none": "none",
        "status": "Status",
        "now": "Now",
        "checking": "checking…",
        "idle": "idle",
        "last_check": "Last check",
        "ok": "ok",
        "matching_new": "{total} matching, {new} new",
        "error": "error",
        "never": "never",
        "next_check": "Next check",
        "soon": "soon",
        "stored": "Stored",
        "active_listings": "{n} active listing(s)",
        "actions": "Actions",
        "check_now": "Check now",
        "send_test_notification": "Send test notification",
        "currently_matching": "Currently matching ({n})",
        "no_match": "No apartment matches your filters right now. You will be notified when one appears.",
        "recent_checks": "Recent checks",
        "col_time": "Time",
        "col_result": "Result",
        "col_matching": "Matching",
        "col_new": "New",
        "col_gone": "Gone",
        "col_details": "Details",
        "no_checks": "No checks yet.",
        "js_any_moment": "any moment",
        "js_in_seconds": "in {n} s",
        "js_in_minutes": "in {n} min ({time})",
        "js_check_started": "Check started – the page refreshes when it is done.",
        "js_test_sent": "Test notification sent via {channels}.",
        # settings
        "setup_title": "Welcome – let's set up your checker",
        "settings_title": "Settings",
        "setup_intro": (
            "Four short steps: your Stadt Wien Konto login, the apartment search to watch, where to "
            "send notifications, and how often to check. Everything is stored only in this container's data volume."
        ),
        "no_password_warning": (
            "This page is not password protected. Keep the port bound to <code>127.0.0.1</code> (the default) "
            "or set <code>UI_PASSWORD</code> in your <code>.env</code> before exposing it to your network."
        ),
        "step_login": "Stadt Wien Konto",
        "login_help": (
            "The same login you use on meinwohnticket.wien. The checker logs in with a headless browser "
            "and only keeps the session cookie."
        ),
        "username": "Username",
        "password": "Password",
        "stored_keep": "(stored – leave blank to keep)",
        "test_login": "Test login",
        "step_search": "Apartment search to watch",
        "search_help": (
            "The same filters as on the website. Leave everything empty to watch all apartments that are offered to you."
        ),
        "watching_label": "Watching:",
        "advanced_url": "Advanced: search URL",
        "advanced_help": (
            "The filters above are stored as this URL. You can also paste a URL copied from the website's "
            "address bar; the filters update accordingly."
        ),
        "test_search": "Test search",
        "step_notifications": "Notifications",
        "notifications_help": (
            "Configure at least one channel. ntfy is the quickest: install the free ntfy app, subscribe to your topic, done."
        ),
        "ntfy_topic": "ntfy topic",
        "ntfy_topic_hint": "– a long random name; anyone who knows it can read your notifications",
        "generate": "Generate",
        "ntfy_server": "ntfy server",
        "ntfy_token": "ntfy access token",
        "optional": "optional",
        "stored_word": "stored",
        "telegram_token": "Telegram bot token",
        "telegram_chat_id": "Telegram chat id",
        "discord_webhook": "Discord webhook URL",
        "step_behaviour": "Behaviour",
        "interval_label": "Check every … minutes",
        "failure_label": "Warn after … failed checks",
        "notify_on_start_label": "Send a confirmation message after the first check",
        "notify_on_removed_label": "Also notify when a listing disappears",
        "save_start": "Save and start watching",
        "save": "Save",
        "cancel": "Cancel",
        "js_logging_in": "Logging in with a headless browser, this takes a few seconds…",
        "js_login_ok": "Login works (account state: {state}).",
        "js_matches": "{total} apartment(s) match this search right now.",
        "js_showing_first": " Showing the first {n}.",
        "js_test_sent_check": "Test message sent via {channels} – check your device.",
        "js_saved": "Saved. Starting the first check…",
        "js_could_not_save": "Could not save.",
        "js_from": "from",
        "js_to": "to",
        "js_to_open": "to (blank = open)",
        "js_range_from": "from {v}",
        "js_range_to": "up to {v}",
        "js_district": "district",
        # api messages
        "api_credentials_required": "Username and password are required.",
        "api_search_url_required": "Please choose filters or paste a https://www.meinwohnticket.wien/wohnungen?... URL.",
        "api_finish_setup": "Finish the setup first.",
        "api_no_channel": "No notification channel configured.",
        "api_send_failed": "Sending failed. Check the values and the container log.",
        # validation
        "v_credentials": "Enter your Stadt Wien Konto username and password.",
        "v_search_url": "The search URL must be a https://www.meinwohnticket.wien/wohnungen?... link.",
        "v_interval": "The check interval must be between 1 minute and 7 days.",
        "v_ntfy_topic": "The ntfy topic may only contain letters, digits, '-' and '_' (max. 64 characters).",
        "v_ntfy_server": "The ntfy server must be a http(s) URL.",
        "v_telegram": "Telegram needs both the bot token and the chat id.",
        "v_discord": "The Discord webhook must be a https URL.",
        "v_channel": "Configure at least one notification channel (ntfy, Telegram or Discord).",
        # notifications
        "n_running_title": "Wohn-Ticket checker is running",
        "n_running_body": (
            "Watching your search. {n} apartment(s) match right now. "
            "You will be notified as soon as a new one appears."
        ),
        "n_new_title": "New apartment: {title}",
        "n_many_new_title": "{n} new apartments",
        "n_removed_title": "{n} apartment(s) no longer listed",
        "n_problem_title": "Wohn-Ticket checker: problem",
        "n_problem_body": "The last {n} checks failed. Latest error:\n{error}",
        "n_recovered_title": "Wohn-Ticket checker: recovered",
        "n_recovered_body": "Checks are working again.",
        "n_test_title": "Wohn-Ticket checker: test",
        "n_test_body": "If you can read this, notifications are configured correctly.",
        # listing texts
        "l_rooms": "{n} rooms",
        "l_monthly": "Monthly:",
        "l_own_funds": "Own funds:",
        "l_price": "Purchase price:",
        "l_equipment": "Equipment:",
        "l_since": "Listed since:",
        "l_open": "Open listing",
        "l_new_apartment": "New apartment",
        "f_LIFT": "Elevator",
        "f_BALKON": "Balcony",
        "f_LOGGIA": "Loggia",
        "f_TERRASSE": "Terrace",
        "f_GARTEN": "Garden",
        "f_BADEWANNE": "Bathtub",
        "f_DUSCHE": "Shower",
        "f_STUFENLOS": "step-free",
        "f_ROLLSTUHLGERECHT": "wheelchair accessible",
    },
    "de": {
        "nav_dashboard": "Übersicht",
        "nav_settings": "Einstellungen",
        "footer_disclaimer": "kein Angebot der Wohnberatung Wien oder der Stadt Wien",
        "language": "Sprache",
        "working": "Bitte warten…",
        "dash_title": "Übersicht",
        "alert_no_channel_1": "Es ist kein Benachrichtigungskanal eingerichtet.",
        "alert_no_channel_link": "Richten Sie einen in den Einstellungen ein",
        "alert_no_channel_2": ", sonst werden neue Wohnungen nur protokolliert.",
        "alert_failures": "Die letzte(n) {n} Prüfung(en) ist/sind fehlgeschlagen",
        "alert_first_check": (
            "Die erste Prüfung ist noch nicht gelaufen. Sie speichert, was aktuell angeboten wird, und schickt "
            "eine Bestätigung; danach löst jede neue Wohnung eine Benachrichtigung aus."
        ),
        "watching": "Beobachtet",
        "account": "Konto",
        "session_cookie": "Sitzungs-Cookie",
        "search": "Suche",
        "all_apartments": "alle für Sie angebotenen Wohnungen",
        "open": "öffnen",
        "interval": "Intervall",
        "every_minutes": "alle {n} Min.",
        "channels": "Kanäle",
        "none": "keine",
        "status": "Status",
        "now": "Jetzt",
        "checking": "prüft…",
        "idle": "bereit",
        "last_check": "Letzte Prüfung",
        "ok": "ok",
        "matching_new": "{total} passend, {new} neu",
        "error": "Fehler",
        "never": "noch nie",
        "next_check": "Nächste Prüfung",
        "soon": "bald",
        "stored": "Gespeichert",
        "active_listings": "{n} aktive Wohnung(en)",
        "actions": "Aktionen",
        "check_now": "Jetzt prüfen",
        "send_test_notification": "Testbenachrichtigung senden",
        "currently_matching": "Aktuell passend ({n})",
        "no_match": "Derzeit passt keine Wohnung zu Ihren Filtern. Sie werden benachrichtigt, sobald eine erscheint.",
        "recent_checks": "Letzte Prüfungen",
        "col_time": "Zeit",
        "col_result": "Ergebnis",
        "col_matching": "Passend",
        "col_new": "Neu",
        "col_gone": "Weg",
        "col_details": "Details",
        "no_checks": "Noch keine Prüfungen.",
        "js_any_moment": "jeden Moment",
        "js_in_seconds": "in {n} s",
        "js_in_minutes": "in {n} Min. ({time})",
        "js_check_started": "Prüfung gestartet – die Seite aktualisiert sich, sobald sie fertig ist.",
        "js_test_sent": "Testbenachrichtigung gesendet über {channels}.",
        "setup_title": "Willkommen – richten wir Ihren Checker ein",
        "settings_title": "Einstellungen",
        "setup_intro": (
            "Vier kurze Schritte: Ihr Login beim Stadt Wien Konto, die zu beobachtende Wohnungssuche, wohin "
            "Benachrichtigungen gehen sollen und wie oft geprüft wird. Alles bleibt ausschließlich im "
            "Datenvolume dieses Containers."
        ),
        "no_password_warning": (
            "Diese Seite ist nicht passwortgeschützt. Lassen Sie den Port auf <code>127.0.0.1</code> (Standard) "
            "oder setzen Sie <code>UI_PASSWORD</code> in Ihrer <code>.env</code>, bevor Sie sie im Netzwerk freigeben."
        ),
        "step_login": "Stadt Wien Konto",
        "login_help": (
            "Derselbe Login wie auf meinwohnticket.wien. Der Checker meldet sich mit einem unsichtbaren Browser an "
            "und behält nur das Sitzungs-Cookie."
        ),
        "username": "Benutzername",
        "password": "Passwort",
        "stored_keep": "(gespeichert – leer lassen zum Behalten)",
        "test_login": "Login testen",
        "step_search": "Zu beobachtende Wohnungssuche",
        "search_help": (
            "Dieselben Filter wie auf der Website. Lassen Sie alles leer, um alle Ihnen angebotenen Wohnungen zu beobachten."
        ),
        "watching_label": "Beobachtet:",
        "advanced_url": "Erweitert: Such-URL",
        "advanced_help": (
            "Die Filter oben werden als diese URL gespeichert. Sie können auch eine URL aus der Adresszeile der "
            "Website einfügen; die Filter passen sich an."
        ),
        "test_search": "Suche testen",
        "step_notifications": "Benachrichtigungen",
        "notifications_help": (
            "Richten Sie mindestens einen Kanal ein. ntfy geht am schnellsten: kostenlose ntfy-App installieren, "
            "Ihr Thema abonnieren, fertig."
        ),
        "ntfy_topic": "ntfy-Thema",
        "ntfy_topic_hint": "– ein langer zufälliger Name; wer ihn kennt, kann Ihre Benachrichtigungen lesen",
        "generate": "Erzeugen",
        "ntfy_server": "ntfy-Server",
        "ntfy_token": "ntfy-Zugangstoken",
        "optional": "optional",
        "stored_word": "gespeichert",
        "telegram_token": "Telegram-Bot-Token",
        "telegram_chat_id": "Telegram-Chat-ID",
        "discord_webhook": "Discord-Webhook-URL",
        "step_behaviour": "Verhalten",
        "interval_label": "Alle … Minuten prüfen",
        "failure_label": "Warnen nach … fehlgeschlagenen Prüfungen",
        "notify_on_start_label": "Nach der ersten Prüfung eine Bestätigung senden",
        "notify_on_removed_label": "Auch benachrichtigen, wenn eine Wohnung verschwindet",
        "save_start": "Speichern und beobachten",
        "save": "Speichern",
        "cancel": "Abbrechen",
        "js_logging_in": "Anmeldung mit unsichtbarem Browser, das dauert ein paar Sekunden…",
        "js_login_ok": "Login funktioniert (Kontostatus: {state}).",
        "js_matches": "{total} Wohnung(en) passen derzeit zu dieser Suche.",
        "js_showing_first": " Die ersten {n} werden angezeigt.",
        "js_test_sent_check": "Testnachricht gesendet über {channels} – prüfen Sie Ihr Gerät.",
        "js_saved": "Gespeichert. Erste Prüfung startet…",
        "js_could_not_save": "Speichern fehlgeschlagen.",
        "js_from": "von",
        "js_to": "bis",
        "js_to_open": "bis (leer = offen)",
        "js_range_from": "ab {v}",
        "js_range_to": "bis {v}",
        "js_district": "Bezirk",
        "api_credentials_required": "Benutzername und Passwort sind erforderlich.",
        "api_search_url_required": "Bitte Filter wählen oder eine https://www.meinwohnticket.wien/wohnungen?... URL einfügen.",
        "api_finish_setup": "Bitte zuerst die Einrichtung abschließen.",
        "api_no_channel": "Kein Benachrichtigungskanal eingerichtet.",
        "api_send_failed": "Senden fehlgeschlagen. Prüfen Sie die Werte und das Container-Log.",
        "v_credentials": "Geben Sie Benutzername und Passwort Ihres Stadt Wien Kontos ein.",
        "v_search_url": "Die Such-URL muss ein https://www.meinwohnticket.wien/wohnungen?... Link sein.",
        "v_interval": "Das Prüfintervall muss zwischen 1 Minute und 7 Tagen liegen.",
        "v_ntfy_topic": "Das ntfy-Thema darf nur Buchstaben, Ziffern, '-' und '_' enthalten (max. 64 Zeichen).",
        "v_ntfy_server": "Der ntfy-Server muss eine http(s)-URL sein.",
        "v_telegram": "Telegram braucht sowohl den Bot-Token als auch die Chat-ID.",
        "v_discord": "Der Discord-Webhook muss eine https-URL sein.",
        "v_channel": "Richten Sie mindestens einen Benachrichtigungskanal ein (ntfy, Telegram oder Discord).",
        "n_running_title": "Wohn-Ticket-Checker läuft",
        "n_running_body": (
            "Ihre Suche wird beobachtet. Derzeit passen {n} Wohnung(en). "
            "Sie werden benachrichtigt, sobald eine neue erscheint."
        ),
        "n_new_title": "Neue Wohnung: {title}",
        "n_many_new_title": "{n} neue Wohnungen",
        "n_removed_title": "{n} Wohnung(en) nicht mehr gelistet",
        "n_problem_title": "Wohn-Ticket-Checker: Problem",
        "n_problem_body": "Die letzten {n} Prüfungen sind fehlgeschlagen. Letzter Fehler:\n{error}",
        "n_recovered_title": "Wohn-Ticket-Checker: wieder OK",
        "n_recovered_body": "Die Prüfungen funktionieren wieder.",
        "n_test_title": "Wohn-Ticket-Checker: Test",
        "n_test_body": "Wenn Sie das lesen können, sind die Benachrichtigungen richtig eingerichtet.",
        "l_rooms": "{n} Zi.",
        "l_monthly": "Monatlich:",
        "l_own_funds": "Eigenmittel:",
        "l_price": "Kaufpreis:",
        "l_equipment": "Ausstattung:",
        "l_since": "Online seit:",
        "l_open": "Wohnung öffnen",
        "l_new_apartment": "Neue Wohnung",
        "f_LIFT": "Lift",
        "f_BALKON": "Balkon",
        "f_LOGGIA": "Loggia",
        "f_TERRASSE": "Terrasse",
        "f_GARTEN": "Garten",
        "f_BADEWANNE": "Badewanne",
        "f_DUSCHE": "Dusche",
        "f_STUFENLOS": "stufenlos",
        "f_ROLLSTUHLGERECHT": "rollstuhlgerecht",
    },
}


def normalize_language(value: Any) -> str:
    code = str(value or "").strip().lower()[:2]
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def translate(lang: str, key: str, **values: Any) -> str:
    """Look up ``key`` in ``lang`` (falling back to English, then to the key itself) and format it."""
    table = STRINGS.get(normalize_language(lang), STRINGS["en"])
    text = table.get(key) or STRINGS["en"].get(key) or key
    try:
        return text.format(**values) if values else text
    except (KeyError, IndexError):
        return text


def strings_for(lang: str) -> dict[str, str]:
    """Complete table for one language (English fills any gaps), e.g. for the browser side."""
    merged = dict(STRINGS["en"])
    merged.update(STRINGS.get(normalize_language(lang), {}))
    return merged
