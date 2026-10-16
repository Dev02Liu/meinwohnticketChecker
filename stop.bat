@echo off
rem Stops the Mein Wohn-Ticket Checker. Your settings and history are kept.
rem Stoppt den Mein Wohn-Ticket Checker. Einstellungen und Verlauf bleiben erhalten.
setlocal
cd /d "%~dp0"
docker compose down
echo.
echo Stopped. Run start.bat to start it again.  /  Gestoppt. Mit start.bat erneut starten.
pause
