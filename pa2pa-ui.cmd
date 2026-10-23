@echo off
rem Double-click: sets up what's missing, starts the model server and opens the runs page (scripts\start.ps1).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
if errorlevel 1 pause
