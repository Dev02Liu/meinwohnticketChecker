# Mein Wohn-Ticket Checker

🇬🇧 **[English instructions → README.en.md](README.en.md)**

Bekommen Sie eine Push-Nachricht aufs Handy, sobald auf
[meinwohnticket.wien](https://www.meinwohnticket.wien), dem Wohnungsportal der Wohnberatung Wien
(Gemeindewohnungen, geförderte Wohnungen, SMART-Wohnungen), eine neue Wohnung erscheint, die zu
Ihrer Suche passt.

Statt jeden Tag die Website zu prüfen, läuft ein kleines Programm auf Ihrem Computer, meldet sich
mit Ihrem Stadt Wien Konto an, prüft Ihre Suche alle paar Minuten und schickt neue Angebote aufs
Handy. Eingerichtet wird alles im Browser, auf Deutsch oder Englisch, ohne Konfigurationsdateien.

## Ist das etwas für mich?

Sie brauchen:

- ein **Wiener Wohn-Ticket** und den **Stadt Wien Konto**-Login, den Sie auf meinwohnticket.wien verwenden,
- einen **Computer, der eingeschaltet bleibt**, solange Sie benachrichtigt werden wollen (ein PC
  oder Mac, der tagsüber läuft, ein Mini-PC, ein NAS oder ein Raspberry Pi; geprüft wird nur,
  solange dieser Computer läuft),
- die kostenlose **[ntfy](https://ntfy.sh)-App** am Handy (Telegram oder Discord gehen auch),
- **Docker Desktop** (kostenlos), einmalig installiert. Die Schritte unten führen Sie durch.

Wer schon einmal ein Programm installiert und einen Ordner entpackt hat, schafft das. Beim ersten
Mal dauert es etwa 15 Minuten, die meiste Zeit davon wartet man auf Downloads.

## Installation Schritt für Schritt

### Windows

1. **Docker Desktop installieren.** Von
   [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
   herunterladen, Installer ausführen und den Computer neu starten, wenn danach gefragt wird.
   *Docker Desktop* starten und warten, bis es läuft (Wal-Symbol in der Taskleiste). Falls es fragt,
   ob *WSL 2* aktiviert werden soll: ja. Ein Docker-Konto ist nicht nötig, die Anmeldung kann man überspringen.
2. **Dieses Projekt herunterladen.** Auf der GitHub-Seite den grünen Knopf **Code** → **Download ZIP**
   klicken und die ZIP-Datei entpacken, zum Beispiel nach `Dokumente\MeinWohnTicketChecker`.
3. **`start.bat` doppelklicken** in diesem Ordner. Ein schwarzes Fenster zeigt den Fortschritt; der
   erste Start lädt etwa 1 GB herunter und dauert einige Minuten. Danach öffnet sich der Browser mit
   **http://localhost:8080**. (Warnt Windows vor einer unbekannten App: *Weitere Informationen → Trotzdem ausführen*.)
4. **Die vier Schritte im Browser durchgehen** (siehe unten).

Zum Beenden `stop.bat` doppelklicken, zum erneuten Starten `start.bat`. Die Einstellungen bleiben erhalten.

### macOS

1. **Docker Desktop** für Mac (je nach Gerät *Apple silicon* oder *Intel*) von
   [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) installieren und starten.
2. **ZIP herunterladen** (grüner Knopf **Code** → **Download ZIP**) und entpacken.
3. **`start.command` doppelklicken** im Ordner. Weigert sich macOS, die Datei zu öffnen: Rechtsklick →
   *Öffnen* → *Öffnen*. Ein Terminal-Fenster zeigt den Fortschritt, der Browser öffnet http://localhost:8080.
4. **Die vier Schritte im Browser durchgehen.**

Beenden mit `stop.command`.

### Linux

Docker Engine mit Compose-Plugin installieren
([docs.docker.com/engine/install](https://docs.docker.com/engine/install/)), Projekt herunterladen
oder klonen und `./start.sh` ausführen. Beenden mit `./stop.sh`.

```bash
git clone https://github.com/Dev02Liu/meinwohnticketChecker.git
cd meinwohnticketChecker
./start.sh
```

## Einrichtung (die vier Schritte im Browser)

**http://localhost:8080** öffnen. Die Sprache lässt sich rechts oben mit *DE · EN* umschalten.

1. **Stadt Wien Konto** – Benutzername und Passwort eingeben und *Login testen* klicken. Der Checker
   meldet sich genau so an wie Sie im Browser und behält nur das Sitzungs-Cookie. Ihr Passwort bleibt
   auf Ihrem Computer.
2. **Wohnungssuche** – dieselben Filter wie auf der Website wählen: Art der Wohnung, Bezirke,
   Wohnräume, Größe, monatliche und einmalige Kosten, SMART-Wohnungen / Superförderung, Ausstattung,
   Freifläche. *Suche testen* zeigt, was gerade passt. (Unter *Erweitert* kann man auch eine von der
   Website kopierte Such-URL einfügen.)
3. **Benachrichtigungen** – die kostenlose ntfy-App am Handy installieren
   ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy),
   [iPhone](https://apps.apple.com/app/ntfy/id1625396347)). Im Checker *Erzeugen* klicken, um einen
   zufälligen Themennamen zu bekommen, dann in der App auf *+* / *Thema abonnieren* tippen und genau
   diesen Namen eingeben. *Testbenachrichtigung senden* klicken; sie sollte in Sekunden ankommen.
   Alternativ gehen Telegram (Bot-Token + Chat-ID) und Discord (Webhook-URL).
4. **Verhalten** – wie oft geprüft wird, dann **Speichern und beobachten**. Der Standard von 60 Minuten
   reicht völlig: Wohnungen erscheinen schubweise (meist am Vormittag), bleiben etwa zwei Tage online
   und werden nach Punkten vergeben, nicht danach, wer zuerst klickt. Einmal täglich (1440) ist die
   Untergrenze; dann erfährt man von einer Wohnung unter Umständen erst fast einen Tag später und hat
   wenig Zeit für die Anmeldung.

Die erste Prüfung speichert nur, was aktuell angeboten wird, und schickt eine Bestätigung. Danach
löst jede neue Wohnung eine Benachrichtigung mit Adresse, Zimmern, Größe, Miete und Link aus.

## Im Alltag

- **Übersicht** (http://localhost:8080): was beobachtet wird, die letzten Prüfungen, die aktuell
  passenden Wohnungen, *Jetzt prüfen* und *Testbenachrichtigung senden*.
- **Filter ändern**: *Einstellungen* → ändern → *Speichern*. Die nächste Prüfung speichert still die
  neue Ausgangslage, damit Sie nicht mit „neuen“ Wohnungen überschwemmt werden, die es schon gab.
- **Stoppen / Starten**: `stop.bat` / `start.bat` (Windows), `stop.command` / `start.command` (macOS),
  `./stop.sh` / `./start.sh` (Linux). Der Checker startet auch automatisch wieder, wenn Docker Desktop startet.
- **Aktualisieren**: neue ZIP herunterladen (oder `git pull`), die Dateien im Ordner ersetzen und
  wieder starten. Einstellungen und Verlauf liegen in einem Docker-Volume und überstehen Updates.
- **Alles entfernen**: stoppen, dann im Ordner `docker compose down -v` ausführen (löscht gespeicherte
  Einstellungen, Passwort und Verlauf), den Ordner löschen und Docker Desktop deinstallieren, falls
  nicht mehr gebraucht.

## Hinweise zur Sicherheit

- Ihr Passwort fürs Stadt Wien Konto liegt im Klartext im Docker-Datenvolume auf Ihrem Computer
  (`config.json`), wie in jeder Konfigurationsdatei. Behalten Sie Computer und Ordner für sich.
- Die Weboberfläche ist nur vom selben Computer aus erreichbar (`127.0.0.1`). Wenn Sie sie von
  anderen Geräten öffnen wollen, setzen Sie zuerst `UI_PASSWORD` (siehe `.env.example`).
- Wer Ihr ntfy-Thema kennt, kann Ihre Benachrichtigungen lesen; verwenden Sie daher den erzeugten Zufallsnamen.
- Es verlässt nichts Ihren Computer außer Anfragen an meinwohnticket.wien / mein.wien.gv.at und an den
  gewählten Benachrichtigungsdienst.

## Ohne Weboberfläche und weitere Optionen

Alles lässt sich auch über Umgebungsvariablen konfigurieren, siehe [`.env.example`](.env.example).
Nach `.env` kopieren und ausfüllen; in der Weboberfläche gespeicherte Werte (`config.json` im
Datenvolume) haben Vorrang. Nützliche Befehle (im Projektordner):

```bash
docker compose up -d --build                 # starten / neu bauen (macht start.*)
docker compose logs -f                       # Log mitlesen
docker compose run --rm checker --no-ui      # Prüfschleife ohne Weboberfläche, konfiguriert über .env
docker compose run --rm checker --once       # eine Prüfung, dann beenden
docker compose run --rm checker --login-test # nur den Login testen
docker compose run --rm checker --test-notification
docker compose run --rm checker --status     # letzte Prüfungen
docker compose down                          # stoppen (macht stop.*)
```

Port 8080 schon belegt? Eine Datei namens `.env` im Ordner mit dem Inhalt `HOST_PORT=8585` anlegen
und neu starten; die Oberfläche ist dann unter http://localhost:8585.

### Konfigurationsreferenz

| Einstellung (UI) | Umgebungsvariable | Standard | Hinweise |
| --- | --- | --- | --- |
| Benutzername / Passwort | `MWT_USERNAME`, `MWT_PASSWORD` | – | Stadt Wien Konto. |
| – | `MWT_SESSION_COOKIE` | – | Alternative zu den Zugangsdaten: Wert des Cookies `wswinteressentenportalSessionCookiewwwmeinwohnticketwien` aus einem angemeldeten Browser. Läuft ab. |
| Filter / Such-URL | `MWT_SEARCH_URL` | alle Angebote | Die Such-URL der Website; die Filterauswahl erzeugt sie. |
| Alle … Minuten prüfen | `CHECK_INTERVAL_MINUTES` | `60` | Plus bis zu 30 s Zufallsversatz; 1440 = einmal täglich ist die Untergrenze. |
| ntfy-Thema / -Server / -Token | `NTFY_TOPIC`, `NTFY_SERVER`, `NTFY_TOKEN` | –, `https://ntfy.sh`, – | Token nur für geschützte Themen oder eigene Server. |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | – | Bot über @BotFather; Chat-ID z. B. über @userinfobot. |
| Discord | `DISCORD_WEBHOOK_URL` | – | Kanal → Integrationen → Webhooks. |
| Sprache (DE · EN) | `LANGUAGE` | `de` | Weboberfläche und Benachrichtigungstexte. |
| Bestätigung nach erster Prüfung | `NOTIFY_ON_START` | `true` | |
| Benachrichtigen, wenn Angebote verschwinden | `NOTIFY_ON_REMOVED` | `false` | |
| Warnen nach … Fehlschlägen | `FAILURE_NOTIFY_THRESHOLD` | `3` | |
| – | `HOST_PORT` | `8080` | Port auf Ihrem Computer (nur docker compose). |
| – | `UI_PASSWORD` | – | Schützt die Weboberfläche (Basic Auth, beliebiger Benutzername). |
| – | `UI_HOST`, `UI_PORT` | `0.0.0.0`, `8080` | Adresse und Port im Container. |
| – | `LOG_LEVEL` | `INFO` | `DEBUG` zeigt jede Anfrage. |
| – | `DATA_DIR` | `/data` | Datenbank, Cookies, config.json. |

Unterstützte Parameter der Such-URL: `wohnungsarten`, `bezirke` (1–23), `anzahlRaeume` (1–7),
`flaeche` (m²), `monatlicheKosten`, `einmaligeKosten` (€), `foerderungen` (`SMART_ZUSICHERUNG`,
`SUPER_FOERDERUNG`), `nutzung`, `ausstattung`, `freiflaechen`, `sortierung`; Listen mit `~` verbunden,
Bereiche als `min-max` (jeweils optional). Der vollständige Katalog mit Bezeichnungen steht in `checker/filters.py`.

## Fehlersuche

- **Docker Desktop startet nicht / verlangt WSL 2**: den Anweisungen folgen (es installiert WSL 2
  selbst); meist ist ein Neustart nötig. Auf manchen PCs muss die Virtualisierung im BIOS aktiviert werden.
- **`start.bat` meldet, der Port sei belegt**: ein anderes Programm nutzt Port 8080. `.env` mit
  `HOST_PORT=8585` anlegen und neu starten.
- **Login schlägt fehl**: Benutzername und Passwort mit *Login testen* prüfen. Im Datenvolume werden
  `login-failure.png` (Screenshot), `login-failure.html` und `login-trace.json` (Weiterleitungen, ohne
  Formularwerte oder Cookies) abgelegt; herausholen mit
  `docker compose cp checker:/data/login-trace.json .`. Verlangt die Website etwas Interaktives (neue
  Bedingungen, Handy-Signatur), einmal in einem normalen Browser anmelden und erneut versuchen.
- **Keine Benachrichtigungen**: *Testbenachrichtigung senden* verwenden. Bei ntfy muss das Thema in der
  App exakt übereinstimmen (Groß-/Kleinschreibung). Für Wohnungen, die bei der ersten Prüfung schon
  da waren, wird nichts gesendet.
- **„GraphQL error … PublicWohnungSucheNotAllowed“**: Ihr Wohn-Ticket ist für die Suche nicht (mehr)
  gültig; Konto auf der Website prüfen.
- **Die Website hat sich geändert**: die GraphQL-Abfrage steht in `checker/api.py`, die Zuordnung
  URL → Filter in `checker/config.py`, der Filterkatalog in `checker/filters.py`, die Login-Selektoren
  in `checker/auth.py`, die Texte in `checker/i18n.py`. Pull Requests willkommen.

## So funktioniert es

1. `checker/auth.py` meldet sich über den SAML-Login des Stadt Wien Kontos mit Playwright
   (unsichtbares Chromium) an und speichert die Sitzungs-Cookies von meinwohnticket.wien.
2. `checker/api.py` ruft die GraphQL-Abfrage `searchWohnungen` der Website mit dem Filter aus Ihrer
   Such-URL auf (`checker/config.py`, `checker/filters.py`).
3. `checker/checker.py` vergleicht das Ergebnis mit der SQLite-Datenbank (`checker/db.py`) und
   verschickt Benachrichtigungen (`checker/notify.py`) für neue oder wieder aufgetauchte Angebote.
4. `checker/service.py` betreibt die Schleife und übernimmt Einstellungsänderungen sofort;
   `checker/web.py` liefert die Oberfläche.

## Entwicklung

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
playwright install chromium-headless-shell      # nur für echte Login-Tests nötig
pytest
DATA_DIR=./data python -m checker --port 8080   # Oberfläche unter http://127.0.0.1:8080
```

Die Tests decken URL-Parsing, den Filterkatalog, die Einstellungsebenen, die Vergleichs- und
Benachrichtigungslogik, den erneuten Login, die Übersetzungen und die Web-API mit Fake-Clients ab;
sie kontaktieren die Website nie.

## Mitmachen

Issues und Pull Requests sind willkommen. Bitte bleiben Sie den Servern der Stadt gegenüber
rücksichtsvoll (vernünftige Intervalle, kein paralleles Abgrasen) und committen Sie nie Zugangsdaten.

## Lizenz

[MIT](LICENSE). Ein privates Projekt, kein Angebot der Wohnberatung Wien oder der Stadt Wien.
