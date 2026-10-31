@echo off
rem EYE3 Box installer for Windows: double-click this file. (Options: -DryRun, -Uninstall, -Dir C:\folder)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
