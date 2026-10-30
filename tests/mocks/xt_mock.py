# A stand-in for an Xtream panel (live channels, a short guide, one series), an XMLTV file and an M3U list. Port 9191.
import json, time, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse as up
b64 = lambda t: base64.b64encode(t.encode()).decode()
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def reply(self, obj):
        body = json.dumps(obj).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        u = up.urlparse(self.path); q = {k: v[0] for k, v in up.parse_qs(u.query).items()}
        if u.path == "/epg/guide.xml":
            import time as _t
            n = int(_t.time()); f = lambda t: _t.strftime("%Y%m%d%H%M%S", _t.gmtime(t)) + " +0000"
            body = ('<tv><channel id="news.one"><display-name>News One</display-name></channel>'
                    '<programme start="%s" stop="%s" channel="news.one"><title>Evening Bulletin</title><desc>All the news</desc></programme>'
                    '<programme start="%s" stop="%s" channel="news.one"><title>Late Talk</title></programme></tv>') % (f(n - 600), f(n + 1500), f(n + 1500), f(n + 4500))
            body = body.encode(); self.send_response(200); self.send_header("Content-Type", "text/xml"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if u.path == "/ua/list.m3u":
            open("/tmp/eye3_ua_seen.txt", "a").write((self.headers.get("User-Agent") or "") + "\n")
            body = ('#EXTM3U x-tvg-url="http://127.0.0.1:9191/epg/guide.xml"\n#EXTINF:-1 tvg-id="news.one" group-title="N",News One\nhttp://127.0.0.1:9191/live/x/y/1.ts\n').encode()
            self.send_response(200); self.send_header("Content-Type", "audio/x-mpegurl"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if u.path.startswith("/series/u/p/"):
            body = b"0"; self.send_response(200); self.send_header("Content-Type", "video/mp4"); self.send_header("Content-Length", "1"); self.end_headers(); self.wfile.write(body); return
        if u.path != "/player_api.php": self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        act = q.get("action"); now = int(time.time())
        if act == "get_live_categories": return self.reply([{"category_id": "1", "category_name": "News"}])
        if act == "get_series_categories": return self.reply([{"category_id": "9", "category_name": "Drama"}])
        if act == "get_series": return self.reply([{"name": "Long Show", "series_id": 31, "category_id": "9"}])
        if act == "get_series_info": return self.reply({"info": {"name": "Long Show"}, "episodes": {"1": [
            {"id": "411", "episode_num": 1, "title": "Pilot", "container_extension": "mp4", "season": 1},
            {"id": "412", "episode_num": 2, "title": "Second", "container_extension": "mp4", "season": 1}]}})
        if act == "get_live_streams": return self.reply([{"name": "Xtream One", "stream_id": 11, "category_id": "1"}, {"name": "Xtream Two", "stream_id": 12, "category_id": "1"}])
        if act == "get_short_epg":
            if q.get("stream_id") != "11": return self.reply({"epg_listings": []})
            return self.reply({"epg_listings": [
                {"title": b64("Evening News"), "description": b64("Headlines"), "start_timestamp": str(now - 600), "stop_timestamp": str(now + 1800)},
                {"title": b64("Late Show"), "description": b64(""), "start_timestamp": str(now + 1800), "stop_timestamp": str(now + 5400)}]})
        return self.reply({"user_info": {"auth": 1, "status": "Active", "exp_date": "1893456000", "max_connections": "2"}})
ThreadingHTTPServer(("127.0.0.1", 9191), H).serve_forever()
