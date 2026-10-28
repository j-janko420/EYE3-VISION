const test = require('node:test'), assert = require('node:assert'), fs = require('fs'), os = require('os'), path = require('path');
const adult = require('../lib/adult');
const mk = () => adult.create(fs.mkdtempSync(path.join(os.tmpdir(), 'pin-')));

test('classifies adult items by group/name', () => {
  assert.ok(adult.isAdult({ group: 'Adult Movies', name: 'x' })); assert.ok(adult.isAdult({ name: 'XXX Night' }));
  assert.ok(!adult.isAdult({ group: 'Sports', name: 'Grand Adulthood Documentary' }));
});
test('PIN setup, wrong pin, unlock, token validity and expiry', () => {
  const p = mk(); assert.ok(!p.isSet()); assert.throws(() => p.setup('12'), /4-8/);
  const t0 = p.setup('1234', 0); assert.ok(p.valid(t0, 1000)); assert.throws(() => p.setup('9999'), /already/);
  assert.throws(() => p.unlock('0000', 0), /Wrong/); const t = p.unlock('1234', 0);
  assert.ok(p.valid(t, 1000)); assert.ok(!p.valid(t, 1000 + 16 * 60 * 1000)); assert.ok(!p.valid('nope'));
  p.lock(t0); assert.ok(!p.valid(t0, 10));
});
test('lockout after repeated failures', () => {
  const p = mk(); p.setup('1234', 0); for (let i = 0; i < 5; i++) assert.throws(() => p.unlock('1111', 0), /Wrong/);
  assert.throws(() => p.unlock('1234', 1000), /Too many/); assert.ok(p.unlock('1234', 61000));
});

test('server: adult items only via unlocked adult view; normal view excludes them', async () => {
  const { spawn } = require('child_process'), dir = fs.mkdtempSync(path.join(os.tmpdir(), 'srv-'));
  const p = spawn(process.execPath, [path.join(__dirname, '../server.js')], { env: { ...process.env, PORT: '18083', HOST: '127.0.0.1', EYE3_TOKEN: '', DATA_DIR: dir } });
  await new Promise((r) => p.stdout.once('data', r));
  try {
    const B = 'http://127.0.0.1:18083', params = encodeURIComponent(JSON.stringify({ urls: 'Adult One|http://e.com/a\nNews|http://e.com/n' }));
    assert.strictEqual((await fetch(`${B}/plugin/list?id=url&adult=1&params=${params}`)).status, 403);
    const { unlock } = await (await fetch(`${B}/adult/setup`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"pin":"4242"}' })).json();
    const normal = await (await fetch(`${B}/plugin/list?id=url&params=${params}`)).json();
    const adultList = await (await fetch(`${B}/plugin/list?id=url&adult=1&unlock=${unlock}&params=${params}`)).json();
    assert.deepStrictEqual(normal.map((i) => i.name), ['News']); assert.deepStrictEqual(adultList.map((i) => i.name), ['Adult One']);
    assert.strictEqual((await fetch(`${B}/adult/unlock`, { method: 'POST', body: '{"pin":"4242"}' })).status, 400);
  } finally { p.kill(); }
});
