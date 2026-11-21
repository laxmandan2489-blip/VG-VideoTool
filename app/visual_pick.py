"""v3.13 VISUAL PICKER – POORI LINE padh ke visual (sirf naam padh ke nahi).

User ki maang (15 Nov 2026):
  * "Yash ka Ravan wala look" line pe Yash ki koi bhi event photo NAHI – poori line ka matlab (Yash + Ravana look)
    search me jaaye.
  * Lambi line ko 2 hisson me todo, har hisse ka apna visual.
  * Har line ke liye 10-12 visual (video + photo) jama karo, sabko SCORE karo (AI aankh / CLIP), sabse achha lagao.
  * VIDEO ko hamesha pehle mauka – photo sirf tab jab koi video sahi na lage.
  * YouTube search quota khatam ho to Brave video search / yt-dlp search (quota nahi lagta).

Flow (make_video.job ke andar, sources.find_visuals ke BAAD):
  1. split_parts()   – line -> 1 ya 2 hisse
  2. line_queries()  – har hisse ke chhote, poore-matlab wale search shabd (+ mukhya naam + film ka naam)
  3. gather()        – Brave video, yt-dlp YouTube search, Pixabay/Pexels video, Brave photo + pehle se mile items
  4. score()         – thumbnail ka CLIP score (line + hissa + subject), video ko +bonus
  5. pick()          – har hisse ke liye sabse achha; video pehle; download + 3-frame jaanch (sources.verify)
Har candidate ka score + wajah TRACE me (asset tracing – Bug D).
"""
import math, re, random, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from common import log, CACHE

ON = {"on": True, "n": 12, "video_bonus": 0.03, "min": 0.180, "any_channel": False, "split_words": 13,
      "stock_min": 0.25}
# v3.15 TOPIC LOCK (user 15 Nov: "Yash ki baat ho to Yash ke around hi visual – billi, baadal, anjaan log, stick
# figures NAHI"). Insaan / film wali video me stock footage tabhi jab wo line se pakka mile aur 'kachra' na ho.
TOPIC = {"lock": False, "main": "", "film": ""}
JUNK = {"animal": ("a cat, dog or other animal", ("cat", "dog", "animal", "bird", "lion", "tiger")),
        "sky": ("clouds and sky", ("cloud", "sky", "weather")),
        "nature": ("a nature landscape with trees, mountains or sunset", ("nature", "forest", "tree", "sunset", "mountain", "landscape")),
        "abstract": ("abstract colorful light particles or bokeh", ("abstract", "particle", "bokeh")),
        "icons": ("simple cartoon icons, stick figures or pictograms", ("icon", "cartoon", "animation", "infographic")),
        "silhouette": ("plain white silhouettes of people", ("silhouette", "shadow")),
        "train": ("a moving train or film strip", ("train", "strip", "railway")),
        # v3.17 (NVIDIA video: Rubin spec sheet, GTC poster, kata hua 'EO ON COMPAN' slide): text bhari slide
        "slide": ("a presentation slide, poster or spec sheet full of small text",
                  ("slide", "chart", "document", "spec", "presentation", "report", "headline", "screenshot", "graph",
                   "poster", "letter", "newspaper"))}
PERSON_LABEL = "a photo of an unknown man or woman"
PERSON_WORDS = (r"(लोग|लोगों|यूज़र|यूजर|users?|people|crowd|भीड़|कर्मचारी|employees?|workers?|किसान|farmers?|छात्र|students?|"
                r"बच्चे|children|सीईओ|ceo|cfo|founder|संस्थापक|नेता|मंत्री|minister|actor|अभिनेता|वैज्ञानिक|scientist|"
                r"डॉक्टर|doctor|पुलिस|police|भक्त|devotees?|परिवार|family)")
STOCK_SRC = ("pixabay", "pexels", "archive", "nasa", "wikimedia", "smithsonian", "openverse", "searx", "brave photo",
             "brave", "pehle mila")
TRACE = {}                 # line -> {...}
CTX = threading.local()    # v3.17: is line ka sandarbh (thread-safe): neg labels, insaan hai ya nahi, naam
SCRIPT = {"all": ""}       # v3.17: poori script (brand ka matlab samajhne ke liye)
STYLE_WORDS = re.compile(r"\b(footage|illustration|animation|animated|visualization|archive|archival|image|photo|video|"
                         r"close\s*up|closeup|aerial|drone|cinematic|stock|hd|4k|research|shot|scene)\b", re.I)
CTA_HINT = re.compile(r"^\s*(follow|subscribe|cta|follow karo|like|share|end)\s*[.!]?\s*$", re.I)


def hint_ladder(hint):
    """v3.18: aapka hint bahut khaas ho ("Sistan sand boa Eryx sistanensis snake crawling sand") to stock site pe
    kuch nahi milta. Isliye seedhi: (1) poora hint, (2) 'footage/illustration/close up' jaise shabd hata ke,
    (3) pehle 4 shabd, (4) aakhri 3 shabd. CLIP jaanch hamesha POORE hint se hoti hai – random nahi aata."""
    h = re.sub(r"\s+", " ", hint or "").strip()
    if not h: return []
    core = re.sub(r"\s+", " ", STYLE_WORDS.sub(" ", h)).strip()
    ws = core.split()
    out = [h, core, " ".join(ws[:4]), " ".join(ws[-3:]) if len(ws) > 4 else ""]
    return [q for q in dict.fromkeys(out) if q and len(q) > 2]


MOVIE_WORDS = re.compile(r"\b(official\s+trailer|trailer|teaser|movie\s+(scene|clip)|full\s+movie|film\s+scene|"
                         r"hindi\s+dubbed|gameplay|walkthrough|music\s+video|lyric(al)?\s+video|movie|movies|bollywood|hollywood|"
                         r"web\s*series|episode|full\s+hd\s+movie|scene\s+from|song|songs|gaana|lyrics?|remix|jukebox|"
                         r"official\s+audio|video\s+song)\b", re.I)
HINT = {}                  # v3.18: line -> script me aapka '/' ya '||' hint (sabse pakka nirdesh)
EXTRA_Q = {}               # v3.16: line -> Gemini / AI-plan ke aam search shabd (chaudi khoj ke liye)
USE = {}                   # v3.15: file/url -> kitni LINES pe laga (ek hi stock clip 8 baar nahi – max 2 line)
_LOCK = threading.Lock()
KEEP_SRC = ("aapka link", "aapki footage", "chehra", "map", "news card", "film trailer", "my_clips")

SPLIT_AT = re.compile(r"\s*(?:,|;|—|–| - | and then | but | because | which | while | so that | then )\s*", re.I)


# ------------------------------------------------------------------ 1) line -> hisse
def split_parts(eng, k=1, max_words=None):
    """Lambi line (13+ shabd) ya 2+ shot wali line -> 2 hisse (beech ke paas comma/conjunction pe).
    Return [part1] ya [part1, part2]."""
    eng = (eng or "").strip()
    words = eng.split()
    mw = max_words or ON["split_words"]
    if len(words) < 8 or (len(words) < mw and k < 2):
        return [eng] if eng else []
    mid = len(eng) / 2
    cuts = [m for m in SPLIT_AT.finditer(eng) if 0.25 * len(eng) < m.start() < 0.75 * len(eng)]
    if cuts:
        m = min(cuts, key=lambda m: abs(m.start() - mid))
        a, b = eng[:m.start()].strip(), eng[m.end():].strip()
    else:
        h = len(words) // 2
        a, b = " ".join(words[:h]), " ".join(words[h:])
    parts = [x for x in (a, b) if len(x.split()) >= 3]
    # dono hisson me kuch DIKHANE layak shabd hone chahiye – warna poori line ek hi (bematlab tukda nahi)
    if len(parts) < 2 or any(len(_kw(x).split()) < 2 for x in parts):
        return [eng]
    return parts


# ------------------------------------------------------------------ 2) search shabd
def _kw(text, main=""):
    try:
        from identity_lock import kw_show
        return kw_show(text, main)
    except Exception:
        return " ".join(re.findall(r"[A-Za-z]{3,}", text or "")[:6])


def line_queries(part, full, main="", film="", secondary=()):
    """Hisse ke shabd + poori line ka context. Mukhya naam (Yash) aage; line me doosra kirdaar (Ravana) ho to
    'Yash Ravana look' jaisa – SIRF 'Yash' kabhi nahi (wo generic photo laata hai)."""
    kp = _kw(part, main); kf = _kw(full, main)
    mn = (main or "").strip()
    pl = " " + (part or "").lower() + " "
    has_main = bool(mn) and (mn.lower().split()[0] in pl or bool(re.search(r" (he|his|him|he's) ", pl))
                             or (part == full and mn.lower().split()[0] in full.lower()))
    base = re.sub(r"\b" + re.escape(mn) + r"\b", "", kp, flags=re.I).strip() if mn else kp
    qs = []
    if has_main and base:
        qs.append(f"{mn} {base}")
    if kp: qs.append(kp)
    if film and base:
        fl = re.split(r"[:(]", film)[0].strip()
        qs.append(f"{fl} {base}" + (f" {mn}" if has_main and mn.lower() not in base.lower() else ""))
    for s in secondary or ():
        if s and s.lower() in (part or "").lower() and has_main:
            qs.append(f"{mn} {s} look"); break
    if kf and kf != kp: qs.append(kf)
    out = []
    for q in qs:
        ws = []
        for w in q.split():
            if w.lower() not in [x.lower() for x in ws]: ws.append(w)     # 'Ramayana Ravana Ramayana' -> ek baar
        q = " ".join(ws[:7]).strip()
        if q and len(q.split()) >= 1 and q.lower() != mn.lower() and q.lower() not in [o.lower() for o in out]:
            out.append(q)
    return out[:4]


# ------------------------------------------------------------------ 2b) AI "line brief" (ADD-ON, user 15 Nov)
BRIEF = {}               # line -> {"meaning": .., "video_q": [..], "image_q": [..], "parts": [{"text","q"}]}


def make_brief(lines, eng, keys, main="", film=""):
    """Poori script EK baar AI (Gemini; limit khatam -> Groq/OpenRouter backup) ko: har line ka MATLAB samjho
    (story + pichhli/agli line ke context me), chhota karo, phir us matlab se video/photo search shabd. Lambi line
    -> 2 hisse, har hisse ka apna search. Offline (koi AI nahi) -> BRIEF khaali, purane offline shabd chalte hain.
    Ye ADD-ON hai: purane queries hatate nahi, bas sabse aage judte hain."""
    BRIEF.clear()
    try:
        import ai
        key = (keys or {}).get("GEMINI") or ""
        if not key and not (ai.BACKUP["keys"].get("GROQ") or ai.BACKUP["keys"].get("OPENROUTER")):
            return {}
        rows = "\n".join(f"{k+1}. {l}" + (f"  [English: {e}]" if e else "") for k, (l, e) in
                         enumerate(zip(lines, list(eng) + [""] * len(lines))))
        prompt = ("You are a senior video editor choosing REAL footage for a Hindi YouTube Short.\n"
                  "FIRST read the WHOLE script and understand the story"
                  + (f" (main subject: {main}" + (f", film: {film}" if film else "") + ")" if main else "") + ".\n"
                  "Then for EACH line: read the FULL line (never just one keyword), understand what it means in the "
                  "story, and write what the viewer must SEE. Example: line 'Yash ka Ravan wala look' -> meaning "
                  "'Yash in his Ravana look from Ramayana, golden crown' -> video_q ['Yash Ravana look Ramayana', "
                  "'Ramayana teaser Yash Ravana'] – NOT just 'Yash'.\n"
                  "Rules: meaning <= 14 words, concrete and filmable. video_q = 2-3 short search queries (2-6 words) "
                  "for real VIDEO footage (trailer/teaser/BTS/news/stock). image_q = 1-2 photo queries. If a line is "
                  "long (two different visuals), give parts = exactly 2 items {text: that half of the line (English), "
                  "q: one search query for that half}; else parts = [].\n"
                  'Return ONLY JSON: {"lines": [{"meaning": "..", "video_q": [".."], "image_q": [".."], '
                  '"parts": [{"text": "..", "q": ".."}]}]}\n\nSCRIPT:\n' + rows)
        data = ai.ask_json(key, [prompt], temperature=0.2, timeout=90, budget=120)
        arr = (data or {}).get("lines") if isinstance(data, dict) else (data if isinstance(data, list) else None)
        if not isinstance(arr, list): return {}
        for k, x in enumerate(arr[:len(lines)]):
            if not isinstance(x, dict): continue
            clean = lambda v: [str(q).strip()[:80] for q in (v or []) if isinstance(q, str) and q.strip()][:3]
            parts = [p_ for p_ in (x.get("parts") or []) if isinstance(p_, dict) and p_.get("q")][:2]
            BRIEF[k] = {"meaning": str(x.get("meaning") or "")[:140], "video_q": clean(x.get("video_q")),
                        "image_q": clean(x.get("image_q")),
                        "parts": [{"text": str(p_.get("text") or "")[:160], "q": str(p_["q"])[:80]} for p_ in parts]
                        if len(parts) == 2 else []}
        if BRIEF:
            log(f"   🧠 line brief: AI ne {len(BRIEF)} lines ka poora matlab samajh ke search shabd banaye "
                f"(jaise line 1: {(BRIEF.get(0) or {}).get('meaning', '')[:60]})")
    except Exception as e:
        log(f"   (line brief skip: {str(e)[:100]})", show=False)
    return BRIEF


# ------------------------------------------------------------------ 3) candidates
GOOD_YT = re.compile(r"(official|trailer|teaser|glimpse|first look|promo|motion poster|song|full video|scene|clip|"
                     r"making|behind the scenes|bts|introduction|title reveal|announcement|interview|press meet)", re.I)
BAD_YT = re.compile(r"(reaction|react|review|explained|breakdown|analysis|spoof|parody|roast|fan ?made|status|"
                    r"whatsapp|#shorts|meme|edit\b|lyrical edit|ai generated)", re.I)


_STOP = {"the", "a", "an", "of", "and", "in", "on", "to", "for", "with", "is", "are", "at", "by", "from", "india",
         "indian", "video", "footage", "4k", "hd", "new", "best", "top", "how", "why", "what", "this", "that"}


def topic_title_ok(c, main="", qtoks=()):
    """v3.16: non-person topic ke liye YouTube video title ka milaan."""
    t = (c.get("title") or "").lower()
    views = int(c.get("view_count") or 0); dur = float(c.get("duration_seconds") or 0)
    if views and views < 5000: return False
    if dur and (dur < 8 or dur > 3 * 3600): return False
    mt = [w for w in re.findall(r"[a-z0-9]+", (main or "").lower()) if w not in _STOP and len(w) > 2]
    tt = set(re.findall(r"[a-z0-9]+", t))
    for nm in getattr(CTX, "names", []) or []:            # v3.17: line ka insaan (Colette Kress) title me ho
        nt = [w for w in re.findall(r"[a-z]+", nm.lower()) if len(w) > 2]
        if len(nt) >= 2 and all(w in tt for w in nt[:2]):
            return True
    if mt and all(w in tt for w in mt[:2]):
        return True
    q = [w for w in re.findall(r"[a-z0-9]+", " ".join(qtoks or c.get("_qtoks") or ()).lower()) if w not in _STOP and len(w) > 3]
    return len({w for w in q if w in tt}) >= 2


def yt_allowed(c, main="", film=""):
    """YouTube clip policy (purana niyam: doosre creator ki video nahi):
    official/trailer/teaser/song/making jaisa title + 10 lakh+ views ya bada channel, ya youtube_channels.txt wala
    channel. style.txt: youtube_kisi_bhi_channel = haan -> koi bhi (aapki zimmedari)."""
    t = c.get("title") or ""
    if ON["any_channel"]:
        return not BAD_YT.search(t)
    try:
        import yt_clips
        if main and c.get("channel") and yt_clips.chan_ok(c["channel"], main):
            return True
    except Exception:
        pass
    if getattr(CTX, "names", None) and not BAD_YT.search(t):
        # v3.17 (NVIDIA video: "CFO Colette Kress" line pe circuit board ki photo – Commons pe free photo nahi thi):
        # line ke insaan ka naam title me ho (interview / news) -> muqable me, chahe main lock kisi aur pe ho
        tt_ = set(re.findall(r"[a-z]+", t.lower()))
        for nm in CTX.names:
            nt = [w for w in re.findall(r"[a-z]+", nm.lower()) if len(w) > 2]
            if len(nt) >= 2 and all(w in tt_ for w in nt[:2]) and int(c.get("view_count") or 0) >= 2000:
                return True
    if not TOPIC["lock"] and ON.get("topic_yt", True) and not BAD_YT.search(t):
        # v3.16 FIX (log 16 Nov "Chhath Puja": "YouTube: official video nahi mili" -> line 1 pe 0 visual, Pixabay pe
        # kuch nahi): 'official/trailer' wala niyam insaan/film ke liye tha. Tyohaar / ghatna / jagah / company /
        # science wali video me asli footage news / documentary / drone video me hoti hai. Ab: title me video ka
        # mukhya vishay (ya line ke 2 khaas shabd) ho + 5000+ views + shorts/reaction/meme nahi -> muqable me.
        # Phir bhi AI aankh (CLIP) score + Gemini jaanch ke baad hi lagti hai.
        if topic_title_ok(c, main):
            return True
    if BAD_YT.search(t) or not GOOD_YT.search(t):
        return False
    big = max(int(c.get("view_count") or 0), int(c.get("channel_followers") or 0)) >= 1_000_000
    named = any(x and x.lower().split()[0] in t.lower() for x in (main, re.split(r"[:(]", film or "")[0]))
    return big and named


def gather(i, parts_q, keys, main="", film="", existing=()):
    """Har query se candidates (video pehle). Return list of dicts (download nahi – sirf thumbnail)."""
    import sources
    seen = set(); out = []
    def add(c, q, prov):
        u = c.get("url") or c.get("path")
        if not u or u in seen: return
        if not film and MOVIE_WORDS.search(" ".join(str(c.get(k_) or "") for k_ in ("title", "credit", "tags", "channel"))):
            return                       # v3.18: topic film nahi -> trailer / movie scene / gameplay clips nahi
        reused = False
        with sources._lock:
            if c.get("url") and c["url"] in sources._used:
                # v3.13: video kisi aur line pe lag chuki -> ALAG hissa chal sakta hai (thoda kam number);
                # photo dobara NAHI
                if c.get("kind") != "video": return
                reused = True
        seen.add(u); c = dict(c, _q=q, _src=prov, _reused=reused); out.append(c)
    pkey = (keys or {}).get("PIXABAY"); xkey = (keys or {}).get("PEXELS")
    sx = (keys or {}).get("SEARXNG"); smk = (keys or {}).get("SMITHSONIAN")
    allq = list(dict.fromkeys(q for qs in parts_q for q in qs))
    brave = bool(sources.BRAVE_KEYS)
    try:
        import youtube_sources as _ys
    except Exception:
        _ys = None
    try:
        import providers as pv
    except Exception:
        pv = None
    space = any(w in sources.SPACE_WORDS for w in re.findall(r"[a-z]+", " ".join(allq).lower()))
    want = ON["n"]

    def run(jobs):
        res = []
        if not jobs: return res
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = [(prov, q, ex.submit(fn)) for prov, q, fn in jobs]
            for prov, q, f in futs:
                try: res.append((prov, q, f.result(timeout=90) or []))
                except Exception as e: log(f"   (visual_pick {prov} skip: {str(e)[:80]})", show=False)
        return res

    # v3.15 PRIORITY: YouTube -> Brave -> SearXNG -> Internet Archive -> NASA -> Smithsonian -> Wikimedia -> (zaroorat
    # ho tab hi) Pixabay / Pexels. Google: authorized integration nahi -> skip.
    jobs = []
    for q in allq[:3]:
        if _ys:
            jobs.append(("youtube search", q, lambda q=q: [
                dict(x, kind="video", yt=x["video_id"], thumb=x.get("thumbnail"), credit=f"YouTube: {x['title'][:70]} – "
                     f"{x.get('channel','')} ({x['url']})") for x in _ys.ytdlp_search(q, 8)]))
        if brave: jobs.append(("brave video", q, lambda q=q: sources.brave_videos(q, n=10)))
        if sx and pv: jobs.append(("searxng video", q, lambda q=q: pv.searxng(q, sx, "videos", 8)))
    for q in allq[:2]:
        if pv: jobs.append(("archive video", q, lambda q=q: pv.archive_videos(q, 4)))
        if space: jobs.append(("nasa", q, lambda q=q: sources.nasa_videos(q)[:4] if hasattr(sources, "nasa_videos") else []))
        if smk and pv: jobs.append(("smithsonian", q, lambda q=q: pv.smithsonian_images(q, smk, 4)))
        if brave: jobs.append(("brave photo", q, lambda q=q: sources.brave_images(q, None, n=8)))
        if sx and pv: jobs.append(("searxng photo", q, lambda q=q: pv.searxng(q, sx, "images", 6)))
    jobs.append(("wikimedia", allq[0] if allq else "", lambda: [dict(c, thumb=c.get("thumb") or c.get("url"))
                                                              for c in sources.wikimedia(allq[0])[:4]] if allq else []))
    # v3.19 (user: "YouTube + Pixabay dono se, aur jahan se bhi sahi mile – sab automatic"):
    try:
        import smart_footage as _sf
    except Exception:
        _sf = None
    for q in allq[:2]:
        if _sf: jobs.append(("inaturalist", q, lambda q=q: _sf.inaturalist(q, 5)))          # jeev / paudhe
        if space: jobs.append(("nasa photo", q, lambda q=q: [dict(c, thumb=c.get("thumb") or (c.get("alts") or [c["url"]])[-1])
                                                            for c in sources.nasa(q)[:4]]))
    if allq and hasattr(sources, "wikimedia_videos"):
        jobs.append(("wikimedia video", allq[0], lambda: sources.wikimedia_videos(allq[0])[:3]))
    if pkey:                                          # Pixabay HAMESHA muqable me (pehle sirf kami pe)
        for q in allq[:2]:
            jobs.append(("pixabay video", q, lambda q=q: sources.pixabay_videos(q, pkey)[:4]))
        if allq: jobs.append(("pixabay photo", allq[0], lambda: [dict(c, thumb=c.get("thumb") or c.get("url"))
                                                                for c in sources.pixabay_images(allq[0], pkey, True)[:3]]))
    res = run(jobs)
    good = sum(1 for _, _, cs in res for c in cs if c.get("kind") == "video")
    if good < 8:                                      # kam mila -> baaki queries se bhi stock
        stock = []
        for q in allq[2:4]:
            if pkey: stock.append(("pixabay video", q, lambda q=q: sources.pixabay_videos(q, pkey)[:5]))
            if xkey: stock.append(("pexels video", q, lambda q=q: sources.pexels_videos(q, xkey)[:5]))
        res += run(stock)
    rows = [(prov, q, c) for prov, q, cs in res for c in cs]
    for c in existing:
        add(c, "", c.get("src") or "pehle mila")
    if TOPIC["lock"]:                                 # v3.15: mukhya insaan/film ki official videos bhi muqable me
        try:
            import subject_pool
            for v in subject_pool.POOL["vids"][:5]:
                add({"kind": "video", "yt": v["video_id"], "url": v["url"], "thumb": v["thumb"], "title": v["title"],
                     "channel": v.get("channel"), "duration_seconds": v["duration_seconds"],
                     "view_count": v["view_count"], "pool": True}, "", "subject pool")
        except Exception:
            pass
    for rnd in range(6):
        for prov, q, cs in res:
            if rnd < len(cs):
                c = cs[rnd]
                if c.get("kind") == "video" and c.get("yt") and not yt_allowed(dict(c, _qtoks=[q]), main, film):
                    continue
                if c.get("kind") == "video" and not c.get("yt") and prov in ("brave video", "searxng video"):
                    continue                          # non-YouTube page – yt-dlp se pakka nahi (chhodo)
                add(c, q, prov)
        if len(out) >= want + len(existing): break
    return out[:want + len(existing)], len(rows)


# ------------------------------------------------------------------ 4) score
def _frame_of(path, kind):
    from PIL import Image
    try:
        if kind == "image":
            return Image.open(path).convert("RGB")
        import subprocess, io
        from common import duration
        d = duration(path) or 3
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d*0.45:.2f}", "-i", str(path), "-frames:v", "1",
                            "-vf", "scale=320:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True,
                           timeout=30, stdin=subprocess.DEVNULL)
        return Image.open(io.BytesIO(r.stdout)).convert("RGB") if r.stdout else None
    except Exception:
        return None


def _toks(t):
    return {w[:-1] if w.endswith("s") and len(w) > 4 else w for w in re.findall(r"[a-z0-9]{3,}", (t or "").lower())}


def text_score(c, texts):
    """CLIP na ho to: title/tags ka line ke shabdon se mel (0.15 .. 0.30 range – CLIP jaisa)."""
    have = _toks(" ".join(str(c.get(k) or "") for k in ("title", "tags", "credit", "channel", "src", "entity")))
    best = 0.0
    for t in texts:
        want = _toks(t)
        if want: best = max(best, len(want & have) / len(want))
    return 0.15 + 0.15 * best


def score(cands, texts):
    """Har candidate ko 0..~0.35 score (CLIP). Thumbnail nahi / CLIP nahi -> text_score."""
    import sources
    texts = [t for t in texts if t]
    ims, idx = [], []
    try:
        import aankh
        clip_ok = sources.AANKH["on"] and aankh.ready()
    except Exception:
        clip_ok = False
    if clip_ok:
        def load(c):
            if c.get("path") and Path(c["path"]).exists():
                return _frame_of(c["path"], c.get("kind", "video"))
            if c.get("thumb"):
                b = sources._thumb_bytes(c["thumb"])
                if b:
                    from PIL import Image
                    import io
                    try: return Image.open(io.BytesIO(b)).convert("RGB")
                    except Exception: return None
            return None
        with ThreadPoolExecutor(max_workers=8) as ex:
            got = list(ex.map(load, cands))
        for j, im in enumerate(got):
            if im is not None: ims.append(im); idx.append(j)
    sc = [None] * len(cands)
    if ims:
        import numpy as np
        try:
            best = None
            for t in texts[:4]:
                m, n = aankh.scores(ims, t)
                v = np.asarray(m, dtype=float) - np.maximum(0.0, np.asarray(n, dtype=float) - np.asarray(m, dtype=float))
                best = v if best is None else np.maximum(best, v)
            for k, j in enumerate(idx): sc[j] = float(best[k])
        except Exception as e:
            log(f"   (visual_pick CLIP skip: {str(e)[:80]})", show=False)
    if ims:                                           # v3.15: kachra / andhera pehchaano (CLIP + roshni)
        try:
            _junk_check(cands, idx, ims, sc, texts)
        except Exception as e:
            log(f"   (junk check skip: {str(e)[:80]})", show=False)
    for j, c in enumerate(cands):
        if sc[j] is None: sc[j] = text_score(c, texts)
        if c.get("_reused"): sc[j] -= 0.02                # doosri line pe lagi video – nayi ko pehle mauka
        c["_score"] = round(sc[j], 4)
        try:
            from providers import PRIORITY
            pb = PRIORITY.get(str(c.get("_src") or ""), 0.0)
        except Exception:
            pb = 0.0
        try:                                               # v3.19: NASA/news/science channel +, gaana/film channel -
            import smart_footage
            pb += smart_footage.channel_bonus(c)
        except Exception:
            pass
        c["_final"] = round(sc[j] + pb + (ON["video_bonus"] if c.get("kind") == "video" else 0.0), 4)
    return cands


def is_stock(c):
    src = str(c.get("_src") or c.get("src") or "").lower()
    if c.get("hero") or c.get("entity") or c.get("pool") or c.get("yt") or "youtube" in src or "trailer" in src:
        return False
    return any(k in src for k in STOCK_SRC) or not src


def _junk_check(cands, idx, ims, sc, texts):
    import numpy as np, aankh
    tl = " ".join(texts).lower()
    labels = [(k, d) for k, (d, words) in JUNK.items() if not any(w in tl for w in words)]
    for k, j in enumerate(idx):
        im = ims[k]
        try:
            lum = float(np.asarray(im.convert("L").resize((64, 64))).mean())
        except Exception:
            lum = 128.0
        if lum < 28:
            cands[j]["_junk"] = f"andhera / kaala frame (roshni {lum:.0f})"
    labels += list(getattr(CTX, "neg", []) or [])            # v3.17: brand ka galat matlab (Copilot -> hawai jahaz)
    anon = TOPIC["lock"] or bool(getattr(CTX, "no_person", False))
    if not labels and not anon:
        return
    texts_l = [d for _, d in labels] + ([PERSON_LABEL] if anon else [])
    tv = aankh.text_vecs([f"a photo of {t}" for t in texts_l])
    iv = aankh.image_vecs(ims)
    sim = iv @ tv.T
    for k, j in enumerate(idx):
        c = cands[j]
        if c.get("_junk") or sc[j] is None: continue
        line = sc[j]
        for li, (name, d) in enumerate(labels):
            v = float(sim[k, li])
            if v > 0.22 and v > line + 0.005:
                c["_junk"] = f"{name} ({v:.3f} > line {line:.3f})"; break
        if not c.get("_junk") and anon and (is_stock(c) or (c.get("yt") and not TOPIC["lock"])) and not c.get("pool"):
            # v3.17 (Microsoft outage video: 3 alag anjaan aadmi ke close-up – line me koi insaan tha hi nahi)
            v = float(sim[k, len(labels)])
            if v > line - 0.005:
                c["_junk"] = (f"anjaan insaan ({v:.3f} vs line {line:.3f}) – " +
                              (f"video {TOPIC['main']} ke baare me hai" if TOPIC["lock"] else "line me koi insaan nahi"))


# ------------------------------------------------------------------ 5) download + pick
def materialize(c, i, verify_text, avoid=()):
    """Candidate -> local file item (ya None). YouTube: sirf 4-5 sec ka hissa (yt-dlp)."""
    import sources
    if c.get("path") and Path(c["path"]).exists():
        return c
    if c.get("yt"):
        try:
            import yt_clips
            if not yt_clips._ytdlp_ok(): return None
            with yt_clips._LOCK:
                if yt_clips._N["n"] >= yt_clips.ON["max_per_video"] or yt_clips._over_budget(): return None
                if yt_clips.USED_VIDS.get(c["yt"], 0) >= 2: return None
            dur = float(c.get("duration_seconds") or 0) or 60.0
            secs = yt_clips.ON["secs"] + 1.0
            try:                                   # v3.19: subtitle + AI aankh se SAHI hissa (warna purana random)
                import smart_footage
                starts = smart_footage.best_starts(c["yt"], dur, verify_text or c.get("_q") or "", secs)[:3]
            except Exception:
                starts = []
            if not starts:
                starts = [round(max(1.0, min(dur - secs - 1.0, dur * fr)), 1)
                          for fr in random.sample((0.18, 0.3, 0.42, 0.55, 0.68), 2)]
            for st in starts:
                key = (c["yt"], int(st // 10))
                with yt_clips._LOCK:
                    if key in yt_clips.USED: continue
                    yt_clips.USED.add(key)
                d = CACHE / "ytclips"; d.mkdir(parents=True, exist_ok=True)
                p = yt_clips._cut(c["yt"], st, secs, d / f"{c['yt']}_{int(st)}")
                if not p: return None
                if sources.verify(p, "video", verify_text, (c.get("_q") or "",), avoid, i) is False:
                    continue
                with yt_clips._LOCK:
                    yt_clips._N["n"] += 1; yt_clips.USED_VIDS[c["yt"]] = yt_clips.USED_VIDS.get(c["yt"], 0) + 1
                url = f"https://www.youtube.com/watch?v={c['yt']}&t={int(st)}"
                _mn = TOPIC.get("main") or ""
                return {"kind": "video", "path": p, "url": url, "src": f"youtube ({c.get('_src')})",
                        "entity": _mn if (c.get("pool") or (_mn and _mn.lower() in (c.get("title") or "").lower())) else "",
                        "credit": f"YouTube: \"{(c.get('title') or '')[:70]}\" – {c.get('channel','')} ({url})",
                        "score": c.get("_score")}
        except Exception as e:
            log(f"   (YouTube clip skip: {str(e)[:100]})", show=False)
        return None
    with sources._lock:
        if c.get("url") in sources._used and not (c.get("_reused") and c.get("kind") == "video"): return None
        sources._used.add(c.get("url"))
    p = sources.download(c)
    if not p: return None
    if sources.verify(p, c["kind"], verify_text, (c.get("_q") or "",), avoid, i) is False:
        return None
    return {"kind": c["kind"], "path": p, "url": c.get("url"), "credit": c.get("credit", ""), "query": c.get("_q"),
            "src": f"{c.get('_src')} ✓", "tags": c.get("tags", ""), "score": c.get("_score")}


def _quota():
    try:
        import youtube_sources
        return youtube_sources.quota_out()
    except Exception:
        return False


def _ok(c):
    if c.get("_junk"): return False
    if not c.get("pool") and USE.get(str(c.get("url") or c.get("path")), 0) >= 2: return False
    if TOPIC["lock"] and is_stock(c) and (c.get("_score") or 0) < ON["stock_min"]: return False
    return True


def improve(i, found, eng, line, keys, need, lock=None, film=None, shot=None):
    """found = sources.find_visuals ka (items, kw). Return naya (items, kw) – poori line + score + video pehle."""
    import sources
    items, kw = (found if isinstance(found, tuple) else (found or [], []))
    items = list(items or [])
    if not ON["on"] or not eng:
        return items, kw
    keep = [x for x in items if any(str(x.get("src", "")).startswith(k) for k in KEEP_SRC) or x.get("face") or x.get("whole")]
    if keep and (len(keep) >= need or any(x.get("face") or x.get("whole") for x in keep)):
        TRACE[i] = {"line": line, "eng": eng, "kept": [str(x.get("path")) for x in keep], "why": "aapki/official/map footage"}
        return items, kw
    main = (lock or {}).get("main_subject") or sources.MAIN.get("name") or ""
    sec = (lock or {}).get("secondary_subjects") or []
    flabel = (film or {}).get("label", "") if film else ""
    parts = split_parts(eng, need)
    br = BRIEF.get(i) or {}
    if br.get("parts") and need >= 2 and len(parts) < 2:          # AI ne line ko 2 matlab me toda
        parts = [p_["text"] or eng for p_ in br["parts"]]
    hq = (HINT.get(i) or "").strip()
    if hq:                                                         # v3.18: aapka hint -> wahi hisse, wahi pehli query
        hp = [x.strip() for x in re.split(r"\s*[+;]\s*", hq) if len(x.strip()) > 2]
        parts = hp[:2] if len(hp) >= 2 and need >= 2 else [hq]
    pq = [line_queries(p, eng, main, flabel, sec) for p in parts]
    if hq:
        pq = [list(dict.fromkeys(hint_ladder(p) + qs))[:6] for p, qs in zip(parts, pq)]
    if br and not hq:                                              # ADD-ON: AI ke "poora matlab" wale shabd sabse aage
        for k_, qs_ in enumerate(pq):
            extra = []
            if br.get("parts") and len(br["parts"]) == len(parts): extra.append(br["parts"][k_]["q"])
            extra += br.get("video_q", [])[:2] + br.get("image_q", [])[:1]
            pq[k_] = list(dict.fromkeys([q for q in extra if q] + qs_))[:6]
    try:                                                           # v3.17: brand ka sahi matlab + line ka sandarbh
        import brand_sense
        senses = brand_sense.detect(line, eng, SCRIPT["all"])
    except Exception:
        senses = []
    if senses:
        bq = brand_sense.queries(senses)
        pq = [list(dict.fromkeys(bq[:2] + [brand_sense.fix_query(q, senses) for q in qs]))[:7] for qs in pq]
        log(f"   🏷 line {i+1}: brand ka sahi matlab – {', '.join(senses)} (hawai jahaz / khel team / nazara NAHI)", show=False)
    CTX.neg = brand_sense.negatives(senses) if senses else []
    ent = sources.ENTITY.get(i) or {}
    names = [ent.get("label")] if str(ent.get("type", "")).lower() == "person" and ent.get("label") else []
    names += [n for n in re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", eng or "") if n not in names and n.lower() not in
              (main or "").lower()][:2]
    CTX.names = [n for n in names if n]
    CTX.no_person = not CTX.names and not (str((lock or {}).get("main_type")) == "person" and
                                           any(sc.get("uses_main") for sc in (lock or {}).get("scenes", [])[i:i + 1])) \
        and not re.search(PERSON_WORDS, f"{line} {eng}", re.I)
    if CTX.names and not senses:                                   # insaan ki line: naam wali query sabse pehle
        pq = [list(dict.fromkeys([CTX.names[0], f"{CTX.names[0]} interview"] + qs))[:7] for qs in pq]
    avoid = sources.AVOID.get(i, ())
    if senses:
        avoid = tuple(dict.fromkeys(tuple(avoid) + tuple(d for _, d in CTX.neg)))[:6]
    others = [x for x in items if x not in keep]
    cands, raw_n = gather(i, pq, keys, main, flabel, others)
    if sum(1 for c in cands if c.get("kind") == "video") < 3 and not TOPIC["lock"]:
        # v3.16 FIX (log 16 Nov: "line 1: 0 visual jaanche" – query "Chhath Puja sunset arghya" bahut khaas thi):
        # kam mile to CHAUDI khoj: (a) sirf mukhya vishay, (b) vishay hata ke line ka drishya (river sunset
        # devotees), (c) AI ke diye aam shabd. Phir bhi CLIP score se hi chunav – random nahi.
        broad = []
        if main: broad.append(main)
        for qs in pq:
            for q in qs[:2]:
                b = re.sub(re.escape(main), "", q, flags=re.I).strip() if main else ""
                if b and len(b.split()) >= 2: broad.append(b)
        broad += [q for q in (EXTRA_Q.get(i) or [])[:3] if isinstance(q, str)]
        broad = [q for q in dict.fromkeys(broad) if q and all(q not in qs for qs in pq)][:4]
        if broad:
            c2, r2 = gather(i, [broad], keys, main, flabel, ())
            seen_ = {str(c.get("url") or c.get("path")) for c in cands}
            add_ = [c for c in c2 if str(c.get("url") or c.get("path")) not in seen_]
            if add_:
                log(f"   🔎 line {i+1}: kam visual mile – chaudi khoj ({', '.join(broad[:3])}) se {len(add_)} aur", show=False)
            cands += add_; raw_n += r2
    full_kw = _kw(eng, main)
    texts_all = ([hq] if hq else []) + [full_kw] + [q for qs in pq for q in qs[:1]] + \
        ([br["meaning"]] if br.get("meaning") and not hq else [])
    score(cands, texts_all)
    # har hisse ke liye alag score (hissa + poori line)
    per_part = []
    for p, qs in zip(parts, pq):
        tx = ([p] if hq else []) + [_kw(p, main)] + qs[:1] + [full_kw] + ([br["meaning"]] if br.get("meaning") and not hq else [])
        pc = [dict(c) for c in cands]
        score(pc, tx)
        per_part.append(pc)
    chosen, used = list(keep), {str(x.get("path") or x.get("url")) for x in keep}
    n_need = max(1, need - len(keep))
    slots = [min(len(parts) - 1, (s * len(parts)) // n_need) for s in range(n_need)]
    trace_rows = []
    for s, pi in enumerate(slots):
        pc = sorted(per_part[pi], key=lambda c: -c["_final"])
        pc = [c for c in pc if _ok(c)]                 # v3.15: kachra / anjaan log / andhera / kamzor stock bahar
        vids = [c for c in pc if c.get("kind") == "video"]
        imgs = [c for c in pc if c.get("kind") != "video"]
        best_img = imgs[0]["_score"] if imgs else 0.0
        # VIDEO PEHLE: video tab tak jab tak wo seema se upar ho aur photo se bahut peeche na ho
        order = [c for c in vids if c["_score"] >= ON["min"] and c["_score"] + ON["video_bonus"] >= best_img] + \
                [c for c in imgs if c["_score"] >= ON["min"]]
        if not any(x.get("part") == pi for x in chosen[len(keep):]) and not order and not TOPIC["lock"]:
            # is hisse ke liye ek bhi achha nahi -> sabse kam-bura (sirf tab; warna achhi clip ka alag hissa chalega)
            order = [c for c in vids if c["_score"] < ON["min"]] + [c for c in imgs if c["_score"] < ON["min"]]
        got = None
        for c in order[:8]:
            u = str(c.get("path") or c.get("url"))
            if u in used: continue
            vt = _kw(parts[pi], main) or full_kw
            it = materialize(c, i, vt, avoid)
            if it:
                got = dict(it, part=pi, part_text=parts[pi][:120], score=c["_score"])
                used.add(u); used.add(str(it.get("path")))
                break
        if not got and TOPIC["lock"]:                  # v3.15: random nahi – mukhya insaan/film ki apni video ka naya hissa
            try:
                import subject_pool
                pit = subject_pool.next_clip(i, "", avoid)
                if pit: got = dict(pit, part=pi, part_text=parts[pi][:120], score=None)
            except Exception as e:
                log(f"   (subject pool clip skip: {str(e)[:80]})", show=False)
        if got:
            chosen.append(got)
            for k_ in {str(got.get("url") or ""), str(got.get("path") or "")} - {""}:
                USE[k_] = USE.get(k_, 0) + 1
        trace_rows.append({"slot": s, "part": parts[pi][:120], "queries": pq[pi],
                           "picked": (str(got.get("path")) if got else None),
                           "picked_kind": got.get("kind") if got else None,
                           "picked_score": got.get("score") if got else None})
    # pehle wale (sources) items jo chune nahi gaye – peeche (repeat se behtar)
    okp = {str(c.get("path")) for c in cands if c.get("path") and _ok(c)}
    for x in others:
        if str(x.get("path")) not in used and len(chosen) < need + 1 and str(x.get("path")) in okp:
            chosen.append(x); used.add(str(x.get("path")))
    if TOPIC["lock"] and len(chosen) < need:          # v3.15: kam pade to mukhya insaan/film ki aur video (naya hissa)
        try:
            import subject_pool
            for _ in range(need - len(chosen)):
                pit = subject_pool.next_clip(i, "", avoid)
                if not pit: break
                chosen.append(dict(pit, part=len(parts) - 1))
        except Exception:
            pass
    nj = [c for c in cands if c.get("_junk")]
    if nj:
        log(f"   🚫 line {i+1}: {len(nj)} visual hataye – " + "; ".join(f"{c.get('_src')}: {c['_junk']}" for c in nj[:3]))
    nv = sum(1 for x in chosen if x.get("kind") == "video")
    why_no_video = ""
    if not nv:                                        # v3.13 (Bug E): photo-only ki SAAF wajah
        vc = [c for c in cands if c.get("kind") == "video"]
        if not vc:
            prov = [n for n, ok in (("Brave", sources.BRAVE_KEYS), ("Pixabay", (keys or {}).get("PIXABAY")),
                                     ("Pexels", (keys or {}).get("PEXELS"))) if ok]
            why_no_video = f"koi video mili hi nahi (providers: {', '.join(prov) or 'koi key nahi'}; YouTube: " + \
                           ("aaj ki API limit khatam" if _quota() else
                            ("official video nahi mili" if TOPIC["lock"] else "title se milti video nahi mili")) + ")"
        else:
            bv = max(vc, key=lambda c: c["_score"])
            why_no_video = (f"{len(vc)} video mili par sabse achhi ka score {bv['_score']:.3f} (seema {ON['min']}) "
                            f"/ download ya 3-frame jaanch fail")
        log(f"   📷 line {i+1}: sirf photo – {why_no_video}")
    TRACE[i] = {"why_no_video": why_no_video, "brief": br or None,"line": line, "eng": eng, "parts": parts, "queries": pq, "raw_results": raw_n,
                "candidates": [{"src": c.get("_src"), "kind": c.get("kind"), "title": (c.get("title") or "")[:80],
                                "url": c.get("url") or str(c.get("path")), "score": c.get("_score"),
                                "final": c.get("_final"), "reject": c.get("_junk") or (None if _ok(c) else
                                "kamzor stock (topic lock)")} for c in sorted(cands, key=lambda c: -c["_final"])],
                "slots": trace_rows, "chosen": [str(x.get("path")) for x in chosen]}
    log(f"   🎯 line {i+1}: {len(parts)} hissa, {len(cands)} visual jaanche → {nv} video + "
        f"{len(chosen) - nv} photo chuni (query: {pq[0][0] if pq and pq[0] else '-'})", show=False)
    if TOPIC["lock"]:                                  # v3.15: chhaante hue kachre ko wapas mat lao
        return (chosen or [x for x in items if str(x.get("path")) in okp]), kw
    # v3.17: kachra (galat-matlab / anjaan insaan / slide) wapas mat lao – khaali line ko fallback (mukhya vishay /
    # kinetic card) sambhalega; galat visual se khaali behtar
    bad = {str(c.get("path")) for c in cands if c.get("path") and c.get("_junk")}
    return (chosen or [x for x in items if str(x.get("path")) not in bad]), kw
