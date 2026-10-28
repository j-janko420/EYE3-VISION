// SRT -> WebVTT conversion (browsers/TVs only understand VTT in <track>).
function srtToVtt(srt) {
  const body = String(srt).replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').replace(/(\d\d:\d\d:\d\d),(\d{3})/g, '$1.$2');
  return 'WEBVTT\n\n' + body.trim() + '\n';
}
module.exports = { srtToVtt };
