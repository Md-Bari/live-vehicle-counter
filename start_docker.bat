@echo off
REM Builds (first run takes a while) and starts the Docker stack, then opens the dashboard.
cd /d "%~dp0"
REM Classic builder: the default "bake" builder asks for extra file permissions on Windows paths
set COMPOSE_BAKE=false
docker compose up -d --build || (echo. & echo Docker failed - is Docker Desktop running? & pause & exit /b 1)
echo Waiting for the backend to become healthy...
:wait
for /f %%s in ('docker inspect -f "{{.State.Health.Status}}" vehicle-counter-backend-1 2^>nul') do set HEALTH=%%s
if not "%HEALTH%"=="healthy" (timeout /t 2 /nobreak >nul & goto wait)
start "" http://localhost:8088
echo Dashboard: http://localhost:8088    (stop with: docker compose down)
