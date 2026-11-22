"""Find free, legal visuals for each sentence.

Order: my_clips -> Pixabay video -> Wikimedia Commons -> Openverse -> NASA -> Pixabay photo -> text card.
Only licences that allow reuse without share-alike: CC0, Public Domain, CC BY (credit written to credits.txt).
"""
import re, json, hashlib, random
from pathlib import Path
from urllib.parse import quote
import requests
from common import log, UA, CACHE, TOOL

S = requests.Session()
S.headers["User-Agent"] = UA
TIMEOUT = 20


def _good_plan(data, lines):
    """Validate a complete one-to-one visual plan; never shift missing scenes."""
    if not isinstance(data, dict) or not isinstance(data.get("lines"), list):
        return False
    items = data["lines"]
    if len(items) != len(lines):
        return False
    for item in items:
        if not isinstance(item, dict):
            return False
        visual = item.get("show") or item.get("visual") or item.get("description")
        queries = item.get("q") if "q" in item else item.get("visual_queries")
        if not isinstance(visual, str) or not visual.strip():
            return False
        if not isinstance(queries, list) or not queries or any(not isinstance(q, str) or not q.strip() for q in queries):
            return False
    return True


BRAVE_KEYS = []          # v3.13: 1-2 Brave keys (BRAVE, BRAVE2) – ek ki limit khatam -> doosri
_BRAVE_BAD = set()


def brave_setup(keys):
    ks = [(keys or {}).get(k) for k in ("BRAVE", "BRAVE2", "BRAVESEARCH", "BRAVEAPI")]
    BRAVE_KEYS[:] = [k for k in dict.fromkeys(ks) if k]
    return BRAVE_KEYS


def _brave_get(kind, q, count, key=None):
    """kind = images | videos. Key bari-bari: 401/403/429 pe agli key. Return results list."""
    keys_ = [key] if key and key not in BRAVE_KEYS else []
    keys_ += [k for k in BRAVE_KEYS if k not in _BRAVE_BAD]
    for k in keys_:
        try:
            resp = S.get(f"https://api.search.brave.com/res/v1/{kind}/search",
                         params={"q": q[:300], "count": min(max(int(count), 1), 20 if kind == "videos" else 50),
                                 "safesearch": "strict" if kind == "images" else "moderate"},
                         headers={"X-Subscription-Token": k, "Accept": "application/json"}, timeout=TIMEOUT)
            code = getattr(resp, "status_code", 200)
            kn = "key 1" if BRAVE_KEYS and k == BRAVE_KEYS[0] else "key 2"     # v3.15: key kabhi log me nahi
            try:
                import providers as _pv
            except Exception:
                _pv = None
            if code in (401, 402, 403, 429):
                why = {401: "key galat", 402: "credit khatam / card nahi", 403: "plan me ye search nahi",
                       429: "rate limit"}[code]
                log(f"  Brave {kind} {code} ({kn}: {why}) – agli key / provider", show=False)
                if _pv: _pv.mark(f"brave-{kn.replace(' ', '')}", False, f"{code} {why}", 0)
                if code != 429: _BRAVE_BAD.add(k)
                continue
            if code != 200:
                log(f"  Brave {kind} {code}", show=False)
                if _pv: _pv.mark(f"brave-{kn.replace(' ', '')}", False, f"HTTP {code}", 0)
                return []
            if _pv: _pv.mark(f"brave-{kn.replace(' ', '')}", True)
            payload = resp.json()
            return payload.get("results", []) if isinstance(payload, dict) else []
        except Exception as exc:
            log(f"  brave {kind} error: {exc}", show=False)
    return []


def _dur_s(t):
    try:
        parts = [float(x) for x in str(t or "").split(":") if x != ""]
        v = 0.0
        for x in parts: v = v * 60 + x
        return v
    except Exception:
        return 0.0


YT_ID = re.compile(r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([A-Za-z0-9_-]{11})")


def brave_videos(q, key=None, n=12):
    """v3.13: Brave VIDEO search (YouTube ki API quota kharch nahi hoti). YouTube wale result ka video_id +
    thumbnail + duration + creator – clip yt-dlp se sirf 4-5 sec kategi (visual_pick)."""
    if not q or not (key or BRAVE_KEYS):
        return []
    out = []
    for x in _brave_get("videos", q, n, key):
        url = x.get("url") or ""
        m = YT_ID.search(url)
        v = x.get("video") or {}
        th = (x.get("thumbnail") or {})
        out.append({"kind": "video", "provider": "brave", "url": url, "yt": m.group(1) if m else None,
                    "title": x.get("title") or "", "channel": v.get("creator") or "",
                    "publisher": v.get("publisher") or ((x.get("meta_url") or {}).get("hostname") or ""),
                    "duration_seconds": _dur_s(v.get("duration")), "view_count": int(v.get("views") or 0),
                    "thumb": th.get("src") or th.get("original") or (f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg" if m else None),
                    "credit": f"{(x.get('title') or '')[:70]} – {v.get('creator') or ''} ({url})"})
    return out


def brave_images(q, key, n=12):
    """Brave image search: return direct image URL + originating webpage for attribution."""
    if not q or not (key or BRAVE_KEYS):
        return []
    try:
        results = _brave_get("images", q, n, key)
    except Exception as exc:
        log(f"  brave image error: {exc}", show=False)
        return []
    out = []
    for x in results:
        props = x.get("properties") or {}
        direct = props.get("url") or x.get("image_url")
        page = x.get("url") or x.get("source")
        if not direct or not str(direct).lower().startswith("https://"):
            continue
        out.append({"kind": "image", "url": direct, "thumb": (x.get("thumbnail") or {}).get("src") or direct,
                    "title": x.get("title") or "", "w": props.get("width") or 0, "h": props.get("height") or 0,
                    "credit": f"Brave Images – {page or 'source page'}", "web": page})
    return out

STOP = set("""a an the of to in on at for from by with and or but is are was were be been being it its this that these those
as into about over under than then so very just also only even more most some any all each such can could would should will
may might must do does did done have has had not no yes there here who whom which what when where why how they them their he she
his her we our you your i me my mine us one two three four five six seven eight nine ten first second third fact facts like
get got make made know think thing things really now new lot lots many much way time times yes okay ok let lets said say says
listen look see actually means mean matter even because if else while during after before again almost around nearly
follow such crazy story begins starts real begins""".split())

SPACE_WORDS = set("mars moon planet space nasa rover galaxy star sun orbit astronaut rocket earth asteroid comet universe saturn jupiter venus mercury neptune uranus spacesuit iss telescope black hole".split())

_used = set()


def _key(url):
    return hashlib.md5(url.encode()).hexdigest()[:16]


BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

# small Hindi -> English list, last fallback when every online translator fails
HI_EN = {
 "मंगल": "mars", "ग्रह": "planet", "धूल": "dust", "नासा": "nasa", "रोवर": "rover", "पर्सिवरेंस": "perseverance rover",
 "स्पेससूट": "spacesuit", "अंतरिक्ष": "space", "एस्ट्रोनॉट": "astronaut", "अंतरिक्षयात्री": "astronaut", "चांद": "moon",
 "चंद्रमा": "moon", "सूरज": "sun", "सूर्य": "sun", "तारा": "star", "तारे": "stars", "धरती": "earth", "पृथ्वी": "earth",
 "समुद्र": "ocean", "पानी": "water", "आग": "fire", "बर्फ": "ice", "पहाड़": "mountain", "जंगल": "forest", "रेगिस्तान": "desert",
 "इंसान": "human", "इंसानों": "people", "लोग": "people", "बच्चे": "children", "दिमाग": "brain", "दिल": "heart",
 "फेफड़ों": "lungs", "फेफड़े": "lungs", "खून": "blood", "बाल": "hair", "आंख": "eye", "शरीर": "human body", "हड्डी": "bone",
 "थायरॉइड": "thyroid", "डॉक्टर": "doctor", "अस्पताल": "hospital", "दवा": "medicine", "वायरस": "virus", "बीमारी": "disease",
 "केमिकल": "chemical", "परक्लोरेट": "chemical laboratory", "लैब": "laboratory", "साइंटिस्ट": "scientist", "वैज्ञानिक": "scientist",
 "खोज": "discovery", "मिट्टी": "soil", "कण": "particles", "नैनोमीटर": "microscope", "माइक्रोस्कोप": "microscope",
 "जानवर": "animal", "शेर": "lion", "बाघ": "tiger", "हाथी": "elephant", "सांप": "snake", "मछली": "fish", "शार्क": "shark",
 "ऑक्टोपस": "octopus", "पक्षी": "bird", "कुत्ता": "dog", "बिल्ली": "cat", "पेड़": "tree", "फूल": "flower",
 "शहर": "city", "गांव": "village", "भारत": "india", "दुनिया": "world", "देश": "country", "सरकार": "government",
 "पैसा": "money", "पैसे": "money", "सोना": "gold", "हीरा": "diamond", "कार": "car", "ट्रेन": "train", "जहाज": "ship",
 "हवाई": "airplane", "प्लेन": "airplane", "रॉकेट": "rocket", "फोन": "smartphone", "कंप्यूटर": "computer", "इंटरनेट": "internet",
 "रोबोट": "robot", "बेस": "space station", "घर": "house", "खाना": "food", "बिजली": "lightning", "तूफान": "storm",
 "बारिश": "rain", "भूकंप": "earthquake", "ज्वालामुखी": "volcano", "रहस्य": "mystery", "खतरनाक": "danger", "जहरीली": "toxic",
 "डर": "fear", "मौत": "death", "समय": "clock", "इतिहास": "history", "राजा": "king", "किला": "fort", "मंदिर": "temple",
}


def _gtx(text):
    r = S.get("https://translate.googleapis.com/translate_a/single",
              params={"client": "gtx", "sl": "hi", "tl": "en", "dt": "t", "q": text},
              headers={"User-Agent": BROWSER_UA}, timeout=10)
    data = r.json()
    return "".join(p[0] for p in data[0] if p and p[0])


def _mymemory(text):
    r = S.get("https://api.mymemory.translated.net/get",
              params={"q": text[:480], "langpair": "hi|en"}, timeout=12)
    t = r.json().get("responseData", {}).get("translatedText", "")
    if "MYMEMORY WARNING" in t.upper():
        return ""
    return t


def _dict(text):
    out = []
    for w in re.split(r"[\s,।?!.]+", text):
        for hi, en in HI_EN.items():
            if w.startswith(hi) and en not in out:
                out.append(en)
    return " ".join(out)


_tr_dead = set()


def translate(text):
    """Hindi -> English. Tries Google, then MyMemory, then built-in word list."""
    for name, fn in (("google", _gtx), ("mymemory", _mymemory)):
        if name in _tr_dead:
            continue
        try:
            t = fn(text)
            if t and t.strip():
                return t
        except Exception as e:
            log(f"  translate ({name}) nahi hua: {e}", show=False)
            _tr_dead.add(name)
    return _dict(text)


WHO = {}          # line -> asli insaan/jagah/brand ka naam (Wikimedia photos ke liye)
SHOW = {}         # v2.17: line -> "kya dikhna chahiye" (Gemini Edit Director) – har check isi se
KEYW = {}         # v2.14: line -> sabse zaroori Hindi shabd (captions me laal)
LINKS = {}        # line -> script me diye links
LINK_POLICIES = {} # line -> FootageFlow rights/range hint
GTOPIC = []       # Gemini ka chuna hua topic (English)
MAIN = {}         # v3.1: video ka mukhya insaan/brand (biography) – {"name":..}
ENTITY = {}       # v3.1: line -> Wikidata entity (pakki pehchaan)
NEED_NAMECARD = {} # v3.1: line -> entity jiski free photo nahi mili
NO_AI_PHOTO = set()  # v3.2: in lines pe asli insaan ki AI (nakli) photo nahi
GEMINI_RAW = {}   # v3.2: poori script ka Gemini jawab (lock + lines)
RAW_PLAN = {}     # v3.1: line -> Gemini scene dict (scene_plan.py)
AVOID = {}        # v3.1 FIX: line -> cheezein jo NAHI dikhni chahiye (scene planner se). Pehle undefined tha.
EXTRA_SRC = {}    # v3.1 FIX: optional extra providers (brave key). Pehle ye define hi nahi tha -> NameError, 7/11 lines khali.


def gemini_queries(lines, key):
    """v2.10: Gemini se har line ke 4 search shabd + naam (agar koi asli insaan/jagah ho) + topic."""
    if not key:
        return None
    from ai import ask_json
    numbered = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
    prompt = ("You pick footage for a Hindi YouTube Shorts video. The viewer must SEE exactly what the voice says.\n"
              "FIRST read the WHOLE script and understand the full story: who/what it is about, how lines connect, "
              "who every pronoun (उनका/उन्होंने/वो/उसका/इसका) refers to. Every line's visuals must stay inside this "
              "one story and its main subject – never random/decorative unrelated footage.\n"
              "Return top-level \"lock\": {main_subject (exact English name of the main person/brand/place/topic), "
              "main_type (person/brand/place/topic), topic (3-6 words), story (1-2 sentences), secondary_subjects "
              "[..], allowed_subjects [8-14 concrete filmable things that belong to THIS story, e.g. for a gamer: "
              "his face, his gameplay, gaming setup, controller, headset], forbidden_subjects [6-12 things that "
              "would be wrong here, e.g. unrelated people, random fire, unrelated science/space, abstract "
              "animation]}.\n"
              "Per line ALSO: uses_main (true if the line is about the main subject, incl. pronouns), action "
              "(what the subject is doing), context (where/when), objects [..], footage_type "
              "(real_subject_clip / subject_photo / stock / map / 3d / graphic), query (ONE best search query "
              "for real footage of exactly this moment, include the main subject's name when uses_main).\n"
              "For EACH numbered line return:\n"
              " q: 4 short English search queries (2-4 words) for Pixabay/Pexels stock VIDEO search. CRITICAL "
              "TOPIC-LOCK RULE: EVERY single query MUST stay strictly inside the main story world/environment! "
              "NEVER output isolated trap words like 'water pressure' (gives street pressure-washer), "
              "'story'/book' (gives people reading a book), 'computer system'/new technology' "
              "(gives random robots/cyborgs), or 'pollution' (gives wildfires) — ALWAYS anchor to the story "
              "setting (e.g., for Mariana Trench: 'deep sea submarine', 'dark ocean abyss', "
              "'bioluminescent deep sea fish', 'ocean plastic waste underwater', 'underwater exploration rover'). "
              "NEVER pick clips with burned-in English subtitles or news logos (Tech Insider, etc.). "
              "Only filmable real-world scenes inside THIS video's world. Set visual_mode to 'AI_SCENE' ONLY when the line is an abstract comparison, metaphor or an impossible/never-filmed scene that no real footage could show; NEVER for a line about a real named person, a real current or news event, a real company/product, a real sports moment or a real crime case (those need REAL footage – set visual_mode 'STOCK'). For AI_SCENE write a vivid 1-sentence photorealistic documentary scene description in ai_prompt; otherwise set visual_mode to 'STOCK'. "
              "Stock sites have NO celebrities/films/brands, so for those use generic visuals (e.g. 'film shooting set', "
              "'red carpet event', 'rocket launch').\n"
              " who: if the line is about a specific REAL famous person, place, building, film or company, its exact "
              "English name as on Wikipedia (e.g. 'Ranbir Kapoor', 'Elon Musk', 'Taj Mahal'); else \"\".\n"
              " key: the ONE most important / shocking word of the line, copied EXACTLY as written in the line "
              "(e.g. a number, 'ज़हर', 'खतरनाक'); \"\" for plain lines.\n"
              " show: ONE short English sentence – exactly what the viewer must SEE during this line, concrete and "
              "literal (e.g. 'a great white shark swimming close to camera'). Think like a pro editor: the visual must "
              "prove the words. If the line is abstract, show the closest real concrete thing.\n"
              " Scene fields (v3.1 scene planner, keep each short): meaning (what the line means), subject, action, "
              "environment, time (era), domain (one of space/ocean/biology/science/technology/history/geography/mystery/"
              "money/nature/biography/general), emotion (shock/mystery/danger/hype/wonder/sad/cta/info), "
              "avoid (list of 2-4 things that would be WRONG to show for this line, e.g. a different person/place), "
              "template (best procedural 3D scene if no real footage exists: space/planet/globe/solar_system/dna/"
              "molecule/cell/underwater/technology/mystery/history/infographic/energy/abstract, or \"\" for real "
              "people/brands).\n"
              " roman: the SAME Hindi line written in natural Hinglish (Latin letters) for captions, EXACTLY the same "
              "number of words in the same order; English loanwords in English spelling (gaming, career, YouTube), "
              "names correctly (CarryMinati -> Carry Minati if written as 2 words).\n"
              "Also return topic: 2-3 English words for the whole video.\n"
              'Return ONLY JSON: {"topic": "...", "lines": [{"q": ["..",".."], "who": "..", "key": ".."}]}\n\n' + numbered)
    prompt = prompt.replace('"who": "..", "key": ".."', '"who": "..", "key": "..", "show": "..", "meaning": "..", '
                            '"subject": "..", "action": "..", "environment": "..", "time": "..", "domain": "..", '
                            '"emotion": "..", "avoid": [".."], "template": "..", "who_type": "person|brand|place|thing", "roman": "..", '
                            '"uses_main": true, "action": "..", "context": "..", "objects": [".."], '
                            '"footage_type": "..", "query": "..", "visual_mode": "STOCK|AI_SCENE", "ai_prompt": ".."')
    prompt = prompt.replace('Return ONLY JSON: {"topic": "...", "lines"', 'Return ONLY JSON: {"lock": {...}, "topic": "...", "lines"')
    data = ask_json(key, [prompt], temperature=0.3, timeout=120)
    if isinstance(data, list):
        data = {"lines": data}
    if not isinstance(data, dict) or not data.get("lines"):
        return None
    GEMINI_RAW.clear(); GEMINI_RAW.update(data)               # v3.2: identity lock ke liye poora jawab
    out = []
    for i, x in enumerate(data["lines"]):
        if isinstance(x, dict):
            q = [v for v in (x.get("q") or []) if isinstance(v, str)]
            # v3.55 UNIVERSAL TOPIC-ANCHOR GUARD: works for ANY topic (cricket, finance, history, crime, science, tech, etc.)!
            _lock_subj = str((data.get("lock") or {}).get("main_subject") or "").strip()
            _vid_topic = str(data.get("topic") or "").strip()
            _anc = (_vid_topic or _lock_subj).strip()
            _ABSTRACT_TRAPS = (
                "pressure", "story", "book", "secret", "mystery", "truth", "shock", "danger",
                "technology", "computer", "internet", "system", "future", "power", "problem",
                "mistake", "plan", "idea", "fact", "proof", "pollution", "robot", "cyborg", "success", "failure"
            )
            if _anc:
                _anc_low = _anc.lower()
                _clean_q = []
                for _qi in q:
                    _ql = _qi.strip().lower()
                    # If query is short/abstract and does NOT already mention the video topic, anchor it to THIS video's topic!
                    if len(_ql.split()) <= 2 and _anc_low not in _ql and any(_t in _ql for _t in _ABSTRACT_TRAPS):
                        _clean_q.append(f"{_anc} {_qi}".strip()[:52])
                    else:
                        _clean_q.append(_qi)
                q = _clean_q
            w = (x.get("who") or "").strip()
            if w and len(w) < 60: WHO[i] = w
            k = (x.get("key") or "").strip()
            if k and len(k) < 30: KEYW[i] = k
            sh = (x.get("show") or "").strip()
            if sh and len(sh) < 160: SHOW[i] = sh                 # v2.17: Edit Director – kya dikhna chahiye
            RAW_PLAN[i] = x                                       # v3.1: scene planner ke liye poora dict
            try:                                                  # v3.1: Gemini ki Hinglish spelling -> captions
                rom = str(x.get("roman") or "").split(); hw_ = lines[i].split() if i < len(lines) else []
                if rom and len(rom) == len(hw_):
                    import translit
                    for h_, r_ in zip(hw_, rom):
                        hc = re.sub(r"[।,!?.\"'“”‘’:;()\-]+$", "", h_); rc = re.sub(r"[.,!?;:\"']+$", "", r_)
                        if hc and rc and re.search(r"[\u0900-\u097F]", hc) and hc not in translit.FIX:
                            translit.OVERRIDE[hc] = rc
            except Exception:
                pass
            av = [a for a in (x.get("avoid") or []) if isinstance(a, str) and a.strip()]
            if av: AVOID[i] = tuple(av[:4])
        else:
            q = [v for v in (x if isinstance(x, list) else [x]) if isinstance(v, str)]
        out.append(q)
    GTOPIC[:] = [w for w in re.findall(r"[a-z]+", str(data.get("topic", "")).lower())][:3]
    return out if len(out) >= len(lines) * 0.8 else None


def person_photos(name, need):
    """Asli insaan/jagah ki free (CC) photos Wikimedia Commons se – naam title me hona chahiye."""
    toks = [t for t in re.findall(r"[a-z]+", name.lower()) if len(t) > 2]
    out = []
    for c in wikimedia(name):
        t = c.get("credit", "").lower() + " " + c.get("url", "").lower()
        if toks and not all(tk in t for tk in toks[:2]):
            continue
        out.append(c)
        if len(out) >= need * 2: break
    return out


# ---------- script ke links
VID_EXT = (".mp4", ".webm", ".mov", ".m4v", ".mkv")
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")


def resolve_link(url, keys, policy=None):
    # Optional caller policy is accepted for compatibility, but never overrides source safety.
    """Link -> download hone layak item. Returns item dict or None (+ kaaran)."""
    u = url.strip()
    low = u.lower().split("?")[0]
    host = re.sub(r"^https?://", "", low).split("/", 1)[0]
    if "googlevideo.com" in host or "youtube.com" in host or "youtu.be" in host:
        return None, "YouTube API/Terms: reference/CDN ko yt-dlp authorized flow se handle karein"
    if host in {"vimeo.com", "www.vimeo.com", "player.vimeo.com", "dailymotion.com", "www.dailymotion.com", "dai.ly", "x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        import footageflow_engine as ff
        rights = (policy or {}).get("rights", "")
        permission = bool((policy or {}).get("explicit_permission"))
        allowed, why = ff.host_allowed(u)
        if not allowed: return None, why
        if not ff._rights_ok(rights, permission): return None, "FootageFlow: rights unknown; reusable licence/permission required"
        return {"provider": "footageflow", "kind": "video", "url": u, "rights_status": rights,
                "explicit_permission": permission, "start": (policy or {}).get("start"),
                "end": (policy or {}).get("end"), "credit": f"FootageFlow source – {u}"}, ""
    if any(x in low for x in ("instagram.com", "facebook.com", "tiktok.com")):
        return None, "YouTube API/Terms: YouTube/Instagram download link blocked (copyright/niyam)"
    pk = keys.get("PIXABAY")
    m = re.search(r"pixabay\.com/(videos|photos|illustrations|vectors)/[^/]*?-(\d+)/?", u)
    if m and pk:
        try:
            if m.group(1) == "videos":
                h = S.get("https://pixabay.com/api/videos/", params={"key": pk, "id": m.group(2)}, timeout=TIMEOUT).json()["hits"][0]
                v = h["videos"]; best = v.get("large") or v.get("medium") or v.get("small")
                return {"kind": "video", "url": best["url"], "credit": f"Pixabay – {h.get('user','')} ({h.get('pageURL','')})"}, ""
            h = S.get("https://pixabay.com/api/", params={"key": pk, "id": m.group(2)}, timeout=TIMEOUT).json()["hits"][0]
            return {"kind": "image", "url": h.get("largeImageURL") or h.get("webformatURL"),
                    "credit": f"Pixabay – {h.get('user','')} ({h.get('pageURL','')})"}, ""
        except Exception as e:
            return None, f"Pixabay link nahi khula ({e})"
    m = re.search(r"commons\.wikimedia\.org/wiki/(File:[^?#]+)", u)
    if m:
        try:
            r = S.get("https://commons.wikimedia.org/w/api.php", params={"action": "query", "format": "json",
                      "titles": requests.utils.unquote(m.group(1)), "prop": "imageinfo", "iiprop": "url|mime",
                      "iiurlwidth": 1600}, timeout=TIMEOUT).json()
            ii = list(r["query"]["pages"].values())[0]["imageinfo"][0]
            kind = "video" if "video" in ii.get("mime", "") else "image"
            return {"kind": kind, "url": ii.get("url") if kind == "video" else (ii.get("thumburl") or ii["url"]),
                    "credit": f"Wikimedia Commons ({u})"}, ""
        except Exception as e:
            return None, f"Wikimedia link nahi khula ({e})"
    m = re.search(r"[?&](?:imgurl|mediaurl)=([^&]+)", u)          # Google/Bing image result link
    if m:
        u = requests.utils.unquote(m.group(1)); low = u.lower().split("?")[0]
    if low.endswith(VID_EXT):
        return {"kind": "video", "url": u, "credit": f"Link: {u[:80]}"}, ""
    if low.endswith(IMG_EXT):
        return {"kind": "image", "url": u, "credit": f"Link: {u[:80]}"}, ""
    try:
        r = S.head(u, allow_redirects=True, timeout=TIMEOUT)
        ct = r.headers.get("content-type", "")
        if ct.startswith("video/"): return {"kind": "video", "url": r.url, "credit": f"Link: {u[:80]}"}, ""
        if ct.startswith("image/"): return {"kind": "image", "url": r.url, "credit": f"Link: {u[:80]}"}, ""
    except Exception:
        pass
    return None, "ye link seedha video/photo nahi hai (photo pe right-click > 'Copy image address' wala link do)"


def keywords(eng, topic_words=()):
    words = re.findall(r"[A-Za-z][A-Za-z\-]+", eng.lower())
    seen = []
    try:                                     # v3.13 FIX: topic "must, have, been" jaise bekaar shabd nahi
        from identity_lock import KW_STOP as _ks
    except Exception:
        _ks = set()
    for w in words:
        w = w.strip("-")
        if len(w) > 2 and w not in STOP and w not in _ks and w not in seen:
            seen.append(w)
    return seen[:5]




def queries_for(kw, topic):
    q = []
    if len(kw) >= 2: q.append(" ".join(kw[:2]))
    if kw: q.append(kw[0])
    if len(kw) >= 3: q.append(kw[1] + " " + kw[2]); q.append(kw[1])
    if topic:
        if kw: q.append(topic[0] + " " + kw[0])
        q.append(" ".join(topic[:2])); q.append(topic[0])
    out = []
    for x in q:
        x = x.strip()
        if x and x not in out:
            out.append(x)
    return out


# ------------------------------------------------------------ providers
def pexels_videos(q, key):
    """v3.8: Pexels video search (free API key: pexels.com/api). 720p+ file, khadi pehle."""
    if not key: return []
    try:
        r = S.get("https://api.pexels.com/videos/search", params={"query": q, "per_page": 15},
                  headers={"Authorization": key}, timeout=TIMEOUT)
        vids = r.json().get("videos", [])
    except Exception as e:
        log(f"  pexels video error: {e}", show=False); return []
    out = []
    for v in vids:
        files = [f for f in (v.get("video_files") or []) if f.get("link") and (f.get("file_type") or "").endswith("mp4")
                 and min(f.get("width") or 0, f.get("height") or 0) >= 700]
        if not files: continue
        best = sorted(files, key=lambda f: (abs(min(f.get("width") or 0, f.get("height") or 0) - 1080)))[0]
        portrait = (best.get("height") or 0) > (best.get("width") or 1)
        tags = re.sub(r"[-/]", " ", (v.get("url") or "").rstrip("/").split("/")[-1])
        out.append({"kind": "video", "url": best["link"], "portrait": portrait, "thumb": v.get("image"),
                    "tags": re.sub(r"\d+$", "", tags).strip(),
                    "credit": f"Pexels – {(v.get('user') or {}).get('name', '')} ({v.get('url', '')})"})
    out.sort(key=lambda x: not x["portrait"])
    return out


def pixabay_videos(q, key):
    if not key: return []
    try:
        r = S.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 15,
                  "safesearch": "true"}, timeout=TIMEOUT)
        hits = r.json().get("hits", [])
    except Exception as e:
        log(f"  pixabay video error: {e}", show=False); return []
    out = []
    for h in hits:
        v = h.get("videos", {})
        # v2.2 quality: pehle 1080p (large), phir 720p (medium). 720p se chhoti video nahi lete.
        best = None
        for k in ("large", "medium"):
            c = v.get(k) or {}
            if c.get("url") and min(c.get("width", 0), c.get("height", 0)) >= 700:
                best = c; break
        if best:
            portrait = best.get("height", 0) > best.get("width", 1)
            thumb = best.get("thumbnail") or (v.get("tiny") or {}).get("thumbnail") or \
                (f"https://i.vimeocdn.com/video/{h['picture_id']}_640x360.jpg" if h.get("picture_id") else None)
            out.append({"kind": "video", "url": best["url"], "portrait": portrait, "thumb": thumb,
                        "tags": h.get("tags", ""),
                        "credit": f"Pixabay – {h.get('user','')} ({h.get('pageURL','')})"})
    out.sort(key=lambda x: not x["portrait"])      # khadi (9:16) videos pehle – zoom nahi karna padta
    return out


def pixabay_images(q, key, vertical=True):
    if not key: return []
    try:
        p = {"key": key, "q": q, "per_page": 20, "image_type": "photo", "safesearch": "true"}
        if vertical: p["orientation"] = "vertical"
        hits = S.get("https://pixabay.com/api/", params=p, timeout=TIMEOUT).json().get("hits", [])
    except Exception as e:
        log(f"  pixabay photo error: {e}", show=False); return []
    return [{"kind": "image", "url": h["largeImageURL"],
             "credit": f"Pixabay – {h.get('user','')} ({h.get('pageURL','')})"} for h in hits if h.get("largeImageURL")]


def _ok_licence(lic):
    l = (lic or "").lower()
    if "sa" in re.findall(r"[a-z]+", l) or "nc" in re.findall(r"[a-z]+", l) or "nd" in re.findall(r"[a-z]+", l):
        return False
    return any(x in l for x in ("cc0", "public domain", "pd", "cc by", "cc-by", "pdm", "by"))


def wikimedia(q):
    try:
        r = S.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1600}, timeout=TIMEOUT)
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:
        log(f"  wikimedia error: {e}", show=False); return []
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        title = p.get("title", "").lower()
        if not _ok_licence(lic) or ii.get("width", 0) < 1000 or ii.get("height", 0) < 700:
            continue
        if re.search(r"(map|diagram|chart|graph|plot|logo|icon|flag|coat of arms|seal|signature|table|scheme|"
                     r"svg|drawing|sketch|stamp|poster|cover|text|page|document|scan|\.png$|\.gif$|\.tif)", title):
            continue
        artist = re.sub("<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
        out.append({"kind": "image", "url": ii.get("thumburl") or ii.get("url"),
                    "credit": f"Wikimedia Commons – {artist or 'unknown'} – {lic} ({ii.get('descriptionurl','')})"})
    return out


def openverse(q):
    try:
        r = S.get("https://api.openverse.org/v1/images/", params={
            "q": q, "license": "cc0,pdm,by", "page_size": 15, "mature": "false"}, timeout=TIMEOUT)
        res = r.json().get("results", [])
    except Exception as e:
        log(f"  openverse error: {e}", show=False); return []
    out = []
    for x in res:
        if (x.get("width") or 1200) < 1000:
            continue
        if re.search(r"(map|diagram|chart|graph|logo|icon|text|poster|drawing)", (x.get("title") or "").lower()):
            continue
        lic = f"{x.get('license','')} {x.get('license_version','')}".strip().upper()
        out.append({"kind": "image", "url": x.get("url"),
                    "credit": f"Openverse/{x.get('source','')} – {x.get('creator') or 'unknown'} – CC {lic} ({x.get('foreign_landing_url','')})"})
    return out


def nasa(q):
    try:
        r = S.get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "image"}, timeout=TIMEOUT)
        items = r.json().get("collection", {}).get("items", [])[:15]
    except Exception as e:
        log(f"  nasa error: {e}", show=False); return []
    out = []
    for it in items:
        links = it.get("links") or []
        if not links: continue
        href = links[0].get("href", "")
        title = (it.get("data") or [{}])[0].get("title", "")
        cands = [href.replace("~thumb", "~large"), href.replace("~thumb", "~medium"), href]
        out.append({"kind": "image", "url": cands[0], "alts": cands[1:],
                    "credit": f"NASA – {title}"})
    return out


def nasa_videos(q):
    """NASA video library (public domain). Picks a small/mobile mp4."""
    try:
        r = S.get("https://images-api.nasa.gov/search", params={"q": q, "media_type": "video"}, timeout=TIMEOUT)
        items = r.json().get("collection", {}).get("items", [])[:3]
    except Exception as e:
        log(f"  nasa video error: {e}", show=False); return []
    out = []
    for it in items:
        try:
            urls = S.get(it["href"], timeout=TIMEOUT).json()
        except Exception:
            continue
        mp4 = [u for u in urls if u.lower().endswith(".mp4")]
        # v2.2 quality: badi (HD) file; sirf 5 sec ka tukda aata hai isliye download chhota hi rehta hai
        pick = next((u for u in mp4 if "~medium" in u), None) or next((u for u in mp4 if "~large" in u), None)
        if pick:
            title = (it.get("data") or [{}])[0].get("title", "")
            thumb = next((l.get("href") for l in it.get("links", []) if l.get("render") == "image"), None)
            out.append({"kind": "video", "url": pick.replace("http://", "https://"), "credit": f"NASA – {title}",
                        "thumb": thumb, "tags": title})
    return out


def wikimedia_videos(q):
    try:
        r = S.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{q} filetype:video",
            "gsrnamespace": 6, "gsrlimit": 10, "prop": "imageinfo", "iiprop": "url|extmetadata|size"}, timeout=TIMEOUT)
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:
        log(f"  wikimedia video error: {e}", show=False); return []
    out = []
    for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (p.get("imageinfo") or [{}])[0]
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        if not _ok_licence(lic) or ii.get("size", 0) > 300 * 1024 * 1024 or min(ii.get("width", 0), ii.get("height", 0)) < 700:
            continue
        artist = re.sub("<[^>]+>", "", ii.get("extmetadata", {}).get("Artist", {}).get("value", "")).strip()
        out.append({"kind": "video", "url": ii.get("url"),
                    "credit": f"Wikimedia Commons – {artist or 'unknown'} – {lic} ({ii.get('descriptionurl','')})"})
    return out


# ------------------------------------------------------------ download
import threading, subprocess
_lock = threading.Lock()


def fetch_clip(url, secs=5.0):
    """Badi video poori download nahi karta – sirf ~5 second ka tukda. Aadhi/kharab file cache me nahi rehti."""
    from requests.utils import requote_uri
    url = requote_uri(url)
    dst = CACHE / (_key(url + "#clip") + ".mp4")
    if dst.exists() and dst.stat().st_size > 20000:
        return dst
    import threading, uuid
    part = dst.with_name(dst.stem + f".{uuid.uuid4().hex[:6]}.part.mp4")
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            "-user_agent", BROWSER_UA, url], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL)
        total = float(r.stdout.strip() or 0)
    except Exception:
        total = 0
    start = random.uniform(total * 0.1, max(total * 0.1, total * 0.75 - secs)) if total > secs * 2 else 0
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-user_agent", BROWSER_UA, "-ss", f"{start:.2f}",
                            "-i", url, "-t", f"{secs:.1f}", "-an", "-vf", "scale='min(1920,iw)':-2", "-c:v", "libx264",
                            "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", str(part)],
                           capture_output=True, timeout=75, stdin=subprocess.DEVNULL)
        if r.returncode == 0 and part.exists() and part.stat().st_size > 20000:
            try:
                part.replace(dst)
            except OSError:                       # doosre thread ne pehle hi bana li
                if dst.exists():
                    try: part.unlink()
                    except Exception: pass
                    return dst
                raise
            return dst
    except Exception as e:
        log(f"  clip fetch fail: {str(e)[:150]}", show=False)
    try:
        if part.exists(): part.unlink()
    except Exception:
        pass
    return None


def valid_media(path, kind="video"):
    """v2.17c: file sach me khulti hai? (aadhi download = 'moov atom not found' – ab pakdi jaati hai)"""
    try:
        if kind == "image":
            from PIL import Image
            with Image.open(path) as im: im.verify()
            return True
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        if r.returncode != 0: return False
        nums = re.findall(r"[\d.]+", r.stdout)
        return len(nums) >= 2 and float(nums[-1] or 0) > 0.5
    except Exception:
        return False


def download(item):
    if item.get("provider") == "footageflow":
        import footageflow_engine as ff
        p = ff.download_authorized_link(item, CACHE / "footageflow")
        return p if p and valid_media(p, item.get("kind", "video")) else None
    p = _download(item)
    if p and not valid_media(p, item.get("kind", "video")):
        log(f"   tooti file mili, hata di: {Path(p).name}", show=False)
        try: Path(p).unlink()
        except Exception: pass
        return None
    return p


def _download(item):
    CACHE.mkdir(parents=True, exist_ok=True)
    for url in [item["url"]] + item.get("alts", []):
        ext = Path(url.split("?")[0]).suffix.lower()
        if item["kind"] == "video":
            if ext not in (".mp4", ".webm", ".ogv", ".mov"): ext = ".mp4"
        elif ext not in (".jpg", ".jpeg", ".png", ".webp"): ext = ".jpg"
        dst = CACHE / (_key(url) + ext)
        if dst.exists() and dst.stat().st_size > 5000:
            return dst
        if item["kind"] == "video":
            c = fetch_clip(url)           # v2.2: HD video ka sirf 5 sec tukda (Pixabay bhi)
            if c: return c
            if "pixabay" not in url: continue
        try:
            with S.get(url, stream=True, timeout=40) as r:
                if r.status_code != 200: continue
                size = 0
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(1 << 16):
                        f.write(chunk); size += len(chunk)
                        if size > 60 * 1024 * 1024:
                            size = -1; break                  # v2.17c: aadhi file nahi rakhni
            if size > 0 and dst.stat().st_size > 5000:
                return dst
        except Exception as e:
            log(f"  download fail: {e}", show=False)
        if dst.exists(): dst.unlink()
    return None


def my_clips_for(idx):
    folder = TOOL / "my_clips"
    if not folder.exists(): return []
    out = []
    for p in sorted(folder.glob("*")):
        m = re.match(r"0*(\d+)", p.stem)
        if m and int(m.group(1)) == idx + 1:
            kind = "video" if p.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv") else "image"
            out.append({"kind": kind, "path": p, "credit": ""})
    return out


PHOTO_MODE = {"v": "kam"}


def style_photos_ok(need, got):
    """photo = kam (default): sirf jab video na mile.  photo = haan: purana tareeka (mix)."""
    return PHOTO_MODE["v"] == "haan"


CHECK = {"on": True}
STRICT = {"on": True}
WHO_ON = {"on": True}


ENT_COUNT = {}      # v3.1: photo url -> kitni lines pe lagi
ENT_USED = {}       # v3.1: entity -> {url: line} – ek hi photo har line pe na aaye


def yt_clips_chan_ok(c, name):
    try:
        import yt_clips
        ch = c.get("channel") or ""
        return (not ch) or yt_clips.chan_ok(ch, name)
    except Exception:
        return True


def _spread(qid, med, idx):
    """Pehle wo photo/video jo kisi aur line pe nahi lagi; sab lag chuki ho to sabse kam use wali."""
    with _lock:
        used = ENT_USED.setdefault(qid, {})
        fresh = [m for m in med if m["url"] not in used]
        old = sorted([m for m in med if m["url"] in used], key=lambda m: list(used).index(m["url"]))
        out = fresh + old
        for m in out[:2]:
            used.setdefault(m["url"], idx)
    return out


def _latin_name(text):
    """Offline: Hindi line me Latin me likha brand/naam (NVIDIA, iPhone, ChatGPT, Tesla) – entity ke liye."""
    m = re.findall(r"\b([A-Z][A-Za-z0-9\-]{2,}(?:\s+[A-Z][A-Za-z0-9\-]{2,})?)\b", text or "")
    m = [x for x in m if x.lower() not in STOP and x.upper() not in ("THE", "AND", "YOU", "WHO")]
    return m[0] if m else None


def yes_who():
    return WHO_ON["on"]


TAGS_ON = {"on": True}


def yes_tags():
    return TAGS_ON["on"] and CHECK["on"]


def _thumb_bytes(url):
    try:
        r = S.get(url, timeout=15)
        if r.status_code == 200 and len(r.content) > 1500:
            from PIL import Image
            import io
            im = Image.open(io.BytesIO(r.content)).convert("RGB"); im.thumbnail((384, 384))
            b = io.BytesIO(); im.save(b, "JPEG", quality=80); return b.getvalue()
    except Exception:
        pass
    return None


STOP = set("the a an of to in on and or for with is are was were be this that it its from by at as into their "
           "his her they them you your we our can will one two three first second third more most very".split())


def _toks(t):
    out = set()
    for w in re.findall(r"[a-z]+", (t or "").lower()):
        if len(w) < 3 or w in STOP: continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def tag_rank(cands, words):
    """v2.14: Gemini ke bina – clip ke tags/naam ko line ke shabdon se milao. (good_in_order, bad)."""
    want = set()
    for w in words: want |= _toks(w)
    if not want:
        return None
    sc = []
    for i, c in enumerate(cands):
        have = _toks(c.get("tags", "")) | _toks(c.get("credit", ""))
        sc.append((len(want & have), i))
    good = [i for n, i in sorted(sc, key=lambda x: -x[0]) if n > 0]
    bad = [i for n, i in sc if n == 0]
    return (good, bad) if good else None


def gemini_rank(key, line, eng, cands, avoid=()):
    """v2.15 STRICT: Gemini har clip ko 0-10 number deta hai – sirf 7+ wali lagti hain.
    Returns (good_in_order, bad) – indices of cands."""
    from ai import ask_json
    parts = [("You are a STRICT video editor checking stock footage for ONE line of a Hindi fact Short. "
              "The viewer must instantly SEE what the voice is saying.\n"
              f"Line (Hindi): {line}\nWhat must be visible (English): {eng}\n"
              "Score every numbered thumbnail 0-10:\n"
              "10 = exactly the subject of the line (same object/animal/place/person/event).\n"
              "7-9 = clearly the same subject, different angle, or a very close real visual of it.\n"
              "4-6 = same general topic but NOT what the line says (e.g. line is about a shark, clip shows a dolphin; "
              "line about Mars, clip shows the Moon; line about India, clip shows another country).\n"
              "0-3 = unrelated, misleading, cartoon/3D when the line is about something real, text slides, logos, "
              "watermarks, interviews or talking heads (unless the line is about them), black/blurry frames.\n"
              "Be strict: if you are not sure it is the right subject, give 5 or less.\n"
              'Return ONLY JSON: {"scores": [{"clip": number, "score": 0-10}]}')]
    idx = []
    for i, c in enumerate(cands):
        b = _thumb_bytes(c["thumb"]) if c.get("thumb") else None
        if not b: continue
        parts += [f"Clip {i}:", {"jpg": b}]; idx.append(i)
    if len(idx) < 2:
        return None
    res = ask_json(key, parts, temperature=0.0, timeout=60, budget=180)
    if not isinstance(res, dict):
        return None
    sc = {}
    for x in res.get("scores") or []:
        try:
            k = int(x.get("clip")); v = float(x.get("score"))
        except Exception:
            continue
        if k in idx: sc[k] = v
    if not sc and (res.get("good") or res.get("bad")):          # purana jawab format
        def nums(x):
            out = []
            for v in x or []:
                try: v = int(v)
                except Exception: continue
                if v in idx and v not in out: out.append(v)
            return out
        return nums(res.get("good")), nums(res.get("bad"))
    if not sc:
        return None
    lim = STRICT_SCORE["v"]
    good = [k for k, v in sorted(sc.items(), key=lambda kv: -kv[1]) if v >= lim]
    bad = [k for k, v in sc.items() if v < lim - 1.5]
    return good, bad


STRICT_SCORE = {"v": 7.0}       # style.txt: footage_sakhti = 7  (0-10, zyada = aur strict)


def double_check(good, cands, eng, extra):
    """v2.15: Gemini ne 'sahi' bola – AI aankh (CLIP) bhi dekh le. Dono bole kharab tabhi hatao (galti kam)."""
    if not AANKH["on"] or not good:
        return good
    try:
        import aankh
        if not aankh.STATE["ok"]:
            return good
        sub = [cands[i] for i in good]
        r = aankh.rank(sub, eng, _thumb_bytes, extra)
        if not r:
            return good
        _, bad = r
        badset = {good[j] for j in bad}
        keep = [g for g in good if g not in badset]
        return keep or good[:1]
    except Exception:
        return good


AANKH = {"on": True}            # style.txt: ai_aankh = haan
LOCK_REF = {"v": None}          # v3.9: identity lock (fallback B-roll ke liye)
GEM_FOOTAGE = {"on": False}     # v2.17c: gemini_footage = haan -> har line Gemini se (zyada limit kharch)


def green_frac(img):
    """Frame me 'green screen' wala hara kitna hai (0..1)."""
    import numpy as np
    a = np.asarray(img.convert("RGB").resize((96, 96))).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return float(((g > 90) & (g > r * 1.45) & (g > b * 1.45)).mean())


def is_green(path, kind="video", tags=""):
    if re.search(r"green\s*screen|chroma|greenscreen", tags or "", re.I):
        return True
    try:
        from PIL import Image
        if kind == "image":
            return green_frac(Image.open(path)) > 0.22
        import io as _io
        from common import duration
        d = duration(path) or 3
        for f in (0.3, 0.7):
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d*f:.2f}", "-i", str(path), "-frames:v", "1",
                                "-vf", "scale=160:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True,
                               timeout=30, stdin=subprocess.DEVNULL)
            if r.stdout and green_frac(Image.open(_io.BytesIO(r.stdout))) > 0.22:
                return True
    except Exception:
        pass
    return False


GREEN = {"mode": "key"}          # v2.17c: key = hara hata ke background pe / nahi = green screen clip mat lo


def green_bg(topic, keys, eng=""):
    """Green screen cheez ke peeche ke liye topic wala background (bina hare ka)."""
    pkey = keys.get("PIXABAY")
    if not pkey: return None
    qs = []
    t0 = (topic or [""])[0] if topic else ""
    for q in ([f"{t0} landscape", f"{t0} background"] if t0 else []) + ["forest landscape", "nature landscape"]:
        if q.strip() and q not in qs: qs.append(q.strip())
    for q in qs:
        for c in pixabay_videos(q, pkey)[:6]:
            if re.search(r"green\s*screen|chroma", c.get("tags", ""), re.I): continue
            p = download(c)
            if p and not is_green(p, "video"):
                return p
    return None


SCORES = []        # v3.1: har jaanchi gayi clip ka relevance score (QC report me)
VERIFY = {"on": True, "min": 0.180}   # v2.17: download ke baad clip ke 3 frame AI aankh se jaanch
REJECTED = {}      # v3.13 (Bug B): line -> [{"path","kind","score","why",...}] – sab reject ho to sabse achhi wapas
AVOID_MARGIN = 0.03   # v3.13: "avoid" cheez line se itna zyada mile (aur aadhe+ frames me) tabhi reject


def _short(text):
    """Lambi English line -> CLIP ke liye chhote shabd (CLIP lambi line pe kamzor score deta hai)."""
    try:
        import identity_lock
        return identity_lock.kw_show(text or "", MAIN.get("name") or "")
    except Exception:
        return ""


def _protected(term):
    """v3.13 FIX (Yash video): mukhya insaan / allowed cheez KABHI 'avoid' nahi ho sakti (pehle line 2 pe 'Yash'
    hi avoid list me tha -> Yash ki har clip reject)."""
    t = (term or "").strip().lower()
    if not t: return True
    mn = (MAIN.get("name") or "").strip().lower()
    lk = LOCK_REF.get("v") or {}
    keep = [mn, (lk.get("main_subject") or "").lower()] + [str(x).lower() for x in (lk.get("allowed_subjects") or [])[:4]]
    return any(k and (t == k or t in k.split() or k in t.split()) for k in keep)


def verify(path, kind, text, extra=(), avoid=(), line_idx=None):
    """Download hui clip/photo sach me line wali cheez dikhati hai? (AI aankh, 3 frame). True / False / None(jaanch nahi).
    v3.13 (Bug B): (1) line ke chhote shabd bhi milaye jaate hain, (2) 'avoid' tabhi reject jab wo line se
    AVOID_MARGIN zyada aur aadhe+ frames me jeete, (3) mukhya insaan kabhi avoid nahi, (4) har reject ki wajah log me
    + REJECTED me (sab reject ho jaye to sabse achhi clip wapas aati hai – chupchaap sab kuch nahi phenka jaata)."""
    if not (VERIFY["on"] and AANKH["on"] and text):
        return None
    try:
        import aankh
        if not aankh.STATE["ok"]: return None
        from PIL import Image
        ims = []
        if kind == "image":
            ims = [Image.open(path).convert("RGB")]
        else:
            import subprocess
            from common import duration
            d = duration(path) or 3
            for f in (0.2, 0.5, 0.8):
                r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d*f:.2f}", "-i", str(path), "-frames:v", "1",
                                    "-vf", "scale=320:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                                   capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
                if r.stdout:
                    import io as _io
                    ims.append(Image.open(_io.BytesIO(r.stdout)).convert("RGB"))
        if not ims: return None
        import numpy as _np
        # v3.57 TURBO: Single-pass CLIP batch scoring (encodes 3 frames ONCE instead of 8x — 100% identical math!)
        qs = [q for q in list(extra)[:2] if q]
        sh = _short(text)
        if sh and sh.lower() != str(text).lower(): qs.append(sh)
        av_list = [a for a in list(avoid)[:4] if not _protected(a)]
        all_texts = [text] + qs + av_list
        sim, neg = aankh.scores_batch(ims, all_texts)
        per = _np.asarray(sim[:, 0], dtype=float)
        for qi in range(1, 1 + len(qs)):
            per = _np.maximum(per, _np.asarray(sim[:, qi], dtype=float) - 0.01)
        best = float(per.max())
        bad_frames = int(((neg > per + 0.03)).sum())
        why = ""
        if best < VERIFY["min"]:
            why = f"line se kam mel (score {best:.3f} < {VERIFY['min']})"
        elif bad_frames >= max(2, len(ims)):
            why = "text/logo/slide jaisa frame zyada"
        if not why and av_list:
            base_idx = 1 + len(qs)
            for ai_, a in enumerate(av_list):     # v3.1: scene plan ka "ye NAHI dikhna chahiye"
                ma = _np.asarray(sim[:, base_idx + ai_], dtype=float)
                wins = int((ma > per + AVOID_MARGIN).sum())
                if wins * 2 > len(ims) and float(ma.max()) > best + AVOID_MARGIN:
                    why = f"'{a}' zyada dikh raha ({float(ma.max()):.3f} vs line {best:.3f})"; break
        ok = not why
        SCORES.append({"text": str(text)[:80], "score": round(best, 3), "ok": bool(ok), "path": str(path), "why": why})
        if not ok:
            log(f"   AI aankh reject: {Path(path).name} – {why}", show=False)
            if line_idx is not None:
                with _lock:
                    REJECTED.setdefault(line_idx, []).append({"path": path, "kind": kind, "score": best, "why": why})
        return ok
    except Exception as e:
        log(f"   (verify skip: {e})", show=False); return None


def best_rejected(line_idx, min_score=0.205):
    """v3.13 (Bug B): line ki saari footage reject ho gayi -> sabse achhi (video pehle) wapas, wajah ke saath.
    v3.66: seema 0.19 -> 0.205 (0.19 CLIP pe lagbhag random clip thi – "random visual" ki ek wajah). Isse kam ho to
    line fallback (map / naam card / doc card) pe jaati hai, random clip pe nahi."""
    rows = [r for r in REJECTED.get(line_idx, []) if r["score"] >= min_score and Path(r["path"]).exists()
            and "text/logo" not in r["why"]]
    if not rows: return None
    rows.sort(key=lambda r: (r["kind"] != "video", -r["score"]))
    return rows[0]


AI_PHOTO = {"on": True}


def ai_photo(idx, text, key):
    """v3.62: Try FREE Pollinations/Flux FIRST (zero 429 quota!), fallback to Gemini image if needed."""
    if not (AI_PHOTO["on"] and text):
        return None
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        dst = CACHE / f"ai_{_key(text)}.png"
        if dst.exists(): return dst
        # 1. Free Pollinations/Flux via cloud_visuals (zero quota error!)
        try:
            import cloud_visuals as _cv
            _ci = _cv.generate_scene_image(text, CACHE, topic="", W=1080, H=1920)
            if _ci and Path(_ci).exists() and Path(_ci).stat().st_size > 5000:
                return Path(_ci)
        except Exception:
            pass
        # 2. Gemini image fallback (only if key available)
        if key:
            import ai
            raw = ai.make_image(key, f"Photorealistic documentary photo, vertical 9:16: {text}. Realistic, accurate, cinematic "
                                     "light, sharp subject. Absolutely no text, letters, logos or watermark.", "9:16")
            if raw and len(raw) > 5000:
                dst.write_bytes(raw); return dst
    except Exception as e:
        log(f"   (AI photo skip: {e})", show=False)
    return None


def find_visuals(sent_idx, eng, topic, need, keys, prefer_video=True, extra_queries=None, line=""):
    """Return up to `need` local files [{kind, path, credit}] for this sentence."""
    got, kw = _find_visuals(sent_idx, eng, topic, need, keys, prefer_video, extra_queries, line)
    return green_fix(got, sent_idx, topic, keys, eng), kw


def green_fix(got, sent_idx, topic, keys, eng=""):
    """v3.13: alag function (visual_pick ki nayi clips pe bhi lagta hai)."""
    out = []
    for g in got:                                   # v2.17c: green screen – hata ke background pe, ya chhod do
        if g.get("green") or "green" in str(g.get("src", "")):   # v3.15: pehle hi jaancha (2 baar "(green→key)" nahi)
            out.append(g); continue
        if g.get("src", "").startswith(("aapki", "aapka", "chehra")):
            out.append(g); continue
        try:
            if is_green(g["path"], g["kind"], g.get("tags", "")):
                if GREEN["mode"] != "key":
                    log(f"   line {sent_idx+1}: green screen clip hata di", show=False); continue
                bg = green_bg(topic, keys, eng)
                g = dict(g, green=True, bg=str(bg) if bg else None, src=g.get("src", "") + " (green→key)")
                log(f"   line {sent_idx+1}: green screen clip – hara hata ke background pe lagegi", show=False)
        except Exception:
            pass
        out.append(g)
    return out


def _find_visuals(sent_idx, eng, topic, need, keys, prefer_video=True, extra_queries=None, line=""):
    got = []
    for c in my_clips_for(sent_idx):
        got.append(c)
    # v2.10: script me diye links sabse pehle
    for u in LINKS.get(sent_idx, []):
        it, why = resolve_link(u, keys, LINK_POLICIES.get(sent_idx))
        if not it:
            log(f"   line {sent_idx+1}: link nahi laga – {why}"); continue
        path = download(it)
        if path:
            got.append({"kind": it["kind"], "path": path, "url": it["url"], "credit": it["credit"], "src": "aapka link"})
        else:
            log(f"   line {sent_idx+1}: link se file download nahi hui")
    if got:
        return got, []
    # v2.10: line me asli insaan/jagah ka naam -> uski free photos (Pixabay pe celebrities nahi hote)
    who = WHO.get(sent_idx) or _latin_name(line)
    # v3.10 FIX (Yash video: "motion control camera" wali line pe bhi Yash ki event photo): mukhya insaan ki photo
    # SIRF un lines pe jahan line usi ke baare me hai (lock: uses_main + real_subject_clip) ya naam likha hai.
    # Baaki lines pe topic ki footage (camera rig, film set...). Aur line me doosra kirdaar (Ravana) ho to wahi rahe.
    lk = LOCK_REF.get("v") or {}
    sc_ = (lk.get("scenes") or [])[sent_idx] if sent_idx < len(lk.get("scenes") or []) else {}
    named = bool(MAIN.get("name")) and MAIN["name"].lower().replace(" ", "") in (eng or "").lower().replace(" ", "")
    about_main = named or (sc_.get("uses_main") and sc_.get("footage_type") in ("real_subject_clip", "subject_photo")) if sc_ else None
    sec = {x.lower() for x in (lk.get("secondary_subjects") or [])}
    if MAIN.get("all_lines") and who and who != MAIN.get("name") and (who or "").lower() not in sec:
        who = MAIN["name"]          # v3.1: "Bollywood" jaisa side-shabd mukhya insaan ki jagah nahi lega
    if not who and MAIN.get("name") and (named or (MAIN.get("all_lines") and about_main is not False)):
        who = MAIN["name"]          # v3.1: line usi insaan ke baare me -> uski asli clip/photo
    if who and yes_who():
        # v3.1: pehle Wikidata ENTITY (pakki pehchaan) – usi insaan/brand ki photo / LOGO. Text search sirf fallback.
        try:
            import entity
            hint = {"person": "", "brand": "company", "place": ""}.get(str((RAW_PLAN.get(sent_idx) or {}).get("who_type", "")), "")
            ent, med = entity.for_line(who, hint, max(need, 4))
            if ent:
                ENTITY[sent_idx] = ent
                try:
                    import translit; translit.learn_name(line, ent["label"])     # captions me sahi naam spelling
                except Exception:
                    pass
                med = _spread(ent["id"], med, sent_idx)                          # har line alag photo
                yk0 = keys.get("YOUTUBE") or keys.get("YOUTUBEAPI") or keys.get("YOUTUBEAPIKEY")
                if ent["type"] in ("person", "brand"):                          # v3.1: asli clip pehle (v3.13b: key ke bina bhi)
                    try:
                        import yt_clips
                        lkw = [q for q in (extra_queries or []) if isinstance(q, str)][:3]
                        n_clip = 2 if ent["type"] == "person" else 1       # v3.2: insaan ki video = mukhya source
                        for c in yt_clips.find(" ".join(lkw[:1]) or ent["label"], yk0, n_clip, "",
                                               AVOID.get(sent_idx, ()), prefer_channel=ent["label"], line_kw=lkw,
                                               channel_ids_=ent.get("yt") or ()):
                            got.append(dict(c, entity=ent["label"]))
                    except Exception as e:
                        log(f"   (YouTube clip skip: {e})", show=False)
            for c in med:
                if len(got) >= max(1, min(need, 2)): break
                with _lock:
                    _used.add(c["url"])
                    nuse = ENT_COUNT.get(c["url"], 0)
                    if nuse >= 2 and c.get("role") != "logo":   # v3.10: ek photo/video max 2 line (pehle photo 3-4 baar)
                        continue                              # v3.1: ek photo 3 se zyada baar nahi
                    ENT_COUNT[c["url"]] = nuse + 1
                path = download(c)
                if path and c["kind"] == "video":                   # v3.1: entity ki asli VIDEO (Commons, free licence)
                    got.insert(0, {"kind": "video", "path": path, "url": c["url"], "credit": c["credit"],
                                   "src": f"{ent['type']}: {ent['label']} (video)", "entity": ent["label"]})
                    continue
                if path:
                    got.append({"kind": "image", "path": path, "url": c["url"], "credit": c["credit"],
                                "src": f"{ent['type']}: {ent['label']}" + (" (logo)" if c.get("role") == "logo" else ""),
                                "hero": True, "entity": ent["label"], "etype": ent["type"], "role": c.get("role"),
                                "desc": (ent.get("desc") or "")[:46], "crop_v": nuse})   # dobara lagi -> alag hissa (crop)
            yk = keys.get("YOUTUBE") or keys.get("YOUTUBEAPI") or keys.get("YOUTUBEAPIKEY")
            if not got and ent and yk:                       # v3.1: Wikimedia pe nahi -> sirf CC BY YouTube thumbnail
                import youtube_sources
                for c in youtube_sources.cc_images(ent["label"], yk, 6):
                    with _lock:                               # v3.4: ek thumbnail ek hi line pe (pehle 6 lines pe same)
                        if c["url"] in _used: continue
                        _used.add(c["url"])
                    if not yt_clips_chan_ok(c, ent["label"]): continue     # v3.4: sirf usi ke channel ka thumbnail
                    path = download(c)
                    if not path: continue
                    if verify(path, "image", f"{ent['label']}, {ent.get('desc','')}", (), AVOID.get(sent_idx, ())) is False:
                        continue                              # AI aankh: ye wo nahi hai
                    got.append({"kind": "image", "path": path, "url": c["url"], "credit": c["credit"],
                                "src": f"{ent['type']}: {ent['label']} (YouTube CC)", "hero": True,
                                "entity": ent["label"], "etype": ent["type"], "desc": (ent.get("desc") or "")[:46]})
                    if len(got) >= max(1, min(need, 2)): break
            if got:
                log(f"   line {sent_idx+1}: {ent['label']} ({ent['type']}) ki {len(got)} asli photo/logo ✓", show=False)
                return got, []
            if ent and ent["type"] in ("person", "brand"):
                log(f"   line {sent_idx+1}: {ent['label']} ki free-licence photo nahi mili – name card / 3D logo lagega",
                    show=False)
                NEED_NAMECARD[sent_idx] = ent
        except Exception as e:
            log(f"   (entity skip: {str(e)[:100]})", show=False)
        for c in person_photos(who, need):
            if len(got) >= max(1, min(need, 2)): break
            with _lock:
                if c["url"] in _used: continue
                _used.add(c["url"])
            path = download(c)
            if path:
                got.append({"kind": "image", "path": path, "url": c["url"], "credit": c["credit"], "src": f"photo: {who}"})
        if got:
            log(f"   line {sent_idx+1}: {who} ki {len(got)} photo ✓", show=False)
            return got, []
    kw = keywords(eng)
    qs = list(extra_queries or []) + [q for q in queries_for(kw, topic) if q not in (extra_queries or [])]
    if not qs and topic:
        qs = [" ".join(topic[:2]), topic[0]]
    # v2.5: NASA sirf tab jab IS LINE me space ki baat ho (pehle poore topic se tay hota tha -> har line pe NASA)
    space = any(w in SPACE_WORDS for w in kw) or any(w in SPACE_WORDS for w in
                                                     re.findall(r"[a-z]+", " ".join(extra_queries or []).lower()))
    # v3.1: green_bg se yahan laaya (wahan sent_idx/qs undefined the). YouTube reference discovery (metadata only; no download/reuse without permission).
    yt_key = keys.get("YOUTUBE") or keys.get("YOUTUBEAPI") or keys.get("YOUTUBEAPIKEY")
    if yt_key:
        try:
            import youtube_sources
            youtube_sources.record_scene(sent_idx, line or eng, qs, yt_key)
        except Exception as exc:
            log(f"  YouTube reference search skip: {exc}", show=False)

    pkey = keys.get("PIXABAY")
    if not EXTRA_SRC.get("brave"):
        bk = brave_setup(keys)
        if bk: EXTRA_SRC["brave"] = bk[0]

    vprov = []; iprov = []
    if pkey: vprov.append(("pixabay video", lambda q: pixabay_videos(q, pkey)))
    xkey = (keys or {}).get("PEXELS")                   # v3.8: Pexels video (free key) – Pixabay se zyada cinematic B-roll
    if xkey: vprov.append(("pexels video", lambda q: pexels_videos(q, xkey)))
    if space: vprov.append(("nasa video", nasa_videos))
    # v3.49 FIX: Keep modern HD Pixabay/Pexels FIRST; use social/archive ONLY as fallback (no 25-min archive.org slowdown!)
    vprov.append(("wikimedia video", wikimedia_videos))
    try:
        import social_visuals as _sv
        vprov.append(("social clip", _sv.social_videos))
        vprov.append(("archive video", _sv.archive_videos))
    except Exception:
        _sv = None
    if space: iprov.append(("nasa", nasa))
    if EXTRA_SRC.get("brave"):
        iprov.append(("brave images", lambda q: brave_images(q, EXTRA_SRC["brave"], n=12)))
    if _sv is not None:
        iprov.append(("pinterest", _sv.pinterest_images))
    iprov += [("wikimedia", wikimedia), ("openverse", openverse)]
    if not space: iprov.append(("nasa", nasa))
    if pkey: iprov.append(("pixabay photo", lambda q: pixabay_images(q, pkey)))

    def collect(providers, limit):
        # v3.57 TURBO: bounded tries (max 10 downloads per line) + top 2 queries so no tough line stalls for 10+ min
        tries = 0
        for name, fn in providers:
            if len(got) >= limit or tries >= 10: break
            if name.startswith("wikimedia") and pkey and any(g["kind"] == "video" for g in got): break
            _is_slow = name.startswith(("archive", "social"))
            _qcap = qs[:1] if _is_slow else qs[:2]
            _ccap = 2 if _is_slow else 4
            for q in _qcap:
                if len(got) >= limit or tries >= 10: break
                cands = fn(q)[:_ccap]
                for c in cands:
                    if len(got) >= limit or tries >= 10: break
                    with _lock:
                        if c["url"] in _used: continue
                        _used.add(c["url"])
                    tries += 1
                    path = download(c)
                    if path and verify(path, c["kind"], eng, qs[:2], AVOID.get(sent_idx, ()), sent_idx) is not False:
                        got.append({"kind": c["kind"], "path": path, "url": c.get("url"), "credit": c["credit"], "query": q, "src": name,
                                    "tags": c.get("tags", "")})

    # v2.6: Gemini footage check – pehle candidates jama karo, Gemini se match karwao, phir sirf achhe download
    gkey = keys.get("GEMINI") if CHECK["on"] else None
    def gather(qlist):
        cands = []; seen = set()
        for name, fn in vprov:
            if name.startswith(("wikimedia", "archive", "social")): continue
            for q in qlist:
                for c in fn(q)[:4]:
                    if c["url"] in seen: continue
                    with _lock:
                        if c["url"] in _used: continue
                    seen.add(c["url"]); c["_src"] = name; c["_q"] = q; cands.append(c)
                if len(cands) >= 10: break
            if len(cands) >= 10: break
        return cands

    if (gkey or yes_tags() or AANKH["on"]) and len(got) < need:
        cands = gather(qs[:3])
        rk = None; how = "Gemini"
        aankh_ok = False
        if AANKH["on"]:
            try:
                import aankh; aankh_ok = bool(aankh.STATE["ok"])
            except Exception:
                aankh_ok = False
        if cands and aankh_ok and not GEM_FOOTAGE["on"]:   # v2.17c: pehle AI aankh (free) – Gemini ki limit bachao
            try:
                rk = aankh.rank(cands, eng, _thumb_bytes, qs[:2]); how = "AI aankh"
            except Exception:
                rk = None
        if rk is None and cands and gkey:
            rk = gemini_rank(gkey, line, eng, cands, AVOID.get(sent_idx, ())); how = "Gemini"
        if rk is not None and how == "Gemini":
            rk = (double_check(rk[0], cands, eng, qs[:2]), rk[1])
        if rk is None and cands and AANKH["on"]:  # v2.15: Gemini nahi -> AI aankh (CLIP) photo dekh ke
            try:
                import aankh
                rk = aankh.rank(cands, eng, _thumb_bytes, qs[:2]); how = "AI aankh"
            except Exception as e:
                log(f"   (AI aankh skip: {e})", show=False); rk = None
        if rk is None and cands and not STRICT["on"]:                  # non-strict mode only: tags fallback
            rk = tag_rank(cands, [eng] + qs[:4]); how = "tags"
            if rk: log(f"   line {sent_idx+1}: tags se check – {len(rk[0])} milti clips", show=False)
        if rk and not rk[0]:                      # pehle round me ek bhi sahi nahi -> doosre shabdon se ek aur try
            for b in rk[1]:
                if 0 <= b < len(cands):
                    with _lock: _used.add(cands[b]["url"])
            more = [q for q in qs[4:] + [" ".join(topic[:2])] if q]
            cands2 = gather(more) if more else []
            rk2 = None
            if cands2:
                if how == "Gemini" and gkey: rk2 = gemini_rank(gkey, line, eng, cands2, AVOID.get(sent_idx, ()))
                elif how == "AI aankh":
                    import aankh; rk2 = aankh.rank(cands2, eng, _thumb_bytes, more[:2])
                else: rk2 = tag_rank(cands2, [eng] + more)
            if rk2:
                cands, rk = cands2, rk2           # nayi list + uski ginti saath-saath
            else:
                rk = ([], [])                     # nayi clip nahi mili – purani galat wali pehle hi hata di
        checked = (how in ("Gemini", "AI aankh") and rk is not None)
        if STRICT["on"] and checked is not True:
            rk = None
        if rk:
            good, bad = rk
            good = [g for g in good if 0 <= g < len(cands)]
            bad = [b for b in bad if 0 <= b < len(cands)]
            log(f"   line {sent_idx+1}: {how} check – {len(good)} sahi, {len(bad)} galat clips", show=False)
            for b in bad:
                with _lock: _used.add(cands[b]["url"])        # galat clips dobara nahi aayengi
            for gi in good:
                if len(got) >= need: break
                c = cands[gi]
                with _lock:
                    if c["url"] in _used: continue
                    _used.add(c["url"])
                path = download(c)
                if path and verify(path, c["kind"], eng, qs[:2], AVOID.get(sent_idx, ()), sent_idx) is False:
                    continue                              # v2.17: thumbnail sahi tha, asli clip galat
                if path:
                    got.append({"kind": c["kind"], "path": path, "url": c.get("url"), "credit": c["credit"], "query": c["_q"],
                                "src": c["_src"] + " ✓", "tags": c.get("tags", "")})
            if any(g["kind"] == "video" for g in got) and len(got) < need:
                return got, kw          # sahi clips mil gayi – baaki unhi ke alag hisse (galat clip se behtar)
            if not got and STRICT["on"]:
                # v2.17: pro editor – galat video nahi: pehle sahi PHOTO (jaanch ke), phir AI photo, phir pichhli clip
                collect(iprov, max(1, min(need, 2)))
                if not got:
                    br = best_rejected(sent_idx)        # v3.13 (Bug B): sab reject -> sabse achhi wapas (wajah ke saath)
                    if br and br["kind"] == "video":
                        log(f"   line {sent_idx+1}: saari clip reject thi – sabse achhi wapas li "
                            f"(score {br['score']:.3f}; wajah thi: {br['why']})")
                        return [{"kind": "video", "path": br["path"], "credit": "", "src": "best-rejected (fallback)",
                                 "score": br["score"]}], kw
                if not got and sent_idx not in NO_AI_PHOTO:
                    ap = ai_photo(sent_idx, eng, keys.get("GEMINI"))
                    if ap:
                        log(f"   line {sent_idx+1}: sahi footage nahi mili – Gemini AI photo laga raha hoon", show=False)
                        return [{"kind": "image", "path": ap, "credit": "AI image (Google Gemini)", "src": "AI photo"}], kw
                    log(f"   line {sent_idx+1}: koi sahi clip nahi – pichhli line ki clip chalegi", show=False)
                return got, kw

    # v2: PEHLE sirf videos dhoondho (saari queries pe)
    collect(vprov, need)
    # photo sirf tab jab ek bhi video na mile (kuch videos mili to unhi ke alag hisse reuse honge)
    if not any(g["kind"] == "video" for g in got) or style_photos_ok(need, got):
        collect(iprov, need)
    if not got:
        br = best_rejected(sent_idx)                       # v3.13 (Bug B)
        if br:
            log(f"   line {sent_idx+1}: saari footage reject thi – sabse achhi wapas li (score {br['score']:.3f}; {br['why']})")
            return [{"kind": br["kind"], "path": br["path"], "credit": "", "src": "best-rejected (fallback)",
                     "score": br["score"]}], kw
    if not got and sent_idx not in NO_AI_PHOTO:
        ap = ai_photo(sent_idx, eng, keys.get("GEMINI"))
        if ap:
            return [{"kind": "image", "path": ap, "credit": "AI image (Google Gemini)", "src": "AI photo"}], kw
    return got, kw
