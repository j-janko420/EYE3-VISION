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

## 18+ section (optional, PIN-protected)
Hidden by default. Type `4`, `2`, `0` on the keyboard/remote (outside a text box) to reveal the **18+** tab, then create a PIN (4-8 digits) on first use. The PIN is scrypt-hashed and stored locally in `DATA_DIR` (default `./data`, git-ignored); 5 wrong tries lock it for a minute; it auto-locks after 15 minutes idle.
- Items from **your own authorised** M3U/portal/URL sources whose group or name marks them as adult (e.g. group-title "Adult") are removed from every normal list and only returned by the server to an unlocked 18+ view, grouped into categories by the playlist's group titles.
- No adult sources, scrapers, VPN or geo-unblocking are included or connected. Adults only; you are responsible for the content you open.

---

README.pt.md
M3UPT

Lista de IPTV gratuita e legal em formato M3U com estações de TV e rádio em português. Apenas com streams públicos e oficiais.

---

## 🎯 Objectivo

Disponibilizar uma lista de IPTV legal e gratuita em formato M3U com estações de TV e rádio em português.

---

## ❓ Porquê?

---

Não é fácil para falantes de português a viver no estrangeiro manter contacto com a sua cultura. Este projecto também ajuda qualquer pessoa que esteja a tentar aprender português ou simplesmente curiosa sobre a língua.

---

## 📺 Principais canais de TV

- RTP 1
- RTP 2
- SIC
- TVI
- RTP 3
- SIC Notícias
- CNN Portugal
- Euronews PT
- ARTV
- RTP Memória
- RTP Açores
- RTP Madeira
- RTP África
- RTP Internacional
- TVI Internacional
- Porto Canal
- Euronews EN
- Euronews ES
- Euronews IT
- Euronews FR
- Euronews DE
- teleSUR
- teleSUR English
- RT News
- RT America
- RT UK
- RT Español
- RT France
- RT Documentary
- CGTN
- CGTN Español
- CGTN Français
- Al Jazeera English
- France 24 English
- France 24 Español
- France 24 Français
- CNN International
- Reuters TV
- NHK World
- Deutsche Welle Español
- Deutsche Welle Deutsch
- Deutsche Welle Arabic
- TV5 Monde Info
- TVE 24h
- La 1
- La 2
- Gulli
- Trace Urban
- Canal 11 Internacional
- Fuel TV
- Red Bull TV
- Fashion TV

## 📻 Principais estações de rádio

- Antena 1
- Antena 2
- Antena 3
- Antena 1 Açores
- Antena 1 Madeira
- RDP Internacional
- RDP África
- Rádio Comercial
- M80
- Rádio Oxigénio
- Rádio Renascença
- TSF
- Venice Classic Radio

## 🏖️ Beachcam

- Mais de 100 cameras em praias portuguesas

---

## 🧭 Começar

Tudo o que precisa para começar é configurar o seu leitor de IPTV favorito com o endereço da lista M3U. Não terá de configurar o endereço do EPG na maior parte dos leitores, porque ele será automaticamente extraído da própria lista M3U.

### 🔗 Links para usar no seu leitor de IPTV

- **M3U**: <https://m3upt.com/iptv>
- **EPG**: <https://m3upt.com/epg> 

---

## 🎬 Leitores de IPTV recomendados

Para ter uma melhor experiência recomendo o uso de um dos seguintes leitores de IPTV.

---

### 🏆 OTT TV ou OTT Navigator IPTV (clones)

Este leitor de IPTV é o mais completo e abre streams encriptados com DRM.

![OTT Navigator IPTV screenshot](/images/OTT-Navigator-IPTV-M3UPT-playlist.avif "OTT Navigator IPTV screenshot")

**Configurações recomendadas:**

- Restaure este backup: HAVBxx (senha: 12345)

Para aplicar o código de backup, siga os seguintes passos após instalar a aplicação OTT Navigator IPTV:

Configurações > Configurações adicionais > Backup e Restauração > Restaurar um backup de configuração feito anteriormente > inserir código > Restaurar posição (Todos) > inserir senha > reiniciar aplicação

[Google Play](https://play.google.com/store/apps/details?id=appnovatica.tv)

---

### 🥇 Sparkle TV

Este leitor de IPTV também abre streams encriptados com DRM.

![Sparkle TV screenshot](/images/Sparkle_TV.avif "Sparkle TV screenshot")

**Configurações recomendadas:**

Configurações - Fontes - Tempo entre a sincronização - 3 horas

[Google Play](https://play.google.com/store/apps/details?id=se.hedekonsult.sparkle)

---

### 🥇 TiviMate

Este leitor de IPTV também abre streams encriptados com DRM.

![TiviMate screenshot](/images/TiviMate.avif "TiviMate screenshot")

**Configurações recomendadas:**

Configurações - Playlists - M3UPT - Intervalo de actualização, horas - 2

[Google Play](https://play.google.com/store/apps/details?id=ar.tvplayer.tv)

---

### 🥇 M3U IPTV

Este leitor de IPTV simples também abre streams encriptados com DRM. Excelente experiência em dispositivos móveis.

![M3U IPTV screenshot](/images/M3U_IPTV.avif "M3U IPTV screenshot")

[Download](https://m3u-ip.tv/)

---

### 🥈 ProgTV

Este é um bom leitor para Android, mas não abre streams encriptados com DRM. Curiosamente, este leitor consegue contornar o bloqueio geográfico dos canais SIC.

![ProgTV screenshot](/images/ProgTV-M3UPT-playlist.avif "ProgTV screenshot")

**Configurações recomendadas:**

- Opções - Opções de reprodução - Motor: ProgDVB Engine

[Google Play](https://play.google.com/store/apps/details?id=com.progdvb.progtva) 

---

### 🥉 Perfect Player (descontinuado)

Este é outro bom leitor para Android, mas não abre streams encriptados com DRM.

![Perfect Player screenshot](/images/Perfect-Player-M3UPT-playlist.avif "Perfect Player screenshot")

**Configurações recomendadas:**

- GUI - Mostrar grupos de canais como pastas ✅
- Reprodução - Descodificador: Hardware
- Reprodução - User-Agent: IE

[🔑 Downloader](https://play.google.com/store/apps/details?id=com.esaba.downloader): 7609389

---

### 🥇 Yuki-IPTV

Este é o leitor recomendado para computadores GNU/Linux.

![Yuki-IPTV screenshot](/images/Yuki-IPTV-M3UPT-playlist.avif "Yuki-IPTV screenshot")

**Configurações recomendadas:**

- Main - Open previous channel on startup ✅
- Video - Deinterlace ✅
- Other - mpv options: --hwdec=auto --demuxer-lavf-o=cenc_decryption_key=a2226def4bc8f249de2daf36b7c12b1e
- Debug - Automatic reconnection ✅

[⬇️ Download]([⬇️ Download](https://github.com/itachi-re/yuki-iptv)

---

### 🥇 Kodi com PVR IPTV Simple Client

Este é o leitor recomendado para as restantes plataformas.

![Kodi screenshot](/images/Kodi-M3UPT-playlist.avif "Kodi screenshot")

**Configurações recomendadas:**

- Deverá instalar o addon YouTube e configurar as suas legendas para pt-PT (Sem gerador automático).

[⬇️ Download](https://kodi.tv/download/)

---

## 📓 Notas

- Streams encriptados com DRM não abrem em alguns leitores.
- Alguns canais só funcionam com IP Português, quem vive fora de Portugal terá de usar uma [VPN](https://m3upt.com/vpn).
- Alguns streams só funcionam no Kodi com o addon YouTube instalado.

---

## 👍 Características recomendadas para TV boxes Android

Para uma boa experiência de utilização o seu aparelho deverá ter um bom processador e memória RAM suficiente. Evite processadores da Rockchip e da Allwinner.

- **SoC**: Amlogic S905Y5, S905A ou S905X5 (rápido, eficiente e suporta o moderno codec de vídeo AV1)
- **RAM**: 4 GB
- **Firmware**: [slimBOXtv (versão ATV)](https://slimboxtv.ru/)

Normalmente TV boxes Android com processadores Amlogic são melhores que aparelhos com processadores Rockchip ou Allwinner.

Pode comprar um excelente aparelho já configurado e pronto a usar na [loja oficial](https://m3upt.com/tvbox).

---

## 🛒 Lojas recomendadas

- [AliExpress](https://m3upt.com/ae)
- [Amazon](https://m3upt.com/amazon)
- [eBay](https://m3upt.com/ebay)
- [Geekbuying](https://m3upt.com/geekbuying)
- [Banggood](https://m3upt.com/banggood)
- [DHgate](https://m3upt.com/dhgate)

Se clicar nestes links e comprar alguma coisa, eu poderei receber uma pequena comissão. Não lhe sai mais caro e assim ajuda a manter este projeto em funcionamento.

---

Este é um projecto de código aberto.

- Visite a página do projeto no [GitHub](https://github.com/LITUATUI/M3UPT).
- Pode usar a secção [Issues](https://github.com/LITUATUI/M3UPT/issues) para reportar bugs ou links inválidos e a secção [Discussions](https://github.com/LITUATUI/M3UPT/discussions) para sugestões ou assuntos diversos.
- No Telegram adira ao [grupo público](https://t.me/m3upt) para ficar actualizado e conversar.
- Temos também um grupo no [Signal](https://m3upt.com/signal).
- Apoie este projecto com a compra de uma [TV Box](https://m3upt.com/tvbox) já configurada ou com um [donativo](https://m3upt.com/donativo). O seu apoio incentiva-me a dedicar mais tempo a este projeto e dá-lhe acesso ao grupo de Telegram privado.

---

## ⭐ Estrelas no GitHub
