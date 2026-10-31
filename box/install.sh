#!/bin/sh
# EYE3 Box installer for Linux, Raspberry Pi and macOS. Run it from the folder (or USB stick) that holds it:
#   sh install.sh               install, start now and start at every boot
#   sh install.sh --dry-run     only say what would happen, change nothing
#   sh install.sh --uninstall   remove the start-up entries (your files stay)
#   sh install.sh --kiosk       also open EYE3 Home fullscreen at every start (for the box behind a TV)
# By default only EYE3 Link is started at boot; your normal browser and its saved data are left alone.
#   sh install.sh --dir=/path   install somewhere else (default: ~/EYE3)
# Needs no internet when this folder already holds the program (eye3-link-linux / eye3-link-macos / eye3-link.py).
# Otherwise it downloads the program from the EYE3 release page and checks its SHA-256 first.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DEST="${EYE3_DIR:-$HOME/EYE3}"
REL="https://github.com/j-janko420/EYE3-VISION/releases/download/eye3-link-latest"
DRY=0; UNINSTALL=0; KIOSK=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --kiosk) KIOSK=1 ;;
    --dir=*) DEST=${a#--dir=} ;;
    *) echo "Unknown option: $a"; exit 2 ;;
  esac
done
say() { printf '%s\n' "$*"; }
act() { if [ "$DRY" = 1 ]; then say "[dry-run] $*"; return 0; fi; "$@"; }
OS=$(uname -s)
case "$OS" in Linux) ASSET=eye3-link-linux ;; Darwin) ASSET=eye3-link-macos ;; *) say "This installer is for Linux, Raspberry Pi and macOS (found $OS). On Windows use install.bat."; exit 1 ;; esac
UNIT="$HOME/.config/systemd/user/eye3-link.service"
DESK="$HOME/.config/autostart/eye3-home.desktop"
PL_LINK="$HOME/Library/LaunchAgents/com.eye3.link.plist"
PL_HOME="$HOME/Library/LaunchAgents/com.eye3.home.plist"

if [ "$UNINSTALL" = 1 ]; then
  say "Removing the EYE3 start-up entries (the folder $DEST and your playlists stay)."
  if [ "$OS" = Linux ]; then
    command -v systemctl >/dev/null 2>&1 && act systemctl --user disable --now eye3-link.service 2>/dev/null
    act rm -f "$UNIT" "$DESK"
  else
    act launchctl unload "$PL_LINK" 2>/dev/null; act launchctl unload "$PL_HOME" 2>/dev/null
    act rm -f "$PL_LINK" "$PL_HOME"
  fi
  exit 0
fi

say "EYE3 Box install into $DEST"
act mkdir -p "$DEST/playlists"

# 1. the program: the one on this stick, else the Python file, else a checked download
if [ -f "$HERE/$ASSET" ]; then
  say "Program: $ASSET from this folder"
  act cp "$HERE/$ASSET" "$DEST/eye3-link"; act chmod +x "$DEST/eye3-link"
elif [ -f "$HERE/eye3-link.py" ] && command -v python3 >/dev/null 2>&1; then
  say "Program: eye3-link.py (runs with Python; it cannot update itself)"
  act cp "$HERE/eye3-link.py" "$DEST/eye3-link.py"
elif [ "$DRY" = 1 ]; then
  say "[dry-run] would download $ASSET from $REL and check its SHA-256"
else
  say "Downloading $ASSET from the EYE3 release page…"
  TMP=$(mktemp -d) || exit 1
  if command -v curl >/dev/null 2>&1; then GET="curl -fsSL -o"; elif command -v wget >/dev/null 2>&1; then GET="wget -q -O"; else say "Need curl or wget (or put the program next to this script)."; exit 1; fi
  $GET "$TMP/$ASSET" "$REL/$ASSET" && $GET "$TMP/SHA256SUMS.txt" "$REL/SHA256SUMS.txt" || { say "Download failed. Check the internet, or copy the kit with the program on the stick."; exit 1; }
  WANT=$(grep " $ASSET\$" "$TMP/SHA256SUMS.txt" | cut -d' ' -f1)
  if command -v sha256sum >/dev/null 2>&1; then GOT=$(sha256sum "$TMP/$ASSET" | cut -d' ' -f1); else GOT=$(shasum -a 256 "$TMP/$ASSET" | cut -d' ' -f1); fi
  if [ -z "$WANT" ] || [ "$WANT" != "$GOT" ]; then say "The download does not match its published SHA-256. Not installed."; rm -rf "$TMP"; exit 1; fi
  cp "$TMP/$ASSET" "$DEST/eye3-link"; chmod +x "$DEST/eye3-link"; rm -rf "$TMP"
  say "Checked SHA-256: ok"
fi

# 2. settings, launcher, the viewer's own playlists
[ -f "$DEST/eye3-link.conf" ] || act cp "$HERE/eye3-link.conf.example" "$DEST/eye3-link.conf"
act cp "$HERE/eye3-start.sh" "$DEST/eye3-start.sh"; act chmod +x "$DEST/eye3-start.sh"
[ -f "$HERE/playlists/README.txt" ] && act cp -n "$HERE/playlists/README.txt" "$DEST/playlists/README.txt"
for f in "$HERE"/playlists/*; do
  case "$f" in *.m3u|*.m3u8|*.txt) [ "$(basename "$f")" = README.txt ] || { say "Playlist: $(basename "$f")"; act cp -n "$f" "$DEST/playlists/"; } ;; esac
done

# 3. start at every boot, and start now
if [ "${EYE3_NO_SERVICE:-0}" = 1 ]; then
  say "Skipping the start-up entries (EYE3_NO_SERVICE=1)."
elif [ "$OS" = Linux ]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    say "Start-up: systemd user service eye3-link (restarts by itself)"
    act mkdir -p "$HOME/.config/systemd/user"
    if [ "$DRY" = 0 ]; then
      cat > "$UNIT" <<UNITEOF
[Unit]
Description=EYE3 Link
After=network-online.target

[Service]
ExecStart=$DEST/eye3-start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNITEOF
    else say "[dry-run] write $UNIT"; fi
    act systemctl --user daemon-reload
    act systemctl --user enable --now eye3-link.service
    command -v loginctl >/dev/null 2>&1 && act loginctl enable-linger "$USER" 2>/dev/null
  else
    say "No systemd user session: add  $DEST/eye3-start.sh  to your start-up programs yourself."
  fi
  if [ "$KIOSK" = 1 ]; then
    say "Kiosk: EYE3 Home fullscreen when the desktop starts"
    act mkdir -p "$HOME/.config/autostart"
    if [ "$DRY" = 0 ]; then
      printf '[Desktop Entry]\nType=Application\nName=EYE3 Home\nExec=%s/eye3-start.sh --browser\nX-GNOME-Autostart-enabled=true\n' "$DEST" > "$DESK"
    else say "[dry-run] write $DESK"; fi
  fi
else
  say "Start-up: macOS launch agents"
  act mkdir -p "$HOME/Library/LaunchAgents"
  mkplist() { # label, arguments
    printf '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict><key>Label</key><string>%s</string><key>ProgramArguments</key><array><string>%s/eye3-start.sh</string>%s</array><key>RunAtLoad</key><true/>%s</dict></plist>\n' "$1" "$DEST" "$2" "$3"
  }
  if [ "$DRY" = 0 ]; then
    mkplist com.eye3.link "" "<key>KeepAlive</key><true/>" > "$PL_LINK"
    launchctl unload "$PL_LINK" 2>/dev/null
    launchctl load "$PL_LINK"
    if [ "$KIOSK" = 1 ]; then mkplist com.eye3.home "<string>--browser</string>" "" > "$PL_HOME"; launchctl unload "$PL_HOME" 2>/dev/null; launchctl load "$PL_HOME"; fi
  else say "[dry-run] write and load $PL_LINK and $PL_HOME"; fi
fi

say ""
say "Done. EYE3 Link runs by itself at every start and updates itself."
say "Open EYE3 Home in your normal browser: https://j-janko420.github.io/EYE3-VISION/home/?splash=0&box=1"
say "Your own playlists go into: $DEST/playlists"
