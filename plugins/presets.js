// Connector: free, public, legally distributed test/demo streams. Add your own authorised entries here.
const ITEMS = [
  { name: 'Big Buck Bunny (Blender, CC-BY) HLS', url: 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8' },
  { name: 'Apple bipbop advanced HLS test', url: 'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_fmp4/master.m3u8' },
  { name: 'Sintel (Blender, CC-BY) HLS', url: 'https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8' },
  { name: 'Big Buck Bunny MP4 (Blender, CC-BY)', url: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4' },
  { name: 'Tears of Steel DASH (Blender, CC-BY)', url: 'https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps.mpd' },
  { name: 'iptv-org free public channel index (M3U)', url: 'https://iptv-org.github.io/iptv/index.m3u', playlist: true },
];
module.exports = {
  category: 'online',
  id: 'presets', name: 'Free & legal presets', description: 'Public demo streams and the open iptv-org playlist of publicly available channels',
  fields: [],
  async list() { return ITEMS.map((i) => ({ name: i.name, url: i.url, playlist: !!i.playlist })); },
};
