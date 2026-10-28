// Minimal dependency-free XMLTV parser -> {channels:{id:name}, programmes:[{channel,start,stop,title}]}
const dec = (s) => String(s || '').replace(/<!\[CDATA\[|\]\]>/g, '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&').trim();
function ts(s) {
  const m = /^(\d{4})(\d\d)(\d\d)(\d\d)(\d\d)(\d\d)?\s*([+-]\d{4})?/.exec(s || ''); if (!m) return null;
  const off = m[7] || '+0000', sign = off[0] === '-' ? -1 : 1;
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) - sign * ((+off.slice(1, 3)) * 60 + (+off.slice(3, 5))) * 60000;
}
function parse(xml) {
  const channels = {}, programmes = [];
  for (const m of xml.matchAll(/<channel\s+id="([^"]*)"[^>]*>([\s\S]*?)<\/channel>/g)) {
    const n = /<display-name[^>]*>([\s\S]*?)<\/display-name>/.exec(m[2]); channels[dec(m[1])] = dec(n && n[1]);
  }
  for (const m of xml.matchAll(/<programme\s+([^>]*)>([\s\S]*?)<\/programme>/g)) {
    const a = (k) => (new RegExp(k + '="([^"]*)"').exec(m[1]) || [])[1];
    const t = /<title[^>]*>([\s\S]*?)<\/title>/.exec(m[2]), start = ts(a('start')), stop = ts(a('stop'));
    if (start && stop) programmes.push({ channel: dec(a('channel')), start, stop, title: dec(t && t[1]) });
  }
  return { channels, programmes };
}
function nowNext(data, now = Date.now()) {
  const out = {};
  for (const p of data.programmes) {
    const e = out[p.channel] || (out[p.channel] = {});
    if (p.start <= now && now < p.stop) e.now = p;
    else if (p.start > now && (!e.next || p.start < e.next.start)) e.next = p;
  }
  return out;
}
module.exports = { parse, nowNext };
