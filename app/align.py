"""v2.6 + v3.84: Captions & visuals ki audio-locked timing – free Whisper (faster-whisper) awaaz sunke har shabd ka
sahi time pakadta hai.

v3.84 SYNC ENGINE UPGRADE:
  1. Number-heavy Hindi/Hinglish expansion (2023 -> दो हजार तेईस, 615 -> छह सौ पंद्रह, 3,84,000 -> तीन लाख चौरासी हजार,
     6:04 -> छह बजकर चार) so Whisper Devanagari words align cleanly with script digits.
  2. Dual-script alignment (Devanagari + transliterated phonetic Latin) so Hinglish / English acronyms (ISRO, LVM3, TV)
     also lock to Whisper timestamps.
  3. Stray single-char match rejection (blk.size >= 2) + trimmed word start (never raw min(ts) from an earlier matra).
  4. Monotonicity & outlier anchor guard (rejects out-of-order jumps before interpolation).
  5. Spoken-weight gap interpolation (weights unmatched words by expanded spoken length, not flat word index).
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


# ------------------------------------------------------------------ v3.84: Hindi number & dual-script normalization
_HI_0_99 = [
    "शून्य", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ",
    "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस",
    "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताईस", "अट्ठाईस", "उनतीस",
    "तीस", "इकतीस", "बत्तीस", "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस", "उनतालीस",
    "चालीस", "इकतालीस", "बयालीस", "तैंतालीस", "चौवालीस", "पैंतालीस", "छियालीस", "सैंतालीस", "अड़तालीस", "उनचास",
    "पचास", "इक्यावन", "बावन", "तिरपन", "चौवन", "पचपन", "छप्पन", "सत्तावन", "अट्ठावन", "उनसठ",
    "साठ", "इकसठ", "बासठ", "तिरसठ", "चौंसठ", "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ", "उनहत्तर",
    "सत्तर", "इकहत्तर", "बहत्तर", "तिहत्तर", "चौहत्तर", "पचहत्तर", "छिहत्तर", "सतहत्तर", "अठहत्तर", "उनासी",
    "अस्सी", "इक्यासी", "बयासी", "तिरासी", "चौरासी", "पचासी", "छियासी", "सत्तासी", "अठासी", "नवासी",
    "नब्बे", "इक्यानवे", "बानवे", "तिरानवे", "चौरानवे", "पचानवे", "छियानवे", "सत्तानवे", "अट्ठानवे", "निन्यानवे",
]
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _int_to_hindi(n):
    """Convert non-negative integer into spoken Hindi words (Indian numbering: lakh/crore)."""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n < 0:
        return "माइनस " + _int_to_hindi(-n)
    if n < 100:
        return _HI_0_99[n]
    # v3.86 FIX: Hindi years 1100-1999 are spoken as "सत्रह सौ उनतालीस" / "अठारह सौ उनचास" / "उन्नीस सौ इक्यानवे"
    if 1100 <= n <= 1999:
        hi, lo = divmod(n, 100)
        return f"{_HI_0_99[hi]} सौ" + (f" {_HI_0_99[lo]}" if lo else "")
    parts = []
    if n >= 10000000:
        parts.append(_int_to_hindi(n // 10000000) + " करोड़")
        n %= 10000000
    if n >= 100000:
        parts.append(_int_to_hindi(n // 100000) + " लाख")
        n %= 100000
    if n >= 1000:
        parts.append(_int_to_hindi(n // 1000) + " हजार")
        n %= 1000
    if n >= 100:
        parts.append(_HI_0_99[n // 100] + " सौ")
        n %= 100
    if n > 0:
        parts.append(_HI_0_99[n])
    return " ".join(parts)


def _expand_token(tok):
    """v3.84: Expand numbers/times (6:04, 3,84,000, 615, 2023) to spoken Hindi words for Whisper matching."""
    t = (tok or "").translate(_DEV_DIGITS).strip()
    if not t:
        return ""
    # Time pattern e.g. 6:04 -> छह बजकर चार
    tm = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if tm:
        h, m = int(tm.group(1)), int(tm.group(2))
        if m == 0:
            return f"{_int_to_hindi(h)} बजे"
        return f"{_int_to_hindi(h)} बजकर {_int_to_hindi(m)}"
    # Percent e.g. 95%
    pm = re.fullmatch(r"(\d+(?:\.\d+)?)%", t)
    if pm:
        return _expand_token(pm.group(1)) + " प्रतिशत"
    # Indian/Western comma numbers e.g. 3,84,000 or 2023 or 615
    clean = t.replace(",", "")
    if re.fullmatch(r"\d+", clean):
        if len(clean) <= 9:
            return _int_to_hindi(int(clean))
        return " ".join(_HI_0_99[int(d)] for d in clean)
    dm = re.fullmatch(r"(\d+)\.(\d+)", clean)
    if dm:
        a = _int_to_hindi(int(dm.group(1)))
        b = " ".join(_HI_0_99[int(d)] for d in dm.group(2)[:4])
        return f"{a} पॉइंट {b}"
    # Mixed token like Chandrayaan-3 or LVM3 -> expand trailing digits
    return re.sub(r"\d+", lambda m: " " + _int_to_hindi(int(m.group(0))) if len(m.group(0)) <= 6 else m.group(0), t)


def _norm(t, phonetic=False):
    # v3.86 FIX: hyphenated words like "कोह-इ-नूर" / "Koh-i-Noor" match Whisper's "कोहिनूर"
    t = re.sub(r"(?<=[A-Za-z\u0900-\u097f])[-–—](?=[A-Za-z\u0900-\u097f])", "", str(t or ""))
    t = _expand_token(t)
    t = t.lower()
    t = re.sub(r"[\u093c\u0902\u0901]", "", t)            # nukta / anusvara / chandrabindu
    if phonetic:
        try:
            from translit import word as _tw
            t = " ".join(_tw(x) for x in t.split())
        except Exception:
            pass
        t = t.lower()
        t = re.sub(r"aa+", "a", t)
        t = re.sub(r"ee+|ii+", "i", t)
        t = re.sub(r"oo+|uu+", "u", t)
        t = re.sub(r"[^a-z0-9]", "", t)
        return t
    return re.sub(r"[^\w\u0900-\u097f]", "", t)


def _spoken_weight(tok):
    """Approximate spoken duration weight for gap interpolation (3,84,000 >> को)."""
    exp = _expand_token(tok)
    n = re.sub(r"[^\w\u0900-\u097f]", "", exp)
    return max(2.0, float(len(n)))


def _bigger_ok():
    """v3.1: 'small' model (~460 MB, ~1.5 GB RAM) tabhi jab RAM >= 6 GB ho."""
    try:
        import hardware
        return (hardware.ram_gb() or 0) >= 12  # v3.22: 8GB RAM laptops stay fast on base model (no hang)
    except Exception:
        return False


def _match_pass(flat, words, phonetic=False):
    """Run one SequenceMatcher pass (Devanagari or phonetic Latin) with stray-match filtering."""
    T = []; Tt = []
    for w in words:
        n = _norm(w["w"], phonetic=phonetic)
        if not n:
            continue
        d = max(0.01, (w["end"] - w["start"])) / max(1, len(n))
        for k, ch in enumerate(n):
            T.append(ch); Tt.append(w["start"] + k * d)
    if not T:
        return 0.0, [None] * len(flat)
    S = []; spans = []
    for w in flat:
        n = _norm(w["w"], phonetic=phonetic)
        a = len(S); S.extend(n); spans.append((a, len(S)))
    if not S:
        return 0.0, [None] * len(flat)
    sm = difflib.SequenceMatcher(None, "".join(S), "".join(T), autojunk=False)
    m = {}
    for blk in sm.get_matching_blocks():
        if blk.size < 2:                                 # v3.84: ignore stray 1-char matra hits!
            continue
        for k in range(blk.size):
            m[blk.a + k] = Tt[blk.b + k]
    matched = len(m) / max(1, len(S))
    starts = []
    for a, b in spans:
        ts = sorted(m[i] for i in range(a, b) if i in m)
        if not ts:
            starts.append(None)
        elif len(ts) >= 3:
            # v3.84: trimmed earliest timestamp (skip single-char outlier at index 0 if gap > 0.35s)
            t0 = ts[1] if (ts[1] - ts[0]) > 0.35 else ts[0]
            starts.append(t0)
        else:
            starts.append(ts[0])
    return matched, starts


def _clean_anchors(starts):
    """v3.84: Remove non-monotonic or isolated outlier anchors before interpolation."""
    out = list(starts)
    known = [i for i, v in enumerate(out) if v is not None]
    if len(known) < 3:
        return out
    # Drop any anchor that jumps backwards relative to BOTH previous and next known anchors,
    # or jumps > 2.5s early relative to linear expectation between neighbors
    for idx_pos in range(1, len(known) - 1):
        p_i, c_i, n_i = known[idx_pos - 1], known[idx_pos], known[idx_pos + 1]
        p_t, c_t, n_t = out[p_i], out[c_i], out[n_i]
        if p_t is None or n_t is None or c_t is None:
            continue
        if c_t < p_t - 0.15 or c_t > n_t + 0.15:
            out[c_i] = None
    return out


def align(sents, wav, size="base", words=None):
    """Script ke shabdon ko asli awaaz ke time se milao. sents ko in-place update karta hai. True/False."""
    if words is None:
        script_text = " ".join(s.get("script") or s["text"] for s in sents)
        words, _ = transcribe(wav, size, "hi", prompt=script_text)
    if not words or len(words) < 3:
        return False
    flat = [w for s in sents for w in s["words"]]
    if not flat:
        return False

    # v3.84: Try Devanagari normalized pass AND phonetic Latin pass; keep the stronger alignment!
    m_dev, st_dev = _match_pass(flat, words, phonetic=False)
    m_lat, st_lat = _match_pass(flat, words, phonetic=True)
    if m_lat > m_dev + 0.05:
        matched, starts = m_lat, st_lat
    else:
        matched, starts = m_dev, st_dev

    if matched < 0.35:
        if size == "base" and _bigger_ok() and wav is not None:
            log(f"   Whisper (base) match kam ({matched:.0%}) – 'small' model se dobara sun raha hoon...", show=False)
            return align(sents, wav, "small")
        log(f"   Whisper match kam ({matched:.0%}) – awaaz ke pauses se timing (fallback)", show=False)
        return False

    starts = _clean_anchors(starts)
    n = len(starts)
    known = [i for i in range(n) if starts[i] is not None]
    if not known:
        return False

    # v3.84: Spoken-weight gap interpolation (3,84,000 gets proper spoken share, not 1 word index!)
    weights = [_spoken_weight(w["w"]) for w in flat]
    cum_w = [0.0]
    for wt in weights:
        cum_w.append(cum_w[-1] + wt)

    for i in range(n):
        if starts[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            if lo is not None and hi is not None:
                denom = max(1e-6, cum_w[hi] - cum_w[lo])
                frac = (cum_w[i] - cum_w[lo]) / denom
                starts[i] = starts[lo] + (starts[hi] - starts[lo]) * frac
            elif lo is not None:
                # Extrapolate using local speaking rate (~0.06s per spoken char)
                starts[i] = starts[lo] + 0.06 * (cum_w[i] - cum_w[lo])
            else:
                starts[i] = max(0.0, starts[hi] - 0.06 * (cum_w[hi] - cum_w[i]))

    for i in range(1, n):
        if starts[i] < starts[i - 1] + 0.05:
            starts[i] = starts[i - 1] + 0.05

    # v3.30 FIX (0:47-0:57 tail freeze): ensure tail words stretch smoothly to actual audio duration
    from common import duration as _aud_dur
    _tot_a = (_aud_dur(wav) if wav else None) or max(starts[-1] + 0.3, words[-1]["end"])
    last_known = max(known) if known else n - 1
    if last_known < n - 1 and _tot_a > starts[last_known] + 1.0:
        span = max(0.5, (_tot_a - 0.15) - starts[last_known])
        denom = max(1e-6, cum_w[n] - cum_w[last_known])
        for k in range(last_known + 1, n):
            starts[k] = starts[last_known] + span * (cum_w[k] - cum_w[last_known]) / denom

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
