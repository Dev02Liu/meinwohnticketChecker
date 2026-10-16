#!/usr/bin/env bash
# Stoppt den Mein Wohn-Ticket Checker. Einstellungen und Verlauf bleiben erhalten.
# Stops the Mein Wohn-Ticket Checker. Your settings and history are kept.
cd "$(dirname "$0")"
docker compose down
echo
echo "Gestoppt. Mit ./start.sh erneut starten.  /  Stopped. Run ./start.sh to start it again."
