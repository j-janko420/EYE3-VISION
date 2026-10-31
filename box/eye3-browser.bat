@echo off
rem Opens EYE3 Home fullscreen (kiosk) in Chrome or Edge; any other browser just opens the page.
cd /d "%~dp0"
timeout /t 6 /nobreak >nul
set "URL=https://j-janko420.github.io/EYE3-VISION/home/?splash=0&box=1"
set "BR="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BR=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BR=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "BR=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined BR if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BR=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BR if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BR=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if defined BR (
  start "" "%BR%" --kiosk --noerrdialogs --disable-infobars --autoplay-policy=no-user-gesture-required --no-first-run "--user-data-dir=%~dp0browser-profile" "%URL%"
) else (
  start "" "%URL%"
)
