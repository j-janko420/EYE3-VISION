# EYE3 Vision — Copilot hand-off backlog

Owner: i3 Design. Live: https://j-janko420.github.io/EYE3-VISION/
Read `AGENTS.md` first. Its rules are binding on every task below.

## Hard rules (apply to every task)
- Keep analysis in the browser. Never upload images. No STUN/TURN (`iceServers: []`). ntfy carries only AES-GCM ciphertext.
- Never auto-connect from `?join=`. `?signal=` and `?pairTimeout=` are honoured on localhost only.
- Pin CDN versions exactly. Never `@latest`.
- Untrusted text goes through `textContent`, never `innerHTML`.
- A failed engine or stream load degrades to an inline message. It must not break the page.
- `portal/c/` and `portal/check/` stay ES5 and plain CSS (no arrow functions, let/const, template literals, `?.`, `??`, spread, custom properties, flex, grid, `inset`, `min()`).
- Free public streams and the viewer's own playlist only. No paid or pirated sources.
- **Never**: flash or modify TV firmware, bypass signed firmware or TV settings, or ship custom firmware. Official Philips updates only (50PUT6103/56).
- Do not commit personal photos or the Smart STB MAC to the public repo. Personal images stay in the browser (localStorage), as the existing personal theme does.

## Priorities
| ID | Task | Priority | Needs |
|---|---|---|---|
| T1 | Red-cosmic restyle, EYE3 Home first | P1 | Copilot |
| T2 | Feature pages wired live | P1 | Copilot |
| T3 | Tests and CI in the repo | P1 | Copilot |
| T4 | Stream health check | P2 | Copilot |
| T5 | Real-device verification | P1 | **Owner** (TV and laptop) |
| T6 | Privacy and housekeeping | P2 | Owner decision |
| T7 | Android launcher (only if a stick is bought) | P3 | Owner decision |

---

## T1 — Red-cosmic restyle
**Goal:** match the "eye3 VISION · SEE BEYOND" look: red cosmic background, stars, bold logo lockup, hero "THE THIRD …".
**Order:** `home/index.html` (modern browser) → `index.html` → `portal/c/index.html` (ES5, plain CSS) → `remote/index.html` → `bridge/index.html`.
**Steps**
1. Define tokens once on `:root` (red, deep-space background, accent, text, muted). Keep a dark theme. Keep the orange as a secondary accent only if contrast allows.
2. Build the star-field and glow with CSS gradients or a small inline SVG. Do not embed base64 photos.
3. Add a logo lockup as inline SVG (text "eye3 VISION", tagline "SEE BEYOND"). No personal silhouettes in the repo.
4. In `portal/c`, reproduce the look with solid colours, borders and tables only, since the TV engine is old.
**Acceptance**
- Contrast is at least 4.5:1 for body text and 3:1 for large text.
- Focus ring is visible on every tile for keyboard and remote navigation.
- No console errors. Nothing overflows at 1280×720 and 1920×1080.
- `portal/c` passes the ES5 and plain-CSS rules above.

## T2 — Feature pages wired live
Model them on the reference layout: Hero, Apps & Inputs, Live TV, Programme Guide, Settings, App page, Notifications, Quick menu, Open a website, Music.

| Page | Source | Fallback |
|---|---|---|
| Hero | static, "THE THIRD …" headline | none needed |
| Apps & Inputs | tiles for Live TV, YouTube, Web, Cast, plus guidance for TV HDMI and Miracast inputs | text hint only. The page cannot switch TV inputs. |
| Live TV | `iptv/eye3.m3u` plus iptv-org lists, hls.js (pinned) with native-HLS fallback. Poster "Ready to tune in?" | "Stream unavailable, try the next channel" |
| Programme Guide | XMLTV or the iptv-org EPG, cached in localStorage | "No guide data for this channel" |
| Settings | theme, playlist link, clock, language. Local storage only | defaults |
| App page (YouTube) | `youtube.com/tv` in an iframe | open in a new tab |
| Notifications | local list (stream down, remote connected, update available) | empty state |
| Quick menu | dialog with keyboard and remote shortcuts | none |
| Open a website | URL box, iframe, new-tab fallback for sites that refuse framing | message |
| Music | free radio streams only (e.g. Radio Browser API or iptv-org radio) | message |

**Acceptance:** every control does something real or shows a clear inline message. Adult groups stay filtered. Back/Esc closes overlays. Nothing blocks when offline.

## T3 — Tests and CI
1. Add `tests/` with Playwright specs and route stubs for the CDN engines, ntfy and HLS (the CDNs are blocked in some environments).
2. Cover: core app (inspect, compare, library), Connect TV and casting handshake, TV portal (menu, search, playlist), phone remote (all commands), EYE3 Home (tiles, Live TV overlay, keyboard nav), PWA (manifest, service worker, offline shell), and every T2 page.
3. Add `.github/workflows/ci.yml` to run them on every pull request.
4. Add a static check that fails if `portal/c/index.html` or `portal/check/index.html` contains ES6 syntax or banned CSS.
**Acceptance:** CI is green on `main`, and a deliberate ES6 line in the portal turns it red.

## T4 — Stream health
- Scheduled GitHub Action (weekly) that probes every URL in `iptv/eye3.m3u` and the built-in channel list, and opens an issue listing dead streams.
- Add at least two fallback sources per category.
**Acceptance:** a dead URL appears in the generated issue, and the portal skips dead channels without a freeze.

## T5 — Real-device verification (owner does this, Copilot records results)
Record each result in `docs/DEVICE_RESULTS.md` with a photo or note.
1. TV update info: Settings → Update software → Current software info. Note the version. Update only through official Philips channels (internet or USB), for 50PUT6103/56.
2. TV browser: Home → Apps → Internet browser. If it exists, open `https://j-janko420.github.io/EYE3-VISION/portal/c/`. Note whether welcome, menu and red errors show.
3. Smart STB: at smart-stb.tv/3802625403 add `https://j-janko420.github.io/EYE3-VISION/iptv/eye3.m3u` and set it as Portal 1. Note whether channels play.
4. Laptop on HDMI: open `https://j-janko420.github.io/EYE3-VISION/home/`, press F for fullscreen, test a wireless mouse and the remote at `/remote/`.
5. Phone remote: open the TV's Phone remote screen, enter the 8-character code in `/remote/`, and test every button over real ntfy.sh.
6. PWA: install EYE3 Home and test kiosk start (see `home/setup.html`).

## T6 — Privacy and housekeeping (owner decides first)
- The repo is public. Early history contains the Smart STB virtual MAC `00:1A:79:EC:5F:08`. Options: purge history, or start a fresh repo. Do not act without the owner's go-ahead.
- Remove duplicated README sections. Decide whether `netlify.toml` stays.
- Update `AGENTS.md` and `README.md` for the new theme and the tests folder.

## T7 — Android launcher (only if a stick is bought later)
Base it on cleanyourtv (MIT, with credit). Write our own DIAL server. Do **not** copy SmartTube (GPL). Does not apply to the Saphi TV itself.

---

## What the owner does to get it on the TV (zero spend)
1. **Check software:** TV Settings → Update software → Current software info. Update only with official Philips files for 50PUT6103/56.
2. **Try the TV browser:** Home → Apps → Internet browser. If present, open `https://j-janko420.github.io/EYE3-VISION/portal/c/`.
3. **Smart STB:** use smart-stb.tv/3802625403 to add the playlist `https://j-janko420.github.io/EYE3-VISION/iptv/eye3.m3u` and set it as Portal 1.
4. **Fallback that always works:** laptop plus HDMI cable plus wireless mouse. Open `https://j-janko420.github.io/EYE3-VISION/home/` and press F.
5. **Phone as remote:** open `https://j-janko420.github.io/EYE3-VISION/remote/`.
6. Send photos of each result so T5 can be closed.

## Suggested Copilot prompt
> Read `AGENTS.md` and `docs/COPILOT_TASKS.md`. Complete task T1 on `home/index.html` only. Open one PR. Follow every hard rule. Do not add personal images.
