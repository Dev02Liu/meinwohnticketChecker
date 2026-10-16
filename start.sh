#!/usr/bin/env bash
# Startet den Mein Wohn-Ticket Checker mit Docker und öffnet die Weboberfläche.
# Starts the Mein Wohn-Ticket Checker with Docker and opens the web UI.
set -u
cd "$(dirname "$0")"

if ! docker version >/dev/null 2>&1; then
  echo
  echo "Docker läuft nicht oder ist nicht installiert.  /  Docker is not running or not installed."
  echo "Docker Desktop (macOS/Windows) bzw. Docker Engine (Linux) installieren und starten, dann erneut ausführen."
  echo "Install and start Docker Desktop (macOS/Windows) or Docker Engine (Linux), then run this again."
  exit 1
fi

PORT="$(grep -E '^HOST_PORT=' .env 2>/dev/null | tail -n1 | cut -d= -f2 | tr -d '[:space:]')"
PORT="${PORT:-8080}"

echo "Checker wird gestartet (der erste Start lädt ca. 1 GB herunter und dauert einige Minuten) ..."
echo "Starting the checker (the first start downloads about 1 GB and takes a few minutes) ..."
if ! docker compose up -d --build; then
  echo
  echo "Start fehlgeschlagen. Siehe Meldungen oben.  /  Start failed. See the messages above."
  echo "Wenn der Port belegt ist: HOST_PORT=8585 in eine Datei namens .env in diesem Ordner schreiben."
  echo "If the port is already in use, put HOST_PORT=8585 into a file named .env in this folder."
  exit 1
fi

URL="http://localhost:${PORT}"
echo
echo "Läuft. Öffnen Sie ${URL}  /  Running. Open ${URL}"
echo "Der Checker läuft im Hintergrund weiter, bis Sie ./stop.sh ausführen."
echo "The checker keeps running in the background until you run ./stop.sh."
if command -v open >/dev/null 2>&1; then open "$URL"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true; fi
