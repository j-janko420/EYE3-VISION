// Connector: MAG/Stalker portal. Uses ctx.portalCall (see server.js).
module.exports = {
  category: 'live',
  id: 'stalker', name: 'MAG / Stalker portal', description: 'Channels from a Stalker middleware portal using a virtual MAC',
  fields: [{ name: 'portal', label: 'Portal URL', placeholder: 'http://host/c/' }, { name: 'mac', label: 'Virtual MAC', default: '00:1A:79:EC:5F:08' }],
  async list(p, ctx) {
    const mac = ctx.normMac(p.mac || '00:1A:79:EC:5F:08'); if (!mac) throw new Error('Invalid MAC');
    const token = (await ctx.portal(p.portal, mac, { type: 'stb', action: 'handshake', token: '' })).token;
    await ctx.portal(p.portal, mac, { type: 'stb', action: 'get_profile', hd: 1, stb_type: 'MAG250' }, token).catch(() => {});
    const d = await ctx.portal(p.portal, mac, { type: 'itv', action: 'get_ordered_list', genre: '*', p: p.page || 1 }, token);
    return (d.data || []).map((c) => ({ name: c.name, resolve: { portal: p.portal, mac, token, cmd: c.cmd } }));
  },
  async resolve(r, ctx) {
    const js = await ctx.portal(r.portal, r.mac, { type: 'itv', action: 'create_link', cmd: r.cmd }, r.token);
    return { url: String(js.cmd || '').replace(/^ffmpeg\s+/, '') };
  },
};
