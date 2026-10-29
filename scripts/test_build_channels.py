#!/usr/bin/env python3
"""Offline tests for build_channels.py: mock HLS servers on localhost. Run: python3 scripts/test_build_channels.py"""
import importlib.util, os, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

spec = importlib.util.spec_from_file_location("bc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_channels.py"))
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)

FILES = {
    "/live/media.m3u8": ("#EXTM3U\n#EXT-X-TARGETDURATION:4\n#EXTINF:4,\nold.ts\n#EXTINF:4,\nnew.ts\n", 200),
    "/live/new.ts": ("\x47" * 188, 200),
    "/live/old.ts": ("gone", 404),
    "/master/master.m3u8": ("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=800000\nv/low.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=2000000\nv/high.m3u8\n", 200),
    "/master/v/low.m3u8": ("#EXTM3U\n#EXTINF:4,\nseg1.ts\n", 200),
    "/master/v/seg1.ts": ("\x47" * 188, 200),
    "/badvariant/master.m3u8": ("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nmissing.m3u8\n", 200),
    "/deadseg/media.m3u8": ("#EXTM3U\n#EXTINF:4,\nseg.ts\n", 200),
    "/deadseg/seg.ts": ("nope", 404),
    "/empty/media.m3u8": ("#EXTM3U\n#EXT-X-ENDLIST\n", 200),
    "/html/page.m3u8": ("<html>not a playlist</html>", 200),
    "/zerobyte/media.m3u8": ("#EXTM3U\n#EXTINF:4,\nseg.ts\n", 200),
    "/zerobyte/seg.ts": ("", 200),
}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body, code = FILES.get(self.path.split("?")[0], ("x", 404))
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode("latin-1"))


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_port

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def a(self, path):
        return bc.alive(self.base + path, 3)

    def test_live_playlist_with_a_real_newest_segment_is_alive(self):
        self.assertTrue(self.a("/live/media.m3u8"))  # the old segment is gone, the newest is fine

    def test_master_playlist_is_followed_to_a_segment(self):
        self.assertTrue(self.a("/master/master.m3u8"))

    def test_dead_variant_dead_segment_empty_html_zero_bytes_are_all_dead(self):
        for path in ("/badvariant/master.m3u8", "/deadseg/media.m3u8", "/empty/media.m3u8", "/html/page.m3u8", "/zerobyte/media.m3u8", "/nothing.m3u8"):
            self.assertFalse(self.a(path), path)

    def test_expired_signed_links_are_recognised(self):
        old = "https://x/y.m3u8?hdnea=st=1701861650~exp=1765449000~acl=/*~hmac=abc"
        self.assertTrue(bc.expired_token(old, now=1_790_000_000))
        self.assertFalse(bc.expired_token(old, now=1_760_000_000))
        self.assertFalse(bc.expired_token("https://x/y.m3u8?token=abc&quality=1080"))
        self.assertTrue(bc.expired_token("https://x/y.m3u8?expires=1700000000", now=1_790_000_000))
        self.assertFalse(bc.expired_token("https://x/y.m3u8?e=12345"))  # not a timestamp

    def test_end_to_end_keeps_only_working_channels(self):
        import json, tempfile
        src = os.path.join(tempfile.mkdtemp(), "in.m3u")
        rows = ["#EXTM3U"]
        for i in range(60):  # enough alive entries to pass the publish safety check
            rows += ['#EXTINF:-1 tvg-id="Live%d.us" group-title="News",Live %d' % (i, i), self.base + "/live/media.m3u8?c=%d" % i]
        rows += ['#EXTINF:-1 tvg-id="Dead.us" group-title="News",Dead', self.base + "/deadseg/media.m3u8",
                 '#EXTINF:-1 tvg-id="Old.us" group-title="News",Expired', self.base + "/live/media.m3u8?hdnea=st=1~exp=1700000000~x"]
        open(src, "w").write("\n".join(rows) + "\n")
        out = tempfile.mkdtemp()
        import sys
        old = sys.argv
        sys.argv = ["x", "--src", src, "--out", out, "--workers", "10", "--timeout", "3"]
        try:
            self.assertEqual(bc.main(), 0)
        finally:
            sys.argv = old
        names = [c["n"] for c in json.load(open(os.path.join(out, "channels.json")))["channels"]]
        self.assertEqual(len(names), 60)
        self.assertNotIn("Dead", names)
        self.assertNotIn("Expired", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
