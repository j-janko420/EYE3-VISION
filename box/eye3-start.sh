#!/bin/sh
# Starts EYE3 Link and keeps it running. It starts the program again after a crash and right away after it
# installed an update (exit code 75). The installer sets this up to run at every start of the computer.
#   eye3-start.sh            run EYE3 Link (and keep it running)
#   eye3-start.sh --browser  open EYE3 Home fullscreen (kiosk) on this screen
DIR=$(cd "$(dirname "$0")" && pwd)
URL="${EYE3_HOME_URL:-https://j-janko420.github.io/EYE3-VISION/home/?splash=0&box=1}"
cd "$DIR" || exit 1
export EYE3_MANAGED=1

if [ "${1:-}" = "--browser" ]; then
  sleep "${EYE3_BROWSER_DELAY:-6}"
  FLAGS="--kiosk --noerrdialogs --disable-infobars --autoplay-policy=no-user-gesture-required --no-first-run"
  for b in chromium-browser chromium google-chrome google-chrome-stable microsoft-edge; do
    if command -v "$b" >/dev/null 2>&1; then exec "$b" $FLAGS "$URL"; fi
  done
  if [ "$(uname -s)" = "Darwin" ]; then
    for app in "Google Chrome" "Microsoft Edge" "Chromium"; do
      if [ -d "/Applications/$app.app" ]; then exec open -na "$app" --args $FLAGS "$URL"; fi
    done
    exec open "$URL"
  fi
  if command -v firefox >/dev/null 2>&1; then exec firefox --kiosk "$URL"; fi
  exec xdg-open "$URL"
fi

while :; do
  if [ -x ./eye3-link ]; then ./eye3-link; rc=$?
  elif command -v python3 >/dev/null 2>&1 && [ -f ./eye3-link.py ]; then python3 ./eye3-link.py; rc=$?
  else echo "EYE3 Link was not found next to this script."; exit 1; fi
  [ "$rc" = 75 ] && continue         # an update was installed: start the new version right away
  [ "$rc" = 0 ] && exit 0            # stopped on purpose (Ctrl+C)
  sleep "${EYE3_RESTART_DELAY:-8}"   # crash or "port busy": wait a little, then try again
done
