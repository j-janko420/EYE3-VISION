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
            if q.get("username") != "u" or q.get("password") != "p":
                return self.reply({"user_info": {"auth": 0}})
            act = q.get("action")
            if act == "get_live_categories":
                return self.reply([{"category_id": "1", "category_name": "News"}, {"category_id": "2", "category_name": "XXX Adult"}])
            if act == "get_live_streams":
                return self.reply([{"name": "Xtream One", "stream_id": 11, "category_id": "1", "stream_icon": "i.png"},
                                   {"name": "Hidden", "stream_id": 12, "category_id": "2"}])
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
            return self.reply({"user_info": {"auth": 1, "status": "Expired" if q.get("username") == "old" else "Active", "exp_date": "1893456000", "max_connections": "2"}})
        if u.path in ("/movie/u/p/21.mp4", "/series/u/p/411.mp4"):
            rng = self.headers.get("Range")
            Mock.seen["range"] = rng
            if rng:
                return self.reply(b"2345", "video/mp4", 206)
            return self.reply(b"0123456789", "video/mp4")
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
