#!/usr/bin/env python3
"""Build EYE3's free channel catalogue from public, free playlists.

Sources (repeat --src to change them; default: both):
  https://iptv-org.github.io/iptv/index.m3u                    (group-title = category)
  https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8   (group-title = country)
Reads each source, keeps only
free public HLS streams, drops adult channels and streams that need special HTTP
headers, probes every stream (playlist, then its newest video segment) and keeps only the ones that really deliver video.

Writes (into --out, default "iptv"):
  eye3-full.m3u     every working channel, grouped by category, for SS IPTV / Smart STB / TiviMate
  channels.json     the same channels, compact, for the EYE3 Home and TV portal screens
  channels-report.txt  counts by category and country

Standard library only. Never run with credentials; it needs no keys.
"""
import argparse, json, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

DEFAULT_SRCS = ["https://iptv-org.github.io/iptv/index.m3u",
                "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"]
UA = "Mozilla/5.0 (EYE3-Vision channel check)"
BAD = re.compile(r"adult|xxx|18\+|porn|erotic|\bsex|playboy|hustler|brazzers|dorcel|penthouse|redlight|private\b", re.I)
CATEGORY_ORDER = ["News", "General", "Entertainment", "Movies", "Series", "Sports", "Music", "Kids", "Documentary",
                  "Lifestyle", "Culture", "Comedy", "Animation", "Business", "Education", "Science", "Religious",
                  "Travel", "Cooking", "Outdoor", "Weather", "Family", "Classic", "Legislative", "Public", "Relax",
                  "Shop", "Auto", "Interactive", "Other"]


# Free-TV groups its channels by country name; map those names to the two-letter codes used everywhere else.
COUNTRY_CODES = {
    "albania": "AL", "algeria": "DZ", "andorra": "AD", "argentina": "AR", "armenia": "AM", "australia": "AU", "austria": "AT",
    "azerbaijan": "AZ", "bahrain": "BH", "bangladesh": "BD", "belarus": "BY", "belgium": "BE", "bolivia": "BO",
    "bosnia and herzegovina": "BA", "brazil": "BR", "bulgaria": "BG", "canada": "CA", "chile": "CL", "china": "CN",
    "colombia": "CO", "costa rica": "CR", "croatia": "HR", "cuba": "CU", "cyprus": "CY", "czech republic": "CZ", "czechia": "CZ",
    "denmark": "DK", "dominican republic": "DO", "ecuador": "EC", "egypt": "EG", "el salvador": "SV", "estonia": "EE",
    "finland": "FI", "france": "FR", "georgia": "GE", "germany": "DE", "greece": "GR", "guatemala": "GT", "honduras": "HN",
    "hong kong": "HK", "hungary": "HU", "iceland": "IS", "india": "IN", "indonesia": "ID", "iran": "IR", "iraq": "IQ",
    "ireland": "IE", "israel": "IL", "italy": "IT", "japan": "JP", "jordan": "JO", "kazakhstan": "KZ", "kenya": "KE",
    "kosovo": "XK", "kuwait": "KW", "latvia": "LV", "lebanon": "LB", "libya": "LY", "lithuania": "LT", "luxembourg": "LU",
    "malaysia": "MY", "malta": "MT", "mexico": "MX", "moldova": "MD", "montenegro": "ME", "morocco": "MA", "nepal": "NP",
    "netherlands": "NL", "new zealand": "NZ", "nicaragua": "NI", "nigeria": "NG", "north macedonia": "MK", "macedonia": "MK",
    "norway": "NO", "oman": "OM", "pakistan": "PK", "palestine": "PS", "panama": "PA", "paraguay": "PY", "peru": "PE",
    "philippines": "PH", "poland": "PL", "portugal": "PT", "puerto rico": "PR", "qatar": "QA", "romania": "RO", "russia": "RU",
    "saudi arabia": "SA", "serbia": "RS", "singapore": "SG", "slovakia": "SK", "slovenia": "SI", "south africa": "ZA",
    "south korea": "KR", "spain": "ES", "sri lanka": "LK", "sweden": "SE", "switzerland": "CH", "syria": "SY", "taiwan": "TW",
    "thailand": "TH", "tunisia": "TN", "turkey": "TR", "turkiye": "TR", "ukraine": "UA", "united arab emirates": "AE", "uae": "AE",
    "united kingdom": "UK", "uk": "UK", "united states": "US", "usa": "US", "us": "US", "uruguay": "UY", "uzbekistan": "UZ",
    "venezuela": "VE", "vietnam": "VN", "yemen": "YE",
}
# When a playlist does not give a category, guess one from the channel name.
GUESS = [
    ("News", r"news|noticias|nachrichten|info|actualit|haber|akhbar|24"),
    ("Sports", r"sport|futbol|football|soccer|dazn|eleven|golf|tennis|racing|f1|nba|nfl|ufc"),
    ("Kids", r"kids|kinder|cartoon|junior|baby|disney|nick|nickelodeon|boomerang|toon"),
    ("Music", r"music|mtv|hits|radio|vevo|trace|kiss|rock|jazz"),
    ("Movies", r"movie|cinema|film|kino|cine|hollywood"),
    ("Documentary", r"documentar|discovery|history|nat geo|national geographic|science|wild|planet|nature|viasat"),
    ("Religious", r"relig|church|islam|quran|catholic|jesus|christ|gospel|bible|ewtn|iman|hidayah"),
]
CATEGORY_SET = {c.lower() for c in CATEGORY_ORDER}


def guess_category(name):
    for cat, rx in GUESS:
        if re.search(rx, name, re.I):
            return cat
    return "General"


def read_source(src):
    if re.match(r"^https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    with open(src, encoding="utf-8") as fh:
        return fh.read()


def attr(line, name):
    m = re.search(name + r'="([^"]*)"', line)
    return m.group(1) if m else ""


def parse(text):
    """Yield channel dicts from an iptv-org style M3U."""
    info, opts = None, False
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            info = line
            opts = False
        elif line.startswith("#EXTVLCOPT") or line.startswith("#KODIPROP"):
            opts = True  # the stream needs custom headers/keys: a browser or TV cannot supply them
        elif line.startswith("#"):
            continue
        elif info is not None:
            yield {"info": info, "url": line, "opts": opts}
            info, opts = None, False


def clean(ch):
    info, url = ch["info"], ch["url"]
    if ch["opts"] or not re.match(r"^https?://", url) or ".m3u8" not in url.lower():
        return None
    name = info.rsplit(",", 1)[-1].strip()
    tvg_id, logo = attr(info, "tvg-id"), attr(info, "tvg-logo")
    group = attr(info, "group-title").split(";")[0].strip() or "Other"
    if group.lower() in ("undefined", ""):
        group = "Other"
    if BAD.search(name) or BAD.search(group) or BAD.search(tvg_id) or group.lower() == "xxx":
        return None
    place = ""
    if group.lower() in CATEGORY_SET:
        group = next(c for c in CATEGORY_ORDER if c.lower() == group.lower())
    else:
        # the playlist groups by country (Free-TV), not by category
        place = COUNTRY_CODES.get(group.lower(), "")
        group = "Other" if group.lower() == "other" else guess_category(name)
    if re.search(r"geo-?blocked", name, re.I):
        return None
    q = re.search(r"\((\d{3,4})p\)", name)
    quality = int(q.group(1)) if q else 0
    n247 = bool(re.search(r"not 24/7", name, re.I))
    base = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name).strip() or name
    country = ""
    if tvg_id:
        suffix = tvg_id.split("@")[0].rsplit(".", 1)
        if len(suffix) == 2 and re.fullmatch(r"[a-z]{2}", suffix[1], re.I):
            country = suffix[1].upper()
    country = country or place
    return {"name": base, "cat": group, "country": country, "url": url, "q": quality, "n247": n247,
            "id": tvg_id.split("@")[0], "logo": logo}


def dedupe(channels):
    best = {}
    for c in channels:
        key = (c["name"].lower(), c["country"])
        cur = best.get(key)
        if cur is None or (c["q"], c["url"].startswith("https")) > (cur["q"], cur["url"].startswith("https")):
            best[key] = c
    return list(best.values())


def get(url, timeout, limit):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status not in (200, 206):
            raise ValueError("HTTP %d" % resp.status)
        return resp.read(limit), resp.geturl()


def expired_token(url, now=None):
    """Signed links carry an expiry (…exp=1765449000…); an expired one can never play again."""
    now = now or time.time()
    return any(1_000_000_000 < int(v) < now for v in re.findall(r"(?:[?&~]|^)(?:exp|expires|e)=(\d{10})\b", url))


def alive(url, timeout):
    """True only if the stream really delivers video: playlist -> (variant playlist) -> newest segment."""
    try:
        text, base = get(url, timeout, 400_000)
        text = text.decode("utf-8", "replace")
        if "#EXTM3U" not in text[:200]:
            return False
        lines = [ln.strip() for ln in text.replace("\r", "").split("\n") if ln.strip()]
        for i, ln in enumerate(lines):  # master playlist: follow its first variant
            if ln.startswith("#EXT-X-STREAM-INF"):
                nxt = next((x for x in lines[i + 1:] if not x.startswith("#")), None)
                if not nxt:
                    return False
                text, base = get(urllib.parse.urljoin(base, nxt), timeout, 400_000)
                text = text.decode("utf-8", "replace")
                if "#EXTM3U" not in text[:200]:
                    return False
                lines = [x.strip() for x in text.replace("\r", "").split("\n") if x.strip()]
                break
        segments = [x for x in lines if not x.startswith("#")]
        if not segments:
            return False
        chunk, _ = get(urllib.parse.urljoin(base, segments[-1]), timeout, 2048)
        return len(chunk) > 0
    except Exception:
        return False


def probe(channels, workers, timeout):
    ok, done, t0 = [], 0, time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(alive, c["url"], timeout): c for c in channels}
        for f in as_completed(futs):
            done += 1
            if f.result():
                ok.append(futs[f])
            if done % 500 == 0:
                print("probed %d/%d, %d alive, %ds" % (done, len(channels), len(ok), time.time() - t0), flush=True)
    return ok


def cat_rank(cat):
    return CATEGORY_ORDER.index(cat) if cat in CATEGORY_ORDER else len(CATEGORY_ORDER)


def esc(s):
    return s.replace('"', "'")


def write_outputs(channels, out, source):
    channels.sort(key=lambda c: (cat_rank(c["cat"]), c["cat"], c["country"], c["name"].lower()))
    with open(out + "/eye3-full.m3u", "w", encoding="utf-8") as fh:
        fh.write("#EXTM3U\n")
        for c in channels:
            label = c["name"] + (" (%dp)" % c["q"] if c["q"] else "") + (" [Not 24/7]" if c["n247"] else "")
            fh.write('#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-logo="%s" tvg-country="%s" group-title="%s",%s\n%s\n'
                     % (esc(c["id"]), esc(c["name"]), esc(c["logo"]), c["country"], esc(c["cat"]), esc(label), c["url"]))
    cats = {}
    for c in channels:
        cats[c["cat"]] = cats.get(c["cat"], 0) + 1
    data = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "count": len(channels),
        "categories": cats,
        "channels": [{"n": c["name"], "c": c["cat"], "k": c["country"], "u": c["url"], "q": c["q"],
                      "s": 1 if c["url"].startswith("https") else 0, "x": 1 if c["n247"] else 0} for c in channels],
    }
    with open(out + "/channels.json", "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
    countries = {}
    for c in channels:
        countries[c["country"] or "??"] = countries.get(c["country"] or "??", 0) + 1
    with open(out + "/channels-report.txt", "w", encoding="utf-8") as fh:
        fh.write("EYE3 channel catalogue, %s\nsource: %s\nchannels: %d (https: %d)\n\nby category\n" % (
            data["updated"], source, len(channels), sum(1 for c in channels if c["url"].startswith("https"))))
        for k in sorted(cats, key=lambda k: (cat_rank(k), k)):
            fh.write("  %-16s %d\n" % (k, cats[k]))
        fh.write("\nby country (top 40)\n")
        for k, v in sorted(countries.items(), key=lambda kv: -kv[1])[:40]:
            fh.write("  %-4s %d\n" % (k, v))
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", action="append", help="playlist URL or file; repeat for several (default: iptv-org + Free-TV)")
    ap.add_argument("--out", default="iptv")
    ap.add_argument("--workers", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--no-probe", action="store_true", help="keep every parsed channel (for local tests)")
    ap.add_argument("--limit", type=int, default=0, help="probe only the first N channels (for local tests)")
    a = ap.parse_args()

    sources = a.src or DEFAULT_SRCS
    raw, used = [], []
    for src in sources:
        try:
            part = list(parse(read_source(src)))
        except Exception as exc:  # one source being down must not lose the others
            print("could not read %s: %s" % (src, exc), file=sys.stderr)
            continue
        print("read %d entries from %s" % (len(part), src), flush=True)
        raw.extend(part)
        used.append(src)
    cleaned = [c for c in (clean(r) for r in raw) if c]
    fresh = [c for c in cleaned if not expired_token(c["url"])]
    if len(fresh) != len(cleaned):
        print("dropped %d links whose signed token has expired" % (len(cleaned) - len(fresh)), flush=True)
    unique = dedupe(fresh)
    if a.limit:
        unique = unique[:a.limit]
    print("parsed %d entries, %d usable, %d after dedupe" % (len(raw), len(cleaned), len(unique)), flush=True)
    kept = unique if a.no_probe else probe(unique, a.workers, a.timeout)
    if not a.no_probe and len(kept) < 50:
        print("refusing to publish: only %d channels answered (network problem?)" % len(kept), file=sys.stderr)
        return 1
    data = write_outputs(kept, a.out, " + ".join(x if re.match(r"^https?://", x) else "local test file" for x in used))
    print("wrote %d channels (%d categories)" % (data["count"], len(data["categories"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
