// Connector: direct stream URLs (HLS/MP4/DASH), one per line.
module.exports = {
  category: 'online',
  id: 'url', name: 'Direct URLs', description: 'Paste stream links (one per line, optional "Name|URL")',
  fields: [{ name: 'urls', label: 'URLs', placeholder: 'Name|https://host/stream.m3u8' }],
  async list(p) {
    return String(p.urls || '').split(/[\n,]+/).map((l) => l.trim()).filter(Boolean).map((l) => {
      const i = l.indexOf('|'), name = i > 0 ? l.slice(0, i).trim() : l, url = (i > 0 ? l.slice(i + 1) : l).trim();
      return { name, url };
    }).filter((x) => /^https?:\/\//i.test(x.url));
  },
};
