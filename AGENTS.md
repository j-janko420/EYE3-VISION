# EYE3 Vision — agent guide

Read by OpenCode, Claude Code and other coding agents.

## What this is
A single static page (`index.html`): an on-device visual workspace. No backend, no API keys, no build step.

## Run
`python3 -m http.server 8080`, then open http://localhost:8080 (the camera needs localhost or HTTPS).

## Structure (all in `index.html`)
- CSS tokens on `:root`; keep the dark/orange look.
- One IIFE script. Engines load lazily through `useEngine()`: COCO-SSD (`getDetector`), MobileNet (`getClassifier`), Tesseract (`getOcr`), exifr. Versions are pinned in `LIBS`.
- Views: Image inspector, Side-by-side compare, Visual library (`setView`).

## Rules
- Images must never be uploaded. Keep analysis in the browser.
- Pin CDN versions exactly; never use `@latest`.
- Render untrusted text (file names, EXIF, OCR) with `textContent`, never `innerHTML`.
- A failed engine load must degrade to an inline message, not break the page.
- Deploys via `.github/workflows/pages.yml` on push to `main`.

## Skills
Design and UI skills from jakubkrehel/skills (MIT) live in `.claude/skills/` and load automatically in Claude Code and OpenCode: better-ui, better-colors, better-typography, better-layout, better-accessibility, better-writing, better-interface, interface-review, break, state-machine, variant, build-design, explain-interface, teardown.

## Verify a change
Load the page, inspect an image, run the live camera, compare two images, save to the library. Check the browser console for errors.
