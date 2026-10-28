// Parental control: PIN (scrypt-hashed, stored locally in DATA_DIR, never in the repo), timed unlock tokens, and adult-item classification.
const crypto = require('crypto'), fs = require('fs'), path = require('path');
const TTL = 15 * 60 * 1000, MAX_FAILS = 5, LOCKOUT = 60 * 1000;
const ADULT_RE = /(^|[^a-z0-9])(adult|adults|xxx|18\+|porn|erotic|explicit)([^a-z0-9]|$)/i;
const isAdult = (item) => ADULT_RE.test(`${item.group || ''} ${item.name || ''}`);

function create(dir) {
  const file = path.join(dir, 'adult-pin.json'); const tokens = new Map(); let fails = 0, lockedUntil = 0;
  const load = () => { try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; } };
  const hash = (pin, salt) => crypto.scryptSync(String(pin), salt, 32).toString('hex');
  const validPin = (p) => /^\d{4,8}$/.test(String(p));
  const issue = (now) => { const t = crypto.randomBytes(16).toString('hex'); tokens.set(t, now + TTL); return t; };
  return {
    isSet: () => !!load(),
    setup(pin, now = Date.now()) {
      if (load()) throw new Error('PIN already set'); if (!validPin(pin)) throw new Error('PIN must be 4-8 digits');
      fs.mkdirSync(dir, { recursive: true }); const salt = crypto.randomBytes(16).toString('hex');
      fs.writeFileSync(file, JSON.stringify({ salt, hash: hash(pin, salt) }), { mode: 0o600 }); return issue(now);
    },
    unlock(pin, now = Date.now()) {
      const r = load(); if (!r) throw new Error('PIN not set'); if (now < lockedUntil) throw new Error('Too many attempts, try later');
      const ok = validPin(pin) && crypto.timingSafeEqual(Buffer.from(hash(pin, r.salt), 'hex'), Buffer.from(r.hash, 'hex'));
      if (!ok) { if (++fails >= MAX_FAILS) { fails = 0; lockedUntil = now + LOCKOUT; } throw new Error('Wrong PIN'); }
      fails = 0; return issue(now);
    },
    valid(t, now = Date.now()) { const e = tokens.get(t); if (!e) return false; if (e < now) { tokens.delete(t); return false; } tokens.set(t, now + TTL); return true; },
    lock(t) { tokens.delete(t); },
  };
}
module.exports = { create, isAdult };
