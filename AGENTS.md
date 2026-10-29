# EYE3 Vision — agent guide

Read by OpenCode, Claude Code and other coding agents.

## What this is
A single static page (`index.html`): an on-device visual workspace. No backend, no API keys, no build step.

## Run
`python3 -m http.server 8080`, then open http://localhost:8080 (the camera needs localhost or HTTPS).

## Structure (all in `index.html`)
- CSS tokens on `:root`; keep the dark/crimson "red portal" look (near-black `#050101`, accent `#ff263f`, soft accent `#ff7a8a`, text `#fff5f6`, muted `#b9a9ac`). The eye-in-diamond mark is inline SVG; no personal photos or base64 images are committed (a personal photo theme stays in the browser's localStorage).
- One IIFE script. Engines load lazily through `useEngine()`: COCO-SSD (`getDetector`), MobileNet (`getClassifier`), Tesseract (`getOcr`), exifr. Versions are pinned in `LIBS`.
- Views: Image inspector, Side-by-side compare, Visual library, Connect TV (`setView`). Connect TV is a mirroring helper (Miracast; iPhone + Philips Saphi needs HDMI or a stick, since Saphi has no browser, AirPlay for Apple TV) with a QR link, a TV-browser route and presentation mode; no native TV app. It also has built-in casting: receiver overlay `#receiver`, sender `connectSender`, scanner.

## EYE3 Home
`home/index.html` is a fullscreen launcher for a laptop/PC connected to the TV over HDMI. Unlike the TV portal it runs in a MODERN browser, so modern CSS/JS is fine. Keyboard/remote nav (arrows, Enter, Back/Esc, F=fullscreen). Opens with a once-per-session splash (`?splash=0` skips it) and a "See beyond" hero. Live TV uses hls.js (pinned) with a native-HLS fallback; adult groups filtered; the viewer's playlist is in localStorage only. Tiles open the main app (`index.html?tv=1`), YouTube leanback, a web iframe, and info overlays. Also: Radio (radio-browser.info directory, https-only streams), My media (USB drive or files via the file picker, played in place with object URLs, never uploaded), a free-list picker in Live TV (iptv-org categories, M3UPT; adult groups stay filtered), a drifting-clock screensaver (key `S`, Settings sets the idle time; it never starts during playback) and a screen wake lock while media plays. Home also has a Phone remote receiver (Settings → Phone remote; same ntfy `eye3rc-<code>` topic scheme as the portal, code kept in localStorage `eye3.home.rc`, `?signal=` honoured on localhost only). It accepts only a fixed whitelist of navigation/media commands (arrows, ok, back, home, chup/chdown, digits, tv/radio/media, volup/voldown/mute, play, sleep, saver); never add commands that take text, URLs or files. A sleep timer (key `Z`, chip in the footer) stops playback and starts the screensaver.

## Channel catalogue
`scripts/build_channels.py` + `.github/workflows/channels.yml` rebuild the free catalogue weekly (and on demand) on a GitHub runner, which has real internet: it reads the public iptv-org `index.m3u`, keeps only HLS streams, drops adult channels, geo-blocked entries and streams that need custom headers, probes every stream and keeps the ones that return a real playlist. Output (committed by the workflow): `iptv/eye3-full.m3u` (for SS IPTV / Smart STB / TiviMate, all working channels grouped by category) and `iptv/channels.json` (compact, read by EYE3 Home and the TV portal; field `s`=1 means https, which is all a browser on https can play). The builder refuses to publish if fewer than 50 channels answer. Do not hand-edit these generated files; change the script. Do not add paid, pirated or adult sources. `iptv/eye3.m3u` stays as the small hand-picked starter list.

## TV portal
`portal/c/index.html` is the Smart STB/MAG IPTV portal and `portal/check/index.html` is the TV capability check. Both must stay ES5 (no arrow functions, let/const, template literals, `?.`, `??`, spread) with plain CSS (no custom properties, flex, grid, `inset`, `min()`), because TV engines are old. The menu has Live TV (picks), All channels (category browser) and By country, both fed by `../../iptv/channels.json` over same-origin XHR, with Back returning to the previous list and a fallback to the built-in channels if the catalogue cannot load. Play through `gSTB.Play('ffmpeg ' + url)` when the MAG API exists, else HTML5 video. The portal also has a Phone remote receiver: it listens on an ntfy topic (`eye3rc-<code>`) via EventSource (XHR-poll fallback) and applies commands by synthesizing `document.onkeydown`; `remote/index.html` is the phone sender (POSTs plain commands). Keep both ES5-safe where they touch the portal. Only free public streams and the viewer's own playlist; never bundle paid or pirated sources.

## Rules
- Images must never be uploaded to a server. Keep analysis in the browser. Casting sends frames only peer-to-peer over the LAN (`RTCPeerConnection` with `iceServers: []`, never add STUN/TURN); ntfy carries only AES-GCM ciphertext keyed by the pairing code.
- Never auto-connect a sender from a `?join=` link; require a button press. The `?signal=` and `?pairTimeout=` overrides are honored on localhost only.
- Pin CDN versions exactly; never use `@latest`.
- Render untrusted text (file names, EXIF, OCR) with `textContent`, never `innerHTML`.
- A failed engine load must degrade to an inline message, not break the page.
- Deploys via `.github/workflows/pages.yml` on push to `main`.

## Skills
Design and UI skills from jakubkrehel/skills (MIT) live in `.claude/skills/` and load automatically in Claude Code and OpenCode: better-ui, better-colors, better-typography, better-layout, better-accessibility, better-writing, better-interface, interface-review, break, state-machine, variant, build-design, explain-interface, teardown.

## Verify a change
Load the page, inspect an image, run the live camera, compare two images, save to the library. Check the browser console for errors.
