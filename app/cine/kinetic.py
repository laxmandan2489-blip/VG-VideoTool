"""KINETIC TYPOGRAPHY (reference reel jaisa) – ASS events, final video me libass se (tez, saaf, Hindi bhi theek).

Animations:
  typewriter : akshar ek-ek karke (PRITES -> PRITESH)
  blur       : dhundhla -> saaf (LEATHER MATERIAL)
  track      : akshar door se paas aate hain (headline / hook)
  count      : number 0 se badhta hai (30-35%)
  name       : upar accent bold naam + neeche safed serif (PRITESH / Mistry)
Har text ke peeche halka glow + soft shadow (mota kaala outline nahi).
"""
import re

from .bible import ass_col

NUM_RE = re.compile(r"(-?\d[\d,]*\.?\d*)")
STAMP = {"BANNED", "ILLEGAL", "REJECT", "INVALID", "FAKE", "ARRESTED", "RESIGNED", "CANCELLED", "GUILTY",
         "DANGER", "SCAM", "ALERT", "SHOCKING", "WARNING", "CRISIS"}


def _esc(t):
    return str(t).replace("{", "(").replace("}", ")").replace("\\", "/")


def _ms(x):
    return int(round(x * 1000))


def _font_for(text, b, kind):
    if re.search(r"[\u0900-\u097F]", text): return b["fonts"]["hindi"]
    return b["fonts"]["head"] if kind in ("word", "number") else b["fonts"]["bold"]


def _base(x, y, size, font, col, extra=""):
    return (f"{{\\an5\\pos({x},{y})\\fn{font}\\fs{size}\\c{col}\\bord1.5\\3c&H101010&\\shad4\\4c&H000000&\\4a&H70&"
            f"\\fsp2{extra}}}")


def _glow(x, y, size, font, col, a0=0, delay=0):
    """Peeche ka halka glow. delay (ms): typewriter me glow tab aaye jab akshar aa chuke hon (bhoot-shabd nahi)."""
    return (f"{{\\an5\\pos({x},{y})\\fn{font}\\fs{size}\\c{col}\\3c{col}\\bord6\\blur14\\shad0\\alpha&HFF&\\fsp2"
            f"\\t({delay},{delay + max(120, a0)},\\alpha&HA0&)\\fad(0,200)}}")


def _fit(kind, text, W):
    """Reference jaisa BADA keyword: chaudai ka ~75-80%, lekin had me."""
    n = max(1, len(text))
    if kind == "name":
        return int(min(W * 0.15, W * 0.82 / (0.66 * n)))
    return int(min(W * 0.30, W * 0.80 / (0.43 * n)))


def events(scenes, sents, total, W, H, b, ass_time, style=None, busy=()):
    """scenes: storyboard list, sents: voice sentences (start/end/words). busy: [(t0,t1)] jahan pehle se graphic hai."""
    style = style or {}
    acc = ass_col(b["palette"]["accent"]); wht = "&H00FFFFFF&"
    y_main = int(H * (0.21 if H > W else 0.24))  # v3.25: clear top margin above 16:9 / Polaroid frames
    size = int((W if H > W else H) * 0.17)
    out = []
    for sc in scenes:
        if not sc.get("kw") or sc.get("graphic") == "map": continue
        i = sc["i"]
        if i >= len(sents): continue
        st = sents[i]["start"] if i else 0.10
        nx = sents[i + 1]["start"] if i + 1 < len(sents) else total
        # v3.52 HINDI-AWARE WORD-EXACT SYNC: match Devanagari spoken words to English keywords via translit + prefix!
        t0 = st + 0.12
        kwl = (sc["kw"] + " " + str(sc.get("kw2") or "")).lower().strip()
        kw_toks = [t_ for t_ in re.findall(r"[a-z0-9]+", kwl) if len(t_) >= 3]
        from .storyboard import STRONG
        his = {h for h, e in STRONG.items() if e.lower() in kwl}
        try:
            import translit as _trl
            _to_lat = lambda s_: re.sub(r"[^a-z0-9]+", "", _trl.to_hinglish(s_).lower())
        except Exception:
            _to_lat = lambda s_: re.sub(r"[^a-z0-9]+", "", s_.lower())
        _matched_w = False
        for wd in sents[i].get("words") or []:
            raw = str(wd.get("w") or wd.get("word") or "")
            w_ = re.sub(r"[^\w%]", "", raw).lower()
            w_lat = _to_lat(raw)
            _hit = False
            if w_ and (w_ in kwl or (NUM_RE.search(kwl) and NUM_RE.search(w_)) or any(h in raw for h in his)):
                _hit = True
            elif w_lat and len(w_lat) >= 3:
                for kt in kw_toks:
                    # Match exact, substring, or first 4 phonetic consonants/letters (mariyana ~ mariana, maunt ~ mount)
                    if kt in w_lat or w_lat in kt or (len(kt) >= 4 and len(w_lat) >= 4 and kt[:4] == w_lat[:4]):
                        _hit = True; break
            if _hit:
                t0 = max(st, float(wd.get("start", st)) - 0.06); _matched_w = True; break
        # If keyword is a proper name/number at the end of line and wasn't matched, don't fire at 0.12s — wait 35% into line
        if not _matched_w and (sc.get("anim") == "name" or NUM_RE.search(kwl)):
            t0 = min(nx - 0.9, st + max(0.35, (nx - st) * 0.35))
        t1 = min(nx + 0.05, t0 + 2.3, total - 0.05)
        if t1 - t0 < 0.7: continue
        if any(a - 0.2 < t0 < bb for a, bb in busy): continue
        kw = _esc(sc["kw"]); kind = sc.get("kind", "word"); anim = sc.get("anim", "blur")
        font = _font_for(kw, b, kind)
        sz = _fit("name" if anim == "name" else "word", kw, W if H > W else int(W * 0.6))
        d = _ms(t1 - t0)
        exitt = f"\\t({max(0, d - 220)},{d},\\blur8\\alpha&HFF&)"
        A, B = ass_time(t0), ass_time(t1)
        x = W // 2
        is_year = bool(re.fullmatch(r"(1[5-9]\d\d|20\d\d)", kw.strip()))
        if is_year:
            anim = "year"                               # v3.1: saal (1975) count-up nahi – bada, shadow ke saath (reference)
        if kw.strip().upper() in STAMP:                 # v3.1: INVALID / BANNED jaisa laal THAPPA (stamp)
            sz2 = int(sz * 0.62); rd = "&H2A2ADD&"
            st_ = (f"{{\\an5\\pos({x},{y_main})\\fn{b['fonts']['impact']}\\fs{sz2}\\c{rd}\\3c{rd}\\bord5\\shad0"
                   f"\\frz-12\\fscx165\\fscy165\\alpha&HFF&\\t(0,140,\\fscx100\\fscy100\\alpha&H10&){exitt}}}")
            out.append(f"Dialogue: 8,{A},{B},Cap,,0,0,0,," + st_ + kw.upper())
            continue
        if anim == "year":
            yfx = (f"\\alpha&HFF&\\fscx118\\fscy118\\blur10\\t(0,300,\\alpha&H00&\\fscx100\\fscy100\\blur0)"
                   f"\\shad8\\4a&H40&{exitt}")
            out.append(f"Dialogue: 7,{A},{B},Cap,,0,0,0,," + _base(x, int(H * 0.36), int(sz * 1.1), b["fonts"]["head"], wht, yfx) + kw)
            continue
        if anim == "count" and NUM_RE.search(kw) and not re.search(r"[\u0900-\u097F]", kw):
            steps = 12; dur_c = 0.6
            for k in range(steps):
                p = (k + 1) / steps
                def rep(mo, p=p):
                    s = mo.group(1); v = float(s.replace(",", "")); dec = len(s.split(".")[1]) if "." in s else 0
                    return f"{v * p:.{dec}f}"
                txt = NUM_RE.sub(rep, kw)
                a = t0 + dur_c * k / steps; bb = t0 + dur_c * (k + 1) / steps
                sc_ = 80 + 20 * p
                out.append(f"Dialogue: 7,{ass_time(a)},{ass_time(bb)},Cap,,0,0,0,," +
                           _base(x, y_main, sz, font, acc, f"\\fscx{sc_:.0f}\\fscy{sc_:.0f}") + txt)
            ta = t0 + dur_c
            out.append(f"Dialogue: 6,{ass_time(ta)},{B},Cap,,0,0,0,," + _glow(x, y_main, sz, font, acc) + kw)
            out.append(f"Dialogue: 7,{ass_time(ta)},{B},Cap,,0,0,0,," +
                       _base(x, y_main, sz, font, acc, f"\\t(0,120,\\fscx106\\fscy106)\\t(120,240,\\fscx100\\fscy100)"
                                                       f"\\t({max(0, _ms(t1 - ta) - 220)},{_ms(t1 - ta)},\\blur8\\alpha&HFF&)") + kw)
            continue
        if anim == "name":
            y1 = y_main - int(sz * 0.45); y2 = y_main + int(sz * 0.75)
            letters = "".join(f"{{\\alpha&HFF&\\t({k*45},{k*45+1},\\alpha&H00&)}}{c}" for k, c in enumerate(kw))
            out.append(f"Dialogue: 6,{A},{B},Cap,,0,0,0,," + _glow(x, y1, sz, b["fonts"]["bold"], acc, 300, 45 * len(kw)) + kw)
            out.append(f"Dialogue: 7,{A},{B},Cap,,0,0,0,," + _base(x, y1, sz, b["fonts"]["bold"], acc, exitt) + letters)
            if sc.get("kw2"):
                k2 = _esc(sc["kw2"]).title()
                dl = 45 * len(kw) + 120
                out.append(f"Dialogue: 7,{A},{B},Cap,,0,0,0,," +
                           _base(x, y2, int(sz * 1.05), b["fonts"]["serif"], wht,
                                 f"\\alpha&HFF&\\blur10\\t({dl},{dl+350},\\alpha&H00&\\blur0){exitt}") + k2)
            continue
        if anim == "typewriter" and not re.search(r"[\u0900-\u097F]", kw):
            step = max(35, min(70, int(420 / max(1, len(kw)))))
            letters = "".join(f"{{\\alpha&HFF&\\t({k*step},{k*step+1},\\alpha&H00&)}}{c}" for k, c in enumerate(kw))
            out.append(f"Dialogue: 6,{A},{B},Cap,,0,0,0,," + _glow(x, y_main, sz, font, acc, 250, step * len(kw)) + kw)
            out.append(f"Dialogue: 7,{A},{B},Cap,,0,0,0,," + _base(x, y_main, sz, font, acc, exitt) + letters)
            continue
        if anim == "spring":
            # restrained overshoot: 82% -> 108% -> 100%, plus 18px lift; no cartoon bounce
            fx_ = (f"\\alpha&HFF&\\fscx82\\fscy82\\move({x},{y_main+18},{x},{y_main},0,360)"
                   f"\\t(0,260,\\alpha&H00&\\fscx108\\fscy108)"
                   f"\\t(260,430,\\fscx100\\fscy100){exitt}")
        elif anim == "pop":
            fx_ = (f"\\alpha&HFF&\\fscx68\\fscy68\\t(0,220,\\alpha&H00&\\fscx112\\fscy112)"
                   f"\\t(220,360,\\fscx100\\fscy100){exitt}")
        elif anim == "glitch":
            # RGB split lasts only 90ms; main word remains legible and settles immediately.
            ghost_cyan = "&H00FFFF&"; ghost_red = "&H4040FF&"
            for dx, col, alpha in [(-7, ghost_cyan, "H40"), (7, ghost_red, "H50")]:
                ghost = (f"{{\\an5\\pos({x+dx},{y_main})\\fn{font}\\fs{sz}\\c{col}\\bord0\\shad0"
                         f"\\alpha&{alpha}&\\blur1\\fsp2\\t(0,90,\\alpha&HFF&)}}")
                out.append(f"Dialogue: 5,{A},{ass_time(min(t1,t0+0.10))},Cap,,0,0,0,,{ghost}{kw}")
            fx_ = f"\\alpha&HFF&\\blur3\\fscx103\\fscy100\\t(0,110,\\alpha&H00&\\blur0\\fscx100\\fscy100){exitt}"
        elif anim == "track":
            fx_ = f"\\fsp{int(sz*0.45)}\\alpha&HFF&\\t(0,180,\\alpha&H00&)\\t(0,520,0.6,\\fsp2){exitt}"
        else:   # blur: premium soft focus -> crisp
            fx_ = f"\\alpha&HFF&\\blur16\\fscx112\\fscy112\\t(0,380,\\alpha&H00&\\blur0\\fscx100\\fscy100){exitt}"
        out.append(f"Dialogue: 6,{A},{B},Cap,,0,0,0,," + _glow(x, y_main, sz, font, acc, 380) + kw)
        out.append(f"Dialogue: 7,{A},{B},Cap,,0,0,0,," + _base(x, y_main, sz, font, acc, fx_) + kw)
    return out
