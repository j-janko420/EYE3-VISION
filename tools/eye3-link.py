#!/usr/bin/env python3
"""EYE3 Link: a small helper that runs on YOUR computer so EYE3 Home can use your own IPTV account.

Why it exists: a web page on github.io is not allowed to read most IPTV providers directly (CORS) and
cannot play http:// streams from an https:// page. This program fetches things for the page instead.

What it does (all on your machine, nothing is sent anywhere except to the provider you typed in):
  * M3U link        -> the channel list
  * Xtream Codes    -> server + username + password -> the channel list
  * MAG / Stalker   -> portal address + MAC -> the channel list, play links created on demand
  * stream proxy    -> plays those streams in the browser (rewrites HLS playlists)

Safety: it listens on 127.0.0.1 only, answers only EYE3's own pages (see ALLOWED ORIGINS), and every play
link carries a secret token created when it starts, so other websites cannot use it as a proxy.
Use it only with accounts and playlists you are entitled to watch. Standard library only, Python 3.8+.
This program is not a VPN. For channels blocked in your country you can send its traffic through a VPN or
proxy you already have:  python3 eye3-link.py --proxy http://127.0.0.1:PORT   (HTTP proxies only).

Run:   python3 eye3-link.py          (Windows: py eye3-link.py)      Stop: Ctrl+C
"""
import argparse, hashlib, json, re, secrets, ssl, sys, time
import urllib.error as ue
import urllib.parse as up
import urllib.request as ur
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.0"
ALLOWED_ORIGINS = ["https://j-janko420.github.io"]          # more: EYE3_ORIGINS=https://a,https://b
LOCAL_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")
BAD = re.compile(r"adult|xxx|18\+|porn|erotic|\bsex|playboy|hustler|brazzers|dorcel|penthouse|redlight", re.I)
UA_PLAYER = "VLC/3.0.20 LibVLC/3.0.20"
UA_MAG = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
MAX_PLAYLIST = 8 * 1024 * 1024


class LinkError(Exception):
    """An error whose message is safe and useful to show to the viewer."""


STATE = {"token": secrets.token_urlsafe(24), "port": 0, "insecure": False, "proxy": "", "origins": list(ALLOWED_ORIGINS), "sessions": {}}


def ssl_context():
    ctx = ssl.create_default_context()
    if STATE["insecure"]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def open_url(req, timeout):
    """Open a request, through the viewer's own HTTP proxy/VPN (--proxy) when one is set."""
    handlers = [ur.HTTPSHandler(context=ssl_context())]
    if STATE["proxy"]:
        handlers.insert(0, ur.ProxyHandler({"http": STATE["proxy"], "https": STATE["proxy"]}))
    return ur.build_opener(*handlers).open(req, timeout=timeout)


def fetch(url, headers=None, timeout=25, limit=MAX_PLAYLIST):
    """GET a URL; returns (body_bytes, final_url, response_headers)."""
    if not re.match(r"^https?://", url, re.I):
        raise LinkError("Only http:// and https:// addresses are supported.")
    req = ur.Request(url, headers=headers or {"User-Agent": UA_PLAYER})
    try:
        with open_url(req, timeout) as r:
            return r.read(limit), r.geturl(), dict(r.headers)
    except ue.HTTPError as e:
        raise LinkError("The server answered HTTP %d." % e.code)
    except ue.URLError as e:
        raise LinkError("Could not reach the server (%s)." % e.reason)
    except Exception as e:  # timeouts, resets, bad certificates
        raise LinkError("Could not reach the server (%s)." % e)


def fetch_json(url, headers=None):
    body, _, _ = fetch(url, headers)
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        raise LinkError("The server did not answer with the expected data. Check the address.")


def link_url(path, **params):
    params["t"] = STATE["token"]
    return "http://127.0.0.1:%d%s?%s" % (STATE["port"], path, up.urlencode(params))


def stream_url(upstream):
    return link_url("/stream", u=upstream)


# --------------------------------------------------------------------------------------- M3U
def attr(line, name):
    m = re.search(name + r'="([^"]*)"', line)
    return m.group(1) if m else ""


def parse_m3u(text):
    out, info = [], None
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            info = line
        elif line.startswith("#"):
            continue
        elif info is not None and re.match(r"^(https?)://", line, re.I):
            name = info.rsplit(",", 1)[-1].strip() or "Channel"
            group = attr(info, "group-title").strip() or "Other"
            if not BAD.search(name + " " + group):
                # Xtream "...live/user/pass/123.ts" also exists as .m3u8, which browsers can play
                url = re.sub(r"(/live/[^/]+/[^/]+/\d+)\.ts$", r"\1.m3u8", line)
                out.append({"n": name, "c": group, "u": stream_url(url), "l": attr(info, "tvg-logo")})
            info = None
        else:
            info = None
    return out


def channels_from_m3u(url):
    body, _, _ = fetch(url)
    chans = parse_m3u(body.decode("utf-8", "replace"))
    if not chans:
        raise LinkError("That link did not contain any playable channels.")
    return {"channels": chans, "account": {}}


# ------------------------------------------------------------------------------------- Xtream
def xtream_base(server):
    server = server.strip()
    if "://" not in server:
        server = "http://" + server
    p = up.urlparse(server)
    if not p.netloc:
        raise LinkError("Enter the server address, for example http://example.com:8080")
    return "%s://%s" % (p.scheme, p.netloc)


def channels_from_xtream(server, user, password):
    base = xtream_base(server)
    api = "%s/player_api.php?username=%s&password=%s" % (base, up.quote(user, safe=""), up.quote(password, safe=""))
    info = fetch_json(api)
    ui = info.get("user_info") if isinstance(info, dict) else None
    if not isinstance(ui, dict) or str(ui.get("auth", 1)) == "0":
        raise LinkError("The server rejected this username or password.")
    status = str(ui.get("status", "")).strip()
    if status and status.lower() not in ("active",):
        raise LinkError("This account is not active (status: %s)." % status)
    cats = {}
    for c in fetch_json(api + "&action=get_live_categories") or []:
        cats[str(c.get("category_id"))] = str(c.get("category_name") or "Other")
    chans = []
    for s in fetch_json(api + "&action=get_live_streams") or []:
        name = str(s.get("name") or "Channel").strip()
        cat = cats.get(str(s.get("category_id")), "Other")
        if BAD.search(name + " " + cat) or not s.get("stream_id"):
            continue
        direct = "%s/live/%s/%s/%s.m3u8" % (base, up.quote(user, safe=""), up.quote(password, safe=""), s["stream_id"])
        chans.append({"n": name, "c": cat, "u": stream_url(direct), "l": str(s.get("stream_icon") or "")})
    if not chans:
        raise LinkError("The account connected but has no live channels.")
    exp = ui.get("exp_date")
    try:
        exp = time.strftime("%Y-%m-%d", time.gmtime(int(exp))) if exp else ""
    except (TypeError, ValueError):
        exp = ""
    return {"channels": chans, "account": {"status": status or "Active", "expires": exp, "maxConnections": ui.get("max_connections")}}


# ------------------------------------------------------------------------------ MAG / Stalker
def norm_mac(mac):
    m = re.sub(r"[^0-9A-Fa-f]", "", mac or "").upper()
    if len(m) != 12:
        raise LinkError("The MAC address must look like 00:1A:79:AB:CD:EF.")
    return ":".join(m[i:i + 2] for i in range(0, 12, 2))


class Stalker:
    """Talks to a Stalker/Ministra portal the way a MAG set-top box does."""

    def __init__(self, portal, mac):
        self.mac = norm_mac(mac)
        p = up.urlparse(portal.strip() if "://" in portal else "http://" + portal.strip())
        if not p.netloc:
            raise LinkError("Enter the portal address, for example http://portal.example.com/c/")
        self.root = "%s://%s" % (p.scheme, p.netloc)
        path = re.sub(r"/c$", "", p.path.rstrip("/"))
        cands = []
        if path:
            cands += [self.root + path + "/server/load.php", self.root + path + "/portal.php"]
        cands += [self.root + "/stalker_portal/server/load.php", self.root + "/server/load.php", self.root + "/portal.php"]
        self.candidates = list(dict.fromkeys(cands))
        self.api, self.token = None, ""
        self.sn = hashlib.md5(self.mac.encode()).hexdigest()[:13].upper()
        self.dev = hashlib.sha256(self.mac.encode()).hexdigest().upper()

    def headers(self):
        h = {"User-Agent": UA_MAG, "X-User-Agent": "Model: MAG250; Link: WiFi", "Accept": "*/*",
             "Referer": self.root + "/c/", "Cookie": "mac=%s; stb_lang=en; timezone=GMT" % self.mac}
        if self.token:
            h["Authorization"] = "Bearer " + self.token
        return h

    def call(self, api=None, **params):
        params["JsHttpRequest"] = "1-xml"
        url = (api or self.api) + "?" + up.urlencode(params)
        body, _, _ = fetch(url, self.headers())
        try:
            data = json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            raise LinkError("The portal answered with a web page, not data. Check the portal address.")
        return data.get("js") if isinstance(data, dict) else None

    def connect(self):
        last, refused = "", False
        for api in self.candidates:
            try:
                self.token = ""
                js = self.call(api, type="stb", action="handshake", token="", prehash="0")
            except LinkError as e:
                last = str(e)
                continue
            if isinstance(js, dict) and js.get("token"):
                self.api, self.token = api, js["token"]
                break
            refused = True  # a real portal answered, but gave no session
        else:
            if refused:
                raise LinkError("The portal answered but did not accept this MAC address. Check the MAC and that it is active.")
            raise LinkError(last or "Could not find the portal's data service. Check the portal address.")
        self.call(type="stb", action="get_profile", hd="1", ver="ImageDescription: 0.2.18-r14-pub-250; ImageDate: Fri Jan 15 15:20:44 EET 2016; PORTAL version: 5.6.1; API Version: JS API version: 328; STB API version: 134; Player Engine version: 0x566",
                  num_banks="2", sn=self.sn, stb_type="MAG250", client_type="STB", image_version="218", video_out="hdmi",
                  device_id=self.dev, device_id2=self.dev, auth_second_step="1", hw_version="1.7-BD-00", not_valid_token="0",
                  api_signature="262", timestamp=str(int(time.time())))

    def channels(self):
        self.connect()
        genres = {}
        for g in self.call(type="itv", action="get_genres") or []:
            genres[str(g.get("id"))] = str(g.get("title") or "Other")
        js = self.call(type="itv", action="get_all_channels") or {}
        data = js.get("data") if isinstance(js, dict) else None
        if not data:  # some portals only offer the paged list
            data, page, total = [], 1, 1
            while page <= min(total, 60):
                js = self.call(type="itv", action="get_ordered_list", genre="*", force_ch_link_check="", fav="0", sortby="number", hd="0", p=str(page)) or {}
                data += js.get("data") or []
                per = int(js.get("max_page_items") or 14) or 14
                total = -(-int(js.get("total_items") or 0) // per)
                page += 1
        sid = secrets.token_urlsafe(8)
        while len(STATE["sessions"]) >= 20:  # keep memory bounded
            STATE["sessions"].pop(next(iter(STATE["sessions"])))
        STATE["sessions"][sid] = self
        out = []
        for ch in data or []:
            name = str(ch.get("name") or "").strip()
            cat = genres.get(str(ch.get("tv_genre_id")), "Other")
            if not name or not ch.get("cmd") or BAD.search(name + " " + cat):
                continue
            out.append({"n": name, "c": cat, "u": link_url("/stalker/play", sid=sid, cmd=ch["cmd"]),
                        "l": str(ch.get("logo") or ch.get("screenshot_uri") or "")})
        if not out:
            raise LinkError("The portal connected but returned no channels. Is the MAC address active on this portal?")
        return {"channels": out, "account": {"status": "Connected", "mac": self.mac}}

    def create_link(self, cmd):
        for attempt in (0, 1):
            js = self.call(type="itv", action="create_link", cmd=cmd, series="", forced_storage="0", disable_ad="0", download="0")
            got = str(js.get("cmd") if isinstance(js, dict) else "") or ""
            m = re.search(r"(https?://\S+)", got)
            if m:
                return m.group(1)
            if attempt == 0:
                self.connect()  # the session may have expired: start over once
        raise LinkError("The portal refused this channel (account expired or MAC not active?).")


# -------------------------------------------------------------------------------- HTTP server
def origin_allowed(origin):
    return bool(origin) and (origin in STATE["origins"] or bool(LOCAL_ORIGIN.match(origin)))


class Handler(BaseHTTPRequestHandler):
    server_version = "EYE3Link/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if STATE.get("verbose"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # -- helpers
    def origin(self):
        return self.headers.get("Origin") or ""

    def host_ok(self):  # blocks DNS-rebinding tricks
        return self.headers.get("Host", "").split(":")[0].lower() in ("127.0.0.1", "localhost")

    def cors(self):
        o = self.origin()
        if origin_allowed(o):
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Allow-Private-Network", "true")

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, code, message):
        self.send_json(code, {"error": message})

    def token_ok(self, q):
        return secrets.compare_digest(q.get("t", [""])[0], STATE["token"])

    # -- routes
    def do_OPTIONS(self):
        self.send_response(204 if origin_allowed(self.origin()) and self.host_ok() else 403)
        self.cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self.host_ok():
            return self.send_error_json(403, "Not allowed.")
        u = up.urlparse(self.path)
        q = up.parse_qs(u.query)
        try:
            if u.path == "/ping":
                return self.send_json(200, {"ok": True, "name": "EYE3 Link", "version": VERSION, "proxy": bool(STATE["proxy"])})
            if u.path == "/api/hello":
                if not origin_allowed(self.origin()):
                    return self.send_error_json(403, "This page is not allowed to use EYE3 Link.")
                return self.send_json(200, {"ok": True, "token": STATE["token"], "version": VERSION, "proxy": bool(STATE["proxy"])})
            if u.path.startswith("/api/"):
                if not (origin_allowed(self.origin()) or self.token_ok(q)):
                    return self.send_error_json(403, "This page is not allowed to use EYE3 Link.")
                return self.api(u.path, q)
            if u.path == "/stream":
                if not self.token_ok(q):
                    return self.send_error_json(403, "Missing or wrong token.")
                return self.stream(q.get("u", [""])[0])
            if u.path == "/stalker/play":
                if not self.token_ok(q):
                    return self.send_error_json(403, "Missing or wrong token.")
                session = STATE["sessions"].get(q.get("sid", [""])[0])
                if not session:
                    return self.send_error_json(404, "This session ended. Reload the account in EYE3 Home.")
                target = stream_url(session.create_link(q.get("cmd", [""])[0]))
                self.send_response(302)
                self.cors()
                self.send_header("Location", target)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_error_json(404, "Not found.")
        except LinkError as e:
            self.send_error_json(502, str(e))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # never crash the helper because of one bad request
            self.send_error_json(500, "Unexpected problem: %s" % e)

    def api(self, path, q):
        one = lambda k: (q.get(k, [""])[0]).strip()
        if path == "/api/m3u":
            return self.send_json(200, channels_from_m3u(one("url")))
        if path == "/api/xtream":
            if not (one("server") and one("user") and one("pass")):
                raise LinkError("Enter the server, username and password.")
            return self.send_json(200, channels_from_xtream(one("server"), one("user"), one("pass")))
        if path == "/api/stalker":
            if not (one("portal") and one("mac")):
                raise LinkError("Enter the portal address and the MAC address.")
            return self.send_json(200, Stalker(one("portal"), one("mac")).channels())
        self.send_error_json(404, "Unknown request.")

    def stream(self, target):
        if not re.match(r"^https?://", target, re.I):
            raise LinkError("Only http:// and https:// streams are supported.")
        if up.urlparse(target).netloc in ("127.0.0.1:%d" % STATE["port"], "localhost:%d" % STATE["port"]):
            raise LinkError("A stream cannot point back to EYE3 Link.")
        headers = {"User-Agent": UA_PLAYER}
        if self.headers.get("Range"):
            headers["Range"] = self.headers["Range"]
        req = ur.Request(target, headers=headers)
        try:
            resp = open_url(req, 25)
        except ue.HTTPError as e:
            return self.send_error_json(502, "The stream server answered HTTP %d." % e.code)
        except Exception as e:
            return self.send_error_json(502, "Could not reach the stream (%s)." % e)
        with resp:
            ctype = resp.headers.get("Content-Type", "")
            final = resp.geturl()
            head = b""
            is_playlist = "mpegurl" in ctype.lower() or up.urlparse(final).path.lower().endswith(".m3u8")
            if is_playlist:
                body = resp.read(MAX_PLAYLIST)
                if body.lstrip()[:7] == b"#EXTM3U":
                    out = rewrite_playlist(body.decode("utf-8", "replace"), final).encode()
                    self.send_response(200)
                    self.cors()
                    self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)
                    return
                head = body  # not really a playlist: pass it through unchanged
            sized = bool(resp.headers.get("Content-Length")) and not head
            self.send_response(resp.status)
            self.cors()
            for h in ("Content-Type", "Content-Range", "Accept-Ranges"):
                if resp.headers.get(h):
                    self.send_header(h, resp.headers[h])
            if sized:
                self.send_header("Content-Length", resp.headers["Content-Length"])
            else:  # live stream of unknown length: the body ends when the connection closes
                self.send_header("Connection", "close")
                self.close_connection = True
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if head:
                self.wfile.write(head)
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)


def rewrite_playlist(text, base):
    """Point every segment/variant/key line of an HLS playlist back through EYE3 Link."""
    def absolute(ref):
        return stream_url(up.urljoin(base, ref))
    out = []
    for line in text.replace("\r", "").split("\n"):
        s = line.strip()
        if not s:
            out.append(line)
        elif s.startswith("#"):
            out.append(re.sub(r'URI="([^"]+)"', lambda m: 'URI="%s"' % absolute(m.group(1)), line))
        else:
            out.append(absolute(s))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="EYE3 Link: helper for EYE3 Home (runs on this computer only).")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--insecure", action="store_true", help="accept providers with an invalid HTTPS certificate")
    ap.add_argument("--proxy", default="", help="send everything through this HTTP proxy, e.g. http://127.0.0.1:40000 (a VPN app's proxy mode)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--origin", action="append", default=[], help="also allow this web page origin (for your own copy of EYE3)")
    a = ap.parse_args()
    if a.proxy and not re.match(r"^https?://[^/\s]+$", a.proxy):
        print("The proxy must look like http://127.0.0.1:8080 (SOCKS proxies are not supported by this helper).")
        return 1
    STATE.update(port=a.port, insecure=a.insecure, verbose=a.verbose, proxy=a.proxy)
    STATE["origins"] += a.origin
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError as e:
        print("Could not start on port %d (%s). Is EYE3 Link already running? Try --port 8766." % (a.port, e))
        return 1
    srv.daemon_threads = True
    print("EYE3 Link %s is running at http://127.0.0.1:%d" % (VERSION, a.port))
    if a.proxy:
        print("All traffic goes through your proxy: %s" % re.sub(r"//[^@/]*@", "//", a.proxy))
    print("Leave this window open while you watch. Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
