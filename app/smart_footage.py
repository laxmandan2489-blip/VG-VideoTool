"""v3.19 SMART FOOTAGE (user 17 Nov: "Wikipedia ka kaam main nahi kar sakta – sab AUTOMATIC chahiye; YouTube (yt-dlp)
se footage zyada genuine aati hai, use band mat karo; Pixabay se bhi lo; jahan se bhi mile sahi visual lao").

1) YouTube ka SAHI HISSA: pehle har YouTube clip ka koi bhi random hissa kat-ta tha. Ab:
     a. yt-dlp us video ke subtitles (auto / manual, English ya Hindi) laata hai – download nahi, sirf text
     b. jis second pe aapki line / hint ki cheez BOLI gayi hai (jaise "Chandra"), wo time chuna jaata hai
     c. un time + kuch aur jagah ke 1-1 frame AI aankh (CLIP) se jaanche jaate hain – sabse milta hissa pehle
   Subtitle na mile / internet band -> purana tareeka (koi kami nahi, sirf pehle jaisa).
2) Bharosemand channel (NASA, ESA, Nat Geo, BBC Earth, news, science) ko thoda zyada number; gaana / movie / gaming
   channel ko kam (aur title me song/trailer ho to v3.18 se pehle hi hat jaata hai).
3) iNaturalist (jaanwar / ped-paudhe): asli scientists/logon ki photo, sirf free licence (CC0 / CC-BY / CC-BY-SA).
   Sirf tab jab search me kisi jeev ka naam sach me mile (Voyager pe keeda nahi aayega).
Sab FREE hai, koi key nahi chahiye. Kuch bhi fail ho -> chupchaap purana tareeka.
"""
import re, sys, time, subprocess, threading
from pathlib import Path
from common import log, CACHE

ON = {"segments": True, "inat": True, "max_frames": 4, "sub_timeout": 15}
_LOCK = threading.Lock()
_VID_LOCKS = {}     # v3.24: prevent 3 threads running yt-dlp on the exact same video_id
_SUB_FAILS = [0]    # v3.24: circuit-breaker if YouTube throttles subtitles
_SUBS = {}          # video_id -> [(start, end, text)]
_BEST = {}          # (video_id, text) -> [start times]

STOP = set("the a an of and in on at to for with from by is are was were be been this that these those it its into "
           "over under about after before their there which while where what when your have has had very more most "
           "into onto than then also just only even still such some any each other another same video footage image "
           "illustration animation animated visualization archive archival photo close up closeup aerial drone shot "
           "scene cinematic stock nasa hd 4k".split())

TRUSTED = re.compile(r"(nasa|esa\b|european space|jpl|hubble|webb|chandra|isro|spacex|national geographic|nat geo|"
                     r"bbc|discovery|smithsonian|pbs|nova|science|scientific|reuters|associated press|\bap\b|afp|"
                     r"dw news|al jazeera|wion|ndtv|india today|aaj tak|the hindu|times of india|bloomberg|cnbc|"
                     r"university|institute|museum|wildlife|zoo|forest department|documentar)", re.I)
UNTRUSTED = re.compile(r"(music|records|t-series|zee music|sony music|tips|saregama|speed records|films|pictures|"
                       r"movies|entertainment|gaming|gamer|status|whatsapp|meme|shorts? channel|lyric)", re.I)


def keywords(text):
    """'Voyager 1 radio signal deep space' -> ['voyager', 'radio', 'signal', 'deep', 'space']."""
    ws = [w for w in re.findall(r"[a-z][a-z0-9\-]+", (text or "").lower()) if len(w) > 2 and w not in STOP]
    return list(dict.fromkeys(ws))[:8]


def channel_bonus(c):
    """Bharosemand channel +0.02, gaana/film/gaming channel -0.04, baaki 0."""
    ch = f"{c.get('channel') or ''}"
    if not c.get("yt") or not ch: return 0.0
    if UNTRUSTED.search(ch): return -0.04
    if TRUSTED.search(ch): return 0.02
    return 0.0


# ------------------------------------------------------------------ 1) subtitles
def _ts(t):
    h, m, s = ([0] + [float(x) for x in t.replace(",", ".").split(":")])[-3:]
    return h * 3600 + m * 60 + s


def parse_vtt(txt):
    """WebVTT -> [(start, end, text)] (YouTube auto-subs ke dohraav hata ke)."""
    out, last = [], ""
    for blk in re.split(r"\n\s*\n", txt or ""):
        m = re.search(r"(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)", blk)
        if not m: continue
        body = blk[m.end():].split("\n", 1)[-1] if "\n" in blk[m.end():] else ""
        body = re.sub(r"<[^>]+>", "", body).replace("&nbsp;", " ").strip()
        body = re.sub(r"\s+", " ", body)
        if not body or body == last: continue
        last = body
        try:
            out.append((_ts(m.group(1)), _ts(m.group(2)), body))
        except Exception:
            continue
    return out


def subtitles(vid):
    """yt-dlp se subtitles (download nahi). Cache: temp/cache/ytsubs/<vid>.*.vtt"""
    with _LOCK:
        if vid in _SUBS: return _SUBS[vid]
        if _SUB_FAILS[0] >= 2:
            _SUBS[vid] = []
            return []
        vlock = _VID_LOCKS.setdefault(vid, threading.Lock())
    with vlock:
        with _LOCK:
            if vid in _SUBS: return _SUBS[vid]
            if _SUB_FAILS[0] >= 2:
                _SUBS[vid] = []
                return []
        d = CACHE / "ytsubs"; d.mkdir(parents=True, exist_ok=True)
        have = sorted(d.glob(f"{vid}*.vtt"))
        if not have:
            try:
                import yt_clips
                cmd = [sys.executable, "-m", "yt_dlp"] + yt_clips.js_args() + [
                    "--skip-download", "--no-playlist", "--no-warnings", "--quiet", "--write-subs", "--write-auto-subs",
                    "--sub-langs", "en,hi", "--sub-format", "vtt", "-o", str(d / "%(id)s.%(ext)s"),
                    f"https://www.youtube.com/watch?v={vid}"]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=ON["sub_timeout"], stdin=subprocess.DEVNULL,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if r.returncode != 0:
                    _SUB_FAILS[0] += 1
            except Exception as e:
                _SUB_FAILS[0] += 1
                log(f"   (subtitle skip {vid}: {str(e)[:60]})", show=False)
            have = sorted(d.glob(f"{vid}*.vtt"))
            if have:
                _SUB_FAILS[0] = 0
    cues = []
    for p in sorted(have, key=lambda p: (".en" not in p.name, p.name))[:2]:   # English pehle
        try:
            cues += parse_vtt(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pass
    with _LOCK: _SUBS[vid] = cues
    return cues


def spoken_times(cues, text, top=3):
    """Jis cue me line/hint ke sabse zyada khaas shabd bole gaye – uske start time (sabse achhe pehle)."""
    kws = keywords(text)
    if not cues or not kws: return []
    scored = []
    for st, en, body in cues:
        b = body.lower()
        hit = [k for k in kws if re.search(r"\b" + re.escape(k), b)]
        if not hit: continue
        # pehla shabd (aksar naam: Voyager / Chandra) zyada keemti
        sc = len(hit) + (0.5 if kws[0] in hit else 0)
        scored.append((sc, st))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = []
    for sc, st in scored:
        if sc < (1.5 if len(kws) >= 3 else 1): continue
        if all(abs(st - o) > 8 for o in out): out.append(st)
        if len(out) >= top: break
    return out


# ------------------------------------------------------------------ 2) frame se jaanch
def _frame_at(url, t):
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-rw_timeout", "20000000", "-ss", f"{t:.2f}", "-i", url,
                            "-frames:v", "1", "-vf", "scale=320:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                           capture_output=True, timeout=30, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.stdout:
            import io
            from PIL import Image
            return Image.open(io.BytesIO(r.stdout)).convert("RGB")
    except Exception:
        pass
    return None


def best_starts(vid, dur, text, secs=5.0):
    """YouTube video ke hisson ka kram: [start1, start2, ...] – sabse sahi pehle. Kuch na ho -> []
    (tab purana random tareeka chalta hai)."""
    if not ON["segments"] or not vid or not text: return []
    key = (vid, text)
    with _LOCK:
        if key in _BEST: return list(_BEST[key])
    dur = float(dur or 0) or 60.0
    lim = lambda t: round(max(1.0, min(dur - secs - 1.0, t)), 1)
    said = [lim(t - 0.5) for t in spoken_times(subtitles(vid), text)]
    times = list(dict.fromkeys(said + [lim(dur * f) for f in (0.25, 0.5, 0.75)]))
    why = {t: ("subtitle me bola gaya" if t in said else "aam jagah") for t in times}
    order = list(times)
    try:
        import sources, aankh
        if sources.AANKH["on"] and aankh.ready():
            import yt_clips
            url = yt_clips._stream_url(vid)
            if url:
                probe = times[:ON["max_frames"]]
                ims = [(t, _frame_at(url, t + secs / 2)) for t in probe]
                ims = [(t, im) for t, im in ims if im is not None]
                if ims:
                    sc, _ = aankh.scores([im for _, im in ims], text)
                    sc = [float(x) + (0.015 if why[t] == "subtitle me bola gaya" else 0.0) for (t, _), x in zip(ims, sc)]
                    ranked = [t for _, t in sorted(zip(sc, [t for t, _ in ims]), key=lambda z: -z[0])]
                    order = ranked + [t for t in times if t not in ranked]
    except Exception as e:
        log(f"   (YouTube hissa jaanch skip {vid}: {str(e)[:80]})", show=False)
    if said:
        log(f"   🎯 YouTube {vid}: line ki baat {', '.join(f'{int(t)}s' for t in said)} pe boli gayi – wahi hissa pehle",
            show=False)
    with _LOCK: _BEST[key] = list(order)
    return order


# ------------------------------------------------------------------ 3) iNaturalist (jeev-jantu, ped-paudhe)
def inaturalist(q, n=6):
    """Query me kisi jeev ka naam ho (sand boa, Eryx sistanensis, tiger) -> us prajaati ki research-grade,
    free-licence photos. Naam match na ho -> [] ."""
    if not ON["inat"] or not q: return []
    try:
        import requests
        ql = q.lower()
        ws = keywords(q)
        tries = [" ".join(ws[i:i + 2]) for i in range(0, max(1, len(ws) - 1))][:4] or [q]
        taxon = None
        for t in tries:
            r = requests.get("https://api.inaturalist.org/v1/taxa", params={"q": t, "per_page": 3, "is_active": "true"},
                             timeout=12, headers={"User-Agent": "ViralGyaanVideoTool/3.19"})
            for x in (r.json().get("results") or []):
                names = [str(x.get("name") or "").lower(), str(x.get("preferred_common_name") or "").lower()]
                # naam ka har shabd query me ho (galat jeev nahi) aur kam se kam prajaati / vansh
                if x.get("rank") in ("species", "subspecies", "genus") and any(
                        nm and all(w in ql for w in nm.split()) for nm in names):
                    taxon = x; break
            if taxon: break
        if not taxon: return []
        r = requests.get("https://api.inaturalist.org/v1/observations", params={
            "taxon_id": taxon["id"], "photos": "true", "quality_grade": "research", "per_page": n * 2,
            "order_by": "votes", "photo_license": "cc0,cc-by,cc-by-sa"}, timeout=15,
            headers={"User-Agent": "ViralGyaanVideoTool/3.19"})
        out = []
        label = taxon.get("preferred_common_name") or taxon.get("name")
        for ob in (r.json().get("results") or []):
            for ph in (ob.get("photos") or [])[:1]:
                lic = str(ph.get("license_code") or "").lower()
                if lic not in ("cc0", "cc-by", "cc-by-sa"): continue
                u = str(ph.get("url") or "")
                if not u: continue
                out.append({"kind": "image", "url": u.replace("square", "large"), "thumb": u.replace("square", "medium"),
                            "tags": f"{label} {taxon.get('name', '')}",
                            "credit": f"iNaturalist – {ph.get('attribution', '')} ({lic.upper()}) "
                                      f"(https://www.inaturalist.org/observations/{ob.get('id')})"})
            if len(out) >= n: break
        if out: log(f"   🦎 iNaturalist: '{label}' ki {len(out)} asli photo", show=False)
        return out
    except Exception as e:
        log(f"   (iNaturalist skip: {str(e)[:80]})", show=False)
        return []
