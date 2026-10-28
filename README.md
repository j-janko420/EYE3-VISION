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

## Features
- **Unified TV UI** (Live / Library / Online / Favourites / Browser / Mirror TV) with TV-remote navigation: arrow keys move focus, Enter selects, Back/Esc returns to the tab bar.
- **Favourites, search, saved profiles** (portal/MAC/playlist settings), stored only in the browser's localStorage, never in the repo.
- **EPG:** paste an XMLTV URL in the Live tab; M3U channels with `tvg-id` show Now/Next.
- **Subtitles:** local files with a sidecar `.srt`/`.vtt` of the same name get subtitles (SRT converted to WebVTT).
- **Free & legal presets** connector (public demo streams, open iptv-org playlist). **Direct URLs** connector for HLS/MP4/DASH.
- **Access token:** the server binds to `127.0.0.1` by default. With `HOST=0.0.0.0` a token is required: set `EYE3_TOKEN`, or a random one is printed; open `http://<ip>:8080/?token=<token>` once (stored as an HttpOnly cookie). Use over a trusted LAN only (plain HTTP).
- **Docker:** `docker build -t eye3-vision . && docker run -p 8080:8080 -e EYE3_TOKEN=choose-one -v /path/to/videos:/media eye3-vision`
- Agent profile and rules: [docs/AGENT.md](docs/AGENT.md).

**Use only content you are licensed or authorised to access.** No geo-unblocking, DRM circumvention or piracy sources are provided.
