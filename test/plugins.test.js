const test = require('node:test'), assert = require('node:assert'), fs = require('fs'), os = require('os'), path = require('path');
const m3u = require('../plugins/m3u'), local = require('../plugins/local'), url = require('../plugins/url'), stalker = require('../plugins/stalker');

test('every plugin has required shape', () => {
  for (const f of fs.readdirSync(path.join(__dirname, '../plugins'))) {
    const p = require('../plugins/' + f);
    assert.ok(p.id && p.name && Array.isArray(p.fields) && typeof p.list === 'function', f);
  }
});
test('m3u parses names and urls', async () => {
  const ctx = { fetchText: async () => '#EXTM3U\n#EXTINF:-1,One\nhttp://a/1.m3u8\n#EXTINF:-1 tvg-id="x",Two\nhttps://b/2.ts\n' };
  assert.deepStrictEqual(await m3u.list({ url: 'x' }, ctx), [{ name: 'One', url: 'http://a/1.m3u8' }, { name: 'Two', url: 'https://b/2.ts', epgId: "x" }]);
});
test('url connector filters non-http and supports Name|URL', async () => {
  const r = await url.list({ urls: 'A|http://x/a.m3u8\nfile:///etc/passwd\nhttps://y/b.mp4' });
  assert.deepStrictEqual(r.map((x) => x.name), ['A', 'https://y/b.mp4']);
});
test('local lists media files recursively with filter', async () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'm-')); fs.mkdirSync(d + '/sub'); fs.writeFileSync(d + '/sub/Movie.mp4', ''); fs.writeFileSync(d + '/n.txt', '');
  const r = await local.list({ filter: 'movie' }, { mediaDir: d });
  assert.deepStrictEqual(r.map((x) => x.url), ['/media/sub/Movie.mp4']);
});
test('stalker rejects invalid MAC and builds channel list', async () => {
  const ctx = { normMac: (m) => (/^[0-9A-F:]{17}$/i.test(m) ? m : null), portal: async (b, m, p) => (p.action === 'handshake' ? { token: 't' } : p.action === 'get_ordered_list' ? { data: [{ name: 'C', cmd: 'ffmpeg http://s' }] } : {}) };
  await assert.rejects(stalker.list({ portal: 'http://p', mac: 'bad' }, ctx));
  const r = await stalker.list({ portal: 'http://p', mac: '00:1A:79:EC:5F:08' }, ctx);
  assert.strictEqual(r[0].resolve.token, 't');
});
