"""v2.6: Captions ki sahi timing – free Whisper (laptop pe hi chalta hai) awaaz sunke har shabd ka time pakadta hai.

Pehli baar: faster-whisper install hota hai aur model (~150 MB 'base' / ~460 MB 'small') download hota hai.
Kuch bhi fail ho to purani (andaze wali) timing hi rehti hai – video nahi rukti.
"""
from pathlib import Path
import re, sys, subprocess, difflib
from common import log

_model = {}


def _ensure():
    try:
        import faster_whisper  # noqa
        return True
    except Exception:
        pass
    log("   (pehli baar) Whisper install ho raha hai – 2-5 minute, ek hi baar...")
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "faster-whisper"],
                           capture_output=True, text=True, timeout=900, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            log(f"   Whisper install nahi hua: {r.stderr[-300:]}", show=False); return False
        import faster_whisper  # noqa
        return True
    except Exception as e:
        log(f"   Whisper install error: {e}", show=False); return False


def load(size="base"):
    # v3.25 SPEED: on 8GB RAM laptops, downgrade 'small' -> 'base' automatically (saves ~6 min/video)
    if size in ("small", "medium") and not _bigger_ok():
        size = "base"
    if size in _model:
        return _model[size]
    if not _ensure():
        return None
    try:
        from faster_whisper import WhisperModel
        log(f"   Whisper ({size}) load ho raha hai (pehli baar model download hoga)...")
        _model[size] = WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=4)
        return _model[size]
    except Exception as e:
        log(f"   Whisper load nahi hua ({e})", show=False); return None


def _load16k(path):
    """ffmpeg se 16 kHz mono float32 numpy (Whisper ko seedha)."""
    try:
        import numpy as np
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True, timeout=900, stdin=subprocess.DEVNULL)
        if r.returncode != 0 or len(r.stdout) < 16000:
            return None
        return np.frombuffer(r.stdout, dtype=np.float32).copy()
    except Exception:
        return None


ONE = {"size": None}          # v3.6: set ho to har 'base' maang isi model se (ek hi baar sunna)
_TX = {}                      # v3.6: (file, size, mtime, bytes) -> result  – same awaaz 4 baar nahi suni jaayegi


def transcribe(path, size="base", lang="hi", prompt=None):
    """Returns (words [{w,start,end}], segments [{text,start,end}]) or (None, None).
    v3.6 TEZ: pehle ek hi awaaz ko 3-4 baar suna jaata tha (faltu-awaaz check, line check, timing base, timing
    small) = laptop pe 4-6 minute. Ab ek model, ek baar – baaki jagah wahi jawab (file badle to hi dobara)."""
    if ONE["size"] and size == "base":
        size = ONE["size"]
    try:
        st_ = Path(path).stat(); ck = (str(Path(path).resolve()), size, lang, st_.st_mtime_ns, st_.st_size)
    except Exception:
        ck = None
    if ck and ck in _TX:
        return _TX[ck]
    r = _transcribe(path, size, lang, prompt)
    if ck and r[0]:
        _TX[ck] = r
    return r


def _transcribe(path, size="base", lang="hi", prompt=None):
    m = load(size)
    if not m:
        return None, None
    try:
        audio = _load16k(path)                 # v2.10: PyAV (av.open) bypass – naye version me 'metadata_errors' galti
        segs, _ = m.transcribe(audio if audio is not None else str(path), language=lang, word_timestamps=True,
                               vad_filter=True,
                               initial_prompt=(prompt[:800] if prompt else None), beam_size=3)
        words, out = [], []
        for s in segs:
            out.append({"text": s.text.strip(), "start": s.start, "end": s.end})
            for w in (s.words or []):
                t = w.word.strip()
                if t: words.append({"w": t, "start": float(w.start), "end": float(w.end)})
        return words, out
    except Exception as e:
        log(f"   Whisper sun nahi paya ({e})", show=False); return None, None


def _norm(t):
    t = t.lower()
    t = re.sub(r"[\u093c]", "", t)                       # nukta
    return re.sub(r"[^\w\u0900-\u097f]", "", t)


def _bigger_ok():
    """v3.1: 'small' model (~460 MB, ~1.5 GB RAM) tabhi jab RAM >= 6 GB ho."""
    try:
        import hardware
        return (hardware.ram_gb() or 0) >= 12  # v3.22: 8GB RAM laptops stay fast on base model (no hang)
    except Exception:
        return False


def align(sents, wav, size="base"):
    """Script ke shabdon ko asli awaaz ke time se milao. sents ko in-place update karta hai. True/False."""
    script_text = " ".join(s.get("script") or s["text"] for s in sents)
    words, _ = transcribe(wav, size, "hi", prompt=script_text)
    if not words or len(words) < 3:
        return False
    # whisper string with per-char time
    T = []; Tt = []
    for w in words:
        n = _norm(w["w"])
        if not n: continue
        d = (w["end"] - w["start"]) / max(1, len(n))
        for k, ch in enumerate(n):
            T.append(ch); Tt.append(w["start"] + k * d)
    if not T:
        return False
    # script string with word char spans
    S = []; spans = []
    flat = [w for s in sents for w in s["words"]]
    for w in flat:
        n = _norm(w["w"]); a = len(S); S.extend(n); spans.append((a, len(S)))
    sm = difflib.SequenceMatcher(None, "".join(S), "".join(T), autojunk=False)
    m = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = Tt[blk.b + k]
    matched = len(m) / max(1, len(S))
    if matched < 0.35:
        if size == "base" and _bigger_ok():
            log(f"   Whisper (base) match kam ({matched:.0%}) – 'small' model se dobara sun raha hoon...", show=False)
            return align(sents, wav, "small")
        log(f"   Whisper match kam ({matched:.0%}) – awaaz ke pauses se timing (fallback)", show=False)
        return False
    starts = []
    for a, b in spans:
        ts = [m[i] for i in range(a, b) if i in m]
        starts.append(min(ts) if ts else None)
    # fill gaps by interpolation, keep increasing
    n = len(starts); known = [i for i in range(n) if starts[i] is not None]
    for i in range(n):
        if starts[i] is None:
            lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
            if lo is not None and hi is not None:
                starts[i] = starts[lo] + (starts[hi] - starts[lo]) * (i - lo) / (hi - lo)
            elif lo is not None:
                starts[i] = starts[lo] + 0.3 * (i - lo)
            else:
                starts[i] = max(0.0, starts[hi] - 0.3 * (hi - i))
    for i in range(1, n):
        if starts[i] < starts[i - 1] + 0.05: starts[i] = starts[i - 1] + 0.05
    # v3.30 FIX (0:47-0:57 tail freeze): ensure tail words stretch smoothly to actual audio duration
    from common import duration as _aud_dur
    _tot_a = _aud_dur(wav) or max(starts[-1] + 0.3, words[-1]["end"])
    last_known = max(known) if known else n - 1
    if last_known < n - 1 and _tot_a > starts[last_known] + 1.0:
        tail_cnt = (n - 1) - last_known
        span = max(0.5, (_tot_a - 0.15) - starts[last_known])
        for k in range(last_known + 1, n):
            starts[k] = starts[last_known] + span * (k - last_known) / (tail_cnt + 0.5)
    for i in range(1, n):
        if starts[i] < starts[i - 1] + 0.05:
            starts[i] = starts[i - 1] + 0.05
    ends = [starts[i + 1] for i in range(n - 1)] + [max(starts[-1] + 0.3, _tot_a - 0.05)]
    for w, a, b in zip(flat, starts, ends):
        w["start"], w["end"] = round(a, 3), round(b, 3)
    # line ki shuruaat bhi asli time pe (isse footage bhi theek line pe badlegi)
    for i, s in enumerate(sents):
        if s["words"]:
            s["start"] = s["words"][0]["start"] if i else 0.0
            s["end"] = s["words"][-1]["end"]
    log(f"   captions timing: Whisper se sahi kiya ✓ ({matched:.0%} match)")
    return True


LAST_RATIO = {"v": 1.0}


def line_coverage(lines, wav, size="base", words=None):
    """v2.15: Har script line ka kitna hissa awaaz me sach me bola gaya (0..1). Whisper na chale to None.
    Isse pata chalta hai Gemini ne koi line chhodi / badli to nahi."""
    if words is None:
        words, _ = transcribe(wav, size, "hi", prompt=" ".join(lines))
    if not words:
        return None
    T = "".join(_norm(w["w"]) for w in words)
    if len(T) < 5:
        return None
    S = []; spans = []
    for l in lines:
        n = "".join(_norm(w) for w in l.split()); a = len(S); S.extend(n); spans.append((a, len(S)))
    LAST_RATIO["v"] = len(T) / max(1, len(S))          # v2.17d: >1.3 = awaaz ne kuch dobara / faltu bola
    sm = difflib.SequenceMatcher(None, "".join(S), T, autojunk=False)
    hitc = [0] * len(S)
    for blk in sm.get_matching_blocks():
        if blk.size < 2: continue                        # akela akshar ittefaq se bhi mil jaata hai
        for k in range(blk.size): hitc[blk.a + k] = 1
    return [(sum(hitc[a:b]) / max(1, b - a)) for a, b in spans]
