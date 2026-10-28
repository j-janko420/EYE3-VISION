// Connector: M3U / M3U8 playlist URL.
module.exports = {
  category: 'live',
  id: 'm3u', name: 'M3U playlist', description: 'Channels from any M3U playlist URL',
  fields: [{ name: 'url', label: 'Playlist URL', placeholder: 'https://example.com/list.m3u' }],
  async list(p, ctx) {
    const text = await ctx.fetchText(p.url);
    const out = []; let name = '', epgId = '';
    text.split(/\r?\n/).forEach((ln) => {
      if (ln.startsWith('#EXTINF')) { name = ln.split(',').pop().trim(); epgId = (/tvg-id="([^"]*)"/.exec(ln) || [])[1] || ''; }
      else if (/^https?:/.test(ln.trim())) { out.push({ name: name || ln, url: ln.trim(), ...(epgId ? { epgId } : {}) }); name = ''; epgId = ''; }
    });
    return out;
  },
};
