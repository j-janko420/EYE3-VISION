// End-to-end tests of EYE3 Home in headless Chromium. Needs: the static server (8099), the mock Xtream/XMLTV server (9191),
// the mock ntfy relay (9292) and EYE3 Link (8765). tests/run.sh starts them all.
const fs = require('fs');
const { chromium, check, suite, done, open, sleep, HOME } = require('../harness');
const H = (q) => HOME + (q || '');
const ONLINE = !!process.env.EYE3_ONLINE;
const MPEGTS_STUB = "window.__tsCalls=[];window.mpegts={isSupported:()=>true,Events:{ERROR:'error'},createPlayer:(cfg)=>{window.__tsCalls.push(cfg.url);return{on:()=>{},attachMediaElement:()=>{},load:()=>{},play:()=>Promise.resolve(),unload:()=>{},detachMediaElement:()=>{},destroy:()=>{}};}};";
const XT = { id: 'a1', name: 'Mock TV', type: 'xtream', server: 'http://127.0.0.1:9191', user: 'u', pass: 'p' };
const ch = (n, u, i) => ({ n, u, g: '', l: '', i: i || '' });
const rows = (p, sel) => p.evaluate((s) => [...document.querySelectorAll(s || '#chlist .ch:not(.action)')].map((r) => r.textContent), sel);
const openTv = async (p) => { await p.evaluate(() => document.querySelector('.tile').click()); await p.waitForTimeout(1500); };
const pickCat = async (p, prefix) => { await p.selectOption('#tv-cat', { label: await p.evaluate((x) => [...document.querySelectorAll('#tv-cat option')].map((o) => o.textContent).find((t) => t.startsWith(x)), prefix) }); await p.waitForTimeout(400); };
const toast = (p) => p.evaluate(() => [...document.querySelectorAll('.toast')].map((t) => t.textContent).pop());

(async () => {
  const browser = await chromium.launch();

  await suite('theme and layout (red and black, every screen size)', async () => {
    const p = await open(browser);
    const t = await p.evaluate(() => { const c = getComputedStyle(document.documentElement); return { bg: c.getPropertyValue('--bg').trim(), accent: c.getPropertyValue('--accent').trim(), ink: c.getPropertyValue('--ink').trim() }; });
    check('colour tokens are the EYE3 red and black', t.bg === '#050101' && t.accent === '#ff263f' && t.ink === '#fff5f6', t);
    check('page background is near black', await p.evaluate(() => getComputedStyle(document.body).backgroundColor) === 'rgb(5, 1, 1)');
    check('the splash/logo animation exists', await p.evaluate(() => [...document.styleSheets[0].cssRules].some((r) => r.name === 'ignite' || r.name === 'tileIn')));
    check('motion is disabled for "reduce motion"', await p.evaluate(() => [...document.styleSheets[0].cssRules].some((r) => r.media && /prefers-reduced-motion/.test(r.media.mediaText))));
    for (const [name, size] of [['phone', { width: 390, height: 844 }], ['tablet', { width: 820, height: 1180 }], ['laptop', { width: 1366, height: 768 }], ['tv', { width: 1920, height: 1080 }]]) {
      const q = await open(browser, {}, { ctx: { viewport: size } });
      await q.evaluate(() => document.querySelector('.tile').click()); await q.waitForTimeout(900);
      const m = await q.evaluate(() => { const ov = document.getElementById('ov-tv'), sc = document.getElementById('screen'), ls = document.getElementById('chlist'); return { open: ov.classList.contains('open'), wOver: ov.scrollWidth - ov.clientWidth, screenTop: sc.getBoundingClientRect().top, listTop: ls.getBoundingClientRect().top, screenW: sc.getBoundingClientRect().width, vw: innerWidth }; });
      check(name + ': Live TV opens without sideways scrolling', m.open && m.wOver <= 1, m);
      if (name === 'phone' || name === 'tablet') check(name + ': the player is on top of the list', m.screenTop < m.listTop && m.screenW > m.vw * 0.8, m);
      else check(name + ': list and player sit side by side', Math.abs(m.screenTop - m.listTop) < 40 || m.screenTop < m.listTop + 40, m);
      await q.close();
    }
    await p.close();
  });

  await suite('the colours stay red and black on every page (no blue left over)', async () => {
    const files = ['index.html', 'home/index.html', 'home/setup.html', 'home/send-files.html', 'remote/index.html', 'portal/c/index.html', 'portal/check/index.html', 'bridge/index.html'];
    const hsl = (r, g, b) => { r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn; if (!d) return [0, 0, l]; const s = d / (1 - Math.abs(2 * l - 1)); let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h = (h * 60 + 360) % 360; return [h, s, l]; };
    for (const f of files) {
      const text = fs.readFileSync(require('path').join(__dirname, '..', '..', f), 'utf8');
      const bad = [];
      (text.match(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g) || []).forEach((h) => { let x = h.slice(1); if (x.length === 3) x = x.split('').map((c) => c + c).join(''); const [H, S, L] = hsl(parseInt(x.slice(0, 2), 16), parseInt(x.slice(2, 4), 16), parseInt(x.slice(4, 6), 16)); if (S > 0.25 && H >= 190 && H <= 270 && L > 0.05 && L < 0.95) bad.push(h); });
      (text.match(/rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+/g) || []).forEach((m) => { const n = m.match(/\d+/g).map(Number); const [H, S, L] = hsl(n[0], n[1], n[2]); if (S > 0.25 && H >= 190 && H <= 270 && L > 0.05 && L < 0.95) bad.push(m); });
      check(f + ' has no blue colours', bad.length === 0, bad);
    }
  });

  await suite('Live TV: search, previous channel, picture and track keys', async () => {
    const p = await open(browser, { 'eye3.home.mychannels': [ch('Café Évasion', 'https://x.example/cafe.m3u8'), ch('News - CNN Español', 'https://x.example/cnn.m3u8'), ch('Sport Alpha', 'https://x.example/sa.m3u8')] });
    await openTv(p);
    check('the free catalogue loads (thousands of channels)', parseInt(await p.textContent('#tv-count'), 10) > 1000, await p.textContent('#tv-count'));
    await p.fill('#tv-search', 'cafe evasion'); await p.waitForTimeout(300);
    check('search ignores accents and case', (await rows(p)).some((r) => /Café Évasion/.test(r)));
    await p.fill('#tv-search', 'espanol cnn'); await p.waitForTimeout(300);
    check('search ignores word order', (await rows(p)).some((r) => /News - CNN Español/.test(r)));
    await p.fill('#tv-search', ''); await p.waitForTimeout(200);
    await pickCat(p, 'My channels');
    await p.click('#chlist .ch >> text=Sport Alpha'); await p.waitForTimeout(400);
    await p.click('#chlist .ch >> text=Café'); await p.waitForTimeout(400);
    await p.keyboard.press('p'); await p.waitForTimeout(400);
    check('P goes back to the previous channel', /Sport Alpha/.test(await p.textContent('#chlabel')), await p.textContent('#chlabel'));
    await p.keyboard.press('x');
    check('X changes the picture shape', await p.evaluate(() => document.getElementById('video').style.objectFit) === 'cover');
    await p.keyboard.press('a'); check('A says when there is one audio track', /one audio track/.test(await toast(p)), await toast(p));
    await p.keyboard.press('t'); check('T says when there are no subtitles', /No subtitles/.test(await toast(p)), await toast(p));
    await p.keyboard.press('l'); await p.waitForTimeout(200);
    check('L adds a favourite', JSON.parse(await p.evaluate(() => localStorage.getItem('eye3.home.favs'))).length === 1);
    check('no page errors', p.errs.length === 0, p.errs);
    await p.close();
  });

  await suite('Xtream account: guide, recently watched, TS fallback, next episode', async () => {
    const p = await open(browser, { 'eye3.home.accts': [XT] });
    await p.route('https://cdn.jsdelivr.net/npm/mpegts.js**', (r) => r.fulfill({ status: 200, contentType: 'application/javascript', body: MPEGTS_STUB }));
    await openTv(p); await pickCat(p, 'Mock TV');
    await p.click('#chlist .ch >> text=Xtream One');
    await p.waitForFunction(() => (window.__tsCalls || []).length > 0, null, { timeout: 25000 }).catch(() => {});   // real hls.js retries before giving up
    check('HLS fails, the TS player is tried with the Link address', (await p.evaluate(() => window.__tsCalls || [])).some((u) => /127\.0\.0\.1:8765\/stream\?/.test(u) && /11\.ts/.test(decodeURIComponent(u))), await p.evaluate(() => ({ calls: window.__tsCalls, label: document.getElementById('chlabel').textContent, hls: !!window.Hls, mpegts: !!window.mpegts, vsrc: document.getElementById('video').src.slice(0, 90), err: document.getElementById('video').error && document.getElementById('video').error.code })));
    await p.click('#chlist .ch >> text=Xtream Two'); await p.waitForTimeout(600);
    check('recently watched appears and lists newest first', JSON.parse(await p.evaluate(() => localStorage.getItem('eye3.home.recent')))[0] === 'Mock TV|Xtream Two');
    check('the category "Recently watched" exists at once', (await p.evaluate(() => [...document.querySelectorAll('#tv-cat option')].map((o) => o.textContent))).some((t) => /Recently watched/.test(t)));
    // the guide label (now/next) is set before the failed stream message replaces it: check the source instead
    const guide = await p.evaluate(async () => { const r = await fetch('http://127.0.0.1:8765/api/epg?server=http%3A%2F%2F127.0.0.1%3A9191&user=u&pass=p&id=11&n=4'); return r.json(); });
    check('EYE3 Link returns the programme list', guide.items && guide.items.length === 2 && guide.items[0].t === 'Evening News', guide);
    // series: next episode countdown
    await p.keyboard.press('Escape'); await p.waitForTimeout(200);
    await p.evaluate(() => document.querySelector('.tile').click()); await p.waitForTimeout(400);
    await p.evaluate(() => document.getElementById('tv-vod').click()); await p.waitForTimeout(500);
    await p.click('#vod-series'); await p.waitForTimeout(1500);
    await p.click('#vod-list .ch >> text=Long Show'); await p.waitForTimeout(1200);
    await p.click('#vod-list .ch >> text=Pilot'); await p.waitForTimeout(1200);
    await p.clock.install();
    await p.evaluate(() => document.getElementById('vod-video').dispatchEvent(new Event('ended')));
    check('a countdown to the next episode starts', /Next: .*Second in 6 s/.test(await p.textContent('#vod-label')), await p.textContent('#vod-label'));
    await p.clock.runFor(7500); await p.waitForTimeout(1200);
    check('the next episode starts by itself', /412\.mp4/.test(decodeURIComponent(await p.evaluate(() => document.getElementById('vod-video').src))));
    check('"Open in VLC" is offered', !(await p.evaluate(() => document.getElementById('vod-vlc').hidden)));
    check('no page errors', p.errs.length === 0, p.errs);
    await p.close();
  });

  await suite('guide from an XMLTV link, quick search, shortcuts, VLC file, continue watching', async () => {
    const p = await open(browser, { 'eye3.home.mychannels': [ch('Café Évasion', 'https://x.example/cafe.m3u8'), ch('News One', 'https://x.example/news.m3u8', 'news.one')], 'eye3.home.xmltv': 'http://127.0.0.1:9191/epg/guide.xml' });
    await p.keyboard.press('Control+k'); await p.waitForTimeout(250);
    check('Ctrl+K opens quick search with actions', await p.evaluate(() => document.getElementById('ov-pal').classList.contains('open')) && (await rows(p, '#pal-res .row')).length >= 5);
    await p.keyboard.type('cafe'); await p.waitForTimeout(400);
    const hits = await rows(p, '#pal-res .row');
    check('your own channels come first in quick search', /Café Évasion/.test(hits[0]), hits);
    await p.keyboard.press('Enter'); await p.waitForTimeout(1500);
    check('Enter opens that channel in Live TV', await p.evaluate(() => document.getElementById('ov-tv').classList.contains('open')) && /Café Évasion/.test(await p.textContent('#chlabel')));
    await p.keyboard.press('Control+k'); await p.waitForTimeout(200); await p.keyboard.press('Escape'); await p.waitForTimeout(200);
    check('Esc closes only the quick search', await p.evaluate(() => document.getElementById('ov-tv').classList.contains('open') && !document.getElementById('ov-pal').classList.contains('open')));
    await p.keyboard.press('Control+k'); await p.waitForTimeout(250); await p.keyboard.type('news one'); await p.waitForTimeout(400); await p.keyboard.press('Enter'); await p.waitForTimeout(2200);
    await p.locator('body').click({ position: { x: 5, y: 5 } }); await p.keyboard.press('g'); await p.waitForTimeout(1500);
    const g = (await p.textContent('#info-body')).replace(/\s+/g, ' ');
    check('G shows the programme list from the XMLTV link', /Evening Bulletin/.test(g) && /Late Talk/.test(g) && /All the news/.test(g), g);
    await p.keyboard.press('Escape'); await p.waitForTimeout(200);
    await openTv(p);
    const [dl] = await Promise.all([p.waitForEvent('download'), p.keyboard.press('v')]);
    const txt = fs.readFileSync(await dl.path(), 'utf8');
    check('V saves a playlist file for VLC', /\.m3u$/.test(dl.suggestedFilename()) && /^#EXTM3U\n#EXTINF:-1,.+\nhttps?:\/\//.test(txt), txt);
    await p.keyboard.press('Escape'); await p.waitForTimeout(150); await p.keyboard.press('?'); await p.waitForTimeout(300);
    check('? lists the keyboard shortcuts', await p.textContent('#info-title') === 'Keyboard shortcuts' && (await p.evaluate(() => document.querySelectorAll('#info-body kbd').length)) > 15);
    await p.keyboard.press('Escape'); await p.waitForTimeout(150);
    await p.goto(H(), { waitUntil: 'domcontentloaded' }); await p.waitForTimeout(900);
    const strip = await p.evaluate(() => [document.getElementById('strip').hidden, ...[...document.querySelectorAll('#strip .pill')].map((x) => x.textContent)]);
    check('the home screen shows "continue watching"', strip[0] === false && strip.length >= 3, strip);
    await p.click('#strip .pill >> text=News One'); await p.waitForTimeout(2500);
    check('a continue-watching pill plays that channel', /News One/.test(await p.textContent('#chlabel')));
    check('no page errors', p.errs.length === 0, p.errs);
    await p.close();
  });

  await suite('Playlist maker: files, paste, big playlists, PDF, adult content stays hidden', async () => {
    const p = await open(browser, {}, { url: H('&add=playlist') });
    fs.writeFileSync('/tmp/eye3_t1.m3u', '#EXTM3U\n#EXTINF:-1 group-title="News",Phone News\nhttps://example.com/a.m3u8\n#EXTINF:-1,Second\nhttps://example.com/b.m3u8\n');
    fs.writeFileSync('/tmp/eye3_t2.txt', 'hello, not a playlist');
    check('the file picker has no type filter (iPhone)', (await p.getAttribute('#mk-import', 'accept')) === null);
    await p.setInputFiles('#mk-import', '/tmp/eye3_t1.m3u'); await p.waitForTimeout(400);
    check('an .m3u file imports', /Imported 2 channels/.test(await p.textContent('#mk-msg')));
    await p.setInputFiles('#mk-import', '/tmp/eye3_t2.txt'); await p.waitForTimeout(300);
    check('a non-playlist gets a clear message', /does not look like an M3U/.test(await p.textContent('#mk-msg')));
    await p.fill('#mk-paste', 'Name A - https://q.example/a.m3u8\nhttps://q.example/b.m3u8'); await p.click('#mk-paste-go'); await p.waitForTimeout(300);
    check('pasted links become channels', /Imported 2 channels/.test(await p.textContent('#mk-msg')));
    // big playlist (a few MB) goes to the library
    const lines = ['#EXTM3U']; for (let i = 0; i < 60000; i++) lines.push('#EXTINF:-1 tvg-id="i' + i + '" group-title="G' + (i % 50) + '",Channel number ' + i + '\nhttp://stream.example.com/live/u/p/' + i + '.ts');
    fs.writeFileSync('/tmp/eye3_big.m3u', lines.join('\n'));
    await p.setInputFiles('#mk-import', '/tmp/eye3_big.m3u');
    await p.waitForFunction(() => /Saved “eye3_big”|No new|Imported/.test(document.getElementById('mk-msg').textContent) && !/Imported 2 channels/.test(document.getElementById('mk-msg').textContent), null, { timeout: 90000 });
    check('a big playlist is kept as its own playlist', /Saved “eye3_big” as a big playlist \(60000 channels\)/.test(await p.textContent('#mk-msg')), await p.textContent('#mk-msg'));
    await p.reload({ waitUntil: 'domcontentloaded' }); await p.waitForTimeout(2500);
    await p.evaluate(() => document.querySelector('.tile').click()); await p.waitForTimeout(1500);
    const cats = await p.evaluate(() => [...document.querySelectorAll('#tv-cat option')].map((o) => o.textContent));
    check('the big playlist is still there after a reload, with its channels', cats.some((t) => /^eye3_big \(60000\)/.test(t)), cats.slice(0, 6));
    await p.evaluate(() => document.getElementById('tv-maker').click()); await p.waitForTimeout(400);
    await p.click('#mk-libs button >> text=Remove'); await p.waitForTimeout(1500);
    check('a big playlist can be removed', /No big playlists yet/.test(await p.textContent('#mk-libs')));
    // adult content: stored, hidden, shown only after unlocking
    fs.writeFileSync('/tmp/eye3_adult.m3u', '#EXTM3U\n#EXTINF:-1 group-title="XXX",Adult Test One\nhttps://example.com/x1.m3u8\n#EXTINF:-1 group-title="XXX",Adult Test Two\nhttps://example.com/x2.m3u8\n');
    await p.keyboard.press('Escape'); await p.goto(H('&add=playlist'), { waitUntil: 'domcontentloaded' }); await p.waitForTimeout(700);
    await p.setInputFiles('#mk-import', '/tmp/eye3_adult.m3u'); await p.waitForTimeout(400);
    check('adult entries are not counted or listed while locked', /No new playable channels/.test(await p.textContent('#mk-msg')) && (await p.evaluate(() => document.querySelectorAll('#mk-list .acct-row').length)) <= 4);
    await p.keyboard.press('Escape'); await p.waitForTimeout(150);
    await p.keyboard.press('Shift+X'); await p.waitForTimeout(300); await p.check('#ex-age'); await p.click('#ex-unlock'); await p.waitForTimeout(400);
    await p.evaluate(() => document.querySelector('.tile').click()); await p.waitForTimeout(1200);
    check('after the hidden unlock they appear only under the Explicit category', (await p.evaluate(() => [...document.querySelectorAll('#tv-cat option')].map((o) => o.textContent))).some((t) => /Explicit \(18\+\) \(2\)/.test(t)));
    check('no page errors', p.errs.length === 0, p.errs);
    await p.close();
    if (ONLINE) {
      const q = await open(browser, {}, { url: H('&add=playlist') });
      const pg = await browser.newPage(); await pg.setContent('<pre>#EXTM3U\n#EXTINF:-1 group-title="News",PDF News One\nhttps://example.com/one.m3u8\n</pre>'); await pg.pdf({ path: '/tmp/eye3_t.pdf' }); await pg.close();
      await q.setInputFiles('#mk-import', '/tmp/eye3_t.pdf'); await q.waitForTimeout(9000);
      check('a PDF playlist is read (real pdf.js from the CDN)', /Imported 1 channel/.test(await q.textContent('#mk-msg')), await q.textContent('#mk-msg'));
      await q.close();
    }
  });

  await suite('Free movies, resume, support report', async () => {
    const p = await open(browser, { 'eye3.home.accts': [Object.assign({}, XT, { user: 'USER123456', pass: 'PASSWORD987' })] });
    await p.route('https://archive.org/**', (r) => { const u = r.request().url(), h = { 'access-control-allow-origin': '*' };
      if (u.includes('advancedsearch')) return r.fulfill({ status: 200, contentType: 'application/json', headers: h, body: JSON.stringify({ response: { numFound: 2, docs: [{ identifier: 'big_film', title: 'Big Film', year: 1950 }, { identifier: 'bad', title: 'XXX Night' }] } }) });
      if (u.includes('/metadata/')) return r.fulfill({ status: 200, contentType: 'application/json', headers: h, body: JSON.stringify({ files: [{ name: 'x.ogv', format: 'Ogg Video', size: '5' }, { name: 'big_film.mp4', format: 'h.264', size: '100' }, { name: 'big_film_trailer.mp4', format: 'h.264', size: '9' }] }) });
      return r.fulfill({ status: 200, contentType: 'video/mp4', body: '0' }); });
    await p.evaluate(() => document.querySelector('.tile').click()); await p.waitForTimeout(400);
    await p.evaluate(() => document.getElementById('tv-vod').click()); await p.waitForTimeout(400);
    await p.click('#vod-free'); await p.waitForTimeout(900);
    const films = await rows(p, '#vod-list .ch:not(.action)');
    check('free movies list the films and drop adult titles', films.length === 1 && /Big Film/.test(films[0]), films);
    await p.evaluate(() => { const v = document.getElementById('vod-video'); let t = 0; Object.defineProperty(v, 'duration', { get: () => 3600, configurable: true }); Object.defineProperty(v, 'currentTime', { get: () => t, set: (x) => { t = x; }, configurable: true }); window.__v = v; });
    await p.click('#vod-list .ch >> text=Big Film'); await p.waitForTimeout(600);
    check('the h.264 file is chosen (not the trailer)', /big_film\.mp4$/.test(await p.evaluate(() => window.__v.src)));
    await p.evaluate(() => { window.__v.currentTime = 1200; window.__v.dispatchEvent(new Event('timeupdate')); });
    check('the position is saved', JSON.parse(await p.evaluate(() => localStorage.getItem('eye3.home.resume')))['free|big_film'].p === 1200);
    await p.evaluate(() => { window.__v.currentTime = 0; }); await p.click('#vod-list .ch >> text=Big Film'); await p.waitForTimeout(500);
    await p.evaluate(() => { window.__v.dispatchEvent(new Event('loadedmetadata')); window.__v.dispatchEvent(new Event('playing')); });
    check('it resumes where it stopped', await p.evaluate(() => window.__v.currentTime) === 1200);
    // support report
    await p.keyboard.press('Escape'); await p.waitForTimeout(150);
    await p.goto(H(), { waitUntil: 'domcontentloaded' }); await p.waitForTimeout(900);
    await p.evaluate(() => document.querySelector('.tile:last-child').click()); await p.waitForTimeout(300);
    await p.click('button >> text=Help, VPN & useful tools'); await p.waitForTimeout(300);
    await p.click('button >> text=Copy support report'); await p.waitForTimeout(300);
    const rep = await p.inputValue('#info-body textarea');
    check('the support report is there and has no logins or passwords', /EYE3 support report/.test(rep) && !/USER123456|PASSWORD987/.test(rep), rep.slice(0, 300));
    const g = await p.context().newPage(); await g.goto(HOME.replace('index.html', '').replace(/\?.*/, '') + 'send-files.html');
    check('the "send a big file" guide page exists', (await g.title()) === 'Send a big file');
    check('no page errors', p.errs.length === 0, p.errs);
    await p.close();
  });

  await suite('phone and laptop sync (encrypted, via the mock relay)', async () => {
    const url = H('&signal=http://127.0.0.1:9292');
    const L = await open(browser, { 'eye3.home.mychannels': [ch('Laptop One', 'https://l.example/1.m3u8'), ch('Shared', 'https://s.example/x.m3u8'), ch('Laptop Two', 'https://l.example/2.m3u8')], 'eye3.home.favs': ['https://l.example/1.m3u8'], 'eye3.home.accts': [Object.assign({}, XT, { user: 'SECRETUSER', pass: 'SECRETPASS' })] }, { url });
    const P = await open(browser, { 'eye3.home.mychannels': [ch('Phone One', 'https://p.example/1.m3u8'), ch('Shared', 'https://s.example/x.m3u8')], 'eye3.home.favs': ['https://p.example/1.m3u8'] }, { url });
    const mine = (pg) => pg.evaluate(() => JSON.parse(localStorage.getItem('eye3.home.mychannels') || '[]').map((c) => c.n).sort());
    const openSync = async (pg) => { await pg.click('.tile >> text=Settings'); await pg.waitForTimeout(300); await pg.click('button >> text=Sync phone and laptop'); await pg.waitForTimeout(200); };
    await openSync(L); await L.click('button >> text=Create a new code'); await L.waitForTimeout(1500);
    const code = await L.evaluate(() => localStorage.getItem('eye3.home.sync'));
    await openSync(P); await P.fill('#info-body input', code); await P.click('button >> text=Start syncing with this code'); await P.waitForTimeout(8000);
    const both = ['Laptop One', 'Laptop Two', 'Phone One', 'Shared'];
    check('pairing merges both lists on both devices', JSON.stringify(await mine(L)) === JSON.stringify(both) && JSON.stringify(await mine(P)) === JSON.stringify(both), [await mine(L), await mine(P)]);
    await P.keyboard.press('Escape'); await P.waitForTimeout(150);
    fs.writeFileSync('/tmp/eye3_sync.m3u', '#EXTM3U\n#EXTINF:-1,Imported On Phone\nhttps://p.example/new.m3u8\n');
    await P.goto(H('&add=playlist&signal=http://127.0.0.1:9292'), { waitUntil: 'domcontentloaded' }); await P.waitForTimeout(900);
    await P.setInputFiles('#mk-import', '/tmp/eye3_sync.m3u'); await P.waitForTimeout(6000);
    check('a channel added on the phone appears on the laptop', (await mine(L)).includes('Imported On Phone'), await mine(L));
    await P.evaluate(() => { const r = [...document.querySelectorAll('#mk-list .acct-row')].find((x) => x.textContent.includes('Laptop Two')); r && [...r.querySelectorAll('button')].pop().click(); }); await P.waitForTimeout(6000);
    check('a channel removed on the phone disappears on the laptop', !(await mine(L)).includes('Laptop Two'), await mine(L));
    const dump = JSON.stringify(await (await fetch('http://127.0.0.1:9292/_dump')).json());
    check('the relay saw only ciphertext (no names, links or logins)', !['Laptop One', 'Imported On Phone', 'SECRET', 'example'].some((w) => dump.includes(w)));
    check('no page errors', L.errs.length + P.errs.length === 0, [L.errs, P.errs]);
    await L.close(); await P.close();
  });

  await suite('phone remote controls Home through the relay', async () => {
    const L = await open(browser, { 'eye3.home.rc': 'KBB98EMJ' }, { url: H('&signal=http://127.0.0.1:9292') });
    await L.waitForTimeout(800);
    const P = await open(browser, {}, { url: HOME.replace(/home\/.*/, 'remote/') + '?signal=http://127.0.0.1:9292#c=KBB98EMJ', ctx: { viewport: { width: 390, height: 844 } } });
    check('the remote shows it is connected', /Connected/.test(await P.evaluate(() => document.body.innerText)));
    const before = await L.evaluate(() => document.querySelector('.tile.on').textContent);
    await P.click('button:text-is("▶")'); await P.waitForTimeout(2000);
    check('pressing right moves the focus on the laptop', (await L.evaluate(() => document.querySelector('.tile.on').textContent)) !== before);
    await L.close(); await P.close();
  });

  await suite('home on an https page: http streams go through EYE3 Link', async () => {
    if (!process.env.EYE3_HTTPS) { console.log('  skip (no https test server)'); return; }
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true }); const p = await ctx.newPage(); const sent = [];
    p.on('request', (r) => { if (r.url().startsWith('http://127.0.0.1:8765/stream')) sent.push(r.url()); });
    await p.addInitScript(() => { if (!localStorage.getItem('s')) { localStorage.setItem('s', '1'); localStorage.setItem('eye3.home.mychannels', JSON.stringify([{ n: 'Plain Http Channel', u: 'http://example.test/live/a.m3u8', g: '', l: '', i: '' }])); } });
    await p.goto('https://localhost:8443/home/?splash=0', { waitUntil: 'domcontentloaded' }); await p.waitForTimeout(800);
    await openTv(p); await pickCat(p, 'My channels');
    await p.click('#chlist .ch >> text=Plain Http Channel'); await p.waitForTimeout(2000);
    check('the stream is fetched through EYE3 Link with its token', sent.length >= 1 && sent.every((u) => /[?&]t=/.test(u) && /u=http%3A%2F%2Fexample\.test/.test(u)), sent);
    await ctx.close();
  });

  await browser.close();
  done();
})().catch((e) => { console.error(e); process.exit(1); });
