@echo off
REM FastAPI backend on http://localhost:8001  (API docs: http://localhost:8001/docs)
cd /d "%~dp0backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8001
