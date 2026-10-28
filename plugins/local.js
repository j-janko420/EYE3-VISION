// Connector: local library (your own downloaded video/audio files in ./media or $MEDIA_DIR).
const fs = require('fs'), path = require('path');
const EXT = /\.(mp4|mkv|webm|m4v|mov|avi|ts|mp3|aac|flac)$/i;
function walk(dir, base, out) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) walk(full, base, out);
    else if (EXT.test(e.name)) out.push(path.relative(base, full).split(path.sep).join('/'));
  }
  return out;
}
module.exports = {
  id: 'local', name: 'Local library', description: 'Play your own downloaded files from the media folder',
  fields: [{ name: 'filter', label: 'Filter', placeholder: 'optional text' }],
  async list(p, ctx) {
    const f = (p.filter || '').toLowerCase();
    return walk(ctx.mediaDir, ctx.mediaDir, []).filter((n) => n.toLowerCase().includes(f))
      .map((n) => ({ name: n, url: '/media/' + n.split('/').map(encodeURIComponent).join('/'), transcodeSrc: n }));
  },
};
