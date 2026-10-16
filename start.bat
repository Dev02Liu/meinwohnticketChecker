@echo off
rem Starts the Mein Wohn-Ticket Checker with Docker and opens the web UI.
rem Startet den Mein Wohn-Ticket Checker mit Docker und oeffnet die Weboberflaeche.
setlocal
cd /d "%~dp0"

docker version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Docker is not running or not installed.  /  Docker laeuft nicht oder ist nicht installiert.
    echo Please install and start Docker Desktop: https://www.docker.com/products/docker-desktop/
    echo Bitte Docker Desktop installieren und starten, dann diese Datei erneut ausfuehren.
    echo.
    pause
    exit /b 1
)

set "PORT=8080"
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="HOST_PORT" set "PORT=%%b"
    )
)

echo Starting the checker (the first start downloads about 1 GB and takes a few minutes) ...
echo Checker wird gestartet (der erste Start laedt ca. 1 GB herunter und dauert einige Minuten) ...
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo Start failed. See the messages above.  /  Start fehlgeschlagen. Siehe Meldungen oben.
    echo If the port is already in use, put HOST_PORT=8585 into a file named .env in this folder.
    echo Wenn der Port belegt ist: HOST_PORT=8585 in eine Datei namens .env in diesem Ordner schreiben.
    pause
    exit /b 1
)

echo.
echo Running. Opening http://localhost:%PORT% ...  /  Laeuft. Oeffne http://localhost:%PORT% ...
echo The checker keeps running in the background until you run stop.bat (or stop Docker Desktop).
echo Der Checker laeuft im Hintergrund weiter, bis Sie stop.bat ausfuehren (oder Docker Desktop beenden).
start "" "http://localhost:%PORT%"
pause
