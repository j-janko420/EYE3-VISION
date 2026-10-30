@echo off
rem Starts EYE3 Link and keeps it running. It starts the program again after a crash and right away
rem after it installed an update (exit code 75). The installer runs this at every sign-in.
cd /d "%~dp0"
set EYE3_MANAGED=1
:loop
if exist eye3-link.exe (
  eye3-link.exe
) else if exist eye3-link.py (
  python eye3-link.py
) else (
  echo EYE3 Link was not found next to this file.
  exit /b 1
)
set RC=%errorlevel%
if "%RC%"=="75" goto loop
if "%RC%"=="0" exit /b 0
timeout /t 8 /nobreak >nul
goto loop
