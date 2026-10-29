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

### No Python? Use the ready-to-run program
GitHub builds ready-to-run programs automatically from `eye3-link.py` and publishes them at
https://github.com/j-janko420/EYE3-VISION/releases/tag/eye3-link-latest (Windows `.exe`, Mac with Apple chip, Linux). Download the one for your system and open it; leave its window open. Check the file against `SHA256SUMS.txt` if you like. They are **not code-signed**, so Windows SmartScreen or macOS Gatekeeper may warn you (Windows: More info, Run anyway; Mac: right-click, Open), and some antivirus tools flag this kind of program. If you prefer, run the Python script instead; it is the reference build.

## Add your account (EYE3 Home → Live TV → IPTV accounts)
| Type | What to enter |
|---|---|
| M3U link | the playlist address your provider gave you |
| Xtream Codes | server address (for example `http://provider.example:8080`), username, password |
| MAG / Stalker | portal address (for example `http://portal.example.com/c/`) and the MAC address registered with your provider |

Your channels appear in Live TV under the account's name, with a group filter for the provider's own groups.

### Movies and series on demand
Add your Xtream Codes account (server, username, password), then Live TV → **Movies & series**. Pick Movies or Series, a category, or search. Series open into seasons and episodes. Big libraries can take a minute to load the first time. Files the browser can play (mp4) start in the page; `.mkv` and some others need VLC.

### Free movies (no account)
In Live TV → **Movies & series** press **Free movies**: public-domain films from the [Internet Archive](https://archive.org), by genre or search. No account and no EYE3 Link needed, only an internet connection that can reach archive.org (a VPN or proxy can block it).

### Direct links
Open these on the laptop to jump straight to the right form (nothing is filled in or saved from the link):
- M3U link: `https://j-janko420.github.io/EYE3-VISION/home/?add=m3u`
- Xtream Codes login: `https://j-janko420.github.io/EYE3-VISION/home/?add=xtream`
- MAG / Stalker portal (address + MAC): `https://j-janko420.github.io/EYE3-VISION/home/?add=mag`
- Movies & series on demand (needs an Xtream account added first): `https://j-janko420.github.io/EYE3-VISION/home/?add=movies`
- Playlist maker (your own channels, M3U import/export): `https://j-janko420.github.io/EYE3-VISION/home/?add=playlist`

Adult groups in your own accounts show only after you unlock the hidden section (see below).

## MAG / Stalker portal says "a web page, not data"
EYE3 Link tries the usual data addresses under your portal (`/server/load.php`, `/stalker_portal/server/load.php`, `/portal.php`, `/c/...`) and the error lists every address it tried and what came back. A "web page" answer usually means the address is the portal's front page or belongs to a different kind of service. Use the address your box or app uses (often ending in `/c/`), or paste the portal's `portal.php` / `load.php` address itself. The name you give the account is only a label (any name, in any language). The MAC must be the one that is active on the portal, and some portals only accept a MAC registered by your provider. If your app is "SmartPro"-style and logs in with a username and password instead of a MAC, add it as an Xtream Codes or M3U account.

## "Could not reach the server (getaddrinfo failed)"
Your computer cannot find the provider's address, although the same address may work in another app or on another device (different DNS or network). Start EYE3 Link with its own lookup as a fallback:

- Program (Windows): right-click `eye3-link-windows.exe` → **Create shortcut** → right-click the shortcut → **Properties** → in **Target** add ` --dns cloudflare` after the closing quote (use `google` for Google's resolver) → OK, then open the shortcut. Or in a command window: `eye3-link-windows.exe --dns cloudflare`.
- Python: `py eye3-link.py --dns cloudflare`

It only asks that public resolver when your normal lookup fails, and only for the provider's host name. Changing Windows DNS to `1.1.1.1` and `8.8.8.8` does the same for the whole computer. This is not a VPN: your traffic still goes straight to the provider.

## Channels blocked in your country (VPN / proxy)
EYE3 does **not** include a VPN: a VPN needs servers and software that a web page or this small helper cannot provide, and pretending otherwise would be unsafe. Options:
- Use a VPN you are allowed to use on this computer. EYE3 Home and EYE3 Link then use it automatically.
- If your VPN app offers a local **HTTP proxy** mode, point EYE3 Link at it: `python3 eye3-link.py --proxy http://127.0.0.1:PORT`. Everything EYE3 Link fetches for your own accounts then goes through it. (SOCKS proxies are not supported.)
- Check the terms of your provider and of the broadcaster before using either.

## Check which channels work from YOUR connection
The weekly list is tested from a server in another country, so some channels that only allow viewers from their own country may be missing or may not work for you. In EYE3 Home → Live TV, press **Check from my connection**. EYE3 Link then tests every channel in the list from your computer (and through your VPN or proxy, if you use one) and, with **hide failed** ticked, hides the ones that do not work for you. Results are remembered for 24 hours. **Where is my connection?** (IPTV accounts screen) tells you which country your connection appears to be in; it asks ipinfo.io once when you press it.

## Explicit (18+) section
Hidden on purpose: double-click the eye logo at the top left of EYE3 Home (or press Shift+X). Confirm you are 18 or older, optionally set a PIN, and an "Explicit (18+)" category appears in Live TV. It shows adult groups from **your own** accounts and playlists only; EYE3 provides no adult channels. It locks again when you reload the page, when the screensaver starts, or when the sleep timer ends. A PIN only stops casual use.

## Problems
- "EYE3 Link is not running": start it (above), then press **Check again**.
- "The server rejected this username or password": check them with your provider.
- MAG portal says it did not accept the MAC: the MAC must be the one activated with your provider.
- A provider with an invalid HTTPS certificate: run `python3 eye3-link.py --insecure`.
- Port busy: `python3 eye3-link.py --port 8766` (EYE3 Home looks for 8765, so keep the default if you can).
- Using your own copy of EYE3 Home on another address: `python3 eye3-link.py --origin https://your.address`.
- Tests: `python3 tools/test_eye3_link.py`.
