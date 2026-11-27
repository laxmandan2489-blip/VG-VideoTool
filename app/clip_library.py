"""v5.3 CLIP LIBRARY – jo clip Director ki jaanch me 8/10+ aayi, uska pata (URL + kahan se + kis cheez ki) yaad.

Agli video me jab wahi cheez chahiye (jaise "airplane cabin", "cigarette smoke"), pehle apni library dekhi jaati hai.
Library clip bhi dobara jaanchi jaati hai (bina jaanch kuch nahi lagta), bas muqable me pehle aa jaati hai.
File: clip_library/library.json (cloud pe GitHub cache me bachi rehti hai – make_video.yml ka "Clip library" step).
Sirf pata yaad rehta hai, video file nahi (cache halka rahe) – zaroorat pe dobara download.
"""
import json
import re
import threading
import time
from pathlib import Path

from common import TOOL, log

LIB_DIR = TOOL / "clip_library"
LIB_FILE = LIB_DIR / "library.json"
MAX = 4000
_L = {"rows": None}
_lock = threading.Lock()
STOP = {"a", "an", "the", "of", "in", "on", "at", "to", "with", "and", "or", "for", "from", "into", "by", "is", "are",
        "shot", "close", "up", "closeup", "wide", "medium", "view", "scene", "footage", "video", "camera", "angle",
        "slow", "motion", "showing", "inside", "outside", "while", "his", "her", "their", "its", "very", "large", "small"}


def _toks(t):
    return {w for w in re.findall(r"[a-z]{3,}", str(t or "").lower()) if w not in STOP}


def load():
    with _lock:
        if _L["rows"] is None:
            try:
                _L["rows"] = json.loads(LIB_FILE.read_text(encoding="utf-8")) if LIB_FILE.exists() else []
            except Exception:
                _L["rows"] = []
        return _L["rows"]


def size():
    return len(load())


def save():
    with _lock:
        rows = _L["rows"] or []
        rows.sort(key=lambda r: (r.get("score", 0), r.get("t", 0)), reverse=True)
        rows = rows[:MAX]
        _L["rows"] = rows
        try:
            LIB_DIR.mkdir(parents=True, exist_ok=True)
            LIB_FILE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log(f"   (library save fail: {e})", show=False)


def add(item, texts, score, topic=""):
    """Sirf asli (download ho sakne wali) clip – AI photo / card / map nahi."""
    src = str(item.get("src", "")).lower()
    url = str(item.get("url") or "")
    if not url or any(k in src for k in ("cloud flux", "card", "map", "explainer", "chehra", "aapki", "library")):
        return False
    yt = ""
    m = re.search(r"youtube\.com/watch\?v=([\w-]{6,})", url)
    if m:
        if "screenshot" in src:                       # copyright-safe still: dobara lene layak nahi
            return False
        yt = m.group(1)
    tags = sorted(_toks(" ".join(t for t in texts if t)))[:30]
    if len(tags) < 2:
        return False
    row = {"url": url.split("&t=")[0] if yt else url, "yt": yt, "kind": item.get("kind", "video"),
           "ss": float(item.get("ss") or 0.0), "tags": tags, "score": float(score or 0), "src": src[:40],
           "credit": str(item.get("credit") or "")[:200], "topic": str(topic or "")[:60], "t": int(time.time()), "uses": 0}
    if yt:
        mt = re.search(r"[?&]t=(\d+)", url)
        if mt:
            row["ss"] = float(mt.group(1))
    rows = load()
    with _lock:
        for r in rows:
            if r["url"] == row["url"] and abs(float(r.get("ss", 0)) - row["ss"]) < 3:
                r["score"] = max(r.get("score", 0), row["score"])
                r["tags"] = sorted(set(r.get("tags", [])) | set(tags))[:40]
                return False
        rows.append(row)
    return True


def find(texts, n=3, exclude=()):
    rows = load()
    if not rows:
        return []
    want = _toks(" ".join(t for t in texts if t))
    if len(want) < 2:
        return []
    ex = {str(u).split("&t=")[0] for u in exclude if u}
    scored = []
    for r in rows:
        if r["url"] in ex:
            continue
        tg = set(r.get("tags") or [])
        hit = len(tg & want)
        if hit < 2:
            continue
        sc = hit / (len(want) ** 0.5) + 0.05 * r.get("score", 0) - 0.15 * r.get("uses", 0)
        scored.append((sc, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:n]]


def materialize(r):
    """Library row -> local file item (download / YouTube ka wahi hissa)."""
    try:
        if r.get("yt"):
            import yt_clips
            if not yt_clips._ytdlp_ok():
                return None
            from common import TOOL as _T
            d = _T / "temp" / "cache" / "ytclips"; d.mkdir(parents=True, exist_ok=True)
            p = yt_clips._cut(r["yt"], float(r.get("ss") or 0), 5.0, d / f"lib_{r['yt']}_{int(r.get('ss') or 0)}")
            if not p:
                return None
            item = {"kind": "video", "path": p, "url": f"https://www.youtube.com/watch?v={r['yt']}&t={int(r.get('ss') or 0)}",
                    "ss": 0.0}
        else:
            import sources
            p = sources.download({"kind": r.get("kind", "video"), "url": r["url"]})
            if not p:
                return None
            item = {"kind": r.get("kind", "video"), "path": p, "url": r["url"], "ss": float(r.get("ss") or 0.0)}
        r["uses"] = int(r.get("uses", 0)) + 1
        item.update(src=f"library ({r.get('src', '')[:20]})", credit=r.get("credit", ""), score=None, lib=True)
        return item
    except Exception as e:
        log(f"   (library clip skip: {str(e)[:80]})", show=False)
        return None
