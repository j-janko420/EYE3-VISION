# EYE3-VISION
Designed by i3 Design

## Welcome and personal theme

EYE3 opens with a **Welcome to EYE3 Vision · Designed by i3 Design** screen. It shows once per session; press OK or tap to start, or add `?welcome=0` to skip it.

**Personalize** (top bar) sets your own photo as the background. EYE3 finds the faces in it (TensorFlow.js BlazeFace, free, on-device) and uses them as round tool icons and as your profile picture, on an i3 navy theme. If no faces are found, or the face model can't load, the centre of the photo becomes the icon. The photo is stored only in this browser (localStorage) and is never uploaded or added to this repo. Switch the theme off or remove the photo from the same dialog.

## Run it live

EYE3 Vision is a static page (`index.html`) with real, free, on-device analysis. No API keys, no backend, no cost.

| Capability | Free tool | Loaded |
| --- | --- | --- |
| Object detection (boxes, live camera) | TensorFlow.js + COCO-SSD | on demand |
| Scene labels | MobileNet v2 | on demand |
| Text extraction (OCR) | Tesseract.js | on click |
| Camera data (EXIF, GPS) | exifr | on demand |
| Palette, compare, difference heatmap, library | Canvas + localStorage | built in |
| Apple TV link code (QR) | qrcode-generator | on demand |
| Scan a pairing code | BarcodeDetector, else jsQR | on demand |
| Device-to-device casting | WebRTC + ntfy (signalling only) | on click |

Run locally (the camera needs `localhost` or HTTPS):

```
python3 -m http.server 8080   # then open http://localhost:8080
```

Publish free on **Netlify**: in Netlify choose **Add new project → Import an existing project → GitHub → EYE3-VISION**. `netlify.toml` already sets the build, publishing only `index.html` and `portal/`. Every push to `main` then redeploys. (GitHub Pages needs a paid plan for private repos; `.github/workflows/pages.yml` is kept as a manual-only option.)

**Phones:** 44px touch targets, safe-area aware, live camera uses the rear lens.
**TV:** auto-enabled on Tizen, webOS, Android TV, Fire TV and similar; otherwise add `?tv=1` or press the **TV mode** button. Large type, big focus rings, D-pad navigation and Back/Escape to stop the camera.

**Connect TV:** the **Connect TV** tool lists every route.
- **iPhone with a TV that has no browser or AirPlay (e.g. Philips Saphi):** use a USB-C/Lightning to HDMI adapter (most reliable), or a streaming stick (Apple TV for AirPlay; Fire TV or Google TV stick for a browser). Wi-Fi mirroring apps (DLNA) also exist; most are paid. IPTV player apps can only play video channels, so they can't run EYE3.
- **Mirroring:** Miracast from an Android phone (Cast / Smart View) or a Windows PC (`Win + K`); AirPlay from an iPhone or Mac to an Apple TV or AirPlay TV.
- **TV browsers:** where a TV or stick has a browser, open the EYE3 link there and TV mode turns on automatically.

**Smart STB portal check (Philips Saphi with Smart STB):** add `https://<user>.github.io/EYE3-VISION/portal/c/` as a portal in Smart STB (at smart-stb.tv, using the code the app shows) and open it on the TV. The page lists what the TV's engine supports: MAG remote API, box MAC, modern JavaScript, WebGL, WebAssembly, WebRTC, HLS/MP4 video, internet access. It also shows every remote key code. It is plain ES5, so it runs on old TV engines, and it sends nothing anywhere. Its **Open EYE3 app** button opens the full app in TV mode.

**Start presentation** hides the menus, switches to the large TV layout and keeps the screen awake.

**Built-in casting to a screen with a browser (Fire TV / Google TV stick, browser TV, laptop):** open EYE3 on that screen, go to **Connect TV** and press **Show pairing code here**. On the iPhone, scan the code with the camera app (or **Scan the TV's code** in EYE3) or type the 8-character code, press **Connect**, and allow it on the TV. Your image or live camera, with detections, appears on the TV. Pictures travel directly between the two devices over the Wi-Fi (WebRTC with no relay). Only the connection details pass through ntfy.sh, encrypted with the pairing code. Add `?receive=1` to a TV bookmark to open straight into pairing. Guest Wi-Fi networks that isolate devices will block it.

Images never leave the browser. Models download once from public CDNs (jsDelivr, Google storage, TF Hub) and are cached by the browser.

---

https://raw.githubusercontent.com/hasanbeder/M3Unator/main/M3Unator.user.js
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
