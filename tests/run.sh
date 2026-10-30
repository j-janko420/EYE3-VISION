#!/bin/sh
# Runs every automatic test: the Python unit tests, then the browser tests against local mock servers.
#   sh tests/run.sh            (needs python3, node and `npm i playwright` with a browser installed)
# Set EYE3_ONLINE=1 to include the tests that need the real internet (the PDF reader from its CDN).
cd "$(dirname "$0")/.." || exit 1
status=0
echo "== Python unit tests"
for t in tools/test_eye3_link.py scripts/test_build_channels.py; do
  python3 "$t" >/tmp/eye3_unit.log 2>&1; rc=$?
  echo "$t: $(grep -E "^(OK|FAILED|Ran)" /tmp/eye3_unit.log | tr "\n" " ")"
  [ $rc -eq 0 ] || { tail -20 /tmp/eye3_unit.log; status=1; }
done
echo "== EYE3 Box kit (install scripts and launcher)"
sh tests/box_test.sh || status=1
echo "== Browser tests"
PIDS=""
start() { "$@" >/dev/null 2>&1 & PIDS="$PIDS $!"; }
start python3 -m http.server 8099 --bind 127.0.0.1
start python3 tests/mocks/xt_mock.py
start python3 tests/mocks/ntfy_mock.py
start python3 tools/eye3-link.py --port 8765 --origin https://localhost:8443 --playlists tests/mocks/playlists --auto-fix
if command -v openssl >/dev/null 2>&1; then
  openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/eye3_key.pem -out /tmp/eye3_cert.pem -days 2 -subj "/CN=localhost" >/dev/null 2>&1
  start python3 tests/mocks/https_srv.py
  export EYE3_HTTPS=1
fi
sleep 2
node tests/e2e/home.js || status=1
kill $PIDS 2>/dev/null
exit $status
