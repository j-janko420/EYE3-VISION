#!/bin/sh
# Tests the EYE3 Box kit on Linux: the dry run changes nothing, a real install copies everything and a user playlist,
# and the launcher starts EYE3 Link again after exit code 75 (update installed) and after a crash.
cd "$(dirname "$0")/.." || exit 1
fail=0
ok() { echo "  ok   $1"; }
bad() { echo "  FAIL $1"; fail=1; }
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

# 1. dry run: nothing is created
sh box/install.sh --dry-run --dir="$T/dry" >"$T/dry.log" 2>&1
[ ! -e "$T/dry" ] && grep -q "dry-run" "$T/dry.log" && ok "dry run says what it would do and creates nothing" || { bad "dry run"; cat "$T/dry.log"; }

# 2. real install from a kit folder holding a stand-in program and the viewer's own playlist (no start-up entries)
K="$T/kit"; mkdir -p "$K/playlists"
cp box/install.sh box/eye3-start.sh box/eye3-link.conf.example "$K/"
cp box/playlists/README.txt "$K/playlists/"
printf '#!/bin/sh\necho started >> "$(dirname "$0")/runs.log"\nexit 0\n' > "$K/eye3-link-linux"; cp "$K/eye3-link-linux" "$K/eye3-link-macos"
printf '#EXTM3U\n#EXTINF:-1 group-title="Mine",One\nhttp://127.0.0.1:1/one.m3u8\n' > "$K/playlists/mine.m3u"
EYE3_NO_SERVICE=1 sh "$K/install.sh" --dir="$T/inst" >"$T/inst.log" 2>&1
[ -x "$T/inst/eye3-link" ] && [ -x "$T/inst/eye3-start.sh" ] && [ -f "$T/inst/eye3-link.conf" ] && ok "install copies the program, launcher and settings" || { bad "install files"; cat "$T/inst.log"; }
[ -f "$T/inst/playlists/mine.m3u" ] && ok "the viewer's own playlist is copied into the playlists folder" || bad "playlist copy"
grep -q '"auto_update": true' "$T/inst/eye3-link.conf" && grep -q '"auto_fix": true' "$T/inst/eye3-link.conf" && ok "agent switches are on in the installed settings" || bad "conf"
printf '{"auto_fix": false}' > "$T/inst/eye3-link.conf"
EYE3_NO_SERVICE=1 sh "$K/install.sh" --dir="$T/inst" >/dev/null 2>&1
grep -q '"auto_fix": false' "$T/inst/eye3-link.conf" && ok "a second install keeps the viewer's settings" || bad "conf kept"

# 3. the launcher restarts after exit 75 and after a crash, and stops after a clean exit
cat > "$T/inst/eye3-link" <<'STUB'
#!/bin/sh
d=$(dirname "$0"); n=$(cat "$d/count" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$d/count"
echo "managed=$EYE3_MANAGED" > "$d/env"
case $n in 1) exit 75 ;; 2) exit 3 ;; *) exit 0 ;; esac
STUB
chmod +x "$T/inst/eye3-link"
EYE3_RESTART_DELAY=0 timeout 20 "$T/inst/eye3-start.sh"
[ "$(cat "$T/inst/count")" = 3 ] && ok "launcher: update exit (75) and crash both start it again; a clean exit stops it" || bad "launcher count $(cat "$T/inst/count" 2>/dev/null)"
grep -q "managed=1" "$T/inst/env" && ok "launcher tells the program it is managed (so Home may offer Restart)" || bad "managed env"

# 4. uninstall (as a dry run, so a real EYE3 install on this computer is never touched)
sh box/install.sh --dry-run --uninstall >/dev/null 2>&1 && ok "uninstall runs" || bad "uninstall"
exit $fail
