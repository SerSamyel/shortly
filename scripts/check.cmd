@echo off
rem Double-click to run all checks; logs go to logs\
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check.ps1" %*
if "%~1"=="" pause
