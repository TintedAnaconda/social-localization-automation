@echo off
echo Starting QA Automation...

cd /d C:\automation\social-localization-automation

set NODES_EXCLUDE=[]
set N8N_HOST=localhost
set N8N_PORT=5678
set N8N_PROTOCOL=http

start powershell -NoExit -Command "n8n"

timeout /t 3 >nul

echo Automation started!
pause