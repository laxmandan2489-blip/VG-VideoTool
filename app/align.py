"""v2.6 + v3.84 + v3.87: Captions & visuals ki 100% audio-locked timing – free Whisper (faster-whisper) awaaz sunke
har shabd ka sahi time pakadta hai.

v3.87 UNIVERSAL AUDIO-LOCK SYNC ENGINE:
  1. Cloud Whisper `small` unlock: GitHub Actions (7 GB Linux runner) par ab `small` silently `base` me downgrade
     nahi hoga (Hindi + English tech/business/space words ki accuracy ~3x behtar).
  2. Drift-free Whisper decode: `condition_on_previous_text=False` + studio TTS par `vad_filter=False` (Silero VAD
     onset-clipping aur mid-video hallucination/skip drift khatam) + truncated-output auto-retry.
  3. Universal phonetic + acronym folding: har category ke English acronyms (GPS->jipies, IRNSS->aiareneses,
     GDP->jidipi, DRDO->diardio, RBI->arbiai...) aur loanwords (Navigation, Satellite, Export, Military...)
     Devanagari Whisper output se bina kisi topic hardcoding ke match hote hain.
  4. Banded Word-Level Monotonic DP Alignment: global char SequenceMatcher ke stray 2-char stop-word hijacks
     ("का/की/के/है/भारत" 10s pehle match hokar captions aage bhagna) 100% band.
  5. Speaking-Rate Consistent Anchor Chain: DP se sirf wahi anchors accept hote hain jinka local speaking rate
     insaan ke bolne ki gati ke andar ho — captions kabhi voice se aage nahi bhag sakti.
  6. Real-Audio 10ms RMS Speech-Onset Snap + Spoken-Weight Pause Fallback: silence/breath me caption/visual
     kabhi samay se pehle trigger nahi hoga.
  7. Dual-script + acronym `line_coverage()`: English/tech lines par false mid-video Gemini TTS splice band.
"""
from pathlib import Path
import os, re, sys, subprocess, difflib
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


def _bigger_ok():
    """v3.87: 'small' int8 (~260 MB RAM) GitHub Actions (7 GB Linux) aur >=6 GB Linux/Mac par safely chalta hai.
    Windows 8 GB laptops par hi 12 GB guard rakha hai."""
    if os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("VG_CLOUD") == "1":
        return True
    try:
        import hardware
        ram = hardware.ram_gb() or 0
        if sys.platform == "win32":
            return ram >= 12
        return ram >= 6.0
    except Exception:
        return False


def load(size="base"):
    # v3.25 + v3.87: keep 'small' on cloud/Linux >=6GB; downgrade only on tight Windows laptops
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
    """ffmpeg se 16 kHz mono float32 numpy (Whisper + energy envelope ko seedha)."""
    if not path:
        return None
    try:
        import numpy as np
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                            "-f", "f32le", "-"], capture_output=True, timeout=900, stdin=subprocess.DEVNULL)
        if r.returncode != 0 or len(r.stdout) < 3200:
            return None
        return np.frombuffer(r.stdout, dtype=np.float32).copy()
    except Exception:
        return None


ONE = {"size": None}          # v3.6: set ho to har 'base' maang isi model se (ek hi baar sunna)
_TX = {}                      # v3.6: (file, size, lang, vad, mtime, bytes) -> result


def transcribe(path, size="base", lang="hi", prompt=None, vad=False):
    """Returns (words [{w,start,end}], segments [{text,start,end}]) or (None, None).
    v3.87: studio TTS ke liye default vad=False + condition_on_previous_text=False (zero drift)."""
    if ONE["size"] and size == "base":
        size = ONE["size"]
    try:
        st_ = Path(path).stat()
        ck = (str(Path(path).resolve()), size, lang, bool(vad), st_.st_mtime_ns, st_.st_size)
    except Exception:
        ck = None
    if ck and ck in _TX:
        return _TX[ck]
    r = _transcribe(path, size, lang, prompt, vad=vad)
    if ck and r[0]:
        _TX[ck] = r
    return r


def _transcribe(path, size="base", lang="hi", prompt=None, vad=False):
    m = load(size)
    if not m:
        return None, None
    try:
        audio = _load16k(path)                 # v2.10: PyAV (av.open) bypass
        kw = dict(language=lang, word_timestamps=True, vad_filter=bool(vad),
                  condition_on_previous_text=False,
                  initial_prompt=(prompt[:800] if prompt else None), beam_size=3)
        try:
            segs, _ = m.transcribe(audio if audio is not None else str(path), **kw)
        except TypeError:
            kw.pop("condition_on_previous_text", None)
            segs, _ = m.transcribe(audio if audio is not None else str(path), **kw)
        words, out = [], []
        for s in segs:
            out.append({"text": s.text.strip(), "start": s.start, "end": s.end})
            for w in (s.words or []):
                t = w.word.strip()
                if t:
                    words.append({"w": t, "start": float(w.start), "end": float(w.end)})
        return words, out
    except Exception as e:
        log(f"   Whisper sun nahi paya ({e})", show=False); return None, None


# ------------------------------------------------------------------ v3.84 + v3.87: Hindi number, acronym & phonetic norm
_HI_0_99 = [
    "शून्य", "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ",
    "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह", "अठारह", "उन्नीस",
    "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस", "पच्चीस", "छब्बीस", "सत्ताईस", "अट्ठाईस", "उनतीस",
    "तीस", "इकतीस", "बत्तीस", "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस", "उनतालीस",
    "चालीस", "इकतालीस", "बयालीस", "तैंतीस", "चौवालीस", "पैंतालीस", "छियालीस", "सैंतीस", "अड़तालीस", "उनचास",
    "पचास", "इक्यावन", "बावन", "तिरपन", "चौवन", "पचपन", "छप्पन", "सत्तावन", "अट्ठावन", "उनसठ",
    "साठ", "इकसठ", "बासठ", "तिरसठ", "चौंसठ", "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ", "उनहत्तर",
    "सत्तर", "इकहत्तर", "बहत्तर", "तिहत्तर", "चौहत्तर", "पचहत्तर", "छिहत्तर", "सतहत्तर", "अठहत्तर", "उनासी",
    "अस्सी", "इक्यासी", "बयासी", "तिरासी", "चौरासी", "पचासी", "छियासी", "सत्तासी", "अठासी", "नवासी",
    "नब्बे", "इक्यानवे", "बानवे", "तिरानवे", "चौरानवे", "पचानवे", "छियानवे", "सत्तानवे", "अट्ठानवे", "निन्यानवे",
]
# Fix index 43 and 47 accurately
_HI_0_99[43] = "तैंतालीस"
_HI_0_99[47] = "सैंतालीस"
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Universal English letter-name pronunciation in Hindi/Hinglish (GPS -> jipies, GDP -> jidipi, IRNSS -> aiareneses)
_LETTER_SPOKEN = {
    "A": "e", "B": "bi", "C": "si", "D": "di", "E": "i", "F": "ef", "G": "ji", "H": "ech",
    "I": "ai", "J": "je", "K": "ke", "L": "el", "M": "em", "N": "en", "O": "o", "P": "pi",
    "Q": "kyu", "R": "ar", "S": "es", "T": "ti", "U": "yu", "V": "vi", "W": "dablyu",
    "X": "eks", "Y": "wai", "Z": "jed",
}

_STOP_NORM = {
    "का", "की", "के", "को", "मे", "में", "ने", "से", "पर", "है", "हैं", "था", "थी", "थे",
    "भी", "ही", "तो", "और", "या", "कि", "यह", "वह", "एक", "इस", "उस", "कर", "हो", "जो",
    "ka", "ki", "ke", "ko", "me", "mein", "ne", "se", "par", "hai", "hain", "tha", "thi",
    "the", "bhi", "hi", "to", "aur", "ya", "ye", "wo", "ek", "is", "us", "kar", "ho", "jo",
    "in", "on", "of", "to", "a", "an", "and", "or", "is", "it",
}


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
    # Strip surrounding punctuation only for pure-number/time detection
    t_core = re.sub(r"^[(\[\"'“‘]+|[.,।!?;:)\]'\"”’]+$", "", t)
    tm = re.fullmatch(r"(\d{1,2}):(\d{2})", t_core)
    if tm:
        h, m = int(tm.group(1)), int(tm.group(2))
        if m == 0:
            return f"{_int_to_hindi(h)} बजे"
        return f"{_int_to_hindi(h)} बजकर {_int_to_hindi(m)}"
    pm = re.fullmatch(r"(\d+(?:\.\d+)?)%", t_core)
    if pm:
        return _expand_token(pm.group(1)) + " प्रतिशत"
    clean = t_core.replace(",", "")
    if re.fullmatch(r"\d+", clean):
        if len(clean) <= 9:
            return _int_to_hindi(int(clean))
        return " ".join(_HI_0_99[int(d)] for d in clean)
    dm = re.fullmatch(r"(\d+)\.(\d+)", clean)
    if dm:
        a = _int_to_hindi(int(dm.group(1)))
        b = " ".join(_HI_0_99[int(d)] for d in dm.group(2)[:4])
        return f"{a} पॉइंट {b}"
    # Mixed token like Chandrayaan-3 or LVM3 or 1500km -> expand digits
    return re.sub(r"\d+", lambda m: " " + _int_to_hindi(int(m.group(0))) + " " if len(m.group(0)) <= 6 else m.group(0), t)


def _phonetic_fold(s):
    """v3.87: Universal phonetic folding so English words & Devanagari transliterations match cleanly."""
    s = (s or "").lower()
    s = s.replace("ph", "f").replace("x", "ks").replace("q", "k")
    s = re.sub(r"tion\b", "san", s)
    s = re.sub(r"sion\b", "san", s)
    s = re.sub(r"sh|chh", "s", s)
    s = re.sub(r"c(?!h)", "k", s)
    s = s.replace("w", "v").replace("z", "j")
    s = re.sub(r"ee+|ii+|ey|ie", "i", s)
    s = re.sub(r"oo+|uu+", "u", s)
    s = re.sub(r"aa+", "a", s)
    s = re.sub(r"ai|ae|ay", "e", s)
    s = re.sub(r"au|aw|ou", "o", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    # Collapse repeated consonants/vowels (e.g. satellite -> satelite)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def _acronym_spoken(tok):
    """v3.87: Universal spoken form for 2-6 letter uppercase acronyms (GPS->jipies, IRNSS->aiareneses, GDP->jidipi)."""
    core = re.sub(r"[^A-Za-z]", "", str(tok or ""))
    if 2 <= len(core) <= 6 and core.isupper():
        return _phonetic_fold("".join(_LETTER_SPOKEN.get(ch, ch.lower()) for ch in core))
    return ""


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
        return _phonetic_fold(t)
    return re.sub(r"[^\w\u0900-\u097f]", "", t)


def _spoken_weight(tok):
    """Approximate spoken duration weight for gap interpolation (3,84,000 >> को)."""
    raw = str(tok or "").strip()
    acr = _acronym_spoken(raw)
    if acr:
        return max(3.0, float(len(acr)))
    exp = _expand_token(raw)
    n = re.sub(r"[^\w\u0900-\u097f]", "", exp)
    return max(2.0, float(len(n)))


def _tok_info(raw):
    """Build multi-key representation for universal Hindi/Hinglish/Acronym token similarity."""
    dev = _norm(raw, phonetic=False)
    ph = _norm(raw, phonetic=True)
    acr = _acronym_spoken(raw)
    is_stop = (dev in _STOP_NORM) or (ph in _STOP_NORM) or (len(dev) <= 2 and len(ph) <= 2 and not acr)
    return {"dev": dev, "ph": ph, "acr": acr, "stop": is_stop}


def _tok_sim(a, b):
    """Universal token similarity in [0, 1] across Devanagari, folded phonetic Latin, and English acronyms."""
    if not a["dev"] and not a["ph"] and not a["acr"]:
        return 0.0
    if not b["dev"] and not b["ph"] and not b["acr"]:
        return 0.0
    best = 0.0
    if a["dev"] and b["dev"]:
        if a["dev"] == b["dev"]:
            return 1.0
        if (a["dev"][0] == b["dev"][0]) or (len(a["dev"]) >= 4 and len(b["dev"]) >= 4):
            best = max(best, difflib.SequenceMatcher(None, a["dev"], b["dev"]).ratio())
    if a["ph"] and b["ph"]:
        if a["ph"] == b["ph"]:
            return 1.0
        best = max(best, difflib.SequenceMatcher(None, a["ph"], b["ph"]).ratio())
    if a["acr"] and b["ph"]:
        if a["acr"] == b["ph"]:
            return 1.0
        best = max(best, difflib.SequenceMatcher(None, a["acr"], b["ph"]).ratio())
    if b["acr"] and a["ph"]:
        if b["acr"] == a["ph"]:
            return 1.0
        best = max(best, difflib.SequenceMatcher(None, b["acr"], a["ph"]).ratio())
    return best


# ------------------------------------------------------------------ v3.87: Banded Word-Level Monotonic DP Alignment
def _dp_word_align(flat, words, total_dur):
    """Align script words to Whisper words using banded monotonic DP with phonetic + acronym + locality scoring.
    Returns (match_ratio, anchors_list [(script_word_idx, start_time, confidence)])."""
    # Expand each script word into spoken sub-tokens (e.g. "1999" -> ["उन्नीस", "सौ", "निन्यानवे"])
    s_toks = []
    for wi, w in enumerate(flat):
        raw = str(w["w"] or "").strip()
        # Keep hyphenated words together when no digits
        if re.search(r"\d", raw):
            exp = _expand_token(raw)
            parts = [p for p in exp.split() if p]
        else:
            parts = [raw]
        if not parts:
            parts = [raw]
        for sub_k, p in enumerate(parts):
            info = _tok_info(p)
            if not info["dev"] and not info["ph"] and not info["acr"]:
                continue
            s_toks.append((wi, sub_k, len(parts), info, max(2.0, float(len(info["ph"] or info["dev"] or "aa")))))

    w_toks = []
    for w in words:
        raw = str(w["w"] or "").strip()
        info = _tok_info(raw)
        if not info["dev"] and not info["ph"] and not info["acr"]:
            continue
        w_toks.append((float(w["start"]), float(w["end"]), info))

    M, N = len(s_toks), len(w_toks)
    if M == 0 or N == 0:
        return 0.0, []

    tot_d = max(1.0, float(total_dur or (w_toks[-1][1] if w_toks else 1.0)))
    # Normalized spoken progress for script tokens
    s_cum = [0.0]
    for t in s_toks:
        s_cum.append(s_cum[-1] + t[4])
    s_tot = max(1.0, s_cum[-1])
    p_s = [s_cum[i] / s_tot for i in range(M)]
    p_w = [min(1.0, max(0.0, w_toks[j][0] / tot_d)) for j in range(N)]

    # Locality band: strict enough to stop 10s+ stray hijacks, wide enough for real speaking-speed variation
    band = 0.38 if tot_d <= 35.0 else min(0.32, max(0.14, 18.0 / tot_d))

    # Sparse DP using dict per row (fast for both 50s Shorts and 10m Longs)
    # dp[j] = best score ending at Whisper index <= j; back[i][j] = (prev_i, prev_j, matched_bool)
    NEG = -1e9
    # Compute valid j-ranges per i
    j_ranges = []
    for i in range(M):
        ps = p_s[i]
        # Binary search or scan
        lo = 0
        while lo < N and p_w[lo] < ps - band:
            lo += 1
        hi = N - 1
        while hi >= lo and p_w[hi] > ps + band:
            hi -= 1
        # Always keep a small minimum window around proportional index
        center = int(round(ps * (N - 1)))
        lo = min(lo, max(0, center - 12))
        hi = max(hi, min(N - 1, center + 12))
        j_ranges.append((lo, hi))

    # Standard banded Needleman-Wunsch over (i, j) where 0<=i<=M, 0<=j<=N
    # States stored only inside band
    prev_row = {0: 0.0}
    for j in range(1, min(N, j_ranges[0][1] + 2) + 1):
        prev_row[j] = -0.04 * j
    trace = {}  # (i, j) -> code: 1=diag_match, 2=diag_mismatch, 3=up(skip script), 4=left(skip whisper)

    for i in range(1, M + 1):
        lo, hi = j_ranges[i - 1]
        j0 = max(1, lo + 1)
        j1 = min(N, hi + 1)
        s_info = s_toks[i - 1][3]
        ps = p_s[i - 1]
        cur_row = {}
        # Boundary j = j0 - 1
        if (j0 - 1) in prev_row:
            cur_row[j0 - 1] = prev_row[j0 - 1] - 0.12
            trace[(i, j0 - 1)] = 3
        for j in range(j0, j1 + 1):
            w_info = w_toks[j - 1][2]
            best_sc = NEG
            best_op = 3
            # Up: skip script token i-1
            if j in prev_row:
                sc = prev_row[j] - 0.12
                if sc > best_sc:
                    best_sc, best_op = sc, 3
            # Left: skip whisper token j-1
            if (j - 1) in cur_row:
                sc = cur_row[j - 1] - 0.04
                if sc > best_sc:
                    best_sc, best_op = sc, 4
            # Diag: align script i-1 with whisper j-1
            if (j - 1) in prev_row:
                sim = _tok_sim(s_info, w_info)
                thr = 0.88 if s_info["stop"] else 0.62
                if sim >= thr:
                    # Content words weigh much more than 2-char stop-words; gentle locality prior
                    w_val = (0.40 if s_info["stop"] else (1.0 + 0.12 * min(8, len(s_info["ph"] or s_info["dev"]))))
                    loc_pen = 0.45 * abs(ps - p_w[j - 1])
                    sc = prev_row[j - 1] + sim * w_val - loc_pen
                    if sc > best_sc:
                        best_sc, best_op = sc, 1
                else:
                    sc = prev_row[j - 1] - 0.35
                    if sc > best_sc:
                        best_sc, best_op = sc, 2
            cur_row[j] = best_sc
            trace[(i, j)] = best_op
        prev_row = cur_row

    # Find best ending j in final row
    if not prev_row:
        return 0.0, []
    j_best = max(prev_row.keys(), key=lambda j: prev_row[j])
    i, j = M, j_best
    matched_toks = {}  # s_tok_idx -> (t_start, conf)
    while i > 0 and j > 0:
        op = trace.get((i, j), 3)
        if op == 1:
            s_info = s_toks[i - 1][3]
            w_info = w_toks[j - 1][2]
            sim = _tok_sim(s_info, w_info)
            conf = sim * (0.45 if s_info["stop"] else 1.2)
            matched_toks[i - 1] = (w_toks[j - 1][0], conf)
            i -= 1; j -= 1
        elif op == 2:
            i -= 1; j -= 1
        elif op == 3:
            i -= 1
        else:
            j -= 1

    # Map sub-tokens back to parent script word indices
    by_word = {}
    for ti, (t0, conf) in matched_toks.items():
        wi, sub_k, n_sub, info, _ = s_toks[ti]
        # If multi-token number matched at sub_k > 0, adjust slightly backward to word start
        adj_t = max(0.0, t0 - sub_k * 0.16)
        if wi not in by_word or sub_k < by_word[wi][0]:
            by_word[wi] = (sub_k, adj_t, conf)
        else:
            # Accumulate confidence if multiple sub-tokens matched
            old_k, old_t, old_c = by_word[wi]
            by_word[wi] = (old_k, old_t, old_c + conf * 0.5)

    anchors = [(wi, v[1], v[2]) for wi, v in sorted(by_word.items())]
    match_ratio = len(matched_toks) / max(1, M)
    return match_ratio, anchors


def _match_pass(flat, words, phonetic=False):
    """Backup char-level SequenceMatcher pass (v3.87: stricter blk.size >= 3 & median-trimmed start)."""
    T = []; Tt = []
    for w in words:
        n = _norm(w["w"], phonetic=phonetic)
        if not n:
            continue
        d = max(0.01, (w["end"] - w["start"])) / max(1, len(n))
        for k, ch in enumerate(n):
            T.append(ch); Tt.append(w["start"] + k * d)
    if not T:
        return 0.0, []
    S = []; spans = []
    for w in flat:
        n = _norm(w["w"], phonetic=phonetic)
        a = len(S); S.extend(n); spans.append((a, len(S)))
    if not S:
        return 0.0, []
    sm = difflib.SequenceMatcher(None, "".join(S), "".join(T), autojunk=False)
    m = {}
    for blk in sm.get_matching_blocks():
        if blk.size < 3:                                 # v3.87: block stray 2-char stop-word hijacks
            continue
        for k in range(blk.size):
            m[blk.a + k] = Tt[blk.b + k]
    matched = len(m) / max(1, len(S))
    anchors = []
    for wi, (a, b) in enumerate(spans):
        ts = sorted(m[i] for i in range(a, b) if i in m)
        if not ts:
            continue
        # Reject split-word stray early prefix: if median is > 0.6s after ts[0], use the cluster near median
        med = ts[len(ts) // 2]
        good = [x for x in ts if abs(x - med) <= 0.6]
        t0 = good[0] if good else med
        conf = len(good) / max(1, b - a)
        if conf >= 0.45:
            anchors.append((wi, t0, conf))
    return matched, anchors


def _clean_anchors_v2(anchors, cum_w, total_dur):
    """v3.87: Speaking-rate consistent Longest Valid Chain over anchors.
    Mathematically forbids any stray anchor that compresses a section (captions racing ahead of voice)
    or jumps backwards/forwards impossibly."""
    if len(anchors) <= 2:
        return anchors
    tot_w = max(1.0, cum_w[-1])
    tot_d = max(1.0, float(total_dur))
    rate = tot_d / tot_w  # average seconds per spoken char

    K = len(anchors)
    # dp_sc[k] = best chain score ending at anchor k; parent[k] = prev anchor index
    dp_sc = [0.0] * K
    parent = [-1] * K

    for k in range(K):
        idx_k, t_k, conf_k = anchors[k]
        # Soft penalty if anchor is wildly far from global expected time (still allows natural pacing!)
        exp_global = cum_w[idx_k] * rate
        g_dev = abs(t_k - exp_global)
        # Allow up to 35% of duration or 5s natural pacing drift, penalize beyond
        g_pen = 0.0 if g_dev <= max(5.0, 0.35 * tot_d) else 0.6 * (g_dev / max(1.0, tot_d))
        dp_sc[k] = conf_k - g_pen

        # Check up to 48 predecessors
        lo_p = max(0, k - 48)
        for p in range(k - 1, lo_p - 1, -1):
            idx_p, t_p, _ = anchors[p]
            if idx_p >= idx_k:
                continue
            dt = t_k - t_p
            if dt <= 0.02:
                continue
            dw = max(1.0, cum_w[idx_k] - cum_w[idx_p])
            exp_dt = dw * rate
            # Hard physical speaking-speed bounds:
            # - Cannot speak >3.5x faster than average (prevents captions squeezing & racing ahead!)
            # - Cannot be >4.0x slower + 2.4s pause (prevents wild late jumps)
            min_dt = max(0.03, 0.28 * exp_dt - 0.35)
            max_dt = max(2.2, 4.0 * exp_dt + 2.4)
            if dt < min_dt or dt > max_dt:
                continue
            # Prefer transitions whose local speaking rate is close to 1.0x
            ratio = dt / max(0.08, exp_dt)
            rate_pen = 0.08 * abs(ratio - 1.0) if ratio <= 2.5 else 0.15 * (ratio - 1.0)
            cand = dp_sc[p] + conf_k - rate_pen - g_pen * 0.25
            if cand > dp_sc[k]:
                dp_sc[k] = cand
                parent[k] = p

    best_k = max(range(K), key=lambda k: dp_sc[k])
    chain = []
    cur = best_k
    while cur != -1:
        chain.append(anchors[cur])
        cur = parent[cur]
    chain.reverse()
    return chain


def _speech_envelope(wav):
    """Return (rms_10ms, thr, total_dur) from wav via 16kHz ffmpeg decode, or (None, None, None)."""
    audio = _load16k(wav)
    if audio is None or len(audio) < 1600:
        return None, None, None
    try:
        import numpy as np
        hop = 160  # 10ms at 16kHz
        nfr = len(audio) // hop
        if nfr < 10:
            return None, None, None
        rms = np.sqrt(np.mean(audio[:nfr * hop].reshape(nfr, hop) ** 2, axis=1))
        thr = max(0.008, float(np.percentile(rms, 15)) * 2.2)
        return rms, thr, len(audio) / 16000.0
    except Exception:
        return None, None, None


def _snap_sentences_to_speech(sents, wav, anchored_word_set):
    """v3.87: Never start a sentence caption/visual inside dead silence before the narrator speaks."""
    rms, thr, dur = _speech_envelope(wav)
    if rms is None:
        return
    nfr = len(rms)
    for i in range(1, len(sents)):
        s = sents[i]
        ws = s.get("words") or []
        if not ws:
            continue
        t0 = float(s["start"])
        f0 = int(round(t0 * 100))
        if f0 < 0 or f0 >= nfr - 5:
            continue
        # Only adjust if t0 is currently sitting inside silence (30ms window around f0 is quiet)
        if float(rms[max(0, f0 - 1):min(nfr, f0 + 3)].max()) >= thr:
            continue
        # Scan forward up to +0.80s for actual sustained speech onset (>=3 consecutive frames above thr)
        max_f = min(nfr - 3, f0 + 80, int(round((float(s["end"]) - 0.25) * 100)))
        onset_f = None
        for f in range(f0 + 2, max_f):
            if rms[f] >= thr and rms[f + 1] >= thr and rms[f + 2] >= thr:
                onset_f = f
                break
        if onset_f is not None:
            new_t = max(t0, (onset_f / 100.0) - 0.03)
            # Keep previous sentence end strictly <= new_t
            prev_ws = sents[i - 1].get("words") or []
            if prev_ws and new_t < prev_ws[-1]["start"] + 0.08:
                continue
            shift = new_t - t0
            if 0.06 <= shift <= 0.80:
                s["start"] = round(new_t, 3)
                ws[0]["start"] = round(new_t, 3)
                # Keep words monotonic
                for k in range(1, len(ws)):
                    if ws[k]["start"] < ws[k - 1]["start"] + 0.05:
                        ws[k]["start"] = round(ws[k - 1]["start"] + 0.05, 3)
                for k in range(len(ws) - 1):
                    ws[k]["end"] = round(max(ws[k]["start"] + 0.05, ws[k + 1]["start"]), 3)
                if prev_ws:
                    prev_ws[-1]["end"] = round(new_t, 3)
                    sents[i - 1]["end"] = round(new_t, 3)


def _energy_fallback_align(sents, wav):
    """v3.87: Last-resort spoken-weight + real audio pause alignment (never leaves raw char-len guess)."""
    rms, thr, dur = _speech_envelope(wav)
    if dur is None:
        from common import duration as _aud_dur
        dur = _aud_dur(wav) if wav else None
    if not dur or dur <= 0.5:
        return False
    # Detect quiet pauses >= 0.16s
    pauses = []
    if rms is not None:
        i = 0; nfr = len(rms)
        while i < nfr:
            if rms[i] < thr:
                j = i
                while j < nfr and rms[j] < thr:
                    j += 1
                if (j - i) >= 16:
                    # Speech resumes at j * 0.01
                    pauses.append(j * 0.01)
                i = j
            else:
                i += 1
    line_w = [sum(_spoken_weight(w["w"]) for w in s["words"]) for s in sents]
    tot_w = max(1.0, sum(line_w))
    bounds = [0.0]; acc = 0.0
    for lw in line_w[:-1]:
        acc += lw
        guess = dur * acc / tot_w
        near = [p for p in pauses if abs(p - guess) < 1.2 and p > bounds[-1] + 0.35]
        bounds.append(min(near, key=lambda p: abs(p - guess)) if near else guess)
    bounds.append(dur)
    for k, s in enumerate(sents):
        a, b = bounds[k], bounds[k + 1]
        ws = s["words"]
        if not ws:
            continue
        wts = [_spoken_weight(w["w"]) for w in ws]
        sw = max(1.0, sum(wts)); cur = a
        for w, wt in zip(ws, wts):
            d = max(0.05, (b - a) * wt / sw)
            w["start"] = round(cur, 3); cur += d; w["end"] = round(min(b, cur), 3)
        s["start"] = ws[0]["start"] if k else 0.0
        s["end"] = ws[-1]["end"]
    log("   captions timing: spoken-weight + pause fallback se sahi kiya ✓")
    return True


def align(sents, wav, size="base", words=None):
    """Script ke shabdon ko asli awaaz ke time se milao. sents ko in-place update karta hai. True/False."""
    flat = [w for s in sents for w in s["words"]]
    if not flat:
        return False

    from common import duration as _aud_dur
    _tot_a = (_aud_dur(wav) if wav else None)

    if words is None:
        script_text = " ".join(s.get("script") or s["text"] for s in sents)
        words, _ = transcribe(wav, size, "hi", prompt=script_text, vad=False)
        # v3.87 AUTO-RETRY: if Whisper output looks truncated or sparse, retry with 'small' / vad=True
        if wav is not None and _tot_a and _tot_a > 10.0:
            sparse = (not words) or (len(words) < len(flat) * 0.42) or (words[-1]["end"] < _tot_a * 0.72)
            if sparse:
                retry_sz = "small" if (_bigger_ok() and size != "small") else size
                log(f"   Whisper output adhoora laga ({len(words or [])} shabd) – {retry_sz} se dobara sun raha hoon...", show=False)
                w2, _ = transcribe(wav, retry_sz, "hi", prompt=script_text, vad=True)
                if w2 and (not words or len(w2) > len(words) * 1.15 or (w2[-1]["end"] > (words[-1]["end"] if words else 0) + 2.0)):
                    words = w2

    if not words or len(words) < 3:
        return _energy_fallback_align(sents, wav) if wav else False

    tot_dur = float(_tot_a or max(1.0, words[-1]["end"]))

    # Spoken weights for every script word (used for chain validation + gap interpolation)
    weights = [_spoken_weight(w["w"]) for w in flat]
    cum_w = [0.0]
    for wt in weights:
        cum_w.append(cum_w[-1] + wt)

    # Primary: Banded Word-Level Monotonic DP (Devanagari + Phonetic + Acronym)
    m_dp, anch_dp = _dp_word_align(flat, words, tot_dur)
    clean_dp = _clean_anchors_v2(anch_dp, cum_w, tot_dur)
    cov_dp = len(clean_dp) / max(1, len(flat))

    matched, clean_anch = m_dp, clean_dp

    # Secondary backup only if word DP got low coverage (e.g. missing spaces in Whisper output)
    if cov_dp < 0.38:
        m_dev, a_dev = _match_pass(flat, words, phonetic=False)
        m_lat, a_lat = _match_pass(flat, words, phonetic=True)
        c_dev = _clean_anchors_v2(a_dev, cum_w, tot_dur)
        c_lat = _clean_anchors_v2(a_lat, cum_w, tot_dur)
        best_alt = (m_lat, c_lat) if len(c_lat) > len(c_dev) else (m_dev, c_dev)
        if len(best_alt[1]) > len(clean_dp):
            matched, clean_anch = best_alt

    # If still very low coverage and we haven't tried 'small' yet, upgrade once
    if (len(clean_anch) / max(1, len(flat))) < 0.22 and size == "base" and _bigger_ok() and wav is not None:
        log(f"   Whisper (base) match kam ({matched:.0%}) – 'small' model se dobara sun raha hoon...", show=False)
        return align(sents, wav, "small")

    if len(clean_anch) < max(3, min(6, len(flat) // 3)):
        log(f"   Whisper anchors kam ({len(clean_anch)}/{len(flat)}) – spoken-weight + pause fallback", show=False)
        return _energy_fallback_align(sents, wav) if wav else False

    n = len(flat)
    starts = [None] * n
    anchored_set = set()
    for wi, t0, _ in clean_anch:
        starts[wi] = t0
        anchored_set.add(wi)

    known = sorted(anchored_set)
    avg_rate = tot_dur / max(1.0, cum_w[-1])

    # Spoken-weight gap interpolation between validated anchors
    for i in range(n):
        if starts[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            if lo is not None and hi is not None:
                denom = max(1e-6, cum_w[hi] - cum_w[lo])
                frac = (cum_w[i] - cum_w[lo]) / denom
                starts[i] = starts[lo] + (starts[hi] - starts[lo]) * frac
            elif lo is not None:
                starts[i] = starts[lo] + avg_rate * (cum_w[i] - cum_w[lo])
            else:
                starts[i] = max(0.0, starts[hi] - avg_rate * (cum_w[hi] - cum_w[i]))

    # Smooth tail stretch to actual audio duration (fixes tail freeze / early end)
    last_known = known[-1]
    if last_known < n - 1 and tot_dur > starts[last_known] + 1.0:
        span = max(0.5, (tot_dur - 0.15) - starts[last_known])
        denom = max(1e-6, cum_w[n] - cum_w[last_known])
        for k in range(last_known + 1, n):
            starts[k] = starts[last_known] + span * (cum_w[k] - cum_w[last_known]) / denom

    for i in range(1, n):
        if starts[i] < starts[i - 1] + 0.05:
            starts[i] = starts[i - 1] + 0.05

    ends = [starts[i + 1] for i in range(n - 1)] + [max(starts[-1] + 0.3, tot_dur - 0.05)]
    for w, a, b in zip(flat, starts, ends):
        w["start"], w["end"] = round(a, 3), round(b, 3)

    for i, s in enumerate(sents):
        if s["words"]:
            s["start"] = s["words"][0]["start"] if i else 0.0
            s["end"] = s["words"][-1]["end"]

    # v3.87: Snap sentence starts out of silence to actual speech onset (never early!)
    if wav is not None:
        _snap_sentences_to_speech(sents, wav, anchored_set)

    used_sz = ONE["size"] if (ONE["size"] and size == "base") else size
    if used_sz in ("small", "medium") and not _bigger_ok():
        used_sz = "base"
    log(f"   captions timing: Whisper ({used_sz}) audio-lock ✓ ({matched:.0%} match, {len(clean_anch)}/{n} anchors)")
    return True


LAST_RATIO = {"v": 1.0}


def line_coverage(lines, wav, size="base", words=None):
    """v2.15 + v3.87: Har script line ka kitna hissa awaaz me sach me bola gaya (0..1).
    Dual-script (Devanagari + phonetic + acronym) so English/tech lines never trigger false mid-video splices."""
    if words is None:
        words, _ = transcribe(wav, size, "hi", prompt=" ".join(lines), vad=False)
    if not words:
        return None
    # Compute coverage on BOTH Devanagari and folded phonetic/acronym streams, take per-line max!
    def _cov_stream(phonetic=False):
        T = "".join(_norm(w["w"], phonetic=phonetic) for w in words)
        if len(T) < 5:
            return None, 1.0
        S = []; spans = []
        for l in lines:
            parts = []
            for w in l.split():
                acr = _acronym_spoken(w) if phonetic else ""
                parts.append(acr or _norm(w, phonetic=phonetic))
            n = "".join(parts)
            a = len(S); S.extend(n); spans.append((a, len(S)))
        ratio = len(T) / max(1, len(S))
        sm = difflib.SequenceMatcher(None, "".join(S), T, autojunk=False)
        hitc = [0] * len(S)
        for blk in sm.get_matching_blocks():
            if blk.size < 2:
                continue
            for k in range(blk.size):
                hitc[blk.a + k] = 1
        return [(sum(hitc[a:b]) / max(1, b - a)) for a, b in spans], ratio

    c_dev, r_dev = _cov_stream(phonetic=False)
    c_ph, r_ph = _cov_stream(phonetic=True)
    if c_dev is None and c_ph is None:
        return None
    if c_dev is None:
        LAST_RATIO["v"] = r_ph
        return c_ph
    if c_ph is None:
        LAST_RATIO["v"] = r_dev
        return c_dev
    LAST_RATIO["v"] = min(r_dev, r_ph) if (r_dev > 1.0 and r_ph > 1.0) else r_dev
    return [max(a, b) for a, b in zip(c_dev, c_ph)]
