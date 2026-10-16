#!/usr/bin/env bash
# Stops the Mein Wohn-Ticket Checker. Your settings and history are kept.
# Stoppt den Mein Wohn-Ticket Checker. Einstellungen und Verlauf bleiben erhalten.
cd "$(dirname "$0")"
docker compose down
echo
echo "Stopped. Run ./start.sh to start it again.  /  Gestoppt. Mit ./start.sh erneut starten."
