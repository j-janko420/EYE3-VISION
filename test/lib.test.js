const test = require('node:test'), assert = require('node:assert'), { spawn } = require('child_process'), path = require('path');
const { parse, nowNext } = require('../lib/xmltv'), { srtToVtt } = require('../lib/subtitles'), presets = require('../plugins/presets');

test('xmltv parse + now/next', () => {
  const xml = '<tv><channel id="a.b"><display-name>A &amp; B</display-name></channel>' +
    '<programme start="20260101120000 +0000" stop="20260101130000 +0000" channel="a.b"><title>Show</title></programme>' +
    '<programme start="20260101130000 +0000" stop="20260101140000 +0000" channel="a.b"><title>Later</title></programme></tv>';
  const d = parse(xml); assert.strictEqual(d.channels['a.b'], 'A & B');
  const nn = nowNext(d, Date.UTC(2026, 0, 1, 12, 30)); assert.strictEqual(nn['a.b'].now.title, 'Show'); assert.strictEqual(nn['a.b'].next.title, 'Later');
});
test('srt converts to vtt', () => assert.strictEqual(srtToVtt('1\r\n00:00:01,500 --> 00:00:02,000\r\nHi\r\n'), 'WEBVTT\n\n1\n00:00:01.500 --> 00:00:02.000\nHi\n'));
test('presets only expose http(s) urls', async () => (await presets.list()).forEach((i) => assert.match(i.url, /^https:\/\//)));

function run(env) {
  return new Promise((resolve) => {
    const p = spawn(process.execPath, [path.join(__dirname, '../server.js')], { env: { ...process.env, ...env } });
    p.stdout.once('data', (d) => resolve({ p, out: String(d) }));
  });
}
test('loopback needs no token; non-loopback requires one', async () => {
  let s = await run({ PORT: '18081', HOST: '127.0.0.1', EYE3_TOKEN: '' });
  assert.strictEqual((await fetch('http://127.0.0.1:18081/plugins')).status, 200); s.p.kill();
  s = await run({ PORT: '18082', HOST: '0.0.0.0', EYE3_TOKEN: 'sekret' });
  assert.strictEqual((await fetch('http://127.0.0.1:18082/plugins')).status, 401);
  assert.strictEqual((await fetch('http://127.0.0.1:18082/plugins?token=wrong')).status, 401);
  assert.strictEqual((await fetch('http://127.0.0.1:18082/plugins?token=sekret')).status, 200); s.p.kill();
});
