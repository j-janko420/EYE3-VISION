// A tiny test harness: no framework needed. `check` records a result, `suite` runs a group and survives exceptions.
const { chromium } = require('playwright');
let pass = 0, fail = 0;
const failures = [];
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  ok   ' + name); return; }
  fail++; failures.push(name);
  console.log('  FAIL ' + name + (detail !== undefined ? '   -> ' + JSON.stringify(detail) : ''));
}
async function suite(title, fn) {
  console.log('\n# ' + title);
  try { await fn(); } catch (e) { fail++; failures.push(title + ': ' + e.message); console.log('  FAIL (exception) ' + e.message.split('\n')[0]); }
}
function done() {
  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  if (fail) console.log('Failed:\n - ' + failures.join('\n - '));
  process.exit(fail ? 1 : 0);
}
const HOME = process.env.EYE3_HOME_URL || 'http://localhost:8099/home/?splash=0';
// a page with local storage pre-filled once (seed = { key: jsonValue })
async function open(browser, seed, extra) {
  const ctx = await browser.newContext(Object.assign({ acceptDownloads: true }, (extra && extra.ctx) || {}));
  const page = await ctx.newPage();
  page.errs = [];
  page.on('pageerror', (e) => page.errs.push(e.message));
  await page.addInitScript((s) => {
    if (localStorage.getItem('__seeded')) return;
    localStorage.setItem('__seeded', '1');
    Object.keys(s || {}).forEach((k) => localStorage.setItem(k, typeof s[k] === 'string' ? s[k] : JSON.stringify(s[k])));
  }, seed || {});
  if (extra && extra.init) await page.addInitScript(extra.init);   // a script that runs before the page's own (for stand-ins of CDN libraries)
  await page.goto((extra && extra.url) || HOME, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(700);
  return page;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
module.exports = { chromium, check, suite, done, open, sleep, HOME };
