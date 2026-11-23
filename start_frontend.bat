@echo off
REM Next.js frontend on http://localhost:3000
cd /d "%~dp0frontend"
if not exist node_modules call npm install
if not exist .next\BUILD_ID call npm run build
call npm run start
