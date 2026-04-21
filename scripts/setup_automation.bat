@echo off
echo Running QA Automation setup...
powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause