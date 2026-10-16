#!/usr/bin/env bash
# Starts the Mein Wohn-Ticket Checker with Docker and opens the web UI.
# Startet den Mein Wohn-Ticket Checker mit Docker und öffnet die Weboberfläche.
set -u
cd "$(dirname "$0")"

if ! docker version >/dev/null 2>&1; then
  echo
  echo "Docker is not running or not installed.  /  Docker läuft nicht oder ist nicht installiert."
  echo "Install and start Docker Desktop (macOS/Windows) or Docker Engine (Linux), then run this again."
  echo "Docker Desktop (macOS/Windows) bzw. Docker Engine (Linux) installieren und starten, dann erneut ausführen."
  exit 1
fi

PORT="$(grep -E '^HOST_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '[:space:]')"
PORT="${PORT:-8080}"

echo "Starting the checker (the first start downloads about 1 GB and takes a few minutes) ..."
echo "Checker wird gestartet (der erste Start lädt ca. 1 GB herunter und dauert einige Minuten) ..."
if ! docker compose up -d --build; then
  echo
  echo "Start failed. See the messages above.  /  Start fehlgeschlagen. Siehe Meldungen oben."
  echo "If the port is already in use, put HOST_PORT=8585 into a file named .env in this folder."
  echo "Wenn der Port belegt ist: HOST_PORT=8585 in eine Datei namens .env in diesem Ordner schreiben."
  exit 1
fi

URL="http://localhost:${PORT}"
echo
echo "Running. Open ${URL}  /  Läuft. Öffnen Sie ${URL}"
echo "The checker keeps running in the background until you run ./stop.sh."
echo "Der Checker läuft im Hintergrund weiter, bis Sie ./stop.sh ausführen."
if command -v open >/dev/null 2>&1; then open "$URL"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true; fi
