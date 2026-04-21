@echo off
echo Stopping n8n...

taskkill /f /im node.exe

echo n8n stopped
pause