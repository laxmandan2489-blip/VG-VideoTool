"""v2.15: "AI aankh" (CLIP) – laptop pe hi chalne wali free AI jo PHOTO DEKH KE batati hai ki wo
'||' wale English shabdon se milti hai ya nahi. Gemini busy / band ho tab bhi footage check hota hai.

Pehli baar: 'fastembed' install hota hai (~50 MB) aur model download hota hai (~600 MB, ek hi baar).
Model VideoTool\\ai_aankh\\ me rehta hai. Kuch bhi fail ho to purana tareeka (tags) chalta hai – video nahi rukti.
"""
import io, sys, subprocess, threading
import numpy as np
from common import TOOL, log

IMG_MODEL = "Qdrant/clip-ViT-B-32-vision"
TXT_MODEL = "Qdrant/clip-ViT-B-32-text"
CACHE = TOOL / "ai_aankh"
_m = {}
_lock = threading.Lock()
STATE = {"ok": None}

# ye cheezein footage me aksar galat hoti hain (line inke baare me na ho to clip kharab)
NEG = [
    "text on a screen",
    "a logo",
    "a presentation slide",
    "a person talking to the camera",
    "a blank black screen",
    "a watermark",
    "subtitles or captions at the bottom of the screen",
    "news broadcast lower third text banner",
    "cute 3d cartoon toy or children animation",
    "empty green grass park lawn with no subject",
    "camera equipment tripod microphone or filming gear on a desk",
    "person setting up a video camera indoors",
]


def _ensure():
    try:
        import fastembed  # noqa
        return True
    except Exception:
        pass
    log("   (pehli baar) AI aankh (CLIP) install ho rahi hai – 2-5 minute, ek hi baar...")
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "fastembed"],
                           capture_output=True, text=True, timeout=1200, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            log(f"   AI aankh install nahi hui: {r.stderr[-300:]}", show=False); return False
        import fastembed  # noqa
        return True
    except Exception as e:
        log(f"   AI aankh install error: {e}", show=False); return False


def ready():
    """Model load (ek baar). True/False."""
    with _lock:
        if STATE["ok"] is not None:
            return STATE["ok"]
        STATE["ok"] = False
        if not _ensure():
            return False
        try:
            from fastembed import ImageEmbedding, TextEmbedding
            CACHE.mkdir(parents=True, exist_ok=True)
            log("   AI aankh (CLIP) load ho rahi hai (pehli baar ~600 MB download)...")
            _m["img"] = ImageEmbedding(model_name=IMG_MODEL, cache_dir=str(CACHE))
            _m["txt"] = TextEmbedding(model_name=TXT_MODEL, cache_dir=str(CACHE))
            STATE["ok"] = True
            log("   AI aankh ready ✓")
        except Exception as e:
            log(f"   AI aankh load nahi hui ({str(e)[:150]}) – tags wala check chalega", show=False)
        return STATE["ok"]


def _unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9)


_TXT_CACHE = {}
_NEG_VECS = None
_NEG_CACHE = {}
LINE_CTX = threading.local()   # v3.66: .relax = NEG labels jo is line pe dheele


def text_vecs(texts):
    """v3.57: Cached text embeddings (exact same vectors, avoids re-encoding repeated prompts)."""
    tlist = list(texts)
    missing = [t for t in dict.fromkeys(tlist) if t not in _TXT_CACHE]
    if missing:
        with _lock:
            vecs = _unit(np.stack(list(_m["txt"].embed(missing))))
            for t, v in zip(missing, vecs):
                if len(_TXT_CACHE) > 2048:
                    _TXT_CACHE.clear()
                _TXT_CACHE[t] = v
    return np.stack([_TXT_CACHE[t] for t in tlist])


def _neg_vecs():
    global _NEG_VECS
    drop = frozenset(getattr(LINE_CTX, "relax", None) or ())
    if drop:                                   # v3.66: is line ki category me ye 'kharab' nahi (YouTuber = talking head)
        keep = [n for n in NEG if n not in drop] or NEG[:1]
        v = _NEG_CACHE.get(drop)
        if v is None:
            v = text_vecs([f"a photo of {n}" for n in keep]); _NEG_CACHE[drop] = v
        return v
    if _NEG_VECS is None:
        _NEG_VECS = text_vecs([f"a photo of {n}" for n in NEG])
    return _NEG_VECS


def set_line_relax(labels):
    """v3.66: make_video.job(i) har line pe set karta hai (thread-local; line ki apni thread me hi asar)."""
    LINE_CTX.relax = set(labels or ())


def image_vecs(images):
    """images: PIL Images ya jpg bytes."""
    from PIL import Image
    ims = []
    for x in images:
        if isinstance(x, (bytes, bytearray)):
            x = Image.open(io.BytesIO(x))
        ims.append(x.convert("RGB"))
    with _lock:
        return _unit(np.stack(list(_m["img"].embed(ims))))


def scores_batch(images, texts):
    """v3.57 TURBO: Encode images ONCE and score against ALL texts + cached NEG in one matrix multiply!
    Returns (sim_matrix [len(images), len(texts)], neg_max [len(images)]). 100% identical math, 10x faster!"""
    iv = image_vecs(images)
    tv = text_vecs([f"a photo of {t}" for t in texts])
    nv = _neg_vecs()
    sim = iv @ tv.T
    neg = (iv @ nv.T).max(axis=1)
    return sim, neg


def scores(images, text):
    """Har photo ka score (cosine, ~0.15 bekaar ... 0.30+ bilkul sahi) + kya wo 'text/logo/talking head' hai."""
    sim, neg = scores_batch(images, [text])
    return sim[:, 0], neg


def rank(cands, eng, thumb_fn, extra=()):
    """sources.find_visuals ke liye: (good_in_order, bad) – indices of cands. None = check nahi ho paya."""
    if not eng or not ready():
        return None
    from concurrent.futures import ThreadPoolExecutor
    def _grab(pair):
        i, c = pair
        return i, (thumb_fn(c["thumb"]) if c.get("thumb") else None)
    idx, ims = [], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, b in ex.map(_grab, enumerate(cands)):
            if b:
                idx.append(i); ims.append(b)
    if len(idx) < 2:
        return None
    try:
        qlist = [eng] + [q for q in list(extra)[:2] if q]
        sim, neg = scores_batch(ims, qlist)
        main = sim[:, 0].copy()
        for k in range(1, sim.shape[1]):
            main = np.maximum(main, sim[:, k] - 0.01)
    except Exception as e:
        log(f"   AI aankh check nahi hua ({str(e)[:100]})", show=False); return None
    best = float(main.max())
    good, bad = [], []
    for j in np.argsort(-main):
        i = idx[int(j)]; s = float(main[j]); n = float(neg[j])
        # v3.13 FIX (Bug B): pehle 0.235 ki pakki seema thi – lambi / abstract line pe CLIP 0.20-0.24 hi deta hai ->
        # lagbhag har clip reject. Ab sabse achhi ke paas wali (relative) + kam se kam 0.205; bad sirf saaf kharab.
        if s >= max(0.180, best - 0.03) and s > n - 0.01:
            good.append(i)
        elif s < 0.185 or n > s + 0.04:
            bad.append(i)
    return good, bad


def match(image, text):
    """Ek photo ka score (thumbnail chunne ke liye). None = aankh nahi chali."""
    if not ready():
        return None
    try:
        m, n = scores([image], text)
        return float(m[0] - max(0.0, n[0] - m[0]))
    except Exception:
        return None
