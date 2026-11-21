"""v3.4 YOUTUBE CLIPS – SIRF us insaan / brand ke APNE (official) channel ki chhoti clip.

v3.3 tak: YouTube search me "CarryMinati" likhne pe doosre creators ki videos bhi aa jaati thi (Mikey, Naman...).
v3.4 se:
  1. Pehle us naam ka OFFICIAL channel pakka kiya jaata hai:
       a) youtube_channels.txt (aap khud likh sakte ho:  CarryMinati = @CarryMinati, @CarryisLive)
       b) Wikidata ka "YouTube channel ID" (P2397) – entity ke saath aata hai
       c) YouTube channel search – sirf wo channel jiska NAAM hi wo naam ho (fan / clip channel nahi),
          aur 1 lakh+ subscribers
  2. Un channels ki apni uploads (playlistItems – quota sasta) se pool banta hai. Doosre channel ki video KABHI nahi.
  3. Har line ke English keywords (gaming / roast / old ...) se pool me sabse milti video chuni jaati hai.
  4. Har video max 2 baar, aur har baar alag hissa (time). Pool bada hai to video har baar alag.
Agar official channel bilkul na mile to YouTube clip NAHI lagti (random channel se lene se behtar hai).
Risk (sach): kisi aur ke channel ki clip pe Content ID claim ho sakta hai – zimmedari user ki.
Private / members-only / age-restricted videos NAHI – koi cookies / DRM bypass nahi.
"""
import hashlib, json, random, re, subprocess, sys, threading, time
from pathlib import Path
from common import log, CACHE, TOOL

ON = {"on": True, "secs": 3.5, "max_per_video": 30, "budget": 420.0}   # v3.5: poori video me clip katne ka max time (sec)
T0 = {"t": None}
USED = set()                 # (video_id, time-bucket)
_N = {"n": 0, "fail": 0, "why": ""}
_LOCK = threading.Lock()
_YTDLP = {"ok": None}
BASE = "https://www.googleapis.com/youtube/v3"
CH_FILE = TOOL / "youtube_channels.txt"
POOL = {}                    # naam -> [videos]
CHANNELS = {}                # naam -> [channel ids]
USED_VIDS = {}               # video_id -> kitni baar lagi


def reset():
    with _LOCK:
        USED.clear(); USED_VIDS.clear(); _N.update(n=0, fail=0, why=""); T0["t"] = None


def _over_budget():
    if T0["t"] is None: T0["t"] = time.time()
    return time.time() - T0["t"] > ON["budget"]


def _ytdlp_ok():
    if _YTDLP["ok"] is None:
        try:
            r = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True, text=True, timeout=30)
            _YTDLP["ok"] = r.returncode == 0
        except Exception:
            _YTDLP["ok"] = False
        if not _YTDLP["ok"]:
            _N["why"] = "yt-dlp install nahi – INSTALL_DEPENDENCIES.bat chalao"
            log("   (YouTube clips: yt-dlp install nahi – INSTALL_DEPENDENCIES.bat chalao)")
    return _YTDLP["ok"]


def js_args():
    """v3.13: YouTube ke liye yt-dlp ko JavaScript runtime chahiye. Deno ho to wahi (default); warna Node.js."""
    import shutil
    if shutil.which("deno"): return []
    if shutil.which("node"): return ["--js-runtimes", "node"]
    return []


_URLS = {}                   # v3.15: video_id -> (direct stream url, time) – ek video ke kai hisse, URL ek baar


def _stream_url(vid):
    """yt-dlp se sirf DIRECT video URL (download nahi) – 5-15 sec. 5 ghante tak yaad."""
    with _LOCK:
        u = _URLS.get(vid)
        if u and time.time() - u[1] < 5 * 3600: return u[0]
    try:
        r = subprocess.run([sys.executable, "-m", "yt_dlp"] + js_args() + [
            "--no-playlist", "--no-warnings", "-g", "-f",
            "bv*[height<=1080][vcodec^=avc1]/bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b[height<=1080]/b",
            f"https://www.youtube.com/watch?v={vid}"], capture_output=True, text=True, timeout=22,
            stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        url = (r.stdout or "").strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else ""
        if not url.startswith("http"):
            raise RuntimeError((r.stderr or "url nahi mila").strip()[-160:])
    except Exception as e:
        with _LOCK: _N["why"] = f"stream url: {str(e)[:160]}"
        return None
    with _LOCK: _URLS[vid] = (url, time.time())
    return url


def _cut(vid, start, secs, out):
    """v3.15 FIX (log 15 Nov 18:44: 4 clip '--download-sections ... timed out after 75 seconds' -> 0 YouTube clip
    -> sab Pixabay kachra): ab TEZ tareeka – yt-dlp sirf direct URL deta hai, ffmpeg seedha us second pe jaa ke
    4-5 sec kaatta hai (poori video download nahi, re-encode sirf itne hisse ka). Fail ho to purana tareeka (150 sec)."""
    out = Path(out); dst = out.with_suffix(".mp4")
    if dst.exists() and dst.stat().st_size > 20000:
        return dst
    t0 = time.time()
    url = _stream_url(vid)
    if url:
        try:
            r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-rw_timeout", "15000000",
                                "-ss", f"{max(0.0, start):.2f}", "-i", url, "-t", f"{secs:.2f}", "-an",
                                "-vf", "scale='min(1920,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
                               capture_output=True, text=True, timeout=35, stdin=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and dst.exists() and dst.stat().st_size > 20000:
                log(f"   🎞 YouTube hissa kata ({vid} @{int(start)}s, {time.time()-t0:.0f} sec)", show=False)
                return dst
            with _LOCK: _URLS.pop(vid, None)               # URL purana / band -> agli baar naya
        except Exception as e:
            log(f"   (YouTube tez kaat fail {vid}: {str(e)[:100]})", show=False)
    cmd = [sys.executable, "-m", "yt_dlp"] + js_args() + ["--no-playlist", "--no-warnings", "--quiet", "--no-part",
           "-f", "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b[height<=1080]/b",
           "--download-sections", f"*{start:.1f}-{start + secs:.1f}",
           "--remux-video", "mp4", "-o", str(out.with_suffix(".%(ext)s")), f"https://www.youtube.com/watch?v={vid}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=45, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            err = r.stderr.strip()[-200:]
            with _LOCK:
                _N["fail"] += 1; _N["why"] = err
            log(f"   (YouTube clip {vid} nahi kati: {err})", show=False); return None
    except Exception as e:
        with _LOCK:
            _N["fail"] += 1; _N["why"] = str(e)[:200]
        log(f"   (YouTube clip {vid} error: {str(e)[:160]})", show=False); return None
    for ext in (".mp4", ".webm", ".mkv"):
        p = out.with_suffix(ext)
        if p.exists() and p.stat().st_size > 20000:
            return p
    return None


# ------------------------------------------------------------------ naam / channel pehchaan
def _norm(t):
    return re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())


def _compact(t):
    return _norm(t).replace(" ", "")


OK_SUFFIX = ("", "official", "officials", "officialchannel", "tv", "films", "music", "vlogs", "live", "gaming", "isLive".lower())


def chan_ok(channel_title, name):
    """Channel ka naam hi wo naam ho: 'CarryMinati' ✓, 'CarryMinati Official' ✓ | 'Mikey', 'Carry Fans Club' ✗.
    v3.5 FIX: 'Yash' search pe 'Yash Rajasthani', 'Yash Anand', 'Yash and Hass' (doosre log!) pass ho jaate the,
    kyunki naam sirf 'shuru' me milta tha. Ab naam ke baad sirf 'official / tv / films...' jaisa hi chalega."""
    c, n = _compact(channel_title), _compact(name)
    if len(n) < 4 or not c:
        return False
    if c == n:
        return True
    if c.startswith(n):
        return c[len(n):] in OK_SUFFIX
    if n.startswith(c) and len(c) >= 6:
        return True
    return False


def search_allowed(name):
    """v3.5: ek shabd ka chhota / aam naam (Yash, Salman, Ajay...) – YouTube search pe hazaaron log isi naam ke.
    Aise naam ka channel SIRF youtube_channels.txt ya Wikidata se lo, search se nahi."""
    n = _compact(name)
    return len((name or "").split()) >= 2 or len(n) >= 9


def _api(path, params, key):
    import requests
    try:                                         # v3.13: din bhar yaad (file) – har video pe 429 dobara nahi
        import youtube_sources as _ys
        if path == "search" and _ys.quota_out(): QUOTA["out"] = True
    except Exception:
        _ys = None
    if path == "search" and QUOTA["out"]:
        return None                              # v3.10: search ki daily limit khatam (100 unit / search)
    try:
        r = requests.get(f"{BASE}/{path}", params=dict(params, key=key), timeout=18)
        if r.status_code != 200:
            try: msg = r.json().get("error", {}).get("message", r.text[:150])
            except Exception: msg = r.text[:150]
            log(f"   (YouTube API {path} {r.status_code}: {msg})", show=False)
            if r.status_code in (403, 429) and re.search(r"quota", msg or "", re.I):
                QUOTA["out"] = True              # v3.10: limit khatam – baaki video me YouTube search nahi
                if _ys: _ys.mark_quota_out(msg)
            return None
        return r.json()
    except Exception as e:
        log(f"   (YouTube API {path} error: {e})", show=False)
        return None


def user_channels(name):
    """youtube_channels.txt:  CarryMinati = @CarryMinati, @CarryisLive, UCxxxxxxxx  (naam bina space/case ke milta hai)."""
    out = []
    try:
        if not CH_FILE.exists(): return out
        for ln in CH_FILE.read_text(encoding="utf-8").splitlines():
            if "# auto" in ln: continue                  # v3.15: auto line sirf jaankari – channel_finder (naya niyam) tay karega
            ln = ln.split("#", 1)[0].strip()
            if "=" not in ln: continue
            k, v = ln.split("=", 1)
            if _compact(k) != _compact(name): continue
            for tok in re.split(r"[,\s]+", v.strip()):
                m = re.search(r"(UC[\w-]{22})", tok) or re.search(r"(@[\w.\-]+)", tok)
                if m: out.append(m.group(1))
    except Exception as e:
        log(f"   (youtube_channels.txt padh nahi paya: {e})", show=False)
    return out


def _user_blocked(name):
    """youtube_channels.txt:  Yash = nahi   -> is naam ka koi channel mat lo (auto bhi nahi)."""
    try:
        for ln in (CH_FILE.read_text(encoding="utf-8") if CH_FILE.exists() else "").splitlines():
            ln = ln.split("#", 1)[0].strip()
            if "=" in ln and _compact(ln.split("=", 1)[0]) == _compact(name) and ln.split("=", 1)[1].strip().lower() in ("nahi", "no", "none"):
                return True
    except Exception:
        pass
    return False


def _context_for(name):
    """Script se context: entity ka desc ('Indian actor'), lock ka topic ('Yash film'), film ka naam."""
    try:
        import sources
        bits = []
        for e in list(sources.ENTITY.values()):
            if isinstance(e, dict) and _compact(e.get("label", "")) == _compact(name) and e.get("desc"):
                bits.append(e["desc"]); break
        lk = sources.LOCK_REF.get("v") or {}
        if lk.get("topic"): bits.append(" ".join(w for w in lk["topic"].split() if _compact(w) != _compact(name)))
        return " ".join(bits)[:60]
    except Exception:
        return ""


_NAME_LOCKS = {}


def _name_lock(k):
    with _LOCK:
        return _NAME_LOCKS.setdefault(k, threading.Lock())


def channel_ids(name, key, wd_ids=()):
    with _name_lock("ch:" + _compact(name)):               # v3.5: 4 thread ek saath = 4 baar API (log me 4 line)
        return _channel_ids(name, key, wd_ids)


def _channel_ids(name, key, wd_ids=()):
    k = _compact(name)
    with _LOCK:
        if k in CHANNELS: return CHANNELS[k]
    ids, why = [], ""
    for tok in user_channels(name):
        if tok.startswith("UC"):
            ids.append(tok)
        else:
            j = _api("channels", {"part": "id", "forHandle": tok}, key) or {}
            ids += [x["id"] for x in j.get("items", []) if x.get("id")]
    if ids: why = "youtube_channels.txt"
    blocked = _user_blocked(name)
    if blocked: ids, why = [], "youtube_channels.txt me 'nahi' likha hai"
    if not ids and wd_ids and not blocked:
        ids = [x for x in wd_ids if isinstance(x, str) and x.startswith("UC")]; why = "Wikidata"
    if not ids and not blocked and _ytdlp_ok():
        # v3.13b: AUTO – Wikipedia + yt-dlp search se official channel khud dhoondho (user ko @handle nahi dena)
        try:
            import channel_finder
            ids, why = channel_finder.find(name, _context_for(name))
            why = "auto: " + (why or "nahi mila")
        except Exception as _e:
            log(f"   (auto channel khoj skip: {str(_e)[:100]})", show=False)
    if ids or blocked:
        pass
    elif not search_allowed(name) or not key:
        why = why or "auto khoj me pakka official channel nahi mila"
    elif not ids:
        j = _api("search", {"part": "snippet", "q": name, "type": "channel", "maxResults": 8}, key) or {}
        cand = [(x["snippet"]["channelId"], x["snippet"].get("title", "")) for x in j.get("items", [])
                if chan_ok(x.get("snippet", {}).get("title", ""), name)]
        if cand:
            st = _api("channels", {"part": "statistics", "id": ",".join(c for c, _ in cand)}, key) or {}
            subs = {x["id"]: int((x.get("statistics") or {}).get("subscriberCount", 0) or 0) for x in st.get("items", [])}
            ids = [c for c, _ in sorted(cand, key=lambda c: -subs.get(c[0], 0)) if subs.get(c, 0) >= 100_000][:2]
            why = "YouTube channel search (naam + 1 lakh+ subscribers)"
    ids = list(dict.fromkeys(ids))
    with _LOCK: CHANNELS[k] = ids
    log(f"   🎞 YouTube: '{name}' ke official channel: {len(ids)} ({why or 'nahi mila – YouTube clip nahi lagegi'})")
    return ids


def _uploads_ytdlp(cid, maxn=150):
    """v3.13b: API key / quota ke bina channel ki uploads (yt-dlp flat list)."""
    try:
        r = subprocess.run([sys.executable, "-m", "yt_dlp"] + js_args() + ["--flat-playlist", "-J", "--no-warnings",
                            "--playlist-items", f"1-{maxn}", f"https://www.youtube.com/channel/{cid}/videos"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
                           stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        j = json.loads(r.stdout or "{}") if r.returncode == 0 else {}
    except Exception:
        j = {}
    out = []
    for x in j.get("entries") or []:
        vid = x.get("id")
        if not vid or len(str(vid)) != 11: continue
        out.append({"video_id": vid, "title": x.get("title") or "", "description": (x.get("description") or "")[:600],
                    "channel": j.get("channel") or x.get("channel") or "", "channel_id": cid, "published_at": "",
                    "url": f"https://www.youtube.com/watch?v={vid}", "duration_seconds": float(x.get("duration") or 0),
                    "view_count": int(x.get("view_count") or 0)})
    return out


def _uploads(cid, key, maxn=250):
    """Channel ki apni uploads (playlistItems = 1 quota unit / 50 video). Key / API na chale -> yt-dlp."""
    if not key:
        return _uploads_ytdlp(cid)
    got = _uploads_api(cid, key, maxn)
    return got or _uploads_ytdlp(cid)


def _uploads_api(cid, key, maxn=250):
    pl = "UU" + cid[2:]
    vids, page = [], None
    while len(vids) < maxn:
        p = {"part": "snippet", "playlistId": pl, "maxResults": 50}
        if page: p["pageToken"] = page
        j = _api("playlistItems", p, key)
        if not j: break
        for x in j.get("items", []):
            sn = x.get("snippet") or {}
            vid = (sn.get("resourceId") or {}).get("videoId")
            if vid: vids.append({"video_id": vid, "title": sn.get("title", ""), "description": (sn.get("description") or "")[:600],
                                 "channel": sn.get("channelTitle", ""), "channel_id": cid,
                                 "published_at": sn.get("publishedAt", ""), "url": f"https://www.youtube.com/watch?v={vid}"})
        page = j.get("nextPageToken")
        if not page: break
    from youtube_sources import _duration_seconds
    for b in range(0, len(vids), 50):
        chunk = vids[b:b + 50]
        j = _api("videos", {"part": "contentDetails,statistics,status", "id": ",".join(v["video_id"] for v in chunk)}, key) or {}
        det = {x["id"]: x for x in j.get("items", [])}
        for v in chunk:
            d = det.get(v["video_id"], {})
            v["duration_seconds"] = _duration_seconds((d.get("contentDetails") or {}).get("duration", ""))
            v["view_count"] = int((d.get("statistics") or {}).get("viewCount", 0) or 0)
            v["private"] = (d.get("status") or {}).get("privacyStatus") not in (None, "public")
    return [v for v in vids if not v.get("private")]


def pool(name, api_key, extra_kw=(), wd_ids=()):
    with _name_lock("pool:" + _compact(name)):
        return _pool(name, api_key, extra_kw, wd_ids)


def _pool(name, api_key, extra_kw=(), wd_ids=()):
    key = _compact(name)
    with _LOCK:
        if key in POOL: return POOL[key]
    ck = CACHE / "ytpool" / f"v315_{hashlib.md5(key.encode()).hexdigest()[:16]}.json"   # v3.5: purana (galat) cache nahi
    out = None
    try:
        if ck.exists() and time.time() - ck.stat().st_mtime < 3 * 86400:
            out = json.loads(ck.read_text(encoding="utf-8"))
    except Exception:
        out = None
    if out is None:
        out = []
        for cid in channel_ids(name, api_key, wd_ids):
            out += [v for v in _uploads(cid, api_key) if 12 <= (v.get("duration_seconds") or 0) <= 5400]
        try:
            if out:
                ck.parent.mkdir(parents=True, exist_ok=True); ck.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    with _LOCK: POOL[key] = out
    log(f"   🎞 YouTube: '{name}' ke apne channel ki {len(out)} videos (sirf official – doosre creator nahi)")
    return out


# ------------------------------------------------------------------ line ke hisaab se video
SYN = {
    "gaming": "game games gaming gameplay gamer play playing live stream gta pubg bgmi minecraft valorant fortnite cs counter "
              "free fire horror commentary",
    "game": "game games gaming gameplay gamer play playing live stream gta pubg",
    "commentary": "game gaming gameplay live stream commentary",
    "roast": "roast roasting reply vs tiktok youtube vs trolled exposed react reaction",
    "roasting": "roast roasting reply vs tiktok exposed react reaction",
    "parody": "roast parody bollywood movie trailer spoof funny react",
    "bollywood": "bollywood movie film trailer actor roast parody",
    "trend": "trend trends viral tiktok instagram reels internet roast",
    "trends": "trend trends viral tiktok instagram reels internet roast",
    "music": "song music rap yalgaar vardaan bye pewdiepie",
    "song": "song music rap yalgaar vardaan",
    "growth": "subscribers million celebration milestone play button",
    "subscriber": "subscribers million celebration milestone play button",
    "milestone": "subscribers million celebration milestone play button",
}
OLD = re.compile(r"\b(old|older|early|earliest|first|beginning|started|start|starting|initial|purani|purana|childhood|"
                 r"archive|archived|then|past)\b")


def _kw(text):
    stop = set("a an the of to in on at and or with for is are was his her their this that from into while very "
               "person man woman someone video videos screen showing shows clip clips footage".split())
    return [w for w in _norm(text).split() if len(w) > 2 and w not in stop]


def rank(cands, want_text, name=""):
    want = set(_kw(want_text)) - set(_kw(name))
    for w in list(want):
        want |= set(SYN.get(w, "").split())
    old = bool(OLD.search(_norm(want_text)))
    by_date = sorted(cands, key=lambda r: r.get("published_at") or "9")
    age = {r["video_id"]: k / max(1, len(by_date) - 1) for k, r in enumerate(by_date)}     # 0 = sabse purani
    def score(r):
        t = set(_kw(f"{r['title']} {r.get('channel', '')} {r.get('description', '')[:300]}"))
        s = len(want & t) * 2.0 - USED_VIDS.get(r["video_id"], 0) * 4
        s += min(1.5, (r.get("view_count") or 0) / 10_000_000)
        if old: s += (1 - age.get(r["video_id"], 0.5)) * 4
        return s + random.random() * 0.8                          # har baar thoda alag – same video baar-baar nahi
    return sorted(cands, key=score, reverse=True)


def find(query, api_key, need=1, verify_text="", avoid=(), prefer_channel="", line_kw=(), channel_ids_=()):
    """Return [{'kind':'video','path','credit','src','url'}] – sirf OFFICIAL channel, har baar ALAG video/hissa."""
    if not (ON["on"] and (prefer_channel or query) and _ytdlp_ok()):     # v3.13b: API key ke bina bhi (yt-dlp)
        return []
    with _LOCK:
        if _N["n"] >= ON["max_per_video"]:
            return []
        if _over_budget():                       # v3.5: YouTube clips me 4 min se zyada nahi – video atke nahi
            if not _N.get("budget_logged"):
                _N["budget_logged"] = 1; log("   🎞 YouTube clips ka time poora (4 min) – baaki lines pe photo/stock")
            return []
    import sources
    name = prefer_channel or query
    cands = pool(name, api_key, line_kw[:3] if line_kw else (), channel_ids_)
    if not cands:
        return []
    ranked = rank(cands, " ".join([query, verify_text] + list(line_kw)), name)
    out = []
    d = CACHE / "ytclips"; d.mkdir(parents=True, exist_ok=True)
    tries = 0
    for r in ranked:
        if len(out) >= need or tries >= 3 or _over_budget(): break
        if USED_VIDS.get(r["video_id"], 0) >= 2: continue          # ek video max 2 jagah (alag hisse)
        dur = r["duration_seconds"]
        film = name.startswith("film:")
        fr = (0.25, 0.45, 0.65) if dur < 75 else (0.18, 0.30, 0.42, 0.55, 0.68, 0.80)
        if film: fr = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80)    # v3.8: trailer me har few sec naya shot
        starts = [dur * f for f in fr]; random.shuffle(starts)
        tries += 1
        for st in starts[:(4 if film and verify_text else 2)]:   # v3.8: line ke insaan wala shot milne tak
            st = round(max(1.0, min(dur - ON["secs"] - 1.5, st)), 1)
            key = (r["video_id"], int(st // 10))
            with _LOCK:
                if key in USED: continue
                USED.add(key)
            p = _cut(r["video_id"], st, ON["secs"], d / f"{r['video_id']}_{int(st)}")
            if not p: break                                    # ye video kat hi nahi rahi – agli video
            ok = sources.verify(p, "video", verify_text, (query,), avoid) if verify_text else None
            if ok is False:
                continue
            with _LOCK:
                _N["n"] += 1; USED_VIDS[r["video_id"]] = USED_VIDS.get(r["video_id"], 0) + 1
            out.append({"kind": "video", "path": p, "url": r["url"] + f"&t={int(st)}", "src": "youtube clip",
                        "credit": f"YouTube: \"{r['title'][:70]}\" – {r['channel']} ({r['url']}&t={int(st)})",
                        "yt_title": r["title"][:90], "yt_channel": r.get("channel", "")})
            log(f"   🎞 YouTube clip: [{r.get('channel', '')}] {r['title'][:50]} ({int(st)}s)", show=False)
            break
    return out


def status():
    return dict(_N)



# ------------------------------------------------------------------ v3.6: FILM ka official trailer
BAD_TR = re.compile(r"(reaction|react|review|explained|breakdown|analysis|spoof|parody|roast|fan ?made|edit|status|"
                    r"recreat|vfx breakdown by|scene by|reacts|trailer review)", re.I)
GOOD_TR = re.compile(r"(official|trailer|teaser|glimpse|first look|promo|motion poster|song)", re.I)


QUOTA = {"out": False}        # v3.10: YouTube ki aaj ki search limit khatam -> is video me aur search mat karo


def film_pool(film, key):
    with _name_lock("film:" + _compact((film or {}).get("label", ""))):
        return _film_pool(film, key)


def _film_pool(film, key):
    """Film ki official trailer/teaser videos: Wikidata P1651 pehle; warna YouTube search – sirf wo video jiske title me
    film ka naam + 'official/trailer/teaser' ho, reaction/review NAHI, aur channel 10 lakh+ subscribers ka ho."""
    label = (film or {}).get("label", "")
    pk = _compact("film:" + label)
    with _LOCK:
        if pk in POOL: return POOL[pk]
    ids = list((film or {}).get("trailers") or [])
    why = "Wikidata" if ids else ""
    if not ids and key and label and not QUOTA["out"]:
        base = re.split(r"[:(\-–]", label)[0].strip()
        j = _api("search", {"part": "snippet", "q": f"{label} official trailer", "type": "video", "maxResults": 15}, key) or {}
        cand = []
        for x in j.get("items", []):
            sn = x.get("snippet") or {}; t = sn.get("title", "")
            if _compact(base) and _compact(base) in _compact(t) and GOOD_TR.search(t) and not BAD_TR.search(t):
                cand.append((x["id"]["videoId"], sn.get("channelId", "")))
        if cand:
            st = _api("channels", {"part": "statistics", "id": ",".join(sorted({c for _, c in cand}))}, key) or {}
            subs = {x["id"]: int((x.get("statistics") or {}).get("subscriberCount", 0) or 0) for x in st.get("items", [])}
            ids = [v for v, c in cand if subs.get(c, 0) >= 1_000_000][:4]
            why = "YouTube search (official trailer, 10 lakh+ channel)"
    vids = []
    if not ids and label:                        # v3.13: API limit khatam / key nahi -> yt-dlp search (quota nahi lagta)
        try:
            import youtube_sources as _ys
            base = re.split(r"[:(\-–]", label)[0].strip()
            for x in _ys.ytdlp_search(f"{label} official trailer", 15) + _ys.ytdlp_search(f"{base} teaser glimpse", 10):
                t = x.get("title", "")
                if not (_compact(base) and _compact(base) in _compact(t) and GOOD_TR.search(t) and not BAD_TR.search(t)):
                    continue
                if max(x.get("view_count") or 0, x.get("channel_followers") or 0) < 1_000_000:
                    continue                     # official ka andaza: 10 lakh+ views / followers
                if any(v["video_id"] == x["video_id"] for v in vids): continue
                vids.append({k: x.get(k) for k in ("video_id", "title", "description", "channel", "channel_id", "url",
                                                   "duration_seconds", "view_count")})
            vids = [v for v in vids if 15 <= (v.get("duration_seconds") or 0) <= 600][:4]
            if vids: why = "yt-dlp search (API quota nahi lagi)"
        except Exception as _e:
            log(f"   (film trailer yt-dlp search skip: {_e})", show=False)
    if ids and key:
        from youtube_sources import _duration_seconds
        j = _api("videos", {"part": "snippet,contentDetails,statistics,status", "id": ",".join(ids)}, key) or {}
        for x in j.get("items", []):
            sn = x.get("snippet") or {}
            if (x.get("status") or {}).get("privacyStatus") not in (None, "public"): continue
            vids.append({"video_id": x["id"], "title": sn.get("title", ""), "description": (sn.get("description") or "")[:300],
                         "channel": sn.get("channelTitle", ""), "channel_id": sn.get("channelId", ""),
                         "published_at": sn.get("publishedAt", ""), "url": f"https://www.youtube.com/watch?v={x['id']}",
                         "duration_seconds": _duration_seconds((x.get("contentDetails") or {}).get("duration", "")),
                         "view_count": int((x.get("statistics") or {}).get("viewCount", 0) or 0)})
        vids = [v for v in vids if 15 <= (v.get("duration_seconds") or 0) <= 600]
    with _LOCK: POOL[pk] = vids
    log(f"   🎬 '{label}' ke official trailer: {len(vids)} ({why or 'nahi mile'})")
    return vids


def film_clip(film, key, line_kw=(), verify_text="", avoid=()):
    """Ek line ke liye film ke trailer ka ALAG hissa (har video max 2 baar, har baar alag time).
    v3.8: verify_text = is line ka insaan/cheez (jaise 'Lord Rama with bow'), avoid = script ke DOOSRE kirdaar
    (jaise 'Ravana') – AI aankh clip ke 3 frame dekhti hai; Ram ki line pe Ravan wala shot reject."""
    if not film_pool(film, key): return []
    return find("film:" + film.get("label", ""), key, 1, verify_text, tuple(avoid)[:3],
                prefer_channel="film:" + film.get("label", ""), line_kw=tuple(line_kw))
