@echo off
REM Starts backend and frontend in their own windows, then opens the dashboard.
start "Vehicle Counter - backend" cmd /k "%~dp0start_backend.bat"
start "Vehicle Counter - frontend" cmd /k "%~dp0start_frontend.bat"
timeout /t 8 /nobreak >nul
start "" http://localhost:3000
