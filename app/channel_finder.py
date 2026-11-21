"""v3.13b AUTO OFFICIAL CHANNEL FINDER – user ko kisi ka @handle dhoondh ke likhna NAHI padega.

Pehle: "Yash" jaisa aam naam -> "youtube_channels.txt me channel likho" (har script ke har insaan ke liye manual kaam).
Ab tool khud dhoondhta hai (sab FREE – YouTube API search quota nahi lagti):
  1. Wikipedia: us insaan ke page ke external links me jo YouTube channel / @handle ho (sabse pakka – Wikipedia
     editors ne official likha hai). Page script ke context se chuna jaata hai ("Yash Kannada actor").
  2. yt-dlp YouTube search: "<naam> official", "<naam> <context>" -> jo channels baar-baar aaye unki jaanch:
       naam milta hai? (fan / fc / edits / status / news wale chhodo)  followers kitne?  description me context
       (actor, film, Kannada...)?  -> score. Aam naam pe aur sakhti (naam + context/10 lakh+ dono).
  3. Jo mila wo temp/auto_channels.json (30 din cache) + youtube_channels.txt me "# auto" ke saath likh deta hai –
     galat ho to wahi line mita do / badal do, tool aapki baat maanega.
Network ya yt-dlp na ho -> chupchaap [] (purana tareeka chalta hai).
"""
import json, re, subprocess, sys, time, threading
from pathlib import Path
from common import TOOL, log

CACHE_FILE = TOOL / "temp" / "auto_channels.json"
CH_FILE = TOOL / "youtube_channels.txt"
_LOCK = threading.Lock()
UA = {"User-Agent": "VG-VideoTool/3.15 (channel finder)"}
BAD = re.compile(r"\b(fan|fans|fc|club|edits?|editz|status|whatsapp|news|updates?|shorts|clips|memes?|army|world|"
                 r"forever|lover|lovers|creations?|unofficial|tribute|reacts?|reaction)\b", re.I)
CTX_STOP = set("the a an of and in on for with film movie video official actor actress".split())


def _compact(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def _ytdlp(args, timeout=60):
    try:
        try:
            from yt_clips import js_args
            jsa = js_args()
        except Exception:
            jsa = []
        r = subprocess.run([sys.executable, "-m", "yt_dlp"] + jsa + ["--no-warnings"] + args, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return json.loads(r.stdout or "{}") if r.returncode == 0 else {}
    except Exception:
        return {}


def channel_info(ref):
    """ref = UC... ya @handle -> {id, title, followers, desc, handle} (yt-dlp, quota nahi)."""
    url = f"https://www.youtube.com/channel/{ref}" if ref.startswith("UC") else f"https://www.youtube.com/{ref}"
    j = _ytdlp(["-J", "--flat-playlist", "--playlist-items", "1", url + "/videos"], 60)
    if not j: return None
    cid = j.get("channel_id") or j.get("id") or ""
    if not str(cid).startswith("UC"): return None
    return {"id": cid, "title": j.get("channel") or j.get("title") or "", "followers": int(j.get("channel_follower_count") or 0),
            "desc": (j.get("description") or "")[:1500], "handle": j.get("uploader_id") or ""}


def wikipedia_refs(name, context=""):
    """Wikipedia page ke external links me YouTube channel/@handle."""
    try:
        import requests
        S = requests.Session(); S.headers.update(UA)
        api = "https://en.wikipedia.org/w/api.php"
        q = f"{name} {context}".strip()
        hits = S.get(api, params={"action": "query", "list": "search", "srsearch": q, "srlimit": 4, "format": "json"},
                     timeout=15).json().get("query", {}).get("search", [])
        tok = _compact(name.split()[0]) if name else ""
        for h in hits:
            if tok and tok not in _compact(h.get("title")): continue
            j = S.get(api, params={"action": "query", "prop": "extlinks", "titles": h["title"], "ellimit": 500,
                                   "format": "json"}, timeout=15).json()
            refs = []
            for pg in (j.get("query", {}).get("pages") or {}).values():
                for el in pg.get("extlinks") or []:
                    u = el.get("*") or el.get("url") or ""
                    m = re.search(r"youtube\.com/(?:channel/(UC[\w-]{22})|(@[\w.\-]+)|c/([\w.\-]+)|user/([\w.\-]+))", u)
                    if m:
                        refs.append(m.group(1) or m.group(2) or ("@" + (m.group(3) or m.group(4))))
            if refs:
                return list(dict.fromkeys(refs))[:3], h["title"]
    except Exception as e:
        log(f"   (Wikipedia channel khoj skip: {str(e)[:80]})", show=False)
    return [], ""


def _score(info, name, ctx_words, seen_n, common):
    t = info["title"]; tc = _compact(t); nc = _compact(name)
    if BAD.search(t) and not BAD.search(name): return -9, "fan/edit/news channel"
    exact = tc == nc or tc in (nc + "official", "official" + nc, nc + "films", nc + "tv", "the" + nc) or \
        (len(nc) >= 9 and nc in tc)
    if not exact and nc not in tc: return -9, "naam nahi milta"
    sc = 3 if exact else 1
    f = info["followers"]
    if f < 10_000: return -9, "bahut chhota channel"
    sc += 2 if f >= 1_000_000 else 1 if f >= 100_000 else 0
    text = (info["title"] + " " + info["desc"]).lower()
    ctx_hit = sum(1 for w in ctx_words if w in text)
    sc += min(2, ctx_hit) + min(1.5, 0.5 * seen_n)
    # v3.15 FIX (log 15 Nov: "Mr. Yash Official" – kisi aur Yash ka channel, context 0, phir bhi le liya):
    # aam naam pe naam BILKUL milna chahiye AUR description me script ka context (actor/film...) dono zaroori
    if common and not (exact and ctx_hit):
        return -9, "aam naam – naam pakka nahi ya context (actor/film) nahi mila"
    return sc, f"score {sc:.1f}, {f:,} followers, context {ctx_hit}"


def find(name, context="", need=2):
    """Return (channel_ids, why). Cache 30 din."""
    if not name: return [], ""
    k = "v315|" + _compact(name) + "|" + _compact(context)[:40]      # v3.15: purana (galat) cache nahi
    with _LOCK:
        try:
            c = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}
        except Exception:
            c = {}
        hit = c.get(k)
        ttl = 30 * 86400 if (hit or {}).get("ids") else 86400          # "nahi mila" sirf 1 din yaad
        if hit and time.time() - hit.get("t", 0) < ttl:
            if hit.get("ids") and not _in_file(name):
                return [], "aapne youtube_channels.txt se auto line mita di – ye channel nahi lunga"
            return hit.get("ids", []), hit.get("why", "cache")
    ctx_words = [w for w in re.findall(r"[a-z]{4,}", (context or "").lower()) if w not in CTX_STOP][:6]
    common = len(name.split()) < 2 and len(_compact(name)) < 9
    ids, why = [], ""
    # 1) Wikipedia (sabse pakka)
    refs, page = wikipedia_refs(name, context)
    for r in refs:
        info = channel_info(r)
        if info:
            ids.append(info["id"]); why = f"Wikipedia ({page}) – {info['title']}"
    # 2) yt-dlp search + jaanch
    if len(ids) < need:
        seen = {}
        try:
            import youtube_sources as ys
            qs = [f"{name} official"] + ([f"{name} {context}"] if context else []) + [f"{name} official trailer"]
            for q in qs:
                for x in ys.ytdlp_search(q, 15):
                    cid = x.get("channel_id")
                    if cid and str(cid).startswith("UC"): seen[cid] = seen.get(cid, 0) + 1
        except Exception:
            pass
        rows = []
        for cid, n in sorted(seen.items(), key=lambda kv: -kv[1])[:6]:
            if cid in ids: continue
            info = channel_info(cid)
            if not info: continue
            s, w = _score(info, name, ctx_words, n, common)
            rows.append((s, info, w))
        for s, info, w in sorted(rows, key=lambda r: -r[0]):
            if s >= 4 and len(ids) < need:
                ids.append(info["id"]); why = (why + "; " if why else "") + f"search – {info['title']} ({w})"
    ids = list(dict.fromkeys(ids))[:need]
    if not ids and not refs and not locals().get("seen"):
        return [], "khoj nahi chal payi (internet / yt-dlp) – agli video me dobara"   # network fail -> cache nahi
    with _LOCK:
        try:
            c = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}
        except Exception:
            c = {}
        c[k] = {"ids": ids, "why": why or "nahi mila", "t": time.time()}
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True); CACHE_FILE.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass
        if ids:
            _remember(name, ids, why)
    return ids, why


def _in_file(name):
    try:
        for ln in (CH_FILE.read_text(encoding="utf-8") if CH_FILE.exists() else "").splitlines():
            if "=" in ln and _compact(ln.split("=", 1)[0].split("#")[0]) == _compact(name): return True
    except Exception:
        pass
    return False


def _remember(name, ids, why):
    """youtube_channels.txt me '# auto' line (user dekh / badal sake). User ki apni line ho to chhedo mat."""
    try:
        old = CH_FILE.read_text(encoding="utf-8") if CH_FILE.exists() else ""
        keep = []
        for ln in old.splitlines():
            if "=" in ln and _compact(ln.split("=", 1)[0].split("#")[0]) == _compact(name):
                if "# auto" not in ln: return                  # user ki apni line – chhedo mat
                continue                                       # purani auto line -> nayi se badlo
            keep.append(ln)
        keep.append(f"{name} = {', '.join(ids)}   # auto (tool ne khud dhoonda: {why[:90]}) – galat ho to ye line mita do")
        CH_FILE.write_text("\n".join(keep) + "\n", encoding="utf-8")
    except Exception:
        pass
