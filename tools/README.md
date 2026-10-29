# EYE3 Link — use your own IPTV account in EYE3 Home

EYE3 Home runs in your browser. IPTV providers (Xtream Codes, MAG/Stalker portals, many M3U links) cannot be read by a web page directly, so **EYE3 Link** runs on your computer and does it for the page.

- It runs **only on your computer** (address `127.0.0.1:8765`). Nothing is uploaded anywhere.
- Only EYE3's own pages may use it, and every play link carries a secret created each time it starts.
- Your account details stay in your browser's storage on this computer. They are never stored by EYE3 Link.
- Use only accounts and playlists you are entitled to watch. Adult groups stay hidden.

## Start it
1. Install **Python 3** from python.org (tick "Add to PATH" on Windows).
2. Download `eye3-link.py` (EYE3 Home → Live TV → IPTV accounts has a download link).
3. Open a terminal in the folder where you saved it and run:
   - Mac / Linux: `python3 eye3-link.py`
   - Windows: `py eye3-link.py`
4. Leave that window open while you watch. Press Ctrl+C to stop.

## Add your account (EYE3 Home → Live TV → IPTV accounts)
| Type | What to enter |
|---|---|
| M3U link | the playlist address your provider gave you |
| Xtream Codes | server address (for example `http://provider.example:8080`), username, password |
| MAG / Stalker | portal address (for example `http://portal.example.com/c/`) and the MAC address registered with your provider |

Your channels appear in Live TV under the account's name, with a group filter for the provider's own groups.

## Problems
- "EYE3 Link is not running": start it (above), then press **Check again**.
- "The server rejected this username or password": check them with your provider.
- MAG portal says it did not accept the MAC: the MAC must be the one activated with your provider.
- A provider with an invalid HTTPS certificate: run `python3 eye3-link.py --insecure`.
- Port busy: `python3 eye3-link.py --port 8766` (EYE3 Home looks for 8765, so keep the default if you can).
- Using your own copy of EYE3 Home on another address: `python3 eye3-link.py --origin https://your.address`.
- Tests: `python3 tools/test_eye3_link.py`.
