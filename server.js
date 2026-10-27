// EYE3-VISION: zero-dependency server. Serves the UI and proxies Stalker/MAG portal + M3U requests (avoids CORS).
const http = require('http'), fs = require('fs'), path = require('path');
const PORT = process.env.PORT || 8080, HOST = process.env.HOST || '127.0.0.1';
const DEFAULT_MAC = '00:1A:79:EC:5F:08'; // virtual MAC (normalised from 00:1A:79:EC5F:08)
const MAC_RE = /^([0-9A-F]{2}:){5}[0-9A-F]{2}$/;
const normMac = (m) => { const h = String(m || '').replace(/[^0-9a-f]/gi, '').toUpperCase(); return h.length === 12 ? h.match(/../g).join(':') : null; };
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
const send = (res, code, body, type = 'application/json') => { res.writeHead(code, { 'Content-Type': type }); res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body)); };
const httpUrl = (u) => { try { const x = new URL(u); return /^https?:$/.test(x.protocol) ? x : null; } catch { return null; } };

async function portal(base, mac, params, token) {
  const u = httpUrl(base); if (!u) throw new Error('Invalid portal URL');
  const root = u.href.replace(/\/(c|stalker_portal\/c)?\/?$/, '/').replace(/\/$/, '');
  const url = `${root}/server/load.php?` + new URLSearchParams({ JsHttpRequest: '1-xml', ...params });
  const headers = { Cookie: `mac=${mac}; stb_lang=en; timezone=GMT`, 'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3', 'X-User-Agent': 'Model: MAG250; Link: WiFi' };
  if (token) headers.Authorization = 'Bearer ' + token;
  const r = await fetch(url, { headers, signal: AbortSignal.timeout(15000) });
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
    const r = await fetch(u, { signal: AbortSignal.timeout(20000) });
    return send(res, 200, await r.text(), 'text/plain');
  }
  send(res, 400, { error: 'Unknown action' });
}

http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  try {
    if (u.pathname === '/api') return await api(req, res, u.searchParams);
    if (u.pathname === '/config') return send(res, 200, { mac: DEFAULT_MAC });
    const file = path.join(__dirname, 'public', u.pathname === '/' ? 'index.html' : path.normalize(u.pathname).replace(/^(\.\.[\/\\])+/, ''));
    if (!file.startsWith(path.join(__dirname, 'public'))) return send(res, 403, 'Forbidden', 'text/plain');
    fs.readFile(file, (e, d) => e ? send(res, 404, 'Not found', 'text/plain') : send(res, 200, d, TYPES[path.extname(file)] || 'application/octet-stream'));
  } catch (e) { send(res, 502, { error: e.message }); }
}).listen(PORT, HOST, () => console.log(`EYE3-VISION on http://${HOST}:${PORT}`));
