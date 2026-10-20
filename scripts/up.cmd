@echo off
rem Double-click to build and start the whole stack in the background; logs go to logs\
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check.ps1" -Steps up
pause
