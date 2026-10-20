@echo off
rem Double-click to see the latest click batches processed by the consumer; output goes to logs\clicks.txt
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check.ps1" -Steps clicks
pause
