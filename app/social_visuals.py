"""v3.46 MULTI-SOURCE SOCIAL & ARCHIVAL VISUAL HARVESTER.

Expands VideoTool beyond YouTube/Pixabay by discovering relevant:
  1) Pinterest high-res editorial/cinematic images (no login required)
  2) Public Twitter/X & Pinterest short 4.5s muted B-roll clips via yt-dlp (14s timeout)
  3) Internet Archive (archive.org) public documentary/historical MP4 footage
All candidates pass through VideoTool existing AI Aankh / Gemini relevance scoring!
"""
import re
import subprocess
import urllib.parse
from pathlib import Path
import requests
from common import log

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
_S = requests.Session()
_S.headers.update({"User-Agent": _UA})


def _ddg_links(query, limit=6):
    """Lightweight DuckDuckGo HTML search returning result URLs (zero API key)."""
    try:
        r = _S.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            timeout=8,
        )
        if not r.ok:
            return []
        urls = []
        for m in re.finditer(r"uddg=([^&\x22\x27]+)", r.text):
            u = urllib.parse.unquote(m.group(1))
            if u.startswith("http") and u not in urls:
                urls.append(u)
            if len(urls) >= limit:
                break
        return urls
    except Exception:
        return []


def archive_videos(q, limit=4):
    """Search Internet Archive (archive.org) for public documentary/historical MP4 clips."""
    out = []
    try:
        params = {
            "q": f"({q}) AND mediatype:movies AND format:MPEG4",
            "fl[]": ["identifier", "title"],
            "rows": str(limit),
            "page": "1",
            "output": "json",
        }
        r = _S.get("https://archive.org/advancedsearch.php", params=params, timeout=8)
        docs = (r.json().get("response") or {}).get("docs") or [] if r.ok else []
        for d in docs[:limit]:
            ident = d.get("identifier")
            if not ident:
                continue
            mr = _S.get(f"https://archive.org/metadata/{ident}/files", timeout=7)
            files = (mr.json().get("result") or []) if mr.ok else []
            mp4 = next(
                (f for f in files if str(f.get("name", "")).lower().endswith(".mp4")
                 and int(f.get("size") or 0) < 12_000_000),
                None,
            )
            if mp4:
                url = f"https://archive.org/download/{ident}/{urllib.parse.quote(mp4['name'])}"
                out.append({
                    "kind": "video",
                    "url": url,
                    "thumb": f"https://archive.org/services/img/{ident}",
                    "tags": str(d.get("title") or q)[:120],
                    "credit": f"Internet Archive – {ident}",
                })
    except Exception as e:
        log(f"  archive.org skip: {e}", show=False)
    return out


def pinterest_images(q, limit=6):
    """Discover high-res Pinterest images (i.pinimg.com) matching query."""
    out = []
    seen = set()
    try:
        # Step 1: find pin pages via DDG
        pin_urls = _ddg_links(f"site:pinterest.com {q}", limit=limit)
        if not pin_urls:                                   # v3.67: cloud pe DDG khaali -> Brave / DDG lite
            try: pin_urls = find_pages(q.replace(" video", ""), "pin", limit=limit)
            except Exception: pin_urls = []
        for pu in pin_urls:
            if len(out) >= limit:
                break
            try:
                pr = _S.get(pu, timeout=6)
                if not pr.ok:
                    continue
                imgs = re.findall(r"https://i\.pinimg\.com/(?:originals|736x|564x)/[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp)", pr.text)
                for img in imgs:
                    if img in seen:
                        continue
                    seen.add(img)
                    # Upgrade 564x -> 736x when available
                    hi = img.replace("/564x/", "/736x/")
                    out.append({
                        "kind": "image",
                        "url": hi,
                        "thumb": img,
                        "tags": f"pinterest {q}",
                        "credit": "Pinterest",
                    })
                    break
            except Exception:
                continue
    except Exception as e:
        log(f"  pinterest image skip: {e}", show=False)
    return out


# ======================================================================================================
# v3.67 CLOUD-READY Twitter/X + Pinterest VIDEO (B-roll / green screen / reaction) – yt-dlp se
#   * Page dhoondhna: Brave web search (key ho to) -> DuckDuckGo html -> DuckDuckGo lite (cloud pe ek band ho
#     to agla). Pehle sirf DDG tha jo GitHub server se aksar khaali aata tha.
#   * Clip: yt-dlp -J (title, thumbnail, direct URL) -> ffmpeg se sirf 6 sec ka tukda (poori video nahi).
#     X ke liye aapki X_COOKIES (GitHub Secret) – bina login X aksar video nahi deta.
#   * Bina video ke kharaab baar-baar koshish nahi: platform 4 baar block -> us video me band (samay bache).
#   * Har clip CLIP (AI aankh) se line ke saath jaanchi jaati hai (visual_pick) – random nahi lagti.
# ======================================================================================================
import json as _json, os as _os, sys as _sys, threading as _th, time as _time

STATUS = {"x": {"n": 0, "fail": 0, "blocked": 0, "why": ""}, "pin": {"n": 0, "fail": 0, "blocked": 0, "why": ""},
          "search": {}, "t0": None}
LIMITS = {"budget": 360.0, "max": 24, "secs": 6.0}
_SL = _th.Lock()
_X_RE = re.compile(r"https?://(?:www\.|mobile\.)?(?:x|twitter)\.com/([A-Za-z0-9_]{1,20})/status/(\d{5,25})")
_PIN_RE = re.compile(r"https?://(?:[a-z]{2,3}\.)?pinterest\.[a-z.]{2,6}/pin/([\w-]{5,40})")
_BLOCK = ("login", "log in", "sign in", "not a bot", "rate-limit", "rate limit", "http error 429", "http error 403",
          "requires authentication", "nsfw", "use --cookies")


def _search_mark(eng, ok, why=""):
    with _SL:
        d = STATUS["search"].setdefault(eng, {"ok": 0, "fail": 0, "why": ""})
        d["ok" if ok else "fail"] += 1
        if why: d["why"] = why[:120]


def _brave_web(query, limit=10):
    try:
        import sources
        keys = list(getattr(sources, "BRAVE_KEYS", []) or [])
    except Exception:
        keys = []
    if not keys:
        return []
    for k in keys:
        try:
            r = _S.get("https://api.search.brave.com/res/v1/web/search", params={"q": query[:300], "count": min(20, limit)},
                       headers={"X-Subscription-Token": k, "Accept": "application/json"}, timeout=12)
            if r.status_code != 200:
                _search_mark("brave", False, f"HTTP {r.status_code}"); continue
            res = ((r.json() or {}).get("web") or {}).get("results") or []
            _search_mark("brave", True)
            return [x.get("url") for x in res if x.get("url")]
        except Exception as e:
            _search_mark("brave", False, str(e))
    return []


def _ddg_lite(query, limit=8):
    try:
        r = _S.post("https://lite.duckduckgo.com/lite/", data={"q": query}, timeout=10)
        if not r.ok:
            _search_mark("ddg-lite", False, f"HTTP {r.status_code}"); return []
        urls = []
        for m in re.finditer(r'href="(https?://[^"]+)"', r.text):
            u = m.group(1)
            if "duckduckgo.com" in u: continue
            if "uddg=" in u: u = urllib.parse.unquote(u.split("uddg=", 1)[1].split("&", 1)[0])
            if u not in urls: urls.append(u)
            if len(urls) >= limit: break
        _search_mark("ddg-lite", bool(urls), "" if urls else "khaali (shayad bot-check)")
        return urls
    except Exception as e:
        _search_mark("ddg-lite", False, str(e)); return []


GEM = {"on": True, "calls": 0, "max": 18, "cache": {}, "why": ""}   # v3.69: Gemini Google Search se post dhoondhna
_KEYS = {"v": None}


def _gem_key():
    if _KEYS["v"] is None:
        try:
            from common import read_keys
            _KEYS["v"] = read_keys().get("GEMINI") or ""
        except Exception:
            _KEYS["v"] = ""
    return _KEYS["v"]


def _gemini_pages(q):
    """v3.69: aapki Gemini key ka Google Search (grounding) -> X / Pinterest ke ASLI post URLs.
    Cloud pe DuckDuckGo khaali aata hai, Brave card maangta hai – ye bina card ke chalta hai. Sirf wahi URL lete hain
    jo Google Search ke sources me aaye (ya jinhe baad me yt-dlp sach me khol paaye) – banaye hue nahi chalte."""
    q = (q or "").strip()
    if not q: return []
    with _SL:
        if q in GEM["cache"]: return GEM["cache"][q]
        if not GEM["on"] or GEM["calls"] >= GEM["max"]: return []
        GEM["calls"] += 1
    key = _gem_key()
    if not key:
        with _SL: GEM["on"] = False; GEM["why"] = "Gemini key nahi"
        return []
    try:
        import ai
        mods = [m for m in ai.models(key) if "lite" not in m and "preview" not in m][:2]
    except Exception:
        mods = []
    # v3.70: free key pe Google Search sabse pakka 2.5 Flash pe milta hai – naye model pe 429 aaye to ye bhi try
    for fb in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest"):
        if fb not in mods: mods.append(fb)
    mods = [m for m in mods if m not in GEM.get("dead", set())][:4]
    prompt = (f"Search the web for public posts on X (x.com / twitter.com) and on Pinterest that contain a short VIDEO "
              f"clip about: {q}. List the exact post URLs you found in the search results (format "
              f"https://x.com/<user>/status/<id> or https://www.pinterest.com/pin/<id>/), one per line, maximum 10. "
              f"Do not invent URLs.")
    body = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2}}
    urls = []
    for m in mods:
        try:
            r = _S.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                        headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=45)
        except Exception as e:
            _search_mark("gemini", False, str(e)); continue
        if r.status_code == 429:
            _msg = ""
            try: _msg = str((r.json().get("error") or {}).get("message") or "")[:160]
            except Exception: pass
            _search_mark("gemini", False, f"{m}: 429 {_msg[:90]}")
            with _SL:
                GEM.setdefault("dead", set()).add(m)          # sirf ye model band – agla model try
                GEM["why"] = f"Gemini search limit ({m}): {_msg[:110]}"
            continue
        if r.status_code != 200:
            _search_mark("gemini", False, f"HTTP {r.status_code}"); continue
        try:
            c = (r.json().get("candidates") or [{}])[0]
            txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []))
            urls += re.findall(r"https?://[^\s)\]>\"']+", txt)
            for ch in ((c.get("groundingMetadata") or {}).get("groundingChunks") or []):
                w = ch.get("web") or {}
                u, t = w.get("uri") or "", (w.get("title") or "").lower()
                if not u: continue
                if "grounding-api-redirect" in u and any(k in t for k in ("x.com", "twitter", "pinterest")):
                    try:
                        rr = _S.get(u, allow_redirects=False, timeout=8)
                        u = rr.headers.get("Location") or u
                    except Exception:
                        pass
                urls.append(u)
        except Exception as e:
            _search_mark("gemini", False, str(e)); continue
        _search_mark("gemini", True)
        break
    if not any(_X_RE.search(u) or _PIN_RE.search(u) for u in urls):
        urls += _groq_pages(q, prompt)                     # v3.70: Gemini nahi -> Groq (compound) web search
    urls = [u.rstrip(".,;") for u in dict.fromkeys(urls)]
    with _SL: GEM["cache"][q] = urls
    return urls


GROQ_S = {"on": True, "calls": 0, "max": 18}
_AI_CACHE = {}


def _ai_pages(q):
    """Gemini (Google Search) se; wahan kuch na mile / limit -> Groq compound web search. Har query ek hi baar."""
    q = (q or "").strip()
    if q in _AI_CACHE: return _AI_CACHE[q]
    urls = _gemini_pages(q)
    if not any(_X_RE.search(u) or _PIN_RE.search(u) for u in urls) and q not in GEM["cache"]:
        urls = urls + _groq_pages(q, f"Search the web for public posts on X (x.com) and Pinterest that contain a short "
                                     f"VIDEO about: {q}. List the exact post URLs you found, one per line, max 10.")
    _AI_CACHE[q] = urls
    return urls


def _groq_pages(q, prompt):
    """v3.70: aapki FREE Groq key – 'compound' model khud web search karta hai. Sirf URLs nikaalte hain."""
    with _SL:
        if not GROQ_S["on"] or GROQ_S["calls"] >= GROQ_S["max"]: return []
        GROQ_S["calls"] += 1
    try:
        from common import read_keys
        k = read_keys().get("GROQ") or ""
    except Exception:
        k = ""
    if not k:
        return []
    for model in ("groq/compound", "groq/compound-mini", "compound-beta"):
        try:
            r = _S.post("https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
                        timeout=60)
        except Exception as e:
            _search_mark("groq", False, str(e)); continue
        if r.status_code in (400, 404):
            _search_mark("groq", False, f"{model}: HTTP {r.status_code}"); continue
        if r.status_code == 429:
            _search_mark("groq", False, "429 limit")
            with _SL: GROQ_S["on"] = False
            return []
        if r.status_code != 200:
            _search_mark("groq", False, f"HTTP {r.status_code}"); continue
        found = re.findall(r"https?://[^\s)\]>\"'\\]+", r.text.replace("\\/", "/"))      # jawab + search results dono me se
        _search_mark("groq", True)
        return [u for u in found if _X_RE.search(u) or _PIN_RE.search(u)]
    return []


def find_pages(q, kind="x", limit=5):
    """kind = x / pin -> asli post page URLs (status / pin)."""
    rx = _X_RE if kind == "x" else _PIN_RE
    qq = f"site:x.com {q} video" if kind == "x" else f"site:pinterest.com {q} video"
    out = []
    def take(urls):
        for u in urls or []:
            m = rx.search(u or "")
            if not m: continue
            if kind == "x":
                nu = f"https://x.com/{m.group(1)}/status/{m.group(2)}"
            else:
                nu = f"https://www.pinterest.com/pin/{m.group(1)}/"
            if nu not in out: out.append(nu)
    take(_ai_pages(q))                                 # v3.69/70: Gemini Google Search -> Groq web search (bina card)
    if len(out) < limit:
        take(_brave_web(qq, 15))
    if len(out) < limit:
        h = _ddg_links(qq, limit=12)
        _search_mark("ddg-html", bool(h), "" if h else "khaali (shayad bot-check)")
        take(h)
    if len(out) < limit:
        take(_ddg_lite(qq, 12))
    if kind == "x" and len(out) < 2:
        take(_brave_web(f"site:twitter.com {q}", 10))
    return out[:limit]


def _plat(page):
    return "x" if ("x.com/" in page or "twitter.com/" in page) else "pin"


def _over(pl):
    with _SL:
        st = STATUS[pl]
        if st["blocked"] >= 4 and st["n"] == 0: return True
        if STATUS["x"]["n"] + STATUS["pin"]["n"] >= LIMITS["max"]: return True
        if STATUS["t0"] is None: STATUS["t0"] = _time.time()
        return _time.time() - STATUS["t0"] > LIMITS["budget"]


def _ytdlp(args, timeout):
    return subprocess.run([_sys.executable, "-m", "yt_dlp", "--no-warnings", "--no-playlist"] + args,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          stdin=subprocess.DEVNULL)


def grab(page, secs=None):
    """Ek X / Pinterest post -> local chhoti mp4 + metadata dict, ya None."""
    from common import CACHE
    pl = _plat(page)
    if _over(pl): return None
    secs = float(secs or LIMITS["secs"])
    try:
        import cookie_jar
        ck = cookie_jar.for_url(page)
    except Exception:
        ck = []
    d = CACHE / "social"; d.mkdir(parents=True, exist_ok=True)
    import hashlib
    key = hashlib.sha1(page.encode()).hexdigest()[:16]
    dst = d / f"{pl}_{key}.mp4"; meta_f = d / f"{pl}_{key}.json"
    if dst.exists() and dst.stat().st_size > 20000 and meta_f.exists():
        try: return dict(_json.loads(meta_f.read_text(encoding="utf-8")), path=dst)
        except Exception: pass
    try:
        r = _ytdlp(ck + ["-J", "-f", "best[ext=mp4][height<=1080]/best[height<=1080]/best", page], 30)
        if r.returncode != 0 or not r.stdout.strip():
            err = (r.stderr or "").strip()[-200:]
            with _SL:
                STATUS[pl]["fail"] += 1
                if any(k in err.lower() for k in _BLOCK):
                    STATUS[pl]["blocked"] += 1
                    STATUS[pl]["why"] = ("X ne login maanga – GitHub Secret X_COOKIES lagao" if pl == "x"
                                         else "Pinterest ne roka: " + err[-90:])
                elif "no video" in err.lower() or "unsupported" in err.lower():
                    pass                                   # post me video hi nahi – block nahi
                else:
                    STATUS[pl]["why"] = err[-120:]
            return None
        j = _json.loads(r.stdout)
        if j.get("_type") == "playlist" and j.get("entries"):
            j = next((e for e in j["entries"] if e), j)
        url = j.get("url") or ""
        if not url and j.get("requested_formats"):
            url = (j["requested_formats"][0] or {}).get("url") or ""
        dur = float(j.get("duration") or 0)
        if dur and dur < 1.5: return None
        st = 0.0 if dur <= secs * 2 else round(min(dur * 0.15, max(0.0, dur - secs - 0.5)), 1)
        hdr = j.get("http_headers") or {}
        ok = False
        if url:
            cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-rw_timeout", "15000000"]
            if hdr.get("User-Agent"): cmd += ["-user_agent", hdr["User-Agent"]]
            if hdr.get("Referer"): cmd += ["-referer", hdr["Referer"]]
            cmd += ["-ss", f"{st:.2f}", "-i", url, "-t", f"{secs:.2f}", "-an", "-vf", "scale='min(1920,iw)':-2",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dst)]
            try:
                rr = subprocess.run(cmd, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
                ok = rr.returncode == 0 and dst.exists() and dst.stat().st_size > 20000
            except Exception:
                ok = False
        if not ok:                                         # purana tareeka: yt-dlp khud tukda kaate
            out_t = d / f"{pl}_{key}.%(ext)s"
            rr = _ytdlp(ck + ["-f", "best[ext=mp4][height<=1080]/best", "--download-sections",
                              f"*{st:.1f}-{st + secs:.1f}", "--remux-video", "mp4", "-o", str(out_t), page], 45)
            ok = rr.returncode == 0 and dst.exists() and dst.stat().st_size > 20000
        if not ok:
            with _SL: STATUS[pl]["fail"] += 1
            return None
        src = "Twitter/X" if pl == "x" else "Pinterest"
        meta = {"kind": "video", "url": page, "thumb": j.get("thumbnail") or "",
                "title": str(j.get("title") or j.get("description") or "")[:120],
                "channel": str(j.get("uploader") or j.get("uploader_id") or "")[:60], "duration_seconds": dur,
                "upload_date": j.get("upload_date") or "", "social": pl,
                "credit": f"{src}: {str(j.get('uploader') or '')[:40]} ({page})",
                "tags": f"{src} {str(j.get('title') or '')[:80]}"}
        try: meta_f.write_text(_json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        except Exception: pass
        with _SL: STATUS[pl]["n"] += 1
        return dict(meta, path=dst)
    except Exception as e:
        with _SL:
            STATUS[pl]["fail"] += 1; STATUS[pl]["why"] = str(e)[:120]
        return None


def social_clips(q, kinds=("x", "pin"), limit=2):
    """visual_pick ke liye: line ki query -> X / Pinterest ki asli chhoti clips (local path ke saath)."""
    out = []
    dl = _time.time() + 75                                 # visual_pick ka job 90 sec me khatam ho
    for kd in kinds:
        if _over(kd) or _time.time() > dl: continue
        got = 0
        for page in find_pages(q, kd, limit=limit + 1):
            if got >= limit or _time.time() > dl: break
            c = grab(page)
            if c:
                c["q"] = q; out.append(c); got += 1
    return out


def social_videos(q, limit=3):
    """Purana naam (sources.collect) – ab local clip deta hai (sources.download path pehchaanta hai)."""
    return social_clips(q, ("x", "pin"), limit=max(1, limit // 2 + 1))[:limit]


def _ytdlp_direct_video(page_url, timeout=20):
    """Purana helper (compat): direct stream URL."""
    try:
        import cookie_jar
        ck = cookie_jar.for_url(page_url)
    except Exception:
        ck = []
    try:
        p = _ytdlp(ck + ["-g", "-f", "best[ext=mp4][height<=1080]/best[ext=mp4]/best", page_url], timeout)
        if p.returncode == 0:
            for line in p.stdout.splitlines():
                if line.strip().startswith("http"): return line.strip()
    except Exception:
        pass
    return None


def status():
    with _SL:
        return {"x": dict(STATUS["x"]), "pinterest": dict(STATUS["pin"]), "search": {k: dict(v) for k, v in STATUS["search"].items()}}


def reset():
    with _SL:
        for k in ("x", "pin"): STATUS[k].update(n=0, fail=0, blocked=0, why="")
        STATUS["search"].clear(); STATUS["t0"] = None
        GEM.update(on=True, calls=0, why=""); GEM["cache"].clear(); GEM["dead"] = set()
        GROQ_S.update(on=True, calls=0); _AI_CACHE.clear()
