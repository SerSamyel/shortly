@echo off
rem Double-click to create GitHub issues from _docs\backlog\ (needs the GitHub CLI, gh)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0create-issues.ps1"
pause
