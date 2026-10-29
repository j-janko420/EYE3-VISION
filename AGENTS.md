# EYE3 Vision — agent guide

Read by OpenCode, Claude Code and other coding agents.

## What this is
A single static page (`index.html`): an on-device visual workspace. No backend, no API keys, no build step.

## Run
`python3 -m http.server 8080`, then open http://localhost:8080 (the camera needs localhost or HTTPS).

## Structure (all in `index.html`)
- CSS tokens on `:root`; keep the dark/orange look.
- One IIFE script. Engines load lazily through `useEngine()`: COCO-SSD (`getDetector`), MobileNet (`getClassifier`), Tesseract (`getOcr`), exifr. Versions are pinned in `LIBS`.
- Views: Image inspector, Side-by-side compare, Visual library, Connect TV (`setView`). Connect TV is a mirroring helper (Miracast; iPhone + Philips Saphi needs HDMI or a stick, since Saphi has no browser, AirPlay for Apple TV) with a QR link, a TV-browser route and presentation mode; no native TV app. It also has built-in casting: receiver overlay `#receiver`, sender `connectSender`, scanner.

## EYE3 Home
`home/index.html` is a fullscreen launcher for a laptop/PC connected to the TV over HDMI. Unlike the TV portal it runs in a MODERN browser, so modern CSS/JS is fine. Keyboard/remote nav (arrows, Enter, Back/Esc, F=fullscreen). Live TV uses hls.js (pinned) with a native-HLS fallback; adult groups filtered; the viewer's playlist is in localStorage only. Tiles open the main app (`index.html?tv=1`), YouTube leanback, a web iframe, and info overlays.

## TV portal
`portal/c/index.html` is the Smart STB/MAG IPTV portal and `portal/check/index.html` is the TV capability check. Both must stay ES5 (no arrow functions, let/const, template literals, `?.`, `??`, spread) with plain CSS (no custom properties, flex, grid, `inset`, `min()`), because TV engines are old. Play through `gSTB.Play('ffmpeg ' + url)` when the MAG API exists, else HTML5 video. Only free public streams and the viewer's own playlist; never bundle paid or pirated sources.

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
