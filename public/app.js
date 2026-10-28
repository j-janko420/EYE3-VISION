const $ = (id) => document.getElementById(id);
const store = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) || d; } catch { return d; } };
const save = (k, v) => localStorage.setItem(k, JSON.stringify(v));
let plugs = [], cat = 'live', items = [], hls, dash;
const TABS = [['live', 'Live'], ['library', 'Library'], ['online', 'Online'], ['favs', 'Favourites'], ['web', 'Browser'], ['mirror', 'Mirror TV']];

// ---- tabs
TABS.forEach(([k, label]) => { const b = document.createElement('button'); b.textContent = label; b.dataset.t = k; b.onclick = () => show(k); $('nav').append(b); });
function show(k) {
  cat = k; document.querySelectorAll('#nav button').forEach((b) => b.classList.toggle('on', b.dataset.t === k));
  document.querySelectorAll('section').forEach((s) => s.classList.remove('on'));
  const id = ['live', 'library', 'online'].includes(k) ? 'src' : k; $(id).classList.add('on');
  if (id === 'src') fillPlugins(); if (k === 'favs') renderFavs();
}

// ---- playback (HLS / DASH / MP4 / transcode) with optional subtitles
function play(url, name, subtitle) {
  const v = $('player'); if (hls) { hls.destroy(); hls = null; } if (dash) { dash.reset(); dash = null; }
  v.querySelectorAll('track').forEach((t) => t.remove());
  if (/\.m3u8(\?|$)/i.test(url) && window.Hls && Hls.isSupported()) { hls = new Hls(); hls.loadSource(url); hls.attachMedia(v); }
  else if (/\.mpd(\?|$)/i.test(url) && window.dashjs) { dash = dashjs.MediaPlayer().create(); dash.initialize(v, url, true); }
  else v.src = url;
  if (subtitle) { const t = document.createElement('track'); t.kind = 'subtitles'; t.label = 'Subtitles'; t.src = subtitle; t.default = true; v.append(t); }
  $('nowplaying').textContent = name ? 'Now playing: ' + name : '';
  v.play().catch(() => {});
}

// ---- connectors
const api = async (path, params) => { const r = await fetch(path + '?' + new URLSearchParams(params)); const j = await r.json(); if (j.error) throw new Error(j.error); return j; };
fetch('/plugins').then((r) => r.json()).then((p) => { plugs = p; fillPlugins(); });
const CATMAP = { live: 'live', library: 'library', online: 'online' };
function fillPlugins() {
  const list = plugs.filter((p) => p.category === CATMAP[cat]); $('pl').innerHTML = '';
  list.forEach((p) => { const o = document.createElement('option'); o.value = p.id; o.textContent = p.name; $('pl').append(o); });
  $('epgbox').style.display = cat === 'live' ? '' : 'none'; plPick();
}
const curPlug = () => plugs.find((p) => p.id === $('pl').value);
function plPick() {
  const p = curPlug(); $('plf').textContent = ''; if (!p) return;
  p.fields.forEach((f) => { const i = document.createElement('input'); i.dataset.f = f.name; i.placeholder = f.placeholder || f.label; i.title = f.label; i.value = f.default || ''; $('plf').append(i); });
  fillProfiles();
}
$('pl').onchange = plPick;
const params = () => Object.fromEntries([...document.querySelectorAll('#plf input')].map((i) => [i.dataset.f, i.value]));

// ---- saved profiles (stored in this browser only)
function fillProfiles() {
  const ps = store('profiles', []).filter((x) => x.plugin === $('pl').value); $('prof').innerHTML = '<option value="">Saved profiles…</option>';
  ps.forEach((x, i) => { const o = document.createElement('option'); o.value = x.name; o.textContent = x.name; $('prof').append(o); });
}
$('prof').onchange = () => {
  const x = store('profiles', []).find((p) => p.plugin === $('pl').value && p.name === $('prof').value); if (!x) return;
  document.querySelectorAll('#plf input').forEach((i) => { if (x.params[i.dataset.f] != null) i.value = x.params[i.dataset.f]; });
};
$('saveprof').onclick = () => {
  const name = prompt('Profile name'); if (!name) return;
  const ps = store('profiles', []).filter((p) => !(p.plugin === $('pl').value && p.name === name));
  ps.push({ plugin: $('pl').value, name, params: params() }); save('profiles', ps); fillProfiles(); $('prof').value = name;
};
$('delprof').onclick = () => { save('profiles', store('profiles', []).filter((p) => !(p.plugin === $('pl').value && p.name === $('prof').value))); fillProfiles(); };

// ---- lists, search, favourites, EPG
const favKey = (it) => it.url || JSON.stringify(it.resolve);
const isFav = (it) => store('favs', []).some((f) => favKey(f) === favKey(it));
function toggleFav(it) {
  const fs = store('favs', []), k = favKey(it);
  save('favs', fs.some((f) => favKey(f) === k) ? fs.filter((f) => favKey(f) !== k) : fs.concat([{ ...it, plugin: it.plugin || $('pl').value }]));
}
async function start(it) {
  try {
    let url = it.url; if (!url) url = (await api('/plugin/resolve', { id: it.plugin, params: JSON.stringify(it.resolve) })).url;
    if ($('tc').checked) url = it.transcodeSrc ? '/transcode?file=' + encodeURIComponent(it.transcodeSrc) : '/transcode?src=' + encodeURIComponent(url);
    play(url, it.name, it.subtitle);
  } catch (e) { $('nowplaying').textContent = 'Error: ' + e.message; }
}
function render(box, list, epg) {
  box.textContent = '';
  list.forEach((it) => {
    const row = document.createElement('div'); row.className = 'item';
    const nm = document.createElement('div'); nm.className = 'nm'; nm.tabIndex = 0; nm.textContent = it.name; nm.onclick = () => start(it);
    nm.onkeydown = (e) => { if (e.key === 'Enter') start(it); };
    const e = epg && it.epgId && epg[it.epgId];
    if (e && (e.now || e.next)) { const s = document.createElement('small'); s.textContent = (e.now ? 'Now: ' + e.now.title : '') + (e.next ? '  Next: ' + e.next.title : ''); nm.append(s); }
    const star = document.createElement('button'); star.textContent = isFav(it) ? '★' : '☆';
    star.onclick = () => { toggleFav({ ...it, plugin: it.plugin || $('pl').value }); if (cat === 'favs') renderFavs(); else star.textContent = isFav(it) ? '★' : '☆'; };
    row.append(nm, star); box.append(row);
  });
}
let epgData = null;
const view = () => { const q = $('q').value.toLowerCase(); render($('list'), items.filter((i) => i.name.toLowerCase().includes(q)), epgData); };
$('q').oninput = view;
$('load').onclick = async () => {
  $('st').textContent = 'Loading...'; epgData = null;
  try {
    items = (await api('/plugin/list', { id: $('pl').value, params: JSON.stringify(params()) })).map((i) => ({ ...i, plugin: $('pl').value }));
    $('st').textContent = items.length + ' items'; view();
    if (cat === 'live' && $('epgurl').value) { try { epgData = await api('/epg', { url: $('epgurl').value }); view(); } catch (e) { $('st').textContent += ' (EPG failed: ' + e.message + ')'; } }
  } catch (e) { $('st').textContent = 'Error: ' + e.message; }
};
const renderFavs = () => render($('favlist'), store('favs', []));

// ---- browser + mirror
const safeUrl = (u) => /^https?:\/\//i.test(u) ? u : '';
$('wgo').onclick = () => { $('frame').src = safeUrl($('wurl').value) || 'about:blank'; };
$('wtab').onclick = () => { const u = safeUrl($('wurl').value); if (u) window.open(u, '_blank', 'noopener'); };
$('mstart').onclick = async () => { $('mv').srcObject = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true }); };
$('mstop').onclick = () => { const s = $('mv').srcObject; if (s) s.getTracks().forEach((t) => t.stop()); $('mv').srcObject = null; };

// ---- TV remote navigation: arrows move focus spatially, Enter clicks, Back returns to the tab bar
function focusables() { return [...document.querySelectorAll('button,input,select,.nm')].filter((e) => e.offsetParent && !e.disabled); }
function moveFocus(dir) {
  const cur = document.activeElement, els = focusables(); if (!els.includes(cur)) return els[0] && els[0].focus();
  const c = cur.getBoundingClientRect(), cx = c.left + c.width / 2, cy = c.top + c.height / 2; let best, bd = Infinity;
  els.forEach((e) => {
    if (e === cur) return; const r = e.getBoundingClientRect(), x = r.left + r.width / 2 - cx, y = r.top + r.height / 2 - cy;
    const ok = dir === 'ArrowRight' ? x > 1 : dir === 'ArrowLeft' ? x < -1 : dir === 'ArrowDown' ? y > 1 : y < -1; if (!ok) return;
    const d = dir === 'ArrowLeft' || dir === 'ArrowRight' ? Math.abs(x) + 3 * Math.abs(y) : Math.abs(y) + 3 * Math.abs(x);
    if (d < bd) { bd = d; best = e; }
  });
  if (best) { best.focus(); best.scrollIntoView({ block: 'nearest' }); }
}
document.addEventListener('keydown', (e) => {
  const t = e.target, typing = t.tagName === 'INPUT' && t.type === 'text' || t.tagName === 'INPUT' && !t.type;
  if (e.key.startsWith('Arrow') && !(typing && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) && t.tagName !== 'SELECT') { e.preventDefault(); moveFocus(e.key); }
  else if (['Escape', 'BrowserBack', 'XF86Back'].includes(e.key) || e.keyCode === 10009 || (e.key === 'Backspace' && !typing)) { const b = document.querySelector('#nav button.on'); if (b) b.focus(); }
  else if (e.key === 'Enter' && t.classList.contains('nm')) t.click();
});
show('live'); document.querySelector('#nav button').focus();
