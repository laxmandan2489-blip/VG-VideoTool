"""v3.1 ENTITY VISUALS – script me jis INSAAN / BRAND / JAGAH / CHEEZ ka naam hai, BILKUL wahi dikhe.

Problem (pehle): "Salman Khan" bola to Wikimedia pe text search -> kisi aur ki photo. "NVIDIA" bola to
bahar ki building. Kyunki search shabd se hota tha, pehchaan (identity) se nahi.

Ab: naam -> Wikidata entity (ek pakki ID, jaise Q41481 = Salman Khan) -> usi entity ki:
   * person : P18 official photo + Commons category ki photos (sirf usi category ki, free licence)
   * brand  : P154 LOGO pehle (NVIDIA -> NVIDIA ka logo), phir product/category photos
   * place  : P18 photo + Commons category + (fx.map_clip map)
   * cheez  : P18 photo
Sab Wikimedia Commons se, licence check ke saath (CC0 / PD / CC BY / CC BY-SA), credit likha jaata hai.
Galat insaan nahi aata kyunki photo usi entity se judi hoti hai, naam ke milte-julte shabd se nahi.
"""
import json, re, hashlib, threading, time
from pathlib import Path
import requests
from common import log, UA, CACHE

S = requests.Session()
# v3.1: Wikimedia policy – pehchaan wala User-Agent (generic UA pe 429 "Too Many Requests" aata tha)
S.headers["User-Agent"] = "VGVideoTool/3.1 (personal video tool; https://www.mediawiki.org/wiki/API:Etiquette) " + UA
_NET = threading.Lock()                 # ek waqt me ek hi Wikimedia request (4 threads -> 429)
_ELOCK = threading.Lock()
WD = "https://www.wikidata.org/w/api.php"
CM = "https://commons.wikimedia.org/w/api.php"
TIMEOUT = 20
PERSON = {"Q5"}
FILM = {"Q11424", "Q24862", "Q506240", "Q202866", "Q5398426", "Q24856", "Q1259759", "Q18011172",
        "Q29168811", "Q130232"}   # v3.6: film / series
BRAND = {"Q4830453", "Q891723", "Q43229", "Q167270", "Q783794", "Q6881511", "Q2085381", "Q1058914", "Q431289",
         "Q210167", "Q18388277", "Q1137109", "Q15265344"}   # business, public co, org, trademark, company, enterprise,
                                                           # publisher, software co, brand, video game dev, tech co...
PLACE = {"Q515", "Q6256", "Q35657", "Q1549591", "Q5119", "Q486972", "Q8502", "Q4022", "Q23397", "Q570116",
         "Q839954", "Q33506", "Q16560", "Q41176", "Q12280", "Q1221156", "Q10864048", "Q3624078", "Q1637706"}
OK_LIC = re.compile(r"(cc0|public domain|pd|cc[- ]by(?![- ]?nc)(?![- ]?nd)|cc-by-sa|cc by-sa|attribution)", re.I)
_mem = {}


def _get(url, params):
    params = dict(params, format="json", maxlag=5)
    for k in range(4):
        with _NET:
            r = S.get(url, params=params, timeout=TIMEOUT)
            time.sleep(0.25)                          # dheere – rate limit se bachne ke liye
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("Retry-After") or (2 * (k + 1)))
            log(f"   (Wikimedia busy {r.status_code}, {wait:.0f}s ruk ke dobara)", show=False)
            time.sleep(min(wait, 15)); continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return r.json()


def _cache(kind, key):
    return CACHE / "entity" / f"{kind}_{hashlib.md5(key.lower().encode()).hexdigest()[:16]}.json"


_RES = {}


def resolve(name, hint="", lang="en"):
    """naam -> {'id','label','desc','type','image','logo','commons','sitelinks'} ya None."""
    k_ = f"{(name or '').strip().lower()}|{hint}"
    with _ELOCK:                                       # 4 threads ek hi naam 3 baar na dhoondhein
        if k_ in _RES: return _RES[k_]
        _RES[k_] = r_ = _resolve(name, hint, lang)
        return r_


def _resolve(name, hint="", lang="en"):
    name = (name or "").strip()
    if not name or len(name) > 80:
        return None
    ck = _cache("ent", f"{name}|{hint}")
    if ck.exists():
        try: return json.loads(ck.read_text(encoding="utf-8")) or None
        except Exception: pass
    best = None
    try:
        cands = []
        for lg in ([lang, "hi"] if lang != "hi" else ["hi", "en"]):
            j = _get(WD, {"action": "wbsearchentities", "search": name, "language": lg, "uselang": "en",
                          "limit": 7, "type": "item"})
            for x in j.get("search", []):
                if x["id"] not in [c["id"] for c in cands]: cands.append(x)
            if cands: break
        if not cands:
            _save(ck, {}); return None
        ids = [c["id"] for c in cands[:7]]
        ents = _get(WD, {"action": "wbgetentities", "ids": "|".join(ids), "props": "claims|sitelinks|labels|descriptions",
                         "languages": "en"}).get("entities", {})
        scored = []
        for k, c in enumerate(cands[:7]):
            e = ents.get(c["id"]) or {}
            info = _info(c["id"], e)
            sc = min(len(e.get("sitelinks") or {}), 60) * 1.0 - k * 3   # mashhoor + search me upar (had tak)
            lab = (info["label"] or "").lower(); nm = name.lower()
            lab_n = re.sub(r"[^a-z0-9]", "", lab); nm_n = re.sub(r"[^a-z0-9]", "", nm)
            mt = ((c.get("match") or {}).get("type") or "")
            if lab_n == nm_n: sc += 80
            elif nm_n and (nm_n in lab_n or lab_n in nm_n): sc += 30
            elif mt == "alias": sc -= 60              # v3.1: "Bollywood" -> alias "King of Bollywood" = SRK (galat)
            h = (hint or "").lower()
            if h and h in (info["desc"] or "").lower(): sc += 25
            if info["type"] in ("person", "brand", "place"): sc += 10
            if info["image"] or info["logo"]: sc += 10
            if "disambiguation" in (info["desc"] or "").lower(): sc -= 200
            scored.append((sc, info))
        scored.sort(key=lambda t: -t[0])
        best = scored[0][1] if scored and scored[0][0] > 0 else None
    except Exception as e:
        log(f"   (entity '{name}' resolve nahi hua: {str(e)[:100]})", show=False)
        return None
    _save(ck, best or {})
    if best:
        log(f"   🔎 entity: '{name}' = {best['label']} ({best['id']}, {best['type']}, {best['desc'][:50]})", show=False)
    return best


def _save(p, d):
    try:
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _claim(e, prop):
    out = []
    for c in (e.get("claims") or {}).get(prop, []):
        try:
            v = c["mainsnak"]["datavalue"]["value"]
            out.append(v["id"] if isinstance(v, dict) and "id" in v else v)
        except Exception:
            continue
    return out


def _year(e):
    """P577 (release date) ka saal – 0 agar nahi."""
    try:
        for v in _claim(e, "P577"):
            t = v.get("time") if isinstance(v, dict) else None
            if t: return int(t[1:5])
    except Exception:
        pass
    return 0


def _info(qid, e):
    p31 = set(_claim(e, "P31"))
    t = "person" if p31 & PERSON else "brand" if p31 & BRAND else "place" if (p31 & PLACE or _claim(e, "P625")) else "thing"
    if t == "thing" and (_claim(e, "P154") or _claim(e, "P452")): t = "brand"      # logo / industry -> company
    return {"id": qid, "label": ((e.get("labels") or {}).get("en") or {}).get("value", ""),
            "desc": ((e.get("descriptions") or {}).get("en") or {}).get("value", ""), "type": t,
            "image": (_claim(e, "P18") or [None])[0], "logo": (_claim(e, "P154") or [None])[0],
            "commons": (_claim(e, "P373") or [None])[0], "sitelinks": len(e.get("sitelinks") or {}),
            "yt": [x for x in _claim(e, "P2397") if isinstance(x, str)][:3],        # v3.4: official YouTube channel
            "trailers": [x for x in _claim(e, "P1651") if isinstance(x, str)][:4],  # v3.6: film ka YouTube trailer ID
            "is_film": bool(p31 & FILM),
            "year": _year(e)}


def _file_info(titles):
    """Commons file titles -> [{title,url,lic,artist,w,h}] (sirf free licence)."""
    if not titles: return []
    j = _get(CM, {"action": "query", "titles": "|".join(titles[:40]), "prop": "imageinfo",
                  "iiprop": "url|extmetadata|size|mime|mediatype", "iiurlwidth": 1600})
    out = []
    for pg in (j.get("query", {}).get("pages") or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata") or {}
        lic = (md.get("LicenseShortName") or {}).get("value", "")
        if not OK_LIC.search(lic or ""):
            continue
        artist = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()[:80]
        is_vid = str(ii.get("mime", "")).startswith("video/")
        if is_vid and int(ii.get("size") or 0) > 120_000_000:
            continue                                             # bahut badi video (laptop/disk) – chhodo
        url = ii.get("url") if is_vid else (ii.get("thumburl") or ii.get("url"))
        if not url: continue
        out.append({"title": pg.get("title", ""), "url": url, "lic": lic, "artist": artist, "video": is_vid,
                    "w": ii.get("width", 0), "h": ii.get("height", 0), "mime": ii.get("mime", "")})
    return out


def _category_files(cat, limit=30):
    j = _get(CM, {"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat, "cmtype": "file",
                  "cmlimit": limit})
    return [m["title"] for m in j.get("query", {}).get("categorymembers", [])
            if re.search(r"\.(jpe?g|png|webp|svg|webm|ogv|mp4)$", m["title"], re.I)]


def media(ent, need=3):
    """Entity ki sahi photos/logo -> [{'kind':'image','url','credit','role'}] best pehle."""
    if not ent: return []
    key = ent["id"]                                   # v3.1: ek baar laao (6 tak), har line usi list se alag chune
    with _ELOCK:
        if key in _mem: return _mem[key]
        res = _media(ent, max(need, 6))
        if res: _mem[key] = res
        return res


def _media(ent, need):
    out = []
    try:
        first = []
        if ent["type"] == "brand" and ent.get("logo"): first.append(("File:" + ent["logo"], "logo"))
        if ent.get("image"): first.append(("File:" + ent["image"], "main"))
        infos = {i["title"]: i for i in _file_info([t for t, _ in first])}
        for t, role in first:
            if t in infos: out.append(dict(infos[t], role=role))
        if ent.get("commons") and len(out) < need + 1:
            toks = [t for t in re.findall(r"[a-z]+", ent["label"].lower()) if len(t) > 2]
            files = _category_files(ent["commons"])
            # person: file ke naam me uska naam ho (group photo / kisi aur ki photo kam)
            if ent["type"] == "person" and toks:
                files = [f for f in files if all(tk in f.lower() for tk in toks[:2])] or files[:0]
            files = [f for f in files if f not in [o["title"] for o in out]]
            infos2 = _file_info(files[:30])
            if ent["type"] == "person":                  # v3.2: Commons ki "video" aksar kisi aur ki (football wala bachcha)
                infos2 = [x for x in infos2 if not x.get("video")]
            infos2.sort(key=lambda i: not i.get("video"))          # v3.1: usi entity ki VIDEO pehle (photo se behtar)
            for i in infos2:
                if i["w"] and i["h"] and min(i["w"], i["h"]) < 360: continue        # chhoti / ghatiya
                out.append(dict(i, role="category"))
                if len(out) >= need + 2: break
    except Exception as e:
        log(f"   (entity media '{ent.get('label')}' fail: {str(e)[:100]})", show=False)
    return [{"kind": "video" if o.get("video") else "image", "url": o["url"],
            "credit": f"{o['title'].replace('File:', '')} – {o['artist'] or 'Wikimedia Commons'} ({o['lic']}), via Wikimedia Commons",
            "role": o["role"], "entity": ent["label"], "qid": ent["id"]} for o in out]


def for_line(name, hint="", need=2):
    """Shortcut: naam -> (entity, media list)."""
    ent = resolve(name, hint)
    return ent, (media(ent, need) if ent else [])


def _soft(t):
    """Transliteration ka farq hatao: raamaayan / ramayana / Ramayanam -> ramayan..."""
    t = re.sub(r"[^a-z0-9]", "", (t or "").lower())
    t = re.sub(r"aa+", "a", t); t = re.sub(r"ee+", "i", t); t = re.sub(r"oo+", "u", t)
    return t


def find_film(names, strong=False):
    """v3.6: script ka topic koi FILM / series hai? (Ramayan film -> 'Ramayana: Part 1').
    names me se har naam Wikidata pe dhoondho, sirf film/series wale entity rakho. Return info ya None."""
    seen, best = set(), None
    # v3.15 FIX (log: "Ramayana movie" se kuch nahi mila, phir 'raamaayan' -> purani 'Ramayanam'): "movie/film"
    # shabd hatao, Hindi-se-aaye naam ke saaf roop (raamaayan -> ramayan, ramayana) bhi dhoondho
    clean = []
    for n in [n for n in names if isinstance(n, str)]:
        n2 = re.sub(r"\b(movie|film|the film|cinema)\b", "", n, flags=re.I).strip(" -:")
        if 2 < len(n2) < 70 and n2.lower() not in [c.lower() for c in clean]: clean.append(n2)
    names = clean
    for nm in names[:6]:
        ck = _cache("film5", nm.strip().lower())          # v3.18: film4 cache me galat 'Voyagers' jaise result the
        try:
            if ck.exists():
                d = json.loads(ck.read_text(encoding="utf-8"))
                if d: return d
                continue
        except Exception:
            pass
        found = None
        try:
            ids = []
            sv = _soft(nm)
            first_plain = None                            # v3.18: naam ka SABSE PEHLA Wikidata matlab
            for q in list(dict.fromkeys([nm, f"{nm} film"] + ([sv, sv + "a"] if sv and sv != nm.lower() else []))):
                j = _get(WD, {"action": "wbsearchentities", "search": q, "language": "en", "uselang": "en",
                              "limit": 10, "type": "item"})
                if q == nm and j.get("search"):
                    first_plain = j["search"][0]["id"]
                ids += [x["id"] for x in j.get("search", []) if x["id"] not in seen]
                seen.update(ids)
            if first_plain and first_plain not in ids[:20]:
                ids = [first_plain] + ids
            if ids:
                ents = _get(WD, {"action": "wbgetentities", "ids": "|".join(ids[:20]), "props": "claims|sitelinks|labels|descriptions",
                                 "languages": "en"}).get("entities", {})
                infos = {i: _info(i, ents.get(i) or {}) for i in ids[:20]}
                films = [f for f in infos.values() if f.get("is_film")]
                nmn = _soft(nm)
                # v3.18 FIX (17 Nov, Voyager 1 video me 'Voyagers' (2021) film ka trailer har line pe):
                # (1) naam ka pehla / mukhya matlab film nahi (Voyager 1 = yaan) -> ye topic film NAHI
                # (2) film ka naam naam se lagbhag POORA mile ('voyage' prefix se 'voyagers' nahi chalega)
                fp = infos.get(first_plain) if first_plain else None
                if fp and not fp.get("is_film") and not strong:
                    log(f"   (film nahi: '{nm}' ka mukhya matlab '{fp.get('label', '')}' hai, film nahi)", show=False)
                    films = []
                def _close(f):
                    lab = _soft(re.split(r"[:(]", f.get("label") or "")[0])
                    if not lab or not nmn: return False
                    if lab == nmn: return True
                    short, long_ = sorted((lab, nmn), key=len)
                    return long_.startswith(short) and len(short) / len(long_) >= 0.85 and len(short) >= 5
                films = [f for f in films if _close(f)]
                # v3.10: "Ramayana" -> 1997 ki 'Ramayanam' nahi, NAYI film (Ramayana: Part 1). Naam mile + sabse naya saal.
                # v3.13 FIX: Hindi se aaya 'raamaayan' -> 'ramayan' (lambi maatra chhoti) – warna naam milta hi nahi tha
                films.sort(key=lambda f: (-(nmn[:6] in _soft(f["label"])),
                                          -(f.get("year") or 0), -len(f.get("trailers") or []), -f["sitelinks"]))
                found = films[0] if films else None
        except Exception as e:
            log(f"   (film dhoondh nahi paya '{nm}': {str(e)[:80]})", show=False)
        _save(ck, found or {})
        if found:
            found["type"] = "film"
            log(f"   🎬 topic film: '{nm}' = {found['label']} ({found['id']}, trailer: {len(found.get('trailers') or [])})")
            return found
    return best
