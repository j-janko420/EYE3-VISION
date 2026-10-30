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
If your computer cannot find a provider's address ("getaddrinfo failed") but another device can, start it with
--dns cloudflare (or google): only when the normal lookup fails, it asks that public DNS-over-HTTPS resolver.

Run:   python3 eye3-link.py          (Windows: py eye3-link.py)      Stop: Ctrl+C
"""
import argparse, base64, gzip, hashlib, ipaddress, json, os, re, secrets, socket, ssl, sys, threading, time
import xml.etree.ElementTree as ET
import urllib.error as ue
import urllib.parse as up
import urllib.request as ur
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.6"
ALLOWED_ORIGINS = ["https://j-janko420.github.io"]          # more: EYE3_ORIGINS=https://a,https://b
LOCAL_ORIGIN = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")
BAD = re.compile(r"adult|xxx|18\+|porn|erotic|\bsex|playboy|hustler|brazzers|dorcel|penthouse|redlight", re.I)
UA_PLAYER = "VLC/3.0.20 LibVLC/3.0.20"
UA_MAG = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
MAX_PLAYLIST = 8 * 1024 * 1024          # one HLS playlist
MAX_LIST = 160 * 1024 * 1024            # a whole channel list (big providers send 40 MB and more)
MAX_CHANNELS = 100000                   # rows sent to the page from one list


class LinkError(Exception):
    """An error whose message is safe and useful to show to the viewer."""


STATE = {"token": secrets.token_urlsafe(24), "port": 0, "insecure": False, "proxy": "", "origins": list(ALLOWED_ORIGINS), "sessions": {}, "hdrs": {}}


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


# ------------------------------------------------------------------ optional DNS-over-HTTPS (--dns)
DOH = {"cloudflare": "https://1.1.1.1/dns-query", "google": "https://8.8.8.8/resolve"}   # by IP: no system DNS needed
_real_getaddrinfo = socket.getaddrinfo
_dns_cache = {}


def is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def doh_lookup(host):
    """IPv4 addresses for host from the chosen DNS-over-HTTPS resolver (JSON API). Raises socket.gaierror."""
    hit = _dns_cache.get(host)
    if hit and hit[0] > time.time():
        return hit[1]
    url = STATE["dns"] + "?" + up.urlencode({"name": host, "type": "A"})
    req = ur.Request(url, headers={"Accept": "application/dns-json", "User-Agent": UA_PLAYER})
    try:
        opener = ur.build_opener(ur.ProxyHandler({}), ur.HTTPSHandler(context=ssl_context()))   # direct, never via --proxy
        with opener.open(req, timeout=8) as r:
            data = json.loads(r.read(65536).decode("utf-8", "replace"))
        answers = [a for a in data.get("Answer", []) if a.get("type") == 1 and is_ip(str(a.get("data", "")))]
    except Exception:
        answers = []
    if not answers:
        raise socket.gaierror(socket.EAI_NONAME, "no address found for %s" % host)
    ips = [str(a["data"]) for a in answers]
    ttl = min(max(int(answers[0].get("TTL", 60) or 60), 30), 300)
    _dns_cache[host] = (time.time() + ttl, ips)
    return ips


def _getaddrinfo(host, port, *args, **kw):
    try:
        return _real_getaddrinfo(host, port, *args, **kw)
    except socket.gaierror:
        if not STATE.get("dns") or not isinstance(host, str) or not host or is_ip(host) or host.lower() == "localhost":
            raise
        out = []
        for ip in doh_lookup(host):
            out += _real_getaddrinfo(ip, port, *args, **kw)
        return out


def install_dns(resolver):
    """Use a DNS-over-HTTPS resolver ('cloudflare', 'google' or an https URL) only when the system lookup fails."""
    STATE["dns"] = DOH.get(resolver, resolver) if resolver else ""
    socket.getaddrinfo = _getaddrinfo


def reach_error(reason):
    text = "Could not reach the server (%s)." % reason
    if (isinstance(reason, socket.gaierror) or "getaddrinfo" in str(reason)) and not STATE.get("dns"):
        text += " Your computer cannot find that address. If it works in another app or device, restart EYE3 Link with --dns cloudflare."
    return text


def fetch(url, headers=None, timeout=25, limit=MAX_PLAYLIST):
    """GET a URL; returns (body_bytes, final_url, response_headers)."""
    if not re.match(r"^https?://", url, re.I):
        raise LinkError("Only http:// and https:// addresses are supported.")
    req = ur.Request(url, headers=headers or {"User-Agent": current_ua() or UA_PLAYER})
    try:
        with open_url(req, timeout) as r:
            return r.read(limit), r.geturl(), dict(r.headers)
    except ue.HTTPError as e:
        raise LinkError("The server answered HTTP %d." % e.code)
    except ue.URLError as e:
        raise LinkError(reach_error(e.reason))
    except Exception as e:  # timeouts, resets, bad certificates
        raise LinkError(reach_error(e))


def fetch_json(url, headers=None):
    body, _, _ = fetch(url, headers)
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        raise LinkError("The server did not answer with the expected data. Check the address.")


def link_url(path, **params):
    params["t"] = STATE["token"]
    return "http://127.0.0.1:%d%s?%s" % (STATE["port"], path, up.urlencode(params))


LOCAL = threading.local()      # the request being served: its custom User-Agent (per playlist/account), if the viewer set one


def current_ua():
    return getattr(LOCAL, "ua", "") or ""


def set_ua(raw):
    LOCAL.ua = re.sub(r"[\x00-\x1f\x7f]", "", str(raw or "")).strip()[:300]


HDR_KEYS = {"user-agent": "User-Agent", "referer": "Referer", "referrer": "Referer", "http-referrer": "Referer", "http-referer": "Referer",
            "origin": "Origin", "http-origin": "Origin", "cookie": "Cookie", "http-user-agent": "User-Agent"}


def clean_headers(raw):
    """Only a few request headers a playlist may ask for (user agent, referrer, origin, cookie); no line breaks, bounded."""
    out = {}
    for k, v in (raw or {}).items():
        name = HDR_KEYS.get(str(k).strip().lower())
        v = re.sub(r"[\x00-\x1f\x7f]", "", str(v)).strip()
        if name and v and len(v) <= 400:
            out[name] = v
    return out


def register_headers(hdrs):
    """Remember a channel's headers under a short id so stream links (and their HLS segments) can carry them."""
    if not hdrs:
        return ""
    hid = hashlib.sha1(json.dumps(hdrs, sort_keys=True).encode()).hexdigest()[:12]
    store = STATE["hdrs"]
    if hid not in store and len(store) >= 4000:
        store.pop(next(iter(store)))
    store[hid] = hdrs
    return hid


def base_hid(extra=None):
    """Header id for a stream: the viewer's custom User-Agent (if any) plus the channel's own headers."""
    h = {"user-agent": current_ua()} if current_ua() else {}
    h.update(extra or {})
    return register_headers(clean_headers(h))


def stream_url(upstream, hid=""):
    return link_url("/stream", u=upstream, h=hid) if hid else link_url("/stream", u=upstream)


# ------------------------------------------------------------------------ check from this connection
def classify(exc):
    if isinstance(exc, LinkError):
        m = str(exc)
        if "HTTP 403" in m or "HTTP 451" in m:
            return "blocked"
        if "HTTP 404" in m or "HTTP 410" in m:
            return "dead"
        if "timed out" in m:
            return "timeout"
        return "unreachable"
    return "unreachable"


def probe_stream(url):
    """Does this stream really deliver video from THIS connection? Returns {"ok": bool, "why": str}."""
    stage = "playlist"
    try:
        body, base, _ = fetch(url, timeout=9, limit=400_000)
        text = body.decode("utf-8", "replace")
        if "#EXTM3U" not in text[:200]:
            return {"ok": False, "why": "not a video playlist"}
        lines = [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]
        for i, ln in enumerate(lines):  # master playlist: follow its first variant
            if ln.startswith("#EXT-X-STREAM-INF"):
                nxt = next((x for x in lines[i + 1:] if not x.startswith("#")), None)
                if not nxt:
                    return {"ok": False, "why": "no video segments"}
                stage = "variant"
                body, base, _ = fetch(up.urljoin(base, nxt), timeout=9, limit=400_000)
                text = body.decode("utf-8", "replace")
                if "#EXTM3U" not in text[:200]:
                    return {"ok": False, "why": "not a video playlist"}
                lines = [x.strip() for x in text.replace("\r", "").split("\n") if x.strip()]
                break
        segments = [x for x in lines if not x.startswith("#")]
        if not segments:
            return {"ok": False, "why": "no video segments"}
        stage = "segment"
        chunk, _, _ = fetch(up.urljoin(base, segments[-1]), timeout=9, limit=2048)
        return {"ok": True, "why": ""} if chunk else {"ok": False, "why": "empty video"}
    except Exception as exc:
        return {"ok": False, "why": classify(exc), "stage": stage}


def where_am_i():
    """The country this computer (or its proxy/VPN) appears to be in. Called only when the viewer asks."""
    body, _, _ = fetch(STATE.get("where_url") or "https://ipinfo.io/country", timeout=10, limit=64)
    code = body.decode("utf-8", "replace").strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", code):
        raise LinkError("Could not work out the country.")
    return {"country": code, "viaProxy": bool(STATE["proxy"])}


# --------------------------------------------------------------------------------------- M3U
def attr(line, name):
    m = re.search(name + r'="([^"]*)"', line)
    return m.group(1) if m else ""


def parse_m3u(text, base=""):
    """M3U/M3U8 -> channel rows. Understands #EXTVLCOPT / #EXTHTTP headers, Kodi 'url|User-Agent=..' suffixes,
    relative links (when base is given) and keeps a .ts fallback for Xtream links that also exist as .m3u8."""
    out, info, pend = [], None, {}
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            info, pend = line, {}
        elif line.startswith("#EXTVLCOPT:"):
            k, _, v = line[11:].partition("=")
            pend[k.strip().lower()] = v
        elif line.startswith("#EXTHTTP:"):
            try:
                d = json.loads(line[9:])
                if isinstance(d, dict):
                    pend.update({str(k).lower(): v for k, v in d.items()})
            except ValueError:
                pass
        elif line.startswith("#"):
            continue
        elif info is not None:
            url, _, suffix = line.partition("|")
            url = url.strip()
            if base and not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
                url = up.urljoin(base, url)
            if not re.match(r"^(https?)://", url, re.I):
                info = None
                continue
            hdr = {"user-agent": current_ua()} if current_ua() else {}
            hdr.update(pend)
            if suffix:
                for part in suffix.split("&"):
                    k, _, v = part.partition("=")
                    hdr[k.strip().lower()] = up.unquote(v)
            hid = register_headers(clean_headers(hdr))
            name = info.rsplit(",", 1)[-1].strip() or "Channel"
            group = attr(info, "group-title").strip() or "Other"
            ch = {"n": name, "c": group, "l": attr(info, "tvg-logo")}
            tid = attr(info, "tvg-id").strip()
            if tid:
                ch["i"] = tid[:100]
            as_hls = re.sub(r"(/live/[^/]+/[^/]+/\d+)\.ts$", r"\1.m3u8", url)
            if as_hls != url:   # Xtream "...live/user/pass/123.ts" also exists as .m3u8, which browsers play natively; the .ts stays as fallback
                ch["u"], ch["a"] = stream_url(as_hls, hid), stream_url(url, hid)
            else:
                ch["u"] = stream_url(url, hid)
                if re.search(r"\.ts(\?|$)", urlpath(url), re.I):
                    ch["t"] = 1
            if BAD.search(name + " " + group):
                ch["x"] = True  # adult: EYE3 Home shows it only after the viewer unlocks the hidden Explicit section
            out.append(ch)
            info, pend = None, {}
        else:
            info = None
    return out


def urlpath(u):
    try:
        return up.urlparse(u).path
    except ValueError:
        return ""


def channels_from_m3u(url):
    body, final, _ = fetch(url, limit=MAX_LIST)
    if body[:2] == b"\x1f\x8b":            # a .m3u.gz list
        try:
            body = gzip.decompress(body)
        except OSError:
            raise LinkError("That link looks compressed but could not be unpacked.")
    chans = parse_m3u(body.decode("utf-8-sig", "replace"), base=final)
    if not chans:
        raise LinkError("That link did not contain any playable channels.")
    total = len(chans)
    info = {"total": total}
    head = body[:2000].decode("utf-8-sig", "replace").split("\n", 1)[0]
    epg = attr(head, "x-tvg-url") or attr(head, "url-tvg")
    if epg and re.match(r"^https?://", epg.split(",")[0].strip(), re.I):
        info["epg"] = epg.split(",")[0].strip()
    if total > MAX_CHANNELS:
        chans = chans[:MAX_CHANNELS]
        info["truncated"] = total - MAX_CHANNELS
    return {"channels": chans, "account": info}


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
    allowed = [str(x).lower() for x in (ui.get("allowed_output_formats") or []) if isinstance(x, str)]
    hls_ok = not allowed or "m3u8" in allowed or "hls" in allowed
    for s in fetch_json(api + "&action=get_live_streams") or []:
        name = str(s.get("name") or "Channel").strip()
        cat = cats.get(str(s.get("category_id")), "Other")
        if not s.get("stream_id"):
            continue
        prefix = "%s/live/%s/%s/%s" % (base, up.quote(user, safe=""), up.quote(password, safe=""), s["stream_id"])
        ch = {"n": name, "c": cat, "l": str(s.get("stream_icon") or ""), "e": s["stream_id"]}
        if hls_ok:
            ch["u"], ch["a"] = stream_url(prefix + ".m3u8", base_hid()), stream_url(prefix + ".ts", base_hid())   # HLS first, raw TS as fallback
        else:
            ch["u"], ch["t"] = stream_url(prefix + ".ts", base_hid()), 1                                          # panel offers only TS
        if BAD.search(name + " " + cat):
            ch["x"] = True
        chans.append(ch)
    if not chans:
        raise LinkError("The account connected but has no live channels.")
    exp = ui.get("exp_date")
    try:
        exp = time.strftime("%Y-%m-%d", time.gmtime(int(exp))) if exp else ""
    except (TypeError, ValueError):
        exp = ""
    return {"channels": chans, "account": {"status": status or "Active", "expires": exp, "maxConnections": ui.get("max_connections")}}


# --------------------------------------------------------------------- Xtream movies & series (VOD)
MAX_VOD = 64 * 1024 * 1024
VOD_EXT = re.compile(r"^[A-Za-z0-9]{2,5}$")


def xtream_api(server, user, password):
    base = xtream_base(server)
    return base, "%s/player_api.php?username=%s&password=%s" % (base, up.quote(user, safe=""), up.quote(password, safe=""))


def vod_json(url):
    body, _, _ = fetch(url, limit=MAX_VOD)
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        raise LinkError("The server did not answer with the expected data. Check the address.")


def vod_list(server, user, password, kind):
    """Movies (kind=movie) or series (kind=series) of an Xtream account, in a compact form."""
    base, api = xtream_api(server, user, password)
    movie = kind != "series"
    cats = {}
    for c in vod_json(api + ("&action=get_vod_categories" if movie else "&action=get_series_categories")) or []:
        cats[str(c.get("category_id"))] = str(c.get("category_name") or "Other")
    raw = vod_json(api + ("&action=get_vod_streams" if movie else "&action=get_series"))
    if isinstance(raw, dict):
        if str(raw.get("user_info", {}).get("auth", 1)) == "0":
            raise LinkError("The server rejected this username or password.")
        raw = []
    items = []
    for s in raw or []:
        if not isinstance(s, dict):
            continue
        ident = s.get("stream_id" if movie else "series_id")
        if not ident:
            continue
        name = str(s.get("name") or s.get("title") or "Untitled").strip()
        cat = cats.get(str(s.get("category_id")), "Other")
        item = {"id": ident, "n": name, "c": cat, "l": str((s.get("stream_icon") if movie else s.get("cover")) or "")}
        year = str(s.get("year") or s.get("releaseDate") or s.get("release_date") or "")[:4]
        if year.isdigit():
            item["y"] = year
        rating = str(s.get("rating") or "").strip()
        if rating and rating not in ("0", "0.0"):
            item["r"] = rating[:4]
        if movie:
            ext = str(s.get("container_extension") or "mp4")
            item["e"] = ext if VOD_EXT.match(ext) else "mp4"
        if BAD.search(name + " " + cat):
            item["x"] = True
        items.append(item)
    if not items:
        raise LinkError("This account has no %s." % ("movies" if movie else "series"))
    return {"items": items}


def vod_series_info(server, user, password, series_id):
    base, api = xtream_api(server, user, password)
    info = vod_json(api + "&action=get_series_info&series_id=%s" % up.quote(str(series_id), safe=""))
    if not isinstance(info, dict):
        raise LinkError("The server did not return that series.")
    meta = info.get("info") if isinstance(info.get("info"), dict) else {}
    seasons = {}
    eps = info.get("episodes") or {}
    if isinstance(eps, list):  # some panels send a list of seasons instead of an object
        eps = {str(i + 1): v for i, v in enumerate(eps)}
    for key, rows in eps.items():
        for e in rows or []:
            if not isinstance(e, dict) or not e.get("id"):
                continue
            ext = str(e.get("container_extension") or "mp4")
            einfo = e.get("info") if isinstance(e.get("info"), dict) else {}
            seasons.setdefault(str(e.get("season") or key), []).append({
                "id": e["id"], "num": e.get("episode_num"), "n": str(e.get("title") or "Episode"),
                "e": ext if VOD_EXT.match(ext) else "mp4", "d": str(einfo.get("duration") or "")})
    out = []
    for key in sorted(seasons, key=lambda k: int(k) if str(k).isdigit() else 9999):
        rows = sorted(seasons[key], key=lambda e: int(e["num"]) if str(e.get("num") or "").isdigit() else 9999)
        out.append({"season": key, "episodes": rows})
    if not out:
        raise LinkError("No episodes were listed for this series.")
    return {"title": str(meta.get("name") or ""), "plot": str(meta.get("plot") or "")[:600], "seasons": out}


def b64text(v):
    """Xtream panels send programme titles and descriptions as base64; some send plain text."""
    v = str(v or "")
    try:
        out = base64.b64decode(v, validate=True).decode("utf-8")
        return out if out.isprintable() or "\n" in out else v
    except Exception:
        return v


def xtream_epg(server, user, password, stream_id, limit=4):
    """What is on now and next for one live channel (Xtream get_short_epg)."""
    base, api = xtream_api(server, user, password)
    if not str(stream_id).isdigit():
        raise LinkError("That channel has no valid id.")
    data = vod_json(api + "&action=get_short_epg&stream_id=%s&limit=%d" % (stream_id, limit))
    rows = data.get("epg_listings") if isinstance(data, dict) else []
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        try:
            start, stop = int(r.get("start_timestamp")), int(r.get("stop_timestamp"))
        except (TypeError, ValueError):
            continue
        title = b64text(r.get("title")).strip()
        if title and stop > start:
            out.append({"t": title[:160], "d": b64text(r.get("description")).strip()[:300], "s": start, "e": stop})
    out.sort(key=lambda x: x["s"])
    return {"items": out}


# ------------------------------------------------------------------------------- XMLTV guide
XMLTV_TTL = 30 * 60
XMLTV_MAX_BYTES = 400 * 1024 * 1024
_xmltv_lock = threading.Lock()


def xmltv_time(v):
    """'20261030203000 +0100' -> epoch seconds (UTC)."""
    m = re.match(r"^\s*(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})?\s*([+-]\d{4})?", v or "")
    if not m:
        return None
    y, mo, d, h, mi, se, tz = m.groups()
    try:
        import calendar
        t = calendar.timegm((int(y), int(mo), int(d), int(h), int(mi), int(se or 0)))
    except (ValueError, OverflowError):
        return None
    if tz:
        t -= (1 if tz[0] == "+" else -1) * (int(tz[1:3]) * 3600 + int(tz[3:5]) * 60)
    return t


def xmltv_load(url):
    """Download and read an XMLTV file once (gzip too); keep only programmes from an hour ago to 36 hours ahead."""
    now = time.time()
    with _xmltv_lock:
        hit = STATE.setdefault("epg", {}).get(url)
        if hit and now - hit["t"] < XMLTV_TTL:
            return hit
    if not re.match(r"^https?://", url, re.I):
        raise LinkError("The guide link must start with http:// or https://")
    req = ur.Request(url, headers={"User-Agent": current_ua() or UA_PLAYER})
    try:
        resp = open_url(req, 40)
    except ue.HTTPError as e:
        raise LinkError("The guide server answered HTTP %d." % e.code)
    except Exception as e:
        raise LinkError(reach_error(e).replace("the server", "the guide server", 1))
    progs, names, lo, hi = {}, {}, now - 3600, now + 36 * 3600
    with resp:
        head = resp.read(2)
        stream = _Chain(head, resp)
        if head == b"\x1f\x8b":
            stream = gzip.GzipFile(fileobj=stream)
        capped = _Capped(stream, XMLTV_MAX_BYTES)
        try:
            for ev, el in ET.iterparse(capped, events=("end",)):
                if el.tag == "channel":
                    cid = el.get("id") or ""
                    for dn in el.findall("display-name"):
                        nm = re.sub(r"\W+", " ", (dn.text or "").lower()).strip()
                        if nm and cid:
                            names.setdefault(nm, cid)
                    el.clear()
                elif el.tag == "programme":
                    st, en = xmltv_time(el.get("start")), xmltv_time(el.get("stop"))
                    cid = el.get("channel") or ""
                    if cid and st is not None and en is not None and en > lo and st < hi:
                        title = (el.findtext("title") or "").strip()
                        if title:
                            row = progs.setdefault(cid, [])
                            if len(row) < 40:
                                row.append({"t": title[:160], "d": (el.findtext("desc") or "").strip()[:300], "s": int(st), "e": int(en)})
                    el.clear()
        except ET.ParseError:
            if not progs:
                raise LinkError("That guide file could not be read (is it XMLTV?).")
        except _TooBig:
            pass
    for rows in progs.values():
        rows.sort(key=lambda r: r["s"])
    if not progs:
        raise LinkError("That guide has no programmes for the next hours.")
    entry = {"t": now, "progs": progs, "names": names}
    with _xmltv_lock:
        store = STATE.setdefault("epg", {})
        if len(store) >= 4:
            store.pop(next(iter(store)))
        store[url] = entry
    return entry


class _TooBig(Exception):
    pass


class _Chain:
    """Put already-read bytes back in front of a stream."""
    def __init__(self, head, rest):
        self.head, self.rest = head, rest

    def read(self, n=-1):
        if self.head:
            h, self.head = self.head, b""
            return h + (self.rest.read(n - len(h)) if n and n > len(h) else b"")
        return self.rest.read(n)


class _Capped:
    def __init__(self, src, limit):
        self.src, self.left, self.seen_first = src, limit, False

    def read(self, n=-1):
        data = self.src.read(n)
        if not self.seen_first:
            self.seen_first = True
            if b"<!ENTITY" in data[:20000]:      # entity tricks ("billion laughs") have no place in a TV guide
                raise LinkError("That guide file uses features that are not allowed.")
        self.left -= len(data)
        if self.left < 0:
            raise _TooBig()
        return data


def xmltv_now_next(url, channel_id, name="", limit=8):
    entry = xmltv_load(url)
    cid = channel_id if channel_id in entry["progs"] else entry["names"].get(re.sub(r"\W+", " ", (name or "").lower()).strip(), "")
    rows = entry["progs"].get(cid, [])
    now = time.time()
    rows = [r for r in rows if r["e"] > now][:limit]
    return {"items": rows}


def vod_play_url(server, user, password, kind, ident, ext):
    base = xtream_base(server)
    if not str(ident).isdigit():
        raise LinkError("That title has no valid id.")
    ext = ext if VOD_EXT.match(ext or "") else "mp4"
    path = "series" if kind == "series" else "movie"
    direct = "%s/%s/%s/%s/%s.%s" % (base, path, up.quote(user, safe=""), up.quote(password, safe=""), ident, ext)
    return {"url": stream_url(direct, base_hid()), "ext": ext}


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
        path = p.path.rstrip("/")
        cands = []
        if path.lower().endswith(".php"):      # the viewer pasted the portal's data address itself
            cands.append(self.root + path)
            path = re.sub(r"/[^/]*$", "", path)
        path = re.sub(r"/c$", "", path)
        if path:
            cands += [self.root + path + "/server/load.php", self.root + path + "/portal.php"]
        cands += [self.root + "/stalker_portal/server/load.php", self.root + "/server/load.php", self.root + "/portal.php",
                  self.root + "/c/server/load.php", self.root + "/c/portal.php"]
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
            title = re.search(r"<title[^>]*>([^<]{1,60})", body.decode("utf-8", "replace"), re.I)
            raise LinkError("a web page" + (' titled "%s"' % title.group(1).strip() if title else "") + ", not data")
        return data.get("js") if isinstance(data, dict) else None

    def connect(self):
        tried, refused = [], False
        for api in self.candidates:
            try:
                self.token = ""
                js = self.call(api, type="stb", action="handshake", token="", prehash="0")
            except LinkError as e:
                tried.append("%s: %s" % (up.urlparse(api).path, re.sub(r"^The server answered ", "", str(e)).rstrip(".")))
                continue
            if isinstance(js, dict) and js.get("token"):
                self.api, self.token = api, js["token"]
                break
            refused = True  # a real portal answered, but gave no session
        else:
            if refused:
                raise LinkError("The portal answered but did not accept this MAC address. Check the MAC and that it is active.")
            raise LinkError("Could not find the portal's data service on %s. Tried %s. Use the portal address your box or app uses (often ending in /c/), or paste the portal.php / load.php address itself." % (self.root, "; ".join(tried)))
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
            if not name or not ch.get("cmd"):
                continue
            row = {"n": name, "c": cat, "u": link_url("/stalker/play", sid=sid, cmd=ch["cmd"]),
                   "l": str(ch.get("logo") or ch.get("screenshot_uri") or "")}
            if BAD.search(name + " " + cat):
                row["x"] = True
            out.append(row)
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
                return self.stream(q.get("u", [""])[0], q.get("h", [""])[0])
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
        set_ua(one("ua"))
        if path == "/api/probe":
            return self.send_json(200, probe_stream(one("u")))
        if path == "/api/where":
            return self.send_json(200, where_am_i())
        if path == "/api/m3u":
            return self.send_json(200, channels_from_m3u(one("url")))
        if path == "/api/xtream":
            if not (one("server") and one("user") and one("pass")):
                raise LinkError("Enter the server, username and password.")
            return self.send_json(200, channels_from_xtream(one("server"), one("user"), one("pass")))
        if path == "/api/xmltv":
            if not one("url"):
                raise LinkError("Enter the guide (XMLTV) link.")
            return self.send_json(200, xmltv_now_next(one("url"), one("id"), one("name"), int(one("n") or 8) if one("n").isdigit() else 8))
        if path == "/api/epg":
            if not (one("server") and one("user") and one("pass")):
                raise LinkError("Enter the server, username and password.")
            return self.send_json(200, xtream_epg(one("server"), one("user"), one("pass"), one("id"), min(int(one("n")), 24) if one("n").isdigit() and int(one("n")) > 0 else 4))
        if path in ("/api/vod", "/api/vod/series", "/api/vod/play"):
            if not (one("server") and one("user") and one("pass")):
                raise LinkError("Enter the server, username and password.")
            creds = (one("server"), one("user"), one("pass"))
            if path == "/api/vod":
                return self.send_json(200, vod_list(*creds, kind=one("kind")))
            if path == "/api/vod/series":
                return self.send_json(200, vod_series_info(*creds, series_id=one("id")))
            return self.send_json(200, vod_play_url(*creds, kind=one("kind"), ident=one("id"), ext=one("ext")))
        if path == "/api/stalker":
            if not (one("portal") and one("mac")):
                raise LinkError("Enter the portal address and the MAC address.")
            return self.send_json(200, Stalker(one("portal"), one("mac")).channels())
        self.send_error_json(404, "Unknown request.")

    def stream(self, target, hid=""):
        if not re.match(r"^https?://", target, re.I):
            raise LinkError("Only http:// and https:// streams are supported.")
        if up.urlparse(target).netloc in ("127.0.0.1:%d" % STATE["port"], "localhost:%d" % STATE["port"]):
            raise LinkError("A stream cannot point back to EYE3 Link.")
        headers = {"User-Agent": UA_PLAYER}
        hid = hid or ""
        headers.update(STATE["hdrs"].get(hid, {}) if re.fullmatch(r"[0-9a-f]{12}", hid) else {})
        if self.headers.get("Range"):
            headers["Range"] = self.headers["Range"]
        req = ur.Request(target, headers=headers)
        try:
            resp = open_url(req, 25)
        except ue.HTTPError as e:
            return self.send_error_json(502, "The stream server answered HTTP %d." % e.code)
        except Exception as e:
            return self.send_error_json(502, reach_error(e).replace("the server", "the stream", 1))
        with resp:
            ctype = resp.headers.get("Content-Type", "")
            final = resp.geturl()
            head = b""
            is_playlist = "mpegurl" in ctype.lower() or up.urlparse(final).path.lower().endswith(".m3u8")
            if is_playlist:
                body = resp.read(MAX_PLAYLIST)
                if body.lstrip()[:7] == b"#EXTM3U":
                    out = rewrite_playlist(body.decode("utf-8", "replace"), final, hid if re.fullmatch(r"[0-9a-f]{12}", hid or "") else "").encode()
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


def rewrite_playlist(text, base, hid=""):
    """Point every segment/variant/key line of an HLS playlist back through EYE3 Link (keeping the channel's headers)."""
    def absolute(ref):
        return stream_url(up.urljoin(base, ref), hid)
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
    ap.add_argument("--dns", default="", metavar="cloudflare|google|URL", help="if this computer cannot find a provider's address, ask this DNS-over-HTTPS resolver (only then)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--origin", action="append", default=[], help="also allow this web page origin (for your own copy of EYE3)")
    a = ap.parse_args()
    if a.proxy and not re.match(r"^https?://[^/\s]+$", a.proxy):
        print("The proxy must look like http://127.0.0.1:8080 (SOCKS proxies are not supported by this helper).")
        return 1
    if a.dns and a.dns not in DOH and not re.match(r"^https://[^/\s]+/\S*$", a.dns):
        print("--dns must be cloudflare, google or an https:// DNS-over-HTTPS address.")
        return 1
    STATE.update(port=a.port, insecure=a.insecure, verbose=a.verbose, proxy=a.proxy)
    if a.dns:
        install_dns(a.dns)
    STATE["where_url"] = os.environ.get("EYE3_WHERE_URL", "")  # for tests only
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
    if a.dns:
        print("If your computer cannot find an address, EYE3 Link asks %s (DNS-over-HTTPS)." % (a.dns if a.dns in DOH else "your DNS-over-HTTPS server"))
    print("Leave this window open while you watch. Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
