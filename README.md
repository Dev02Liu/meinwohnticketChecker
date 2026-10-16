# Mein Wohn-Ticket Checker

Get a push notification the moment a new apartment that matches your search appears on
[meinwohnticket.wien](https://www.meinwohnticket.wien), the apartment portal of
Wohnberatung Wien (Gemeindewohnungen, geförderte Wohnungen, SMART-Wohnungen).

Instead of refreshing the site every day, run this small container at home or on a server.
It logs in with your Stadt Wien Konto, checks your search every few minutes, remembers what it
has already seen and sends new listings to your phone via **ntfy**, **Telegram** or **Discord**.
Setup happens in a small web interface; no config files needed.

## Features

- Web UI with a guided setup: test your login, preview your search, send a test notification
- Dashboard with the currently matching apartments, recent checks and a "check now" button
- Uses the same API as the website (no screen scraping), configured by pasting your search URL
- Automatic login and re-login with a headless browser; only the session cookie is kept
- SQLite database of seen listings, so you are only notified about *new* ones
- Alerts you when checks keep failing (expired ticket, wrong password, site changes)
- Single Docker image, runs as a non-root user, state in one volume

## Requirements

- A Wiener Wohn-Ticket and a Stadt Wien Konto (the login you use on meinwohnticket.wien)
- Docker with Compose (Docker Desktop on Windows/macOS, or Docker Engine on Linux)
- Something that receives notifications: the free [ntfy](https://ntfy.sh) app is the easiest

## Quick start

```bash
git clone https://github.com/<you>/MeinWohnTicketChecker.git
cd MeinWohnTicketChecker
docker compose up -d --build
```

Then open **http://localhost:8080** and follow the four steps. (Port taken? Create a `.env`
file next to `docker-compose.yml` containing `HOST_PORT=8585` and run the command again.)

1. **Stadt Wien Konto** – enter your username and password and click *Test login*.
2. **Search** – on meinwohnticket.wien set your filters (SMART, rooms, districts, max. rent, …),
   copy the URL from the address bar, paste it and click *Test search* to see what currently matches.
3. **Notifications** – for ntfy: install the app, click *Generate* for a random topic, subscribe to
   that topic in the app, then *Send test notification*. Telegram and Discord work too.
4. **Behaviour** – how often to check (10 minutes is a good default), then *Save and start watching*.

The first check only stores what is currently listed and sends a confirmation message. From
then on every new listing triggers a notification with address, rooms, size, rent and a link.

The first build takes a few minutes because it installs a headless Chromium.

### Without Compose

```bash
docker build -t meinwohnticket-checker .
docker run -d --name meinwohnticket-checker --restart unless-stopped --init --shm-size 512m \
  -p 127.0.0.1:8080:8080 -v checker-data:/data meinwohnticket-checker
```

## Security notes

- Your city-account password is stored in plain text in the data volume (`config.json`),
  like it would be in any `.env` file. Keep the volume on a machine you control.
- The web UI is bound to `127.0.0.1` by default. If you expose the port to your network, set
  `UI_PASSWORD` (HTTP basic auth) in a `.env` file first.
- Anyone who knows your ntfy topic can read your notifications, so use the generated random one.
- Nothing leaves your machine except requests to meinwohnticket.wien / mein.wien.gv.at and to
  the notification service you configured.

## Headless use (no web UI)

Everything can also be configured through environment variables; see
[`.env.example`](.env.example). Copy it to `.env`, fill it in and run with `--no-ui`:

```bash
docker compose run --rm checker --no-ui
```

Values saved by the web UI (`config.json` in the data volume) take precedence over
environment variables, which are useful for pre-filling the UI or for a fully headless setup.

Other one-off commands (all read the same configuration):

```bash
docker compose run --rm checker --once               # one check, then exit
docker compose run --rm checker --login-test         # only test the login
docker compose run --rm checker --test-notification  # send a test message
docker compose run --rm checker --status             # recent runs
```

## Configuration reference

| Setting (UI) | Environment variable | Default | Notes |
| --- | --- | --- | --- |
| Username / password | `MWT_USERNAME`, `MWT_PASSWORD` | – | Stadt Wien Konto. |
| – | `MWT_SESSION_COOKIE` | – | Alternative to credentials: value of the `wswinteressentenportalSessionCookiewwwmeinwohnticketwien` cookie from a logged-in browser. Expires. |
| Search URL | `MWT_SEARCH_URL` | all listings | Copied from the website; its query parameters become the filter. |
| Check every … minutes | `CHECK_INTERVAL_MINUTES` | `10` | Plus up to 30 s random jitter. |
| ntfy topic / server / token | `NTFY_TOPIC`, `NTFY_SERVER`, `NTFY_TOKEN` | –, `https://ntfy.sh`, – | Token only for protected topics or self-hosted servers. |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | – | Bot via @BotFather; chat id e.g. via @userinfobot. |
| Discord | `DISCORD_WEBHOOK_URL` | – | Channel → Integrations → Webhooks. |
| Confirmation after first check | `NOTIFY_ON_START` | `true` | |
| Notify when listings disappear | `NOTIFY_ON_REMOVED` | `false` | |
| Warn after … failed checks | `FAILURE_NOTIFY_THRESHOLD` | `3` | |
| – | `HOST_PORT` | `8080` | Port on your machine (docker compose only). |
| – | `UI_PASSWORD` | – | Protects the web UI (basic auth, any username). |
| – | `UI_HOST`, `UI_PORT` | `0.0.0.0`, `8080` | Bind address and port inside the container. |
| – | `LOG_LEVEL` | `INFO` | `DEBUG` shows every request. |
| – | `DATA_DIR` | `/data` | Database, cookies, config.json. |

Supported URL filters: `anzahlRaeume`, `foerderungen`, `bezirke`, `wohnungsarten`,
`ausstattung`, `freiflaechen`, `nutzung`, `monatlicheKosten`, `einmaligeKosten`, `flaeche`
and `sortierung`, exactly as the website writes them.

## Troubleshooting

- **Login fails**: check username and password with *Test login*. Diagnostics are saved in the data
  volume: `login-failure.png` (screenshot), `login-failure.html` and `login-trace.json` (redirect
  chain, without form values or cookies). Copy them out with
  `docker compose cp checker:/data/login-trace.json .`. If the site asks for something interactive
  (new terms, phone-signature prompt), log in once in a normal browser and try again.
- **No notifications**: use *Send test notification*. For ntfy, the topic in the app must match
  exactly (case-sensitive). Remember that nothing is sent for listings that were already there on
  the first check.
- **"GraphQL error … PublicWohnungSucheNotAllowed"**: your Wohn-Ticket is not (or no longer) valid for
  the search; check your account on the website.
- **The site changed**: the GraphQL query lives in `checker/api.py`, the URL-to-filter mapping in
  `checker/config.py`, the login selectors in `checker/auth.py`. Pull requests welcome.

## How it works

1. `checker/auth.py` logs in through the Stadt Wien Konto SAML flow with Playwright (headless
   Chromium) and stores the resulting meinwohnticket.wien session cookies.
2. `checker/api.py` calls the site's `searchWohnungen` GraphQL query with the filter built from your
   search URL (`checker/config.py`).
3. `checker/checker.py` diffs the result against the SQLite database (`checker/db.py`) and sends
   notifications (`checker/notify.py`) for new or reappeared listings.
4. `checker/service.py` runs the loop and applies settings changes live; `checker/web.py` serves the UI.

## Development

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
playwright install chromium-headless-shell      # only needed to test real logins
pytest
DATA_DIR=./data python -m checker --port 8080   # UI at http://127.0.0.1:8080
```

The tests cover URL parsing, the settings layering, the diff/notification logic, the re-login path
and the web API with fake clients; they never contact the website.

## Contributing

Issues and pull requests are welcome. Please keep the tool polite towards the city's servers
(reasonable intervals, no parallel scraping) and never commit credentials.

## License

[MIT](LICENSE). This is a private project and not affiliated with Wohnberatung Wien or the City of Vienna.
