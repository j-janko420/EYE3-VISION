# EYE3-VISION
Designed by i3 Design
https://raw.githubusercontent.com/hasanbeder/M3Unator/main/M3Unator.user.js
## Smart TV platform (IPTV / MAG portal)
Turns any device with a browser (non-Android TVs, boxes, PCs) into a smart TV.

- **MAG/Stalker portal client** using virtual MAC `00:1A:79:EC:5F:08` (default; editable in the UI; the requested `00:1A:79:EC5F:08` was normalised to a valid 6-octet MAC).
- M3U playlist loader, HLS/MP4 online streaming, built-in web browser tab, screen mirroring (Screen Capture API).

```
npm start   # http://127.0.0.1:8080  (HOST/PORT env vars to change; set HOST=0.0.0.0 to expose on LAN)
```
Use only with portals/streams you are authorised to access.

## Connectors (plugins)
Each file in `plugins/` is a connector: `{id, name, description, fields, list(params, ctx), resolve?(item, ctx)}`; it is auto-loaded and shown in the **Connectors** tab. Included: `url` (paste stream links), `stalker` (MAG portal + virtual MAC), `m3u`, `local` (your files in `media/`, or `MEDIA_DIR`). Tick **Transcode** to stream through `ffmpeg` (must be installed) to H.264/AAC MP4 for TV browsers.

Run tests with `npm test` (Node built-in runner, no dependencies).
