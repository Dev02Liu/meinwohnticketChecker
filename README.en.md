# Mein Wohn-Ticket Checker

🇩🇪 **[Deutsche Anleitung (Standard) → README.md](README.md)**

Get a push notification on your phone the moment a new apartment that matches your search
appears on [meinwohnticket.wien](https://www.meinwohnticket.wien), the apartment portal of
Wohnberatung Wien (Gemeindewohnungen, geförderte Wohnungen, SMART-Wohnungen).

Instead of checking the website every day, a small program runs on your computer, logs in with
your Stadt Wien Konto, checks your search every few minutes and sends new listings to your
phone. Everything is set up in your browser, in German or English, no config files needed.

## Is this for me?

You need:

- a **Wiener Wohn-Ticket** and the **Stadt Wien Konto** login you use on meinwohnticket.wien,
- a **computer that stays on** while you want to be notified (a PC or Mac that runs all day, a
  mini PC, a NAS or a Raspberry Pi; it only checks while that computer is on),
- the free **[ntfy](https://ntfy.sh) app** on your phone (Telegram or Discord work too),
- **Docker Desktop** (free), installed once. The steps below walk you through it.

If you have installed a program and unzipped a folder before, you can do this. It takes about
15 minutes the first time, most of it waiting for downloads.

## Installation, step by step

### Windows

1. **Install Docker Desktop.** Download it from
   [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/), run the
   installer and restart the computer if asked. Start *Docker Desktop* and wait until it says it
   is running (whale icon in the taskbar). If it asks to enable *WSL 2*, say yes. You do not need
   a Docker account; you can skip the sign-in.
2. **Download this project.** On the GitHub page click the green **Code** button →
   **Download ZIP**, then unzip it, for example to `Documents\MeinWohnTicketChecker`.
3. **Double-click `start.bat`** in that folder. A black window shows the progress; the first start
   downloads about 1 GB and takes a few minutes. When it is done, your browser opens
   **http://localhost:8080**. (If Windows warns about an unknown app, choose *More info → Run anyway*.)
4. **Follow the four steps in the browser** (see below).

To stop it, double-click `stop.bat`. To start again, `start.bat`. Your settings are kept.

### macOS

1. **Install Docker Desktop** for Mac (choose *Apple silicon* or *Intel* as appropriate) from
   [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) and start it.
2. **Download the ZIP** (green **Code** button → **Download ZIP**) and unzip it.
3. **Double-click `start.command`** in the folder. If macOS refuses to open it, right-click it →
   *Open* → *Open*. A Terminal window shows the progress and your browser opens http://localhost:8080.
4. **Follow the four steps in the browser.**

Stop with `stop.command`.

### Linux

Install Docker Engine with the Compose plugin
([docs.docker.com/engine/install](https://docs.docker.com/engine/install/)), download or clone the
project and run `./start.sh`. Stop with `./stop.sh`.

```bash
git clone https://github.com/Dev02Liu/meinwohnticketChecker.git
cd meinwohnticketChecker
./start.sh
```

### On a NAS or server (runs around the clock)

A NAS (UGREEN, Synology, QNAP, …) or a small server is the best place because it is always on.
Nothing needs to be built there: GitHub provides a ready-made image
(`ghcr.io/dev02liu/meinwohnticketchecker:latest`, x86_64).

1. Enable Docker on the NAS (UGREEN: "Docker" app; Synology: "Container Manager") and turn on SSH.
2. Create a folder, e.g. `/volume1/docker/wohnticket`, and put
   [`deploy/docker-compose.nas.yml`](deploy/docker-compose.nas.yml) there as `docker-compose.yml`.
3. Next to it create a file `.env` containing `UI_PASSWORD=<a good password>`. On a NAS the web UI is
   reachable from your whole home network, so the password is mandatory here.
4. Run `docker compose up -d` in that folder and open `http://<NAS-IP>:8080` in your browser (any
   username, the password from `.env`). Then follow the four steps below.

Updates: `docker compose pull && docker compose up -d`.

## Setting it up (the four steps in the browser)

Open **http://localhost:8080**. The language can be switched with *DE · EN* at the top right.

1. **Stadt Wien Konto** – enter your username and password and click *Test login*. The checker logs
   in exactly like you do in the browser and only keeps the session cookie. Your password stays on
   your computer.
2. **Apartment search** – pick the same filters as on the website: apartment type, districts,
   rooms, size, monthly and one-time costs, SMART-Wohnungen / Superförderung, equipment, outdoor
   space. Click *Test search* to see what matches right now. (Under *Advanced* you can also paste a
   search URL copied from the website.)
3. **Notifications** – install the free ntfy app on your phone
   ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy),
   [iPhone](https://apps.apple.com/app/ntfy/id1625396347)). In the checker click *Generate* to get
   a random topic name, then in the app tap *+* / *Subscribe to topic* and enter exactly that name.
   Click *Send test notification*; it should arrive within seconds. Telegram (bot token + chat id)
   and Discord (webhook URL) are available as alternatives.
4. **Behaviour** – how often to check, then **Save and start watching**. The default of 60 minutes
   is plenty: listings appear in batches (usually in the morning), stay online for about two days,
   and are allocated by points, not by who clicks first. Once a day (1440) is the bare minimum; with
   that you may learn about a listing almost a day late and have little time left to apply.

The first check only stores what is currently listed and sends one confirmation message. From then
on every new listing triggers a notification with address, rooms, size, rent and a link to it.

## Everyday use

- **Dashboard** (http://localhost:8080): what is being watched, the last checks, the apartments that
  currently match, *Check now* and *Send test notification*.
- **Changing filters**: *Settings* → change → *Save*. The next check silently stores the new baseline
  so you are not flooded with "new" listings that were already there.
- **Stopping / starting**: `stop.bat` / `start.bat` (Windows), `stop.command` / `start.command` (macOS),
  `./stop.sh` / `./start.sh` (Linux). The checker also starts again automatically when Docker Desktop starts.
- **Updating**: download the new ZIP (or `git pull`), replace the folder's files and run start again.
  Settings and history live in a Docker volume and survive updates.
- **Removing everything**: stop, then run `docker compose down -v` in the folder (deletes the stored
  settings, password and history), delete the folder, and uninstall Docker Desktop if you no longer need it.

## Security notes

- Your city-account password is stored in plain text in Docker's data volume on your computer
  (`config.json`), like it would be in any config file. Keep the computer and the folder to yourself.
- The web interface is reachable only from the same computer (`127.0.0.1`). If you want to open it
  from other devices, set `UI_PASSWORD` (see `.env.example`) before changing the port binding.
- Anyone who knows your ntfy topic can read your notifications, so use the generated random one.
- Nothing leaves your computer except requests to meinwohnticket.wien / mein.wien.gv.at and to the
  notification service you chose.

## Headless use and advanced options

Everything can also be configured through environment variables; see [`.env.example`](.env.example).
Copy it to `.env` and fill it in; values saved by the web UI (`config.json` in the data volume) take
precedence. Useful commands (run in the project folder):

```bash
docker compose up -d --build                 # start / rebuild (what start.* does)
docker compose logs -f                       # watch the log
docker compose run --rm checker --no-ui      # run the loop without the web UI, configured via .env
docker compose run --rm checker --once       # one check, then exit
docker compose run --rm checker --login-test # only test the login
docker compose run --rm checker --test-notification
docker compose run --rm checker --status     # recent runs
docker compose down                          # stop (what stop.* does)
```

Port 8080 already in use? Create a file named `.env` in the folder containing `HOST_PORT=8585`
and start again; the UI is then at http://localhost:8585.

### Configuration reference

| Setting (UI) | Environment variable | Default | Notes |
| --- | --- | --- | --- |
| Username / password | `MWT_USERNAME`, `MWT_PASSWORD` | – | Stadt Wien Konto. |
| – | `MWT_SESSION_COOKIE` | – | Alternative to credentials: value of the `wswinteressentenportalSessionCookiewwwmeinwohnticketwien` cookie from a logged-in browser. Expires. |
| Filters / search URL | `MWT_SEARCH_URL` | all listings | The website's own search URL; the picker generates it. |
| Check every … minutes | `CHECK_INTERVAL_MINUTES` | `60` | Plus up to 30 s random jitter; 1440 = once a day is the minimum. |
| ntfy topic / server / token | `NTFY_TOPIC`, `NTFY_SERVER`, `NTFY_TOKEN` | –, `https://ntfy.sh`, – | Token only for protected topics or self-hosted servers. |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | – | Bot via @BotFather; chat id e.g. via @userinfobot. |
| Discord | `DISCORD_WEBHOOK_URL` | – | Channel → Integrations → Webhooks. |
| Language (DE · EN) | `LANGUAGE` | `de` | Web UI and notification texts. |
| Confirmation after first check | `NOTIFY_ON_START` | `true` | |
| Notify when listings disappear | `NOTIFY_ON_REMOVED` | `false` | |
| Warn after … failed checks | `FAILURE_NOTIFY_THRESHOLD` | `3` | |
| – | `HOST_PORT` | `8080` | Port on your machine (docker compose only). |
| – | `UI_PASSWORD` | – | Protects the web UI (basic auth, any username). |
| – | `UI_HOST`, `UI_PORT` | `0.0.0.0`, `8080` | Bind address and port inside the container. |
| – | `LOG_LEVEL` | `INFO` | `DEBUG` shows every request. |
| – | `DATA_DIR` | `/data` | Database, cookies, config.json. |

Supported search-URL parameters: `wohnungsarten`, `bezirke` (1–23), `anzahlRaeume` (1–7),
`flaeche` (m²), `monatlicheKosten`, `einmaligeKosten` (€), `foerderungen` (`SMART_ZUSICHERUNG`,
`SUPER_FOERDERUNG`), `nutzung`, `ausstattung`, `freiflaechen`, `sortierung`; lists joined with `~`,
ranges as `min-max` (either side optional). The full catalog with labels is in `checker/filters.py`.

## Troubleshooting

- **Docker Desktop will not start / asks for WSL 2**: follow its instructions (it installs WSL 2
  for you); a restart is usually needed. Virtualisation must be enabled in the BIOS on some PCs.
- **`start.bat` says the port is in use**: another program uses port 8080. Create `.env` with
  `HOST_PORT=8585` and start again.
- **Login fails**: check username and password with *Test login*. Diagnostics are saved in the data
  volume: `login-failure.png` (screenshot), `login-failure.html` and `login-trace.json` (redirect
  chain, without form values or cookies); copy them out with
  `docker compose cp checker:/data/login-trace.json .`. If the site asks for something interactive
  (new terms, phone-signature prompt), log in once in a normal browser and try again.
- **No notifications**: use *Send test notification*. For ntfy the topic in the app must match exactly
  (case-sensitive). Nothing is sent for listings that were already there on the first check.
- **"GraphQL error … PublicWohnungSucheNotAllowed"**: your Wohn-Ticket is not (or no longer) valid for
  the search; check your account on the website.
- **The site changed**: the GraphQL query lives in `checker/api.py`, the URL-to-filter mapping in
  `checker/config.py`, the filter catalog in `checker/filters.py`, the login selectors in
  `checker/auth.py`, the texts in `checker/i18n.py`. Pull requests welcome.

## How it works

1. `checker/auth.py` logs in through the Stadt Wien Konto SAML flow with Playwright (headless
   Chromium) and stores the resulting meinwohnticket.wien session cookies.
2. `checker/api.py` calls the site's `searchWohnungen` GraphQL query with the filter built from your
   search URL (`checker/config.py`, `checker/filters.py`).
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

The tests cover URL parsing, the filter catalog, settings layering, the diff/notification logic,
the re-login path, translations and the web API with fake clients; they never contact the website.

## Contributing

Issues and pull requests are welcome. Please keep the tool polite towards the city's servers
(reasonable intervals, no parallel scraping) and never commit credentials.

## License

[MIT](LICENSE). This is a private project and not affiliated with Wohnberatung Wien or the City of Vienna.
