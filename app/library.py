"""v2.19: APNI FOOTAGE LIBRARY + 👍/👎 se seekhna.

👍 dabaya  -> us video ki sahi clips (line ke English shabdon ke saath) library me rakh leta hai.
             Aage kisi script me waisi hi line aaye to pehle library dekhta hai (AI aankh se milake) – pakki sahi clip.
👎 dabaya  -> us video ki clips 'ban' – dobara kabhi nahi aayengi.
Library: VideoTool\\footage_library  (band karna: style.txt -> library = nahi)
"""
import json, time, shutil, hashlib, datetime, io, subprocess
from pathlib import Path
from common import log, TOOL

LIB = TOOL / "footage_library"
IDX = LIB / "index.json"
BAN = TOOL / "seekha" / "ban_urls.txt"
LIKES = TOOL / "seekha" / "likes.json"
MAX_ITEMS = 900
_VEC = {"ids": None, "m": None}


def _load():
    try:
        return json.loads(IDX.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(lst):
    LIB.mkdir(parents=True, exist_ok=True)
    tmp = IDX.with_suffix(".tmp")
    tmp.write_text(json.dumps(lst, ensure_ascii=False), encoding="utf-8")
    tmp.replace(IDX)
    _VEC["ids"] = None


def count():
    return len(_load())


def _thumb(src, kind, dst):
    try:
        if kind == "image":
            from PIL import Image
            Image.open(src).convert("RGB").resize((224, int(224 * 1.6))).save(dst, "JPEG", quality=80); return True
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", "1.0", "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=320:-2", str(dst)], capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
        return dst.exists()
    except Exception:
        return False


def add_from_result(res_path):
    """👍 – result json ki clips library me. Returns kitni nayi."""
    r = json.loads(Path(res_path).read_text(encoding="utf-8"))
    items = r.get("items") or {}
    eng = r.get("eng") or []
    lst = _load(); have = {e.get("url") or e["file"] for e in lst}
    new = 0
    for k, its in items.items():
        i = int(k)
        e = eng[i] if i < len(eng) else ""
        if not e: continue
        for it in its:
            src = it.get("src", "")
            p = Path(it.get("path", ""))
            if not p.exists() or it.get("whole"): continue
            if any(x in src for x in ("aapki", "aapka", "chehra", "AI photo", "news", "card", "map")) or "card_" in p.name:
                continue
            key = it.get("url") or str(p)
            if key in have: continue
            hid = hashlib.md5(key.encode()).hexdigest()[:12]
            LIB.mkdir(parents=True, exist_ok=True)
            dst = LIB / (hid + p.suffix.lower())
            try:
                shutil.copy(p, dst)
            except Exception:
                continue
            th = LIB / (hid + "_t.jpg")
            _thumb(dst, it.get("kind", "video"), th)
            lst.append({"id": hid, "file": dst.name, "thumb": th.name if th.exists() else "", "eng": e,
                        "kind": it.get("kind", "video"), "url": it.get("url"), "credit": it.get("credit", ""),
                        "added": datetime.date.today().isoformat(), "used": "", "likes": 1})
            have.add(key); new += 1
    while len(lst) > MAX_ITEMS:                                    # sabse purani hatao
        old = lst.pop(0)
        for f in (old.get("file"), old.get("thumb")):
            if f:
                try: (LIB / f).unlink()
                except Exception: pass
    _save(lst)
    try:
        lk = json.loads(LIKES.read_text(encoding="utf-8")) if LIKES.exists() else {"up": 0, "down": 0}
    except Exception:
        lk = {"up": 0, "down": 0}
    lk["up"] = lk.get("up", 0) + 1
    LIKES.parent.mkdir(parents=True, exist_ok=True); LIKES.write_text(json.dumps(lk), encoding="utf-8")
    return new


def ban_from_result(res_path):
    """👎 – is video ki saari online clips dobara nahi. Returns kitni ban."""
    r = json.loads(Path(res_path).read_text(encoding="utf-8"))
    urls = [x.get("url") for v in (r.get("items") or {}).values() for x in v if x.get("url")]
    BAN.parent.mkdir(parents=True, exist_ok=True)
    old = set(banned())
    with open(BAN, "a", encoding="utf-8") as f:
        for u in urls:
            if u not in old: f.write(u + "\n")
    lst = _load(); keep = [e for e in lst if e.get("url") not in set(urls)]
    if len(keep) != len(lst): _save(keep)
    try:
        lk = json.loads(LIKES.read_text(encoding="utf-8")) if LIKES.exists() else {"up": 0, "down": 0}
    except Exception:
        lk = {"up": 0, "down": 0}
    lk["down"] = lk.get("down", 0) + 1
    LIKES.write_text(json.dumps(lk), encoding="utf-8")
    return len(urls)


def banned():
    try:
        return [l.strip() for l in BAN.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return []


def _vectors(lst):
    import aankh, numpy as np
    from PIL import Image
    ids = [e["id"] for e in lst]
    if _VEC["ids"] == ids: return _VEC["m"]
    cache = LIB / "vecs.npz"; old = {}
    try:
        z = np.load(cache, allow_pickle=False)
        old = dict(zip([str(x) for x in z["ids"]], z["m"]))
    except Exception:
        pass
    need = [e for e in lst if e["id"] not in old and e.get("thumb") and (LIB / e["thumb"]).exists()]
    if need:
        ims = []
        for e in need:
            try: ims.append(Image.open(LIB / e["thumb"]).convert("RGB"))
            except Exception: ims.append(Image.new("RGB", (64, 64)))
        vs = aankh.image_vecs(ims)
        for e, v in zip(need, vs): old[e["id"]] = v
        try:
            keep = [i for i in ids if i in old]
            np.savez(cache, ids=np.array(keep), m=np.stack([old[i] for i in keep]))
        except Exception:
            pass
    m = np.stack([old[i] if i in old else np.zeros_like(next(iter(old.values()))) for i in ids]) if old else None
    _VEC["ids"], _VEC["m"] = ids, m
    return m


def find(eng, need=2, used=(), thr=0.265, gap_days=2):
    """Line ke liye library se clips. [{kind, path, credit, src}] (khaali = kuch nahi mila)."""
    lst = _load()
    if not lst or not eng: return []
    try:
        import aankh, numpy as np
        if not aankh.ready(): return []
        m = _vectors(lst)
        if m is None: return []
        tv = aankh.text_vecs([f"a photo of {eng}"] + [f"a photo of {n}" for n in aankh.NEG])
        sim = m @ tv.T
        main, neg = sim[:, 0], sim[:, 1:].max(axis=1)
        # line ke shabd library wali line se bhi milao (text-text) – dono sahi to hi lo
        ev = aankh.text_vecs([f"a photo of {e['eng']}" for e in lst])
        tt = ev @ tv[0]
    except Exception as ex:
        log(f"   (library skip: {ex})", show=False); return []
    cut = (datetime.date.today() - datetime.timedelta(days=gap_days)).isoformat()
    order = np.argsort(-(main + 0.5 * tt))
    out = []; best = float(main.max()) if len(main) else 0
    for j in order:
        e = lst[int(j)]; s = float(main[j])
        if s < thr or s < best - 0.03 or float(neg[j]) > s or float(tt[j]) < 0.80: continue
        if e.get("used", "") > cut: continue                       # abhi-abhi kisi video me lagi – repeat nahi
        p = LIB / e["file"]
        if not p.exists() or str(p) in used or e.get("url") in used: continue
        out.append({"kind": e["kind"], "path": p, "url": e.get("url"), "credit": e.get("credit", ""),
                    "src": f"library ✓ ({s:.2f})", "lib_id": e["id"]})
        if len(out) >= need: break
    return out


def mark_used(ids):
    if not ids: return
    lst = _load(); t = datetime.date.today().isoformat(); ch = False
    for e in lst:
        if e["id"] in ids: e["used"] = t; ch = True
    if ch: _save(lst)


def stats():
    try:
        lk = json.loads(LIKES.read_text(encoding="utf-8"))
    except Exception:
        lk = {"up": 0, "down": 0}
    return {"clips": count(), "up": lk.get("up", 0), "down": lk.get("down", 0), "ban": len(banned())}
