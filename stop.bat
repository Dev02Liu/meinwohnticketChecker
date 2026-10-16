@echo off
rem Stoppt den Mein Wohn-Ticket Checker. Einstellungen und Verlauf bleiben erhalten.
rem Stops the Mein Wohn-Ticket Checker. Your settings and history are kept.
setlocal
cd /d "%~dp0"
docker compose down
echo.
echo Gestoppt. Mit start.bat erneut starten.  /  Stopped. Run start.bat to start it again.
pause
