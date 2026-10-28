const $ = (id) => document.getElementById(id);
let token = '', hls;
document.querySelectorAll('#nav button').forEach((b) => b.onclick = () => {
  document.querySelectorAll('#nav button,section').forEach((e) => e.classList.remove('on'));
  b.classList.add('on'); $(b.dataset.t).classList.add('on');
});
fetch('/config').then((r) => r.json()).then((c) => { $('mac').value = localStorage.mac || c.mac; $('portal').value = localStorage.portal || ''; });
const api = async (p) => { const r = await fetch('/api?' + new URLSearchParams({ portal: $('portal').value, mac: $('mac').value, token, ...p })); const j = await r.json(); if (j.error) throw new Error(j.error); return j; };
function play(url) {
  const v = $('player'); if (hls) hls.destroy();
  if (/\.m3u8/.test(url) && window.Hls && Hls.isSupported()) { hls = new Hls(); hls.loadSource(url); hls.attachMedia(v); } else v.src = url;
  v.play().catch(() => {});
}
async function connect() {
  try {
    $('status').textContent = 'Connecting...';
    localStorage.mac = $('mac').value; localStorage.portal = $('portal').value;
    token = (await api({ act: 'handshake' })).token;
    const g = await api({ act: 'genres' });
    $('genre').innerHTML = '<option value="*">All</option>' + g.map((x) => `<option value="${x.id}">${esc(x.title)}</option>`).join('');
    $('status').textContent = 'Connected as ' + $('mac').value; chans();
  } catch (e) { $('status').textContent = 'Error: ' + e.message; }
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
async function chans() {
  const d = await api({ act: 'channels', genre: $('genre').value });
  const l = $('list'); l.textContent = '';
  (d.data || []).forEach((c) => { const e = document.createElement('div'); e.textContent = c.name; e.onclick = async () => play((await api({ act: 'link', cmd: c.cmd })).url); l.append(e); });
}
async function loadM3U() {
  const t = await (await fetch('/api?' + new URLSearchParams({ act: 'm3u', url: $('m3u').value }))).text();
  const l = $('list'); l.textContent = ''; let name = '';
  t.split(/\r?\n/).forEach((ln) => {
    if (ln.startsWith('#EXTINF')) name = ln.split(',').pop();
    else if (/^https?:/.test(ln)) { const u = ln, e = document.createElement('div'); e.textContent = name || u; e.onclick = () => play(u); l.append(e); name = ''; }
  });
}
async function mirror() { $('mv').srcObject = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true }); }
function stopMirror() { const s = $('mv').srcObject; s && s.getTracks().forEach((t) => t.stop()); $('mv').srcObject = null; }

let plugs = [];
fetch('/plugins').then((r) => r.json()).then((p) => { plugs = p; $('pl').innerHTML = p.map((x) => `<option value="${x.id}">${esc(x.name)}</option>`).join(''); plPick(); });
function plPick() {
  const p = plugs.find((x) => x.id === $('pl').value); if (!p) return;
  $('plf').innerHTML = p.fields.map((f) => `<input data-f="${f.name}" placeholder="${esc(f.placeholder || f.label)}" title="${esc(f.label)}" value="${esc(f.default || '')}">`).join('');
}
const plParams = () => Object.fromEntries([...document.querySelectorAll('#plf input')].map((i) => [i.dataset.f, i.value]));
const plq = (path, extra) => fetch(path + '?' + new URLSearchParams({ id: $('pl').value, params: JSON.stringify(extra || plParams()) })).then(async (r) => { const j = await r.json(); if (j.error) throw new Error(j.error); return j; });
async function plList() {
  const l = $('pllist'); l.textContent = ''; $('plst').textContent = 'Loading...';
  try {
    const items = await plq('/plugin/list'); $('plst').textContent = items.length + ' items';
    items.forEach((it) => {
      const e = document.createElement('div'); e.textContent = it.name;
      e.onclick = async () => {
        let url = it.url || (await plq('/plugin/resolve', it.resolve)).url;
        if ($('tc').checked) url = it.transcodeSrc ? '/transcode?file=' + encodeURIComponent(it.transcodeSrc) : '/transcode?src=' + encodeURIComponent(url);
        play(url);
      };
      l.append(e);
    });
  } catch (e) { $('plst').textContent = 'Error: ' + e.message; }
}
