// EYE3-VISION: zero-dependency server. Serves the UI and proxies Stalker/MAG portal + M3U requests (avoids CORS).
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const DATA_DIR = path.resolve(process.env.DATA_DIR || path.join(__dirname, 'data'));
const MEDIA_DIR = path.resolve(process.env.MEDIA_DIR || path.join(__dirname, 'media'));
const adult = require('./lib/adult'), crypto = require('crypto'), { parse: parseXmltv, nowNext } = require('./lib/xmltv'), { srtToVtt } = require('./lib/subtitles');
const PORT = process.env.PORT || 8080, HOST = process.env.HOST || '127.0.0.1';
// Access token: required whenever the server is reachable beyond loopback.
const LOOPBACK = ['127.0.0.1', 'localhost', '::1'].includes(HOST);
const TOKEN = process.env.EYE3_TOKEN || (LOOPBACK ? '' : crypto.randomBytes(12).toString('hex'));
const sameTok = (a, b) => { const x = Buffer.from(String(a)), y = Buffer.from(String(b)); return x.length === y.length && crypto.timingSafeEqual(x, y); };
const cookieTok = (req) => (/(?:^|;\s*)eye3=([^;]+)/.exec(req.headers.cookie || '') || [])[1];
const DEFAULT_MAC = '00:1A:79:EC:5F:08'; // virtual MAC (normalised from 00:1A:79:EC5F:08)
const MAC_RE = /^([0-9A-F]{2}:){5}[0-9A-F]{2}$/;
const normMac = (m) => { const h = String(m || '').replace(/[^0-9a-f]/gi, '').toUpperCase(); return h.length === 12 ? h.match(/../g).join(':') : null; };
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
const send = (res, code, body, type = 'application/json') => { res.writeHead(code, { 'Content-Type': type }); res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body)); };
// SSRF guard: outbound fetches may not target loopback, link-local (cloud metadata) or unspecified addresses. LAN ranges stay allowed for local portals.
const dns = require('dns').promises, net = require('net');
const blockedIp = (ip) => net.isIPv4(ip) ? /^(127\.|169\.254\.|0\.)/.test(ip) : /^(::1?|::ffff:(127\.|169\.254\.|0\.)|fe80:)/i.test(ip);
async function safeFetch(url, opts) {
  const u = httpUrl(url); if (!u) throw new Error('Invalid URL');
  const host = u.hostname.replace(/^\[|\]$/g, '');
  const addrs = net.isIP(host) ? [{ address: host }] : await dns.lookup(host, { all: true });
  if (addrs.some((a) => blockedIp(a.address))) throw new Error('Target address not allowed');
  return fetch(u, { ...opts, redirect: 'manual' });
}
const httpUrl = (u) => { try { const x = new URL(u); return /^https?:$/.test(x.protocol) ? x : null; } catch { return null; } };

async function portal(base, mac, params, token) {
  const u = httpUrl(base); if (!u) throw new Error('Invalid portal URL');
  const root = u.href.replace(/\/(c|stalker_portal\/c)?\/?$/, '/').replace(/\/$/, '');
  const url = `${root}/server/load.php?` + new URLSearchParams({ JsHttpRequest: '1-xml', ...params });
  const headers = { Cookie: `mac=${mac}; stb_lang=en; timezone=GMT`, 'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3', 'X-User-Agent': 'Model: MAG250; Link: WiFi' };
  if (token) headers.Authorization = 'Bearer ' + token;
  const r = await safeFetch(url, { headers, signal: AbortSignal.timeout(15000) });
  const j = JSON.parse(await r.text());
  return j.js;
}

async function api(req, res, q) {
  const mac = normMac(q.get('mac') || DEFAULT_MAC);
  if (!mac || !MAC_RE.test(mac)) return send(res, 400, { error: 'Invalid MAC' });
  const base = q.get('portal');
  const act = q.get('act');
  let token = q.get('token') || '';
  if (act === 'handshake') {
    const js = await portal(base, mac, { type: 'stb', action: 'handshake', token: '' });
    token = js.token;
    await portal(base, mac, { type: 'stb', action: 'get_profile', hd: 1, stb_type: 'MAG250' }, token).catch(() => {});
    return send(res, 200, { token, mac });
  }
  if (act === 'genres') return send(res, 200, await portal(base, mac, { type: 'itv', action: 'get_genres' }, token));
  if (act === 'channels') return send(res, 200, await portal(base, mac, { type: 'itv', action: 'get_ordered_list', genre: q.get('genre') || '*', p: q.get('page') || 1 }, token));
  if (act === 'link') {
    const js = await portal(base, mac, { type: 'itv', action: 'create_link', cmd: q.get('cmd') || '' }, token);
    return send(res, 200, { url: String(js.cmd || '').replace(/^ffmpeg\s+/, '') });
  }
  if (act === 'm3u') {
    const u = httpUrl(q.get('url')); if (!u) return send(res, 400, { error: 'Invalid URL' });
    const r = await safeFetch(u.href, { signal: AbortSignal.timeout(20000) });
    return send(res, 200, await r.text(), 'text/plain');
  }
  send(res, 400, { error: 'Unknown action' });
}

// ---- Plugin / connector system: every plugins/*.js exports {id,name,description,fields,list(params,ctx),resolve?(r,ctx)}
const parental = adult.create(DATA_DIR);
const ctx = { portal, normMac, mediaDir: MEDIA_DIR, fetchText: async (url) => { const u = httpUrl(url); if (!u) throw new Error('Invalid URL'); return (await safeFetch(u.href, { signal: AbortSignal.timeout(20000) })).text(); } };
const plugins = {};
for (const f of fs.readdirSync(path.join(__dirname, 'plugins')).filter((x) => x.endsWith('.js'))) {
  try { const p = require(path.join(__dirname, 'plugins', f)); plugins[p.id] = p; } catch (e) { console.error('plugin', f, e.message); }
}
function inMedia(rel) { const f = path.resolve(MEDIA_DIR, rel); return f.startsWith(MEDIA_DIR + path.sep) ? f : null; }
async function pluginApi(u, res) {
  if (u.pathname === '/plugins') return send(res, 200, Object.values(plugins).map(({ id, name, description, fields, category }) => ({ id, name, description, fields, category })));
  const q = u.searchParams, p = plugins[q.get('id')]; if (!p) return send(res, 404, { error: 'Unknown plugin' });
  const params = JSON.parse(q.get('params') || '{}');
  if (u.pathname === '/plugin/list') {
    // Adult items are only ever returned (and only in the adult view) with a valid unlock token.
    const wantAdult = q.get('adult') === '1';
    if (wantAdult && !parental.valid(q.get('unlock'))) return send(res, 403, { error: 'Locked' });
    const all = await p.list(params, ctx);
    return send(res, 200, all.filter((i) => adult.isAdult(i) === wantAdult).map((i) => (wantAdult ? { ...i, adult: true } : i)));
  }
  if (u.pathname === '/plugin/resolve' && p.resolve) return send(res, 200, await p.resolve(params, ctx));
  send(res, 400, { error: 'Unsupported' });
}
function serveMedia(req, res, rel) {
  const f = inMedia(rel); if (!f || !fs.existsSync(f) || !fs.statSync(f).isFile()) return send(res, 404, 'Not found', 'text/plain');
  const size = fs.statSync(f).size, m = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
  const mime = { '.mp4': 'video/mp4', '.webm': 'video/webm', '.mkv': 'video/x-matroska', '.mp3': 'audio/mpeg' }[path.extname(f).toLowerCase()] || 'application/octet-stream';
  let s = 0, e = size - 1; if (m) { s = m[1] ? +m[1] : 0; e = m[2] ? Math.min(+m[2], size - 1) : size - 1; }
  if (s > e || s >= size) { res.writeHead(416, { 'Content-Range': `bytes */${size}` }); return res.end(); }
  res.writeHead(m ? 206 : 200, { 'Content-Type': mime, 'Accept-Ranges': 'bytes', 'Content-Length': e - s + 1, ...(m ? { 'Content-Range': `bytes ${s}-${e}/${size}` } : {}) });
  fs.createReadStream(f, { start: s, end: e }).pipe(res);
}
// FFmpeg transcode connector: fixed, allow-listed args (no user flags) -> fragmented MP4 (H.264/AAC) playable on most TV browsers.
function transcode(req, res, q) {
  let src = q.get('src'); const lf = q.get('file');
  if (lf) { src = inMedia(lf); if (!src) return send(res, 400, { error: 'Bad file' }); } else if (!httpUrl(src)) return send(res, 400, { error: 'Bad source' });
  const height = { 480: 480, 720: 720, 1080: 1080 }[q.get('h')] || 720;
  const args = ['-hide_banner', '-loglevel', 'error', '-i', src, '-vf', `scale=-2:${height}`, '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-movflags', 'frag_keyframe+empty_moov', '-f', 'mp4', 'pipe:1'];
  const ff = spawn('ffmpeg', args, { stdio: ['ignore', 'pipe', 'ignore'] });
  ff.on('error', () => { if (!res.headersSent) send(res, 501, { error: 'ffmpeg not installed' }); });
  res.writeHead(200, { 'Content-Type': 'video/mp4' }); ff.stdout.pipe(res);
  res.on('close', () => ff.kill('SIGKILL'));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    if (!/^application\/json/.test(req.headers['content-type'] || '')) return reject(new Error('JSON required'));
    let b = ''; req.on('data', (c) => { b += c; if (b.length > 2048) { reject(new Error('Too large')); req.destroy(); } });
    req.on('end', () => { try { resolve(JSON.parse(b || '{}')); } catch { reject(new Error('Bad JSON')); } });
  });
}
async function adultApi(req, res, u) {
  if (u.pathname === '/adult/status') return send(res, 200, { pinSet: parental.isSet() });
  if (req.method !== 'POST') return send(res, 405, { error: 'POST required' });
  let b; try { b = await readJson(req); } catch (e) { return send(res, 400, { error: e.message }); }
  try {
    if (u.pathname === '/adult/setup') return send(res, 200, { unlock: parental.setup(b.pin) });
    if (u.pathname === '/adult/unlock') return send(res, 200, { unlock: parental.unlock(b.pin) });
    if (u.pathname === '/adult/lock') { parental.lock(b.unlock); return send(res, 200, { ok: true }); }
  } catch (e) { return send(res, 403, { error: e.message }); }
  send(res, 404, { error: 'Unknown' });
}
async function epg(res, q) {
  const text = await ctx.fetchText(q.get('url'));
  send(res, 200, nowNext(parseXmltv(text)));
}
async function subtitle(res, q) {
  let text; const lf = q.get('file');
  if (lf) { const f = inMedia(lf); if (!f || !/\.(srt|vtt)$/i.test(f) || !fs.existsSync(f)) return send(res, 404, 'Not found', 'text/plain'); text = fs.readFileSync(f, 'utf8'); } else text = await ctx.fetchText(q.get('src'));
  send(res, 200, /^\uFEFF?WEBVTT/.test(text) ? text : srtToVtt(text), 'text/vtt');
}

http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  try {
    if (TOKEN) {
      const qt = u.searchParams.get('token');
      if (qt && sameTok(qt, TOKEN)) { res.setHeader('Set-Cookie', `eye3=${TOKEN}; HttpOnly; SameSite=Strict; Path=/`); req.headers.cookie = `eye3=${TOKEN}`; }
      if (!sameTok(cookieTok(req) || '', TOKEN)) return send(res, 401, 'Access token required (open /?token=...)', 'text/plain');
    }
    if (u.pathname === '/api') return await api(req, res, u.searchParams);
    if (u.pathname.startsWith('/plugin')) return await pluginApi(u, res);
    if (u.pathname.startsWith('/media/')) return serveMedia(req, res, decodeURIComponent(u.pathname.slice(7)));
    if (u.pathname.startsWith('/adult/')) return await adultApi(req, res, u);
    if (u.pathname === '/epg') return await epg(res, u.searchParams);
    if (u.pathname === '/subtitle') return await subtitle(res, u.searchParams);
    if (u.pathname === '/transcode') return transcode(req, res, u.searchParams);
    if (u.pathname === '/config') return send(res, 200, { mac: DEFAULT_MAC });
    const file = path.join(__dirname, 'public', u.pathname === '/' ? 'index.html' : path.normalize(u.pathname).replace(/^(\.\.[\/\\])+/, ''));
    if (!file.startsWith(path.join(__dirname, 'public'))) return send(res, 403, 'Forbidden', 'text/plain');
    fs.readFile(file, (e, d) => e ? send(res, 404, 'Not found', 'text/plain') : send(res, 200, d, TYPES[path.extname(file)] || 'application/octet-stream'));
  } catch (e) { send(res, 502, { error: e.message }); }
}).listen(PORT, HOST, () => console.log(`EYE3-VISION on http://${HOST}:${PORT}` + (TOKEN && !LOOPBACK ? `/?token=${TOKEN}` : '')));
