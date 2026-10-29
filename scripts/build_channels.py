#!/usr/bin/env python3
"""Build EYE3's free channel catalogue from the public iptv-org index.

Reads https://iptv-org.github.io/iptv/index.m3u (or --src FILE_OR_URL), keeps only
free public HLS streams, drops adult channels and streams that need special HTTP
headers, probes every stream and keeps the ones that answer with a real playlist.

Writes (into --out, default "iptv"):
  eye3-full.m3u     every working channel, grouped by category, for SS IPTV / Smart STB / TiviMate
  channels.json     the same channels, compact, for the EYE3 Home and TV portal screens
  channels-report.txt  counts by category and country

Standard library only. Never run with credentials; it needs no keys.
"""
import argparse, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

DEFAULT_SRC = "https://iptv-org.github.io/iptv/index.m3u"
UA = "Mozilla/5.0 (EYE3-Vision channel check)"
BAD = re.compile(r"adult|xxx|18\+|porn|erotic|\bsex|playboy|hustler|brazzers|dorcel|penthouse|redlight|private\b", re.I)
CATEGORY_ORDER = ["News", "General", "Entertainment", "Movies", "Series", "Sports", "Music", "Kids", "Documentary",
                  "Lifestyle", "Culture", "Comedy", "Animation", "Business", "Education", "Science", "Religious",
                  "Travel", "Cooking", "Outdoor", "Weather", "Family", "Classic", "Legislative", "Public", "Relax",
                  "Shop", "Auto", "Interactive", "Other"]


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


def alive(url, timeout):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            return b"#EXTM3U" in resp.read(2048)[:200]
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
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default="iptv")
    ap.add_argument("--workers", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--no-probe", action="store_true", help="keep every parsed channel (for local tests)")
    ap.add_argument("--limit", type=int, default=0, help="probe only the first N channels (for local tests)")
    a = ap.parse_args()

    raw = list(parse(read_source(a.src)))
    cleaned = [c for c in (clean(r) for r in raw) if c]
    unique = dedupe(cleaned)
    if a.limit:
        unique = unique[:a.limit]
    print("parsed %d entries, %d usable, %d after dedupe" % (len(raw), len(cleaned), len(unique)), flush=True)
    kept = unique if a.no_probe else probe(unique, a.workers, a.timeout)
    if not a.no_probe and len(kept) < 50:
        print("refusing to publish: only %d channels answered (network problem?)" % len(kept), file=sys.stderr)
        return 1
    data = write_outputs(kept, a.out, a.src if re.match(r"^https?://", a.src) else "local test file")
    print("wrote %d channels (%d categories)" % (data["count"], len(data["categories"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
