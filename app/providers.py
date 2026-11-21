"""v3.15 EXTRA SEARCH PROVIDERS + .env + provider health / usage.

Providers (sab ek hi candidate format me – visual_pick inhe score karta hai):
  * SearXNG (apna self-hosted)  – SEARXNG_BASE_URL. Web / image / video. JSON format on hona chahiye.
  * Internet Archive            – free, key nahi. Sirf CC / public-domain licence wali VIDEO (licenseurl jaanch ke).
  * Smithsonian Open Access     – SMITHSONIAN_API_KEY (api.data.gov key). Sirf CC0 photo.
  * Brave                       – sources.py me (BRAVE_API_KEY_1 / BRAVE_API_KEY_2 bhi chalti hain).
  * NASA / Wikimedia / Pixabay / Pexels – purane (sources.py).
Google: koi authorized Google search integration nahi hai -> Google search NAHI hoti (scraping nahi).

Har provider ka hisaab: temp/provider_usage.json (is mahine kitni requests, kitni fail, aakhri galti). Galti pe
provider kuch der ke liye band (429/403/CAPTCHA/galat JSON) – video nahi rukti, agla provider chalta hai.
Keys kabhi log / Telegram me nahi jaati.
"""
import json, re, threading, time
from datetime import datetime
from pathlib import Path
from common import TOOL, log

S = None
TIMEOUT = 20
_LOCK = threading.Lock()
STATS = {}            # provider -> {req, ok, fail, last_error, down_until}
USAGE_FILE = TOOL / "temp" / "provider_usage.json"
ENV_MAP = {"BRAVE_API_KEY_1": "BRAVE", "BRAVE_API_KEY_2": "BRAVE2", "BRAVE_API_KEY": "BRAVE",
           "SEARXNG_BASE_URL": "SEARXNG", "SMITHSONIAN_API_KEY": "SMITHSONIAN", "PIXABAY_API_KEY": "PIXABAY",
           "PEXELS_API_KEY": "PEXELS", "GEMINI_API_KEY": "GEMINI", "YOUTUBE_API_KEY": "YOUTUBE",
           "GROQ_API_KEY": "GROQ", "OPENROUTER_API_KEY": "OPENROUTER", "TELEGRAM_BOT_TOKEN": "TELEGRAM"}


def _s():
    global S
    if S is None:
        import requests
        S = requests.Session(); S.headers["User-Agent"] = "VG-VideoTool/3.15 (+educational shorts)"
    return S


# ------------------------------------------------------------------ .env
def read_env(dirs=None):
    """.env (KEY=VALUE) padho -> tool ke naam (BRAVE, BRAVE2, SEARXNG, SMITHSONIAN ...). Value kabhi log nahi."""
    out = {}
    cands = [Path(d) / ".env" for d in (dirs or [])] + [TOOL / ".env"]
    for p in cands:
        try:
            if not p.exists(): continue
            for ln in p.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln: continue
                k, v = ln.split("=", 1)
                k = k.strip().upper().replace("EXPORT ", ""); v = v.strip().strip('"').strip("'")
                if not v: continue
                name = ENV_MAP.get(k)
                if name and name not in out: out[name] = v
        except Exception:
            continue
    return out


# ------------------------------------------------------------------ health / usage
def _st(name):
    return STATS.setdefault(name, {"req": 0, "ok": 0, "fail": 0, "last_error": "", "down_until": 0.0})


def up(name):
    return time.time() >= _st(name)["down_until"]


def mark(name, ok, err="", down=0):
    with _LOCK:
        st = _st(name); st["req"] += 1
        if ok: st["ok"] += 1
        else:
            st["fail"] += 1; st["last_error"] = str(err)[:160]
            if down: st["down_until"] = time.time() + down
    if not ok and down:
        log(f"   ⚠️ {name}: {str(err)[:100]} – {int(down/60) or 1} min ke liye band, baaki providers chalenge", show=False)


def save_usage():
    """Mahine ka hisaab (Brave ~ $5 / 1000 request -> andaza)."""
    try:
        mon = datetime.now().strftime("%Y-%m")
        data = json.loads(USAGE_FILE.read_text(encoding="utf-8")) if USAGE_FILE.exists() else {}
        m = data.setdefault(mon, {})
        for k, v in STATS.items():
            row = m.setdefault(k, {"req": 0, "ok": 0, "fail": 0})
            row["req"] += v["req"]; row["ok"] += v["ok"]; row["fail"] += v["fail"]
            if v["last_error"]: row["last_error"] = v["last_error"]
        brave = sum(r["req"] for k, r in m.items() if k.startswith("brave"))
        m["_brave_dollar_estimate"] = round(brave * 0.005, 2)
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        USAGE_FILE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        for v in STATS.values(): v.update(req=0, ok=0, fail=0)
        return m
    except Exception:
        return {}


def health_line():
    parts = []
    for k, v in sorted(STATS.items()):
        if not v["req"] and not v["fail"]: continue
        parts.append(f"{k} {v['ok']}/{v['req']}" + ("" if up(k) else " (band)"))
    return ", ".join(parts) or "koi request nahi"


# ------------------------------------------------------------------ SearXNG
YT = re.compile(r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})")


def searxng(q, base, kind="videos", n=10):
    """kind = videos | images. Return candidates."""
    name = "searxng"
    if not (base and q) or not up(name): return []
    try:
        r = _s().get(base.rstrip("/") + "/search", params={"q": q, "format": "json", "categories": kind,
                                                          "safesearch": 1}, timeout=TIMEOUT)
        if r.status_code in (403, 429):
            mark(name, False, f"HTTP {r.status_code} (JSON format band / rate limit?)", 600); return []
        if r.status_code != 200:
            mark(name, False, f"HTTP {r.status_code}", 120); return []
        try:
            res = r.json().get("results") or []
        except Exception:
            mark(name, False, "JSON nahi aaya (settings.yml me formats: [html, json] karo)", 1800); return []
        mark(name, True)
    except Exception as e:
        mark(name, False, e, 300); return []
    out = []
    for x in res[:n * 2]:
        url = x.get("url") or ""
        if kind == "videos":
            m = YT.search(url)
            if not m: continue                     # sirf YouTube link (yt-dlp se kat sakta hai)
            out.append({"kind": "video", "yt": m.group(1), "url": url, "title": x.get("title") or "",
                        "channel": x.get("author") or "", "thumb": x.get("thumbnail") or
                        f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg", "duration_seconds": 0,
                        "provider": "searxng", "credit": f"{(x.get('title') or '')[:70]} ({url})"})
        else:
            img = x.get("img_src") or ""
            if not img.startswith("https://"): continue
            out.append({"kind": "image", "url": img, "thumb": x.get("thumbnail_src") or img, "title": x.get("title") or "",
                        "provider": "searxng", "credit": f"via SearXNG – {url or img}"})
        if len(out) >= n: break
    return out


# ------------------------------------------------------------------ Internet Archive
def _ok_lic(lic):
    l = (lic or "").lower()
    if not l: return False
    if "publicdomain" in l or "/zero/" in l or "cc0" in l: return True
    if "creativecommons.org/licenses/" in l:
        return not any(x in l for x in ("-nc", "-nd", "-sa", "/nc", "/nd", "/sa"))
    return False


def archive_videos(q, n=6):
    """Internet Archive: sirf movies + CC/PD licence. File = chhoti mp4 (h.264)."""
    name = "archive"
    if not q or not up(name): return []
    try:
        r = _s().get("https://archive.org/advancedsearch.php", params={
            "q": f"({q}) AND mediatype:(movies) AND licenseurl:*", "fl[]": ["identifier", "title", "licenseurl", "downloads"],
            "rows": 12, "sort[]": "downloads desc", "output": "json"}, timeout=TIMEOUT)
        docs = (r.json().get("response") or {}).get("docs") or [] if r.status_code == 200 else []
        mark(name, r.status_code == 200, f"HTTP {r.status_code}", 0 if r.status_code == 200 else 300)
    except Exception as e:
        mark(name, False, e, 300); return []
    out = []
    for d in docs:
        if len(out) >= n: break
        if not _ok_lic(d.get("licenseurl")): continue
        ident = d.get("identifier")
        try:
            md = _s().get(f"https://archive.org/metadata/{ident}", timeout=TIMEOUT).json()
        except Exception:
            continue
        if (md.get("metadata") or {}).get("access-restricted-item") in ("true", True): continue
        files = [f for f in md.get("files") or [] if str(f.get("name", "")).lower().endswith(".mp4")
                 and int(f.get("size") or 0) < 400_000_000]
        files.sort(key=lambda f: ("h.264" not in str(f.get("format", "")).lower(), int(f.get("size") or 0)))
        if not files: continue
        f = files[0]
        url = f"https://archive.org/download/{ident}/{f['name']}"
        out.append({"kind": "video", "url": url, "thumb": f"https://archive.org/services/img/{ident}",
                    "title": d.get("title") or ident, "provider": "archive",
                    "duration_seconds": float(f.get("length") or 0) if str(f.get("length") or "").replace(".", "").isdigit() else 0,
                    "credit": f"Internet Archive – {(d.get('title') or ident)[:70]} ({d.get('licenseurl')}) https://archive.org/details/{ident}"})
    return out


# ------------------------------------------------------------------ Smithsonian Open Access
def smithsonian_images(q, key, n=6):
    name = "smithsonian"
    if not (q and key) or not up(name): return []
    try:
        r = _s().get("https://api.si.edu/openaccess/api/v1.0/search",
                     params={"q": f"{q} AND online_media_type:\"Images\"", "rows": 20, "api_key": key}, timeout=TIMEOUT)
        if r.status_code in (401, 403):
            mark(name, False, f"HTTP {r.status_code} (SMITHSONIAN_API_KEY galat?)", 3600); return []
        if r.status_code == 429:
            mark(name, False, "HTTP 429 limit", 900); return []
        rows = ((r.json().get("response") or {}).get("rows") or []) if r.status_code == 200 else []
        mark(name, r.status_code == 200, f"HTTP {r.status_code}", 0 if r.status_code == 200 else 300)
    except Exception as e:
        mark(name, False, e, 300); return []
    out = []
    for row in rows:
        c = row.get("content") or {}
        dn = c.get("descriptiveNonRepeating") or {}
        for m in ((dn.get("online_media") or {}).get("media") or []):
            if str((m.get("usage") or {}).get("access", "")).upper() != "CC0": continue
            url = m.get("content") or ""
            if not url.startswith("http"): continue
            out.append({"kind": "image", "url": url, "thumb": m.get("thumbnail") or url,
                        "title": row.get("title") or "", "provider": "smithsonian",
                        "credit": f"Smithsonian Open Access (CC0) – {(row.get('title') or '')[:70]}"})
            break
        if len(out) >= n: break
    return out


PRIORITY = {"subject pool": 0.02, "youtube search": 0.02, "brave video": 0.012, "searxng video": 0.01,
            "archive video": 0.008, "nasa": 0.006, "smithsonian": 0.004, "wikimedia": 0.002, "brave photo": 0.002,
            "searxng photo": 0.001, "pixabay video": 0.0, "pexels video": 0.0,
            "inaturalist": 0.006, "nasa photo": 0.004, "wikimedia video": 0.004, "pixabay photo": 0.0}   # v3.19
