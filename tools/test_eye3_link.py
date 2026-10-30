#!/usr/bin/env python3
"""Offline tests for eye3-link.py: mock IPTV servers (M3U, Xtream, Stalker, HLS) on localhost. Run: python3 tools/test_eye3_link.py"""
import http.client, importlib.util, json, os, threading, unittest
import urllib.parse as up
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

spec = importlib.util.spec_from_file_location("link", os.path.join(os.path.dirname(os.path.abspath(__file__)), "eye3-link.py"))
link = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link)

MAC = "00:1A:79:AA:BB:CC"
SEGMENT = b"\x47" + bytes(187)


class Mock(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    seen = {}
    release = {}      # path -> bytes: a stand-in for the GitHub release page (updates)

    def log_message(self, *a):
        pass

    def reply(self, body, ctype="application/json", code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = up.urlparse(self.path)
        q = {k: v[0] for k, v in up.parse_qs(u.query).items()}
        host = "http://127.0.0.1:%d" % self.server.server_port
        if u.path == "/pl.m3u":
            return self.reply('#EXTM3U\n#EXTINF:-1 tvg-logo="http://x/l.png" group-title="News",Good News\n%s/live/u/p/7.ts\n'
                              '#EXTINF:-1 group-title="Adult",Bad One\n%s/x.m3u8\n#EXTINF:-1 group-title="Sports",Sport 1\n%s/hls/index.m3u8\n' % (host, host, host), "audio/x-mpegurl")
        if u.path == "/player_api.php":
            if q.get("username") not in ("u", "tsonly") or q.get("password") != "p":
                return self.reply({"user_info": {"auth": 0}})
            act = q.get("action")
            if act == "get_live_categories":
                return self.reply([{"category_id": "1", "category_name": "News"}, {"category_id": "2", "category_name": "XXX Adult"}])
            if act == "get_live_streams":
                return self.reply([{"name": "Xtream One", "stream_id": 11, "category_id": "1", "stream_icon": "i.png"},
                                   {"name": "Hidden", "stream_id": 12, "category_id": "2"}])
            if act == "get_short_epg":
                import base64 as _b
                enc = lambda t: _b.b64encode(t.encode()).decode()
                if q.get("stream_id") == "11":
                    return self.reply({"epg_listings": [
                        {"title": enc("Evening News"), "description": enc("Headlines of the day"), "start_timestamp": "2000", "stop_timestamp": "3000"},
                        {"title": enc("Weather"), "description": "", "start_timestamp": "1000", "stop_timestamp": "2000"},
                        {"title": "Plain Title", "description": "plain words", "start_timestamp": "3000", "stop_timestamp": "4000"},
                        {"title": enc("Broken"), "start_timestamp": "x", "stop_timestamp": "5000"}]})
                return self.reply({"epg_listings": []})
            if act == "get_vod_categories":
                return self.reply([{"category_id": "7", "category_name": "Action"}, {"category_id": "8", "category_name": "XXX Adult"}])
            if act == "get_vod_streams":
                return self.reply([{"name": "Big Movie", "stream_id": 21, "category_id": "7", "stream_icon": "m.jpg", "container_extension": "mp4", "rating": "7.5", "year": "2019"},
                                   {"name": "Odd Ext", "stream_id": 22, "category_id": "7", "container_extension": "../x"},
                                   {"name": "Late Night", "stream_id": 23, "category_id": "8", "container_extension": "mkv"}])
            if act == "get_series_categories":
                return self.reply([{"category_id": "9", "category_name": "Drama"}])
            if act == "get_series":
                return self.reply([{"name": "Long Show", "series_id": 31, "category_id": "9", "cover": "c.jpg", "releaseDate": "2021-05-01"}])
            if act == "get_series_info":
                return self.reply({"info": {"name": "Long Show", "plot": "A plot."},
                                   "episodes": {"2": [{"id": "502", "episode_num": 1, "title": "S2E1", "container_extension": "mp4", "season": 2, "info": {"duration": "00:40:00"}}],
                                                "1": [{"id": "502x", "episode_num": 3, "title": "bad id"}, {"id": "412", "episode_num": 2, "title": "S1E2", "container_extension": "mkv", "season": 1},
                                                      {"id": "411", "episode_num": 1, "title": "S1E1", "container_extension": "mp4", "season": 1}]}})
            ui = {"auth": 1, "status": "Expired" if q.get("username") == "old" else "Active", "exp_date": "1893456000", "max_connections": "2"}
            if q.get("username") == "tsonly":
                ui["allowed_output_formats"] = ["ts"]
            return self.reply({"user_info": ui})
        if u.path in ("/movie/u/p/21.mp4", "/series/u/p/411.mp4"):
            rng = self.headers.get("Range")
            Mock.seen["range"] = rng
            if rng:
                return self.reply(b"2345", "video/mp4", 206)
            return self.reply(b"0123456789", "video/mp4")
        if u.path in ("/hdr/stream.ts", "/hdr/index.m3u8", "/hdr/seg1.ts"):
            Mock.seen[u.path] = {"ua": self.headers.get("User-Agent"), "ref": self.headers.get("Referer"), "cookie": self.headers.get("Cookie")}
            if u.path.endswith(".m3u8"):
                return self.reply("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n#EXTINF:4,\nseg1.ts\n", "application/vnd.apple.mpegurl")
            return self.reply(SEGMENT, "video/mp2t")
        if u.path == "/big.m3u":
            n = int(q.get("n", "1000")); host2 = host
            body = "#EXTM3U\n" + "".join('#EXTINF:-1 group-title="G%d",Channel %d\n%s/live/u/p/%d.ts\n' % (i % 50, i, host2, i) for i in range(n))
            return self.reply(body, "audio/x-mpegurl")
        if u.path == "/list.m3u.gz":
            import gzip as _gz
            return self.reply(_gz.compress("\ufeff#EXTM3U\n#EXTINF:-1,Zipped One\nhttp://example.test/z/1.m3u8\n".encode()), "application/gzip")
        if u.path == "/rel/list.m3u":
            return self.reply("#EXTM3U\n#EXTINF:-1,Relative One\n../hdr/index.m3u8\n#EXTINF:-1,Absolute\nhttp://example.test/a.m3u8\n", "audio/x-mpegurl")
        if u.path == "/hdr/list.m3u":
            return self.reply("#EXTM3U\n"
                              "#EXTINF:-1 group-title=\"H\",Needs Headers\n#EXTVLCOPT:http-user-agent=MyAgent/9\n#EXTVLCOPT:http-referrer=https://ref.example/\n%s/hdr/index.m3u8\n"
                              "#EXTINF:-1,Kodi Style\n%s/hdr/stream.ts|User-Agent=KodiUA&Referer=https%%3A%%2F%%2Fk.example%%2F&X-Evil=1\n"
                              "#EXTINF:-1,Injection\n%s/hdr/stream.ts|User-Agent=Bad%%0D%%0AX-Evil%%3A%%20y\n" % (host, host, host), "audio/x-mpegurl")
        if u.path in ("/epg/guide.xml", "/epg/guide.xml.gz", "/epg/bad.xml", "/epg/evil.xml"):
            import time as _t, gzip as _gz
            Mock.seen["xmltv_hits"] = Mock.seen.get("xmltv_hits", 0) + 1
            Mock.seen["xmltv_ua"] = self.headers.get("User-Agent")
            if u.path == "/epg/bad.xml":
                return self.reply("<tv><channel id='x'>", "text/xml")
            if u.path == "/epg/evil.xml":
                return self.reply('<?xml version="1.0"?><!DOCTYPE tv [<!ENTITY a "aaaa">]><tv></tv>', "text/xml")
            now = int(_t.time())
            fmt = lambda t, tz="+0100": _t.strftime("%Y%m%d%H%M%S", _t.gmtime(t + 3600)) + " " + tz       # +0100 local time of the epoch t
            body = ('<?xml version="1.0" encoding="UTF-8"?><tv>'
                    '<channel id="news.one"><display-name>News One HD</display-name></channel>'
                    '<channel id="other"><display-name>Other</display-name></channel>'
                    '<programme start="%s" stop="%s" channel="news.one"><title>Gone By</title></programme>'
                    '<programme start="%s" stop="%s" channel="news.one"><title lang="en">Evening Bulletin</title><desc>All the news</desc></programme>'
                    '<programme start="%s" stop="%s" channel="news.one"><title>Late Talk</title></programme>'
                    '<programme start="%s" stop="%s" channel="news.one"><title>Far Future</title></programme>'
                    '<programme start="%s" stop="%s" channel="other"><title>Other Show</title></programme>'
                    '</tv>') % (fmt(now - 7200), fmt(now - 3700), fmt(now - 600), fmt(now + 1200), fmt(now + 1200), fmt(now + 3000),
                               fmt(now + 90 * 3600), fmt(now + 91 * 3600), fmt(now - 100), fmt(now + 100))
            if u.path.endswith(".gz"):
                return self.reply(_gz.compress(body.encode()), "application/gzip")
            return self.reply(body, "text/xml")
        if u.path == "/ua/list.m3u":
            Mock.seen["m3u_ua"] = self.headers.get("User-Agent")
            return self.reply('#EXTM3U x-tvg-url="%s/epg/guide.xml"\n#EXTINF:-1 tvg-id="news.one" group-title="N",News One\n%s/hdr/stream.ts\n' % (host, host), "audio/x-mpegurl")
        if u.path.startswith("/rel/") and u.path[5:] in Mock.release:
            return self.reply(Mock.release[u.path[5:]], "application/octet-stream")
        if u.path == "/where":
            return self.reply("AE\n", "text/plain")
        if u.path == "/forbidden/index.m3u8":
            return self.reply("denied", "text/plain", 403)
        if u.path == "/hls/index.m3u8":
            return self.reply('#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-KEY:METHOD=AES-128,URI="key.bin"\n#EXT-X-TARGETDURATION:4\n#EXTINF:4,\nseg1.ts\n#EXTINF:4,\n%s/abs/seg2.ts\n' % host, "application/vnd.apple.mpegurl")
        if u.path in ("/hls/seg1.ts", "/abs/seg2.ts"):
            return self.reply(SEGMENT, "video/mp2t")
        if u.path == "/hls/key.bin":
            return self.reply(b"k" * 16, "application/octet-stream")
        if u.path == "/live/u/p/11.m3u8" or u.path == "/live/u/p/7.m3u8":
            return self.reply("#EXTM3U\n#EXTINF:4,\nseg1.ts\n", "application/x-mpegURL")
        if u.path == "/stalker_portal/server/load.php":
            cookie = self.headers.get("Cookie", "")
            Mock.seen["ua"], Mock.seen["xua"], Mock.seen["auth"] = self.headers.get("User-Agent"), self.headers.get("X-User-Agent"), self.headers.get("Authorization")
            act = q.get("action")
            if act == "handshake":
                return self.reply({"js": {"token": "TOK1"}} if ("mac=" + MAC) in cookie else {"js": {}})
            if self.headers.get("Authorization") != "Bearer TOK1":
                return self.reply({"js": []})
            if act == "get_profile":
                return self.reply({"js": {"id": 1}})
            if act == "get_genres":
                return self.reply({"js": [{"id": "5", "title": "Movies"}, {"id": "6", "title": "Adult XXX"}]})
            if act == "get_all_channels":
                return self.reply({"js": {"data": [{"id": "1", "name": "Stalker Cinema", "cmd": "ffrt http://localhost/ch/1", "tv_genre_id": "5", "logo": "l.png"},
                                                    {"id": "2", "name": "Spicy", "cmd": "ffrt http://localhost/ch/2", "tv_genre_id": "6"}]}})
            if act == "create_link":
                if q.get("cmd") == "ffrt http://localhost/ch/1":
                    return self.reply({"js": {"cmd": "ffmpeg %s/hls/index.m3u8?play_token=abc" % host}})
                return self.reply({"js": {"cmd": ""}})
        return self.reply("nope", "text/plain", 404)


class WebOnly(BaseHTTPRequestHandler):
    """A 'portal' address that only has a web page (and a 404 for the Stalker data paths under /stalker_portal)."""
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = b"<html><head><title>Welcome to the portal</title></head><body>Hello</body></html>"
        code = 404 if self.path.startswith("/stalker_portal") else 200
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Doh(BaseHTTPRequestHandler):
    """Mock DNS-over-HTTPS (JSON): panel.eye3test.invalid -> 127.0.0.1, everything else has no answer."""
    asked = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        q = up.parse_qs(up.urlparse(self.path).query)
        name = q.get("name", [""])[0]
        Doh.asked.append((name, self.headers.get("Accept")))
        body = json.dumps({"Answer": [{"name": name, "type": 1, "TTL": 60, "data": "127.0.0.1"}]} if name == "panel.eye3test.invalid" else {"Status": 3}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/dns-json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    s.daemon_threads = True
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def get(port, path, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path, headers=headers or {})
    r = c.getresponse()
    out = (r.status, dict(r.getheaders()), r.read())
    c.close()
    return out


class LinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.up = serve(Mock)
        cls.srv = serve(link.Handler)
        link.STATE.update(port=cls.srv.server_port)
        cls.port, cls.up_port = cls.srv.server_port, cls.up.server_port
        cls.up_url = "http://127.0.0.1:%d" % cls.up_port
        cls.tok = link.STATE["token"]
        cls.origin = {"Origin": "https://j-janko420.github.io"}

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.up.shutdown()

    def api(self, path, **params):
        return get(self.port, "%s?%s" % (path, up.urlencode(params)), self.origin)

    # --- movies and series on demand (Xtream VOD)
    def vod(self, path, **params):
        params.update(server=self.up_url, user="u", **{"pass": "p"})
        return self.api(path, **params)

    def test_vod_movies_are_listed_compactly_and_adult_is_flagged(self):
        code, _, body = self.vod("/api/vod", kind="movie")
        self.assertEqual(code, 200)
        items = {i["n"]: i for i in json.loads(body)["items"]}
        self.assertEqual(items["Big Movie"], {"id": 21, "n": "Big Movie", "c": "Action", "l": "m.jpg", "y": "2019", "r": "7.5", "e": "mp4"})
        self.assertEqual(items["Odd Ext"]["e"], "mp4")            # a hostile extension is replaced
        self.assertTrue(items["Late Night"]["x"])                 # adult is flagged, never dropped

    def test_vod_series_list_and_episodes_sorted_by_season_and_number(self):
        code, _, body = self.vod("/api/vod", kind="series")
        self.assertEqual(json.loads(body)["items"][0]["y"], "2021")
        code, _, body = self.vod("/api/vod/series", id="31")
        d = json.loads(body)
        self.assertEqual([s["season"] for s in d["seasons"]], ["1", "2"])
        self.assertEqual([e["n"] for e in d["seasons"][0]["episodes"]], ["S1E1", "S1E2", "bad id"])
        self.assertEqual(d["plot"], "A plot.")

    def test_vod_play_link_is_proxied_with_range_and_checks_the_id(self):
        code, _, body = self.vod("/api/vod/play", kind="movie", id="21", ext="mp4")
        url = json.loads(body)["url"]
        self.assertIn("/stream?", url)
        path = url.split("127.0.0.1:%d" % self.port)[1]
        code, h, data = get(self.port, path, {"Range": "bytes=2-5"})
        self.assertEqual((code, data, Mock.seen["range"]), (206, b"2345", "bytes=2-5"))
        self.assertEqual(self.vod("/api/vod/play", kind="movie", id="../21", ext="mp4")[0], 502)
        self.assertEqual(self.vod("/api/vod/play", kind="series", id="411", ext="mp4/../")[0], 200)  # bad ext falls back to mp4

    def test_vod_wrong_password_and_other_sites_are_refused(self):
        code, _, body = self.api("/api/vod", server=self.up_url, user="u", **{"pass": "nope", "kind": "movie"})
        self.assertNotEqual(code, 200)
        code, _, _ = get(self.port, "/api/vod?" + up.urlencode({"server": self.up_url, "user": "u", "pass": "p", "kind": "movie"}), {"Origin": "https://evil.example"})
        self.assertEqual(code, 403)

    # --- M3U: big lists, gzip, relative links, headers, TS fallbacks
    def m3u(self, path, **kw):
        return self.api("/api/m3u", url=self.up_url + path)

    def test_big_list_is_parsed_and_capped(self):
        import time as _t
        t0 = _t.time()
        code, _, body = self.m3u("/big.m3u?n=30000")
        self.assertEqual(code, 200)
        d = json.loads(body)
        self.assertEqual(d["account"]["total"], 30000)
        self.assertEqual(len(d["channels"]), 30000)
        self.assertLess(_t.time() - t0, 30)
        old = link.MAX_CHANNELS
        link.MAX_CHANNELS = 100
        try:
            d = json.loads(self.m3u("/big.m3u?n=250")[2])
        finally:
            link.MAX_CHANNELS = old
        self.assertEqual((len(d["channels"]), d["account"]["total"], d["account"]["truncated"]), (100, 250, 150))

    def test_gzip_list_and_relative_links(self):
        d = json.loads(self.m3u("/list.m3u.gz")[2])
        self.assertEqual([c["n"] for c in d["channels"]], ["Zipped One"])      # BOM and gzip handled
        d = json.loads(self.m3u("/rel/list.m3u")[2])
        urls = [up.unquote(up.parse_qs(up.urlparse(c["u"]).query)["u"][0]) for c in d["channels"]]
        self.assertEqual(urls, [self.up_url + "/hdr/index.m3u8", "http://example.test/a.m3u8"])   # ../hdr resolved against the list address

    def test_playlist_headers_reach_the_stream_and_its_segments(self):
        d = json.loads(self.m3u("/hdr/list.m3u")[2])
        chans = {c["n"]: c for c in d["channels"]}
        path = lambda c: c["u"].split("127.0.0.1:%d" % self.port)[1]
        code, _, pl = get(self.port, path(chans["Needs Headers"]))
        self.assertEqual(code, 200)
        self.assertEqual(Mock.seen["/hdr/index.m3u8"], {"ua": "MyAgent/9", "ref": "https://ref.example/", "cookie": None})
        seg = [l for l in pl.decode().split("\n") if l and not l.startswith("#")][0]
        get(self.port, seg.split("127.0.0.1:%d" % self.port)[1])
        self.assertEqual(Mock.seen["/hdr/seg1.ts"]["ua"], "MyAgent/9")           # segments keep the channel's headers
        get(self.port, path(chans["Kodi Style"]))
        self.assertEqual(Mock.seen["/hdr/stream.ts"], {"ua": "KodiUA", "ref": "https://k.example/", "cookie": None})
        self.assertEqual(chans["Kodi Style"].get("t"), 1)                         # raw .ts is flagged for the TS player
        get(self.port, path(chans["Injection"]))
        self.assertEqual(Mock.seen["/hdr/stream.ts"]["ua"], "BadX-Evil: y")        # line breaks stripped: no header injection

    def test_xtream_output_follows_allowed_formats(self):
        d = json.loads(self.api("/api/xtream", server=self.up_url, user="u", **{"pass": "p"})[2])["channels"][0]
        self.assertIn(".m3u8", up.unquote(d["u"]))
        self.assertIn(".ts", up.unquote(d["a"]))                                  # HLS first, TS as fallback
        d = json.loads(self.api("/api/xtream", server=self.up_url, user="tsonly", **{"pass": "p"})[2])["channels"][0]
        self.assertTrue(up.unquote(d["u"]).split("?")[0].endswith(".ts") or ".ts&" in up.unquote(d["u"]) or ".ts" in up.unquote(d["u"]))
        self.assertEqual(d.get("t"), 1)
        self.assertNotIn("a", d)

    # --- the agent: config file, your own playlists folder, updates, self-fixing DNS
    def test_config_file_keeps_only_valid_known_settings(self):
        import tempfile
        d = tempfile.mkdtemp()
        path = os.path.join(d, "eye3-link.conf")
        with open(path, "w") as f:
            json.dump({"port": 8800, "auto_fix": True, "auto_update": "yes", "dns": "cloudflare", "evil": 1, "port2": 5, "origins": ["https://a.example"]}, f)
        self.assertEqual(link.load_conf(path), {"port": 8800, "auto_fix": True, "dns": "cloudflare", "origins": ["https://a.example"]})
        with open(path, "w") as f:
            f.write("not json")
        self.assertEqual(link.load_conf(path), {})
        self.assertEqual(link.load_conf(os.path.join(d, "missing.conf")), {})

    def test_local_playlists_folder_reads_only_its_own_files(self):
        import tempfile, gzip as _gz
        root = tempfile.mkdtemp()
        outside = tempfile.mkdtemp()
        open(os.path.join(root, "My News.m3u"), "w").write('#EXTM3U\n#EXTINF:-1 tvg-id="n1" group-title="News",Local News\nhttps://example.test/news.m3u8\n#EXTINF:-1 group-title="XXX",Adult Test\nhttps://example.test/a.m3u8\n')
        open(os.path.join(root, "links.txt"), "w").write("1. Sport One - https://example.test/s1.m3u8\nhttps://example.test/bare.m3u8\n")
        open(os.path.join(root, "zipped.m3u"), "wb").write(_gz.compress(b"#EXTM3U\n#EXTINF:-1,Zipped Local\nhttps://example.test/z.m3u8\n"))
        open(os.path.join(root, "program.exe"), "w").write("#EXTM3U\n#EXTINF:-1,Nope\nhttps://example.test/no.m3u8\n")
        open(os.path.join(outside, "secret.m3u"), "w").write("#EXTM3U\n#EXTINF:-1,Outside\nhttps://example.test/out.m3u8\n")
        try:
            os.symlink(os.path.join(outside, "secret.m3u"), os.path.join(root, "escape.m3u"))
        except OSError:
            pass
        os.mkdir(os.path.join(root, "sub"))
        open(os.path.join(root, "sub", "deep.m3u"), "w").write("#EXTM3U\n#EXTINF:-1,Deep\nhttps://example.test/deep.m3u8\n")
        old = link.STATE["playlists"]
        link.STATE["playlists"] = root
        try:
            code, _, body = self.api("/api/local")
            self.assertEqual(code, 200)
            d = json.loads(body)
        finally:
            link.STATE["playlists"] = old
        names = sorted(f["file"] for f in d["files"])
        self.assertEqual(names, ["My News.m3u", "links.txt", "zipped.m3u"])               # no .exe, no symlink out, no sub-folders
        chans = {c["n"]: c for c in d["channels"]}
        self.assertEqual(set(chans), {"Local News", "Adult Test", "Sport One", "example.test", "Zipped Local"})
        self.assertTrue(chans["Adult Test"]["x"])                                           # flagged, so Home keeps it behind the Explicit unlock
        self.assertEqual(chans["Local News"]["f"], "My News")
        self.assertEqual(chans["Local News"]["i"], "n1")
        self.assertIn("/stream?", chans["Sport One"]["u"])
        link.STATE["playlists"] = ""
        self.assertEqual(json.loads(self.api("/api/local")[2]), {"files": [], "channels": []})

    def test_health_and_agent_switches_are_remembered(self):
        import tempfile
        conf = os.path.join(tempfile.mkdtemp(), "eye3-link.conf")
        open(conf, "w").write('{"auto_fix": false}')
        old = (link.STATE["conf_path"], link.STATE["auto_fix"], link.STATE["auto_update"])
        link.STATE["conf_path"] = conf
        try:
            d = json.loads(self.api("/api/health")[2])
            self.assertEqual((d["version"], d["auto_fix"], d["auto_update"], d["packaged"]), (link.VERSION, old[1], old[2], False))
            self.assertFalse(d["managed"])                                                    # not started by the box launcher
            self.api("/api/agent", auto_fix="1", auto_update="1")
            d = json.loads(self.api("/api/health")[2])
            self.assertTrue(d["auto_fix"] and d["auto_update"])
            self.assertEqual(json.load(open(conf)), {"auto_fix": True, "auto_update": True})   # kept for the next start
        finally:
            link.STATE["conf_path"], link.STATE["auto_fix"], link.STATE["auto_update"] = old

    def test_update_is_checked_downloaded_verified_and_swapped(self):
        import hashlib as _h, tempfile
        new_bin = b"#!/bin/sh\necho new eye3 link\n"
        name = link.asset_name()
        Mock.release = {"eye3-link-version.txt": b"9.9\n", name: new_bin,
                        "SHA256SUMS.txt": ("%s  %s\n%s  other-file\n" % (_h.sha256(new_bin).hexdigest(), name, "0" * 64)).encode()}
        old_base = link.STATE["update_base"]
        link.STATE["update_base"] = self.up_url + "/rel"
        try:
            u = link.check_update(force=True)
            self.assertEqual((u["latest"], u["available"]), ("9.9", True))
            self.assertTrue(any("9.9" in e["t"] for e in link.STATE["events"]))
            d = tempfile.mkdtemp()
            exe = os.path.join(d, "eye3-link")
            open(exe, "w").write("old program")
            with self.assertRaises(link.LinkError):                                          # a copy that runs from the .py cannot replace itself
                link.stage_update(exe, frozen=False)
            Mock.release["SHA256SUMS.txt"] = ("%s  %s\n" % ("1" * 64, name)).encode()       # a wrong checksum: nothing is installed
            with self.assertRaises(link.LinkError) as cm:
                link.stage_update(exe, frozen=True)
            self.assertIn("checksum", str(cm.exception))
            self.assertFalse(os.path.exists(os.path.join(d, "eye3-link.update")))
            Mock.release["SHA256SUMS.txt"] = ("%s  %s\n" % (_h.sha256(new_bin).hexdigest(), name)).encode()
            r = link.stage_update(exe, frozen=True)
            self.assertTrue(r["staged"])
            self.assertEqual(open(exe).read(), "old program")                                 # staging replaces nothing
            self.assertTrue(link.apply_staged_update(exe))                                     # the swap at the next start
            self.assertEqual(open(exe, "rb").read(), new_bin)
            self.assertEqual(open(os.path.join(d, "eye3-link.old")).read(), "old program")
            self.assertFalse(os.path.exists(os.path.join(d, "eye3-link.update.ok")))
            self.assertFalse(link.apply_staged_update(exe))                                    # nothing waiting any more
            # an update that is not newer is dropped, not installed
            open(os.path.join(d, "eye3-link.update"), "w").write("x")
            open(os.path.join(d, "eye3-link.update.ok"), "w").write(link.VERSION)
            self.assertFalse(link.apply_staged_update(exe))
            self.assertFalse(os.path.exists(os.path.join(d, "eye3-link.update")))
            Mock.release["eye3-link-version.txt"] = b"not a version"
            self.assertTrue(link.check_update(force=True)["error"])                            # a broken version file is an error, not a crash
        finally:
            link.STATE["update_base"] = old_base
            link.STATE["update"] = {}
            Mock.release = {}

    def test_agent_turns_on_secure_dns_by_itself_when_a_name_cannot_be_found(self):
        server = "http://panel.eye3test.invalid:%d" % self.up_port
        doh = serve(Doh)
        old = (link.STATE["auto_fix"], link.STATE.get("dns", ""), dict(link.DOH), list(link.STATE["events"]))
        link.install_dns("")
        link.DOH["cloudflare"] = "http://127.0.0.1:%d/dns-query" % doh.server_port
        try:
            link.STATE["auto_fix"] = False
            code, _, body = self.api("/api/xtream", server=server, user="u", **{"pass": "p"})
            self.assertEqual(code, 502)                                                       # without the agent the name stays unknown
            link.STATE["auto_fix"] = True
            code, _, body = self.api("/api/xtream", server=server, user="u", **{"pass": "p"})
            self.assertEqual(code, 200)                                                       # with it, one failed lookup fixes it
            h = json.loads(self.api("/api/health")[2])
            self.assertTrue(h["dns"] and any(e["k"] == "dns" and "panel.eye3test.invalid" in e["t"] for e in h["events"]))
            self.assertEqual(json.loads(self.api("/api/xtream", server=self.up_url, user="u", **{"pass": "p"})[2])["channels"][0]["n"], "Xtream One")   # normal names still use the system
        finally:
            link.STATE["auto_fix"], link.STATE["dns"] = old[0], ""
            link.DOH.clear(); link.DOH.update(old[2])
            link.install_dns("")
            doh.shutdown()

    # --- XMLTV guide, custom User-Agent
    def xmltv(self, path="/epg/guide.xml", **kw):
        return self.api("/api/xmltv", url=self.up_url + path, **kw)

    def test_xmltv_now_next_by_id_and_by_name_with_time_zones(self):
        Mock.seen["xmltv_hits"] = 0
        code, _, body = self.xmltv(id="news.one")
        self.assertEqual(code, 200)
        items = json.loads(body)["items"]
        self.assertEqual([i["t"] for i in items], ["Evening Bulletin", "Late Talk"])       # finished and far-future programmes are left out
        self.assertEqual(items[0]["d"], "All the news")
        import time as _t
        self.assertTrue(items[0]["s"] < _t.time() < items[0]["e"])                         # it is on now (+0100 was converted to UTC)
        by_name = json.loads(self.xmltv(id="", name="news one hd")[2])["items"]
        self.assertEqual(by_name[0]["t"], "Evening Bulletin")                              # display-name fallback
        self.assertEqual(Mock.seen["xmltv_hits"], 1)                                       # one download, then cached
        gz = json.loads(self.xmltv("/epg/guide.xml.gz", id="news.one")[2])["items"]
        self.assertEqual(gz[0]["t"], "Evening Bulletin")                                   # gzip guides work
        self.assertEqual(json.loads(self.xmltv(id="nobody")[2])["items"], [])

    def test_xmltv_rejects_bad_files(self):
        self.assertEqual(self.xmltv("/epg/bad.xml", id="x")[0], 502)
        code, _, body = self.xmltv("/epg/evil.xml", id="x")
        self.assertEqual(code, 502)
        self.assertIn("not allowed", json.loads(body)["error"])

    def test_custom_user_agent_and_guide_link_in_m3u_header(self):
        d = json.loads(self.api("/api/m3u", url=self.up_url + "/ua/list.m3u", ua="MyPlayer/7.1")[2])
        self.assertEqual(Mock.seen["m3u_ua"], "MyPlayer/7.1")                              # the playlist itself is fetched with it
        self.assertEqual(d["account"]["epg"], self.up_url + "/epg/guide.xml")             # x-tvg-url is reported
        ch = d["channels"][0]
        self.assertEqual(ch["i"], "news.one")                                              # tvg-id is passed on
        get(self.port, ch["u"].split("127.0.0.1:%d" % self.port)[1])
        self.assertEqual(Mock.seen["/hdr/stream.ts"]["ua"], "MyPlayer/7.1")                # and the stream carries it
        d = json.loads(self.api("/api/xtream", server=self.up_url, user="u", ua="XtreamUA/2", **{"pass": "p"})[2])["channels"][0]
        url = d["u"].split("127.0.0.1:%d" % self.port)[1]
        self.assertIn("&h=", url)                                                          # Xtream streams carry a header id too

    # --- TV guide (EPG): now and next
    def test_epg_decodes_titles_sorts_and_skips_bad_rows(self):
        code, _, body = self.vod("/api/epg", id="11")
        self.assertEqual(code, 200)
        items = json.loads(body)["items"]
        self.assertEqual([i["t"] for i in items], ["Weather", "Evening News", "Plain Title"])
        self.assertEqual(items[1], {"t": "Evening News", "d": "Headlines of the day", "s": 2000, "e": 3000})
        self.assertEqual(items[2]["d"], "plain words")                       # plain text is kept as it is
        self.assertEqual(json.loads(self.vod("/api/epg", id="99")[2])["items"], [])
        self.assertEqual(self.vod("/api/epg", id="1;rm")[0], 502)            # ids must be numeric
        code, _, body = self.api("/api/xtream", server=self.up_url, user="u", **{"pass": "p"})
        self.assertEqual(json.loads(body)["channels"][0]["e"], 11)           # live rows carry their stream id

    # --- --dns: DNS-over-HTTPS only when the normal lookup fails
    def test_dns_off_gives_a_hint_and_on_resolves_through_doh(self):
        server = "http://panel.eye3test.invalid:%d" % self.up_port
        link.install_dns("")
        code, _, body = self.api("/api/xtream", server=server, user="u", **{"pass": "p"})
        self.assertEqual(code, 502)
        self.assertIn("--dns cloudflare", json.loads(body)["error"])
        doh = serve(Doh)
        try:
            link.install_dns("http://127.0.0.1:%d/dns-query" % doh.server_port)
            code, _, body = self.api("/api/xtream", server=server, user="u", **{"pass": "p"})
            self.assertEqual(code, 200)
            self.assertEqual(json.loads(body)["channels"][0]["n"], "Xtream One")
            self.assertEqual(Doh.asked[0], ("panel.eye3test.invalid", "application/dns-json"))
            n = len(Doh.asked)
            self.api("/api/xtream", server=server, user="u", **{"pass": "p"})
            self.assertEqual(len(Doh.asked), n)                       # cached
            self.api("/api/xtream", server=self.up_url, user="u", **{"pass": "p"})
            self.assertEqual(len(Doh.asked), n)                       # a name the system can resolve never asks DoH
        finally:
            link.install_dns("")
            doh.shutdown()

    # --- access control
    def test_ping_is_open_and_hello_needs_an_allowed_origin(self):
        self.assertEqual(json.loads(get(self.port, "/ping")[2])["name"], "EYE3 Link")
        code, hdrs, body = get(self.port, "/api/hello", self.origin)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["token"], self.tok)
        self.assertEqual(hdrs["Access-Control-Allow-Origin"], self.origin["Origin"])
        self.assertEqual(get(self.port, "/api/hello", {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(get(self.port, "/api/hello")[0], 403)
        self.assertEqual(get(self.port, "/api/hello", {"Origin": "http://localhost:8080"})[0], 200)

    def test_api_and_stream_refuse_strangers(self):
        self.assertEqual(get(self.port, "/api/m3u?url=" + up.quote(self.up_url + "/pl.m3u"), {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(get(self.port, "/stream?u=" + up.quote(self.up_url + "/hls/seg1.ts"))[0], 403)
        self.assertEqual(get(self.port, "/stream?t=wrong&u=" + up.quote(self.up_url + "/hls/seg1.ts"))[0], 403)

    def test_dns_rebinding_host_is_refused(self):
        self.assertEqual(get(self.port, "/ping", {"Host": "evil.example"})[0], 403)

    def test_preflight(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("OPTIONS", "/api/hello", headers={"Origin": "https://j-janko420.github.io", "Access-Control-Request-Private-Network": "true"})
        r = c.getresponse()
        r.read()
        c.close()
        self.assertEqual(r.status, 204)
        self.assertEqual(r.getheader("Access-Control-Allow-Private-Network"), "true")

    # --- M3U
    def test_m3u_filters_adult_and_makes_streams_playable(self):
        code, _, body = self.api("/api/m3u", url=self.up_url + "/pl.m3u")
        d = json.loads(body)
        names = [c["n"] for c in d["channels"]]
        self.assertEqual(names, ["Good News", "Bad One", "Sport 1"])
        self.assertEqual([c.get("x", False) for c in d["channels"]], [False, True, False])  # adult is flagged, not dropped
        self.assertIn("/stream?", d["channels"][0]["u"])
        self.assertIn("7.m3u8", up.unquote(d["channels"][0]["u"]))  # Xtream .ts rewritten to .m3u8
        self.assertEqual(d["channels"][0]["l"], "http://x/l.png")
        self.assertEqual(self.api("/api/m3u", url="ftp://x/y")[0], 502)

    # --- Xtream
    def test_xtream(self):
        code, _, body = self.api("/api/xtream", server=self.up_url + "/c/", user="u", **{"pass": "p"})
        d = json.loads(body)
        self.assertEqual([c["n"] for c in d["channels"]], ["Xtream One", "Hidden"])
        self.assertTrue(d["channels"][1]["x"] and not d["channels"][0].get("x"))
        self.assertIn("11.m3u8", up.unquote(d["channels"][0]["u"]))
        self.assertEqual(d["account"]["status"], "Active")
        self.assertEqual(d["account"]["expires"], "2030-01-01")

    def test_xtream_bad_password_and_expired(self):
        code, _, body = self.api("/api/xtream", server=self.up_url, user="u", **{"pass": "wrong"})
        self.assertEqual(code, 502)
        self.assertIn("rejected", json.loads(body)["error"])
        code, _, body = self.api("/api/xtream", server=self.up_url, user="old", **{"pass": "p"})
        self.assertIn("rejected", json.loads(body)["error"])  # mock answers auth 0 for unknown users
        self.assertEqual(self.api("/api/xtream", server=self.up_url, user="u")[0], 502)

    # --- Stalker / MAG
    def test_stalker_flow(self):
        code, _, body = self.api("/api/stalker", portal=self.up_url + "/c/", mac=MAC.lower().replace(":", "-"))
        d = json.loads(body)
        self.assertEqual(code, 200, body)
        self.assertEqual([c["n"] for c in d["channels"]], ["Stalker Cinema", "Spicy"])
        self.assertTrue(d["channels"][1]["x"] and not d["channels"][0].get("x"))
        self.assertEqual(d["channels"][0]["c"], "Movies")
        self.assertEqual(d["account"]["mac"], MAC)
        self.assertIn("MAG250", Mock.seen["xua"])
        self.assertEqual(Mock.seen["auth"], "Bearer TOK1")
        # playing resolves create_link through the portal, then streams through the proxy
        play = up.urlparse(d["channels"][0]["u"])
        code, hdrs, _ = get(self.port, play.path + "?" + play.query)
        self.assertEqual(code, 302)
        loc = up.urlparse(hdrs["Location"])
        code, hdrs, body = get(self.port, loc.path + "?" + loc.query)
        self.assertEqual(code, 200)
        self.assertIn(b"/stream?", body)

    def test_stalker_web_page_answer_lists_what_was_tried_and_a_pasted_api_address_works(self):
        web = serve(WebOnly)
        try:
            code, _, body = self.api("/api/stalker", portal="http://127.0.0.1:%d/web/c/" % web.server_port, mac=MAC)
        finally:
            web.shutdown()
        err = json.loads(body)["error"]
        self.assertEqual(code, 502)
        self.assertIn('/web/server/load.php: a web page titled "Welcome to the portal", not data', err)
        self.assertIn("/stalker_portal/server/load.php: HTTP 404", err)
        self.assertNotIn(MAC, err)                                   # the MAC is never echoed
        code, _, body = self.api("/api/stalker", portal=self.up_url + "/stalker_portal/server/load.php", mac=MAC)
        self.assertEqual(code, 200)                                  # pasting the data address itself is accepted

    def test_stalker_wrong_mac_and_bad_input(self):
        code, _, body = self.api("/api/stalker", portal=self.up_url, mac="00:1A:79:00:00:01")
        self.assertEqual(code, 502)
        self.assertIn("did not accept this MAC", json.loads(body)["error"])
        self.assertIn("MAC", json.loads(self.api("/api/stalker", portal=self.up_url, mac="nonsense")[2])["error"])

    def test_stalker_refused_channel_gives_a_clear_error(self):
        d = json.loads(self.api("/api/stalker", portal=self.up_url, mac=MAC)[2])
        s = link.STATE["sessions"][up.parse_qs(up.urlparse(d["channels"][0]["u"]).query)["sid"][0]]
        with self.assertRaises(link.LinkError):
            s.create_link("ffrt http://localhost/ch/2")

    # --- stream proxy
    def test_hls_playlist_is_rewritten_and_segments_pass_through(self):
        pl = link.stream_url(self.up_url + "/hls/index.m3u8")
        p = up.urlparse(pl)
        code, hdrs, body = get(self.port, p.path + "?" + p.query)
        text = body.decode()
        self.assertEqual(code, 200)
        self.assertIn("mpegurl", hdrs["Content-Type"].lower())
        lines = [l for l in text.split("\n") if l and not l.startswith("#")]
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(l.startswith("http://127.0.0.1:%d/stream?" % self.port) for l in lines), lines)
        self.assertIn('URI="http://127.0.0.1:%d/stream?' % self.port, text)  # key URI rewritten
        seg = up.urlparse(lines[0])
        code, hdrs, body = get(self.port, seg.path + "?" + seg.query)
        self.assertEqual((code, body), (200, SEGMENT))
        self.assertEqual(hdrs["Content-Length"], str(len(SEGMENT)))

    def test_stream_cannot_loop_back_or_leave_http(self):
        for target in ("http://127.0.0.1:%d/ping" % self.port, "file:///etc/passwd"):
            p = up.urlparse(link.stream_url(target))
            code, _, body = get(self.port, p.path + "?" + p.query)
            self.assertEqual(code, 502, body)

    def test_unreachable_upstream_is_reported(self):
        p = up.urlparse(link.stream_url("http://127.0.0.1:1/none.m3u8"))
        code, _, body = get(self.port, p.path + "?" + p.query)
        self.assertEqual(code, 502)
        self.assertIn("error", json.loads(body))


class CheckTests(unittest.TestCase):
    """Does a stream play from THIS connection?"""
    setUpClass = classmethod(LinkTests.setUpClass.__func__)
    tearDownClass = classmethod(LinkTests.tearDownClass.__func__)
    api = LinkTests.api

    def probe(self, path):
        code, _, body = self.api("/api/probe", u=self.up_url + path)
        self.assertEqual(code, 200)
        return json.loads(body)

    def test_probe_says_ok_only_for_real_video(self):
        self.assertEqual(self.probe("/hls/index.m3u8"), {"ok": True, "why": ""})

    def test_probe_names_the_problem(self):
        self.assertEqual(self.probe("/nothing.m3u8")["why"], "dead")
        self.assertEqual(self.probe("/where")["why"], "not a video playlist")  # answers, but it is not a stream
        self.assertEqual(self.probe("/forbidden/index.m3u8")["why"], "blocked")
        self.assertEqual(link.probe_stream("http://127.0.0.1:1/x.m3u8")["why"], "unreachable")

    def test_probe_needs_an_allowed_origin(self):
        self.assertEqual(get(self.port, "/api/probe?u=" + up.quote(self.up_url + "/hls/index.m3u8"), {"Origin": "https://evil.example"})[0], 403)

    def test_where_am_i_reports_a_country_through_the_current_route(self):
        link.STATE["where_url"] = self.up_url + "/where"
        try:
            self.assertEqual(json.loads(self.api("/api/where")[2]), {"country": "AE", "viaProxy": False})
            link.STATE["where_url"] = self.up_url + "/hls/seg1.ts"
            self.assertEqual(self.api("/api/where")[0], 502)
        finally:
            link.STATE["where_url"] = ""


class ProxyHandler(BaseHTTPRequestHandler):
    """A tiny HTTP proxy: maps the made-up host 'provider.test' to the mock provider and counts what it carries."""
    protocol_version = "HTTP/1.1"
    hits = []
    target_port = 0

    def log_message(self, *a):
        pass

    def do_GET(self):
        ProxyHandler.hits.append(self.path)
        u = up.urlparse(self.path)
        c = http.client.HTTPConnection("127.0.0.1", ProxyHandler.target_port, timeout=10)
        c.request("GET", u.path + ("?" + u.query if u.query else ""))
        r = c.getresponse()
        body = r.read()
        c.close()
        self.send_response(r.status)
        self.send_header("Content-Type", r.getheader("Content-Type", "text/plain"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ProxyTests(unittest.TestCase):
    def test_traffic_goes_through_the_viewers_proxy(self):
        mock = serve(Mock)
        proxy = serve(ProxyHandler)
        ProxyHandler.target_port = mock.server_port
        ProxyHandler.hits.clear()
        link.STATE["proxy"] = "http://127.0.0.1:%d" % proxy.server_port
        try:
            body, _, _ = link.fetch("http://provider.test:%d/pl.m3u" % mock.server_port)
            self.assertIn(b"Good News", body)
            self.assertEqual(len(ProxyHandler.hits), 1)
            self.assertTrue(ProxyHandler.hits[0].startswith("http://provider.test:"))
            # the stream proxy uses it too
            srv = serve(link.Handler)
            link.STATE["port"] = srv.server_port
            p = up.urlparse(link.stream_url("http://provider.test:%d/hls/seg1.ts" % mock.server_port))
            code, _, data = get(srv.server_port, p.path + "?" + p.query)
            self.assertEqual((code, data), (200, SEGMENT))
            self.assertEqual(len(ProxyHandler.hits), 2)
            self.assertTrue(json.loads(get(srv.server_port, "/ping")[2])["proxy"])
            srv.shutdown()
        finally:
            link.STATE["proxy"] = ""
            mock.shutdown()
            proxy.shutdown()

    def test_without_a_proxy_nothing_is_routed_and_ping_says_so(self):
        link.STATE["proxy"] = ""
        srv = serve(link.Handler)
        try:
            self.assertFalse(json.loads(get(srv.server_port, "/ping")[2])["proxy"])
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
