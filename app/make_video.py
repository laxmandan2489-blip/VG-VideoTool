"""VG Fact Video Tool – ek command me poori video.

   script.txt  ->  awaaz  ->  visuals  ->  edit  ->  output/xxx.mp4
"""
import sys, os, re, time, shutil, datetime, random, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
import edit_style
from common import (log, fail, read_style, yes, num, find_script, read_keys, check_ffmpeg, no_console_freeze, KEY_SOURCE,
                    run, duration, safe_name, TOOL, OUT, WORK, LOG_FILE, ASSETS)


STAGES = []            # v3.6: (naam, shuru time) – kis kaam me kitna samay laga
_log0 = log


def log(msg, show=True):
    m_ = re.match(r"^(\d)\) ", msg or "")
    if m_:
        STAGES.append(({"1": "script", "2": "awaaz + Whisper", "3": "footage khoj + jaanch", "4": "editing (shots)",
                        "5": "captions + sound", "6": "final video", "7": "thumbnail/title", "8": "Gemini review"}
                       .get(m_.group(1), msg[:20]), time.time()))
    _log0(msg, show)


def _jsafe(o):
    """v3.10 FIX: numpy number (float32) JSON me – pehle isi se video banne ke BAAD crash -> bot ne safe mode me
    poori video DOBARA banayi (15 Nov log)."""
    try:
        return o.item()
    except Exception:
        return str(o)


def stage_report(end=None):
    end = end or time.time()
    agg = {}
    for k, (nm, t0) in enumerate(STAGES):
        t1 = STAGES[k + 1][1] if k + 1 < len(STAGES) else end
        agg[nm] = agg.get(nm, 0) + (t1 - t0)
    tot = sum(agg.values())
    return tot, sorted(agg.items(), key=lambda x: -x[1])


SECTIONS = []          # v2.11: [(line_index, "section ka naam")]  – "## naam" wali lines se
FORMAT = {"v": None}   # "lambi" / "short" – script ki pehli line LONG / SHORT se
MARKS = {}             # v2.14: line -> ["boom", ...]  (script me [boom])
FX = {}                # v2.15: line -> [("map", "Chamoli"), ("label", "1:14 PM"), ...]  (fx.py)


USER_HINT = {}   # v3.18: line -> aapka (English) hint
CONTENT_MODE = {"v": None}  # v3.66: script me "MODE: history" (auto / news / influencer / history / science ...)
USER_AI_HINT = {}  # v3.58: line -> explicit "|| AI: ..." cinematic AI scene prompt

# v3.18: '/' ya '//' ke baad = visual hint ("लाइन / Voyager 1 spacecraft"). Hint NAHI maana jaata jab slash:
# URL ka hissa ho (https://), do number ke beech ho (24/7, 1/2), ya do Hindi shabdon me chipka ho (और/या).
_DEV = re.compile(r"[\u0900-\u097F]")


def split_slash_hint(s):
    i = 0
    while True:
        i = s.find("/", i)
        if i < 0: return s, ""
        j = i
        while j < len(s) and s[j] == "/": j += 1
        before = s[i - 1] if i > 0 else ""; after = s[j] if j < len(s) else ""
        n = j - i
        tok_a = s.rfind(" ", 0, i) + 1; tok_b = s.find(" ", j); tok = s[tok_a:(tok_b if tok_b >= 0 else len(s))]
        bad = (n > 2 or before == ":" or (before.isdigit() and after.isdigit())
               or bool(_DEV.match(before or " ") and _DEV.match(after or " "))
               or bool(re.search(r"https?:|www\.|\.(com|org|net|in|gov)\b", tok, re.I)))
        if not bad and s[:i].strip() and s[j:].strip():
            return s[:i].strip(), s[j:].strip()
        i = j


def part_cut_time(sent, eng_line, st, en):
    """v3.18 FIX ("awaaz pehle, visual baad me"): lambi line ke 2 visual pehle aadhe-aadhe TIME pe badalte the. Ab
    doosra visual us SHABD pe aata hai jahan line ka doosra hissa shuru hota hai (comma / 'और' / 'लेकिन' / 'जो',
    warna English hisse ke anupaat se). Dono shot kam se kam 1 sec. Return time ya None."""
    ws = sent.get("words") or []
    if len(ws) < 6 or not all(isinstance(w.get("start"), (int, float)) for w in ws): return None
    n = len(ws); idx = None; best_sc = 0.0
    lo, hi = int(n * 0.25), int(n * 0.75)
    for k_ in range(max(1, lo), min(n - 1, hi) + 1):
        prev = str(ws[k_ - 1].get("w", "")); cur = str(ws[k_].get("w", "")).strip(",.।")
        punct = prev.endswith((",", "।", ";"))
        if punct or cur in ("और", "लेकिन", "पर", "जो", "जिसे", "जिसके", "क्योंकि", "फिर", "तो"):
            sc_ = abs(k_ - n / 2) - (n * 0.25 if punct else 0)        # comma wali jagah sabse pehle
            if idx is None or sc_ < best_sc: idx, best_sc = k_, sc_
    if idx is None:
        try:
            import visual_pick as _vp
            prt = _vp.split_parts(eng_line, 2)
            if len(prt) == 2:
                idx = int(round(n * len(prt[0].split()) / max(1, len(prt[0].split()) + len(prt[1].split()))))
        except Exception:
            idx = None
    if not idx or not (0 < idx < n): return None
    t = float(ws[idx]["start"])
    return t if (t - st >= 1.0 and en - t >= 1.0) else None


def read_script(path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    title = None; topic_kw = []; lines = []; hints = []
    SECTIONS.clear(); FORMAT["v"] = None; MARKS.clear(); FX.clear(); CONTENT_MODE["v"] = None
    import fx
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("##"):
            name = s.lstrip("#").strip()
            if name: SECTIONS.append((len(lines), name))
            continue
        if s.startswith("#"):
            continue
        up = s.upper()
        if not lines and up.strip(" .:!") in ("LONG", "LAMBI", "LONG VIDEO", "LAMBI VIDEO", "FORMAT: LONG", "FORMAT: LAMBI"):
            FORMAT["v"] = "lambi"; continue
        if not lines and up.strip(" .:!") in ("SHORT", "SHORTS", "FORMAT: SHORT"):
            FORMAT["v"] = "short"; continue
        if up.startswith("TITLE:"):
            title = [x.strip() for x in s.split(":", 1)[1].split("|") if x.strip()]; continue
        if up.startswith(("MODE:", "CATEGORY:", "CONTENT MODE:")):     # v3.66: content mode (bola nahi jaata)
            CONTENT_MODE["v"] = s.split(":", 1)[1].strip().lower() or None; continue
        if up.startswith("KEYWORDS:"):
            topic_kw = [x.strip().lower() for x in s.split(":", 1)[1].split(",") if x.strip()]; continue
        if up.startswith(("HOOK TEXT", "FACT CHECK", "SCRIPT:")) or re.match(r"^\d+\.\s", s) and len(lines) > 3 and not re.search(r"[ऀ-ॿ]{3}", s):
            if up.startswith(("HOOK TEXT", "FACT CHECK")):
                break
            continue
        hint = ""
        if "||" in s:
            s, hint = [x.strip() for x in s.split("||", 1)]
        else:
            # v3.18: user slash se bhi batata hai ki line pe kya dikhe:  "लाइन / Voyager 1 spacecraft"  ya  "लाइन // ..."
            # (https:// wala slash, 24/7 jaise number aur ‘और/या’ jaise Hindi shabd hint nahi maane jaate)
            s, hint = split_slash_hint(s)
        s, fxl, marks = fx.parse_tags(s)                          # v2.15: [map: ..] [label: ..] + [boom] sound
        if hint:
            hint, fx2, m2 = fx.parse_tags(hint); fxl += fx2; marks += m2
        if s:
            if marks: MARKS[len(lines)] = [m.lower() for m in marks]
            if fxl: FX[len(lines)] = fxl
            # v3.62 UNIVERSAL MICRO-BEAT SPLIT: long multi-clause sentence (15+ words, no manual hint) -> split at Hindi contrast conjunctions
        # so EVERY clause/emotion ("paise ki kami nahi" vs "prakriti ki taakat", "sookhe mausam" vs "baarish me") gets its OWN exact visual!
        if not hint and len(s.split()) >= 15 and not fxl and not marks:
            _parts = re.split(r"(?:,\s*|\s+(?=(?:लेकिन|बल्कि|मगर|परंतु|जबकि)\b))", s, maxsplit=1)
            _parts = [p_.strip(" ,।") for p_ in _parts if p_.strip(" ,।")]
            if len(_parts) == 2 and len(_parts[0].split()) >= 5 and len(_parts[1].split()) >= 5:
                lines.append(_parts[0] + "।"); hints.append("")
                lines.append(_parts[1]); hints.append("")
                continue
        lines.append(s); hints.append(hint)
    return lines, hints, title, topic_kw


def gemini_wait(fn, style, what):
    """v2.15b: Gemini busy -> sirf `gemini_try` (2) baar aur, 30-40 sec ruk ke. Phir bina Gemini aage (jaldi video)."""
    import ai
    rounds = int(num(style, "gemini_try", 0, 3)) if style.get("gemini_try") not in (None, "") else 2
    for k in range(1, rounds + 1):
        wait = random.uniform(30, 40)
        log(f"   ⏳ Gemini busy hai ({what}), {wait:.0f} sec baad dobara try ({k}/{rounds})")
        time.sleep(wait)
        r = fn()
        if r:
            log(f"   Gemini mil gaya ✓ ({what})")
            return r
        if not ai.BUSY["flag"] and what != "awaaz":
            break                                   # busy nahi, koi aur galti – intezaar bekaar
    return None


def section_voice(lines, style, work, key):
    """Lambi video: har section ki awaaz alag banao (5 min tak ek jaisi rahe), phir jodo."""
    import numpy as np, voice
    starts = [i for i, _ in SECTIONS if i < len(lines)]
    if not starts or starts[0] != 0: starts = [0] + starts
    bounds = list(zip(starts, starts[1:] + [len(lines)]))
    pieces = []; sents = []; t = 0.0
    gap = np.zeros(int(0.45 * voice.SR), dtype=np.float32)
    for k, (a, b) in enumerate(bounds):
        if b <= a: continue
        sub = work / f"sec_{k}"; sub.mkdir(exist_ok=True)
        log(f"   awaaz: section {k+1}/{len(bounds)}")
        r = voice.gemini_voice(lines[a:b], style, sub, key)
        if not r:
            log("   section awaaz nahi bani – poori ek saath try karunga", show=False); return None
        x = voice.edge_fade(voice.load_wav(r[0]))
        for s in r[1]:
            s = dict(s); s["start"] += t; s["end"] += t
            s["words"] = [dict(w, start=w["start"] + t, end=w["end"] + t) for w in s["words"]]
            sents.append(s)
        pieces += [x, gap]; t += (len(x) + len(gap)) / voice.SR
    if len(sents) != len(lines):
        log(f"   section awaaz lines match nahi ({len(sents)} vs {len(lines)})", show=False)
    wav = work / "voice.wav"; voice.save_wav(wav, np.concatenate(pieces))
    return wav, sents


def build_fx(sents, events, eng, total, W, H, style, work, joined, gkey, ink_times, pro):
    """v2.15: label / bubble / list / gola / ink ki ASS lines. events (number) jo inse takraate hain hata deta hai."""
    if not pro:
        return []
    import fx, render
    font = work / "fonts" / "VTBaloo.ttf"
    if not font.exists(): font = render.FONT
    at = render.ass_time
    out = []; busy = []; golas = []
    auto = yes(style.get("auto_patti", "nahi"))       # v2.17: laal patti sirf [label: ..] likhne pe (apne-aap nahi)
    for i, s in enumerate(sents):
        st = s["start"] if i else 0.15
        nx = sents[i + 1]["start"] if i + 1 < len(sents) else total
        t0 = st + 0.15; t1 = max(t0 + 1.2, min(nx + 0.2, t0 + 3.4, total))
        items = list(FX.get(i, []))
        if auto and not any(n_ in ("label", "map", "news") for n_, _ in items):
            lb = fx.auto_label(s.get("script") or s["text"])
            if lb: items.append(("label", lb))
        for name, val in items:
            try:
                if name == "label" and val:
                    out += fx.label_events(val, t0, t1, W, H, font, at); busy.append((t0, t1))
                elif name == "bubble" and val:
                    out += fx.bubble_events(val, t0, t1, W, H, font, at); busy.append((t0, t1))
                elif name == "list" and val:
                    out += fx.list_events(re.split(r"[,،;]", val), t0, max(t1, nx), W, H, at); busy.append((t0, t1))
                elif name == "gola":
                    golas.append((t0 + 0.1, min(t1, t0 + 2.6), val or (eng[i] if i < len(eng) else "")))
            except Exception as e:
                log(f"   (line {i+1} ka {name} effect skip: {e})", show=False)
    for e in events:                                  # purane arrow/circle -> naya gola
        if e["kind"] in ("arrow", "circle") and not any(abs(e["t0"] - g[0]) < 1.5 for g in golas):
            si = max([k for k, s in enumerate(sents) if s["start"] <= e["t0"]] or [0])
            golas.append((e["t0"], min(total, e["t0"] + 1.8), eng[si] if si < len(eng) else ""))
    if golas:
        frames = [fx.frame_at(joined, (a + b) / 2, work, k) for k, (a, b, _) in enumerate(golas)]
        ok = [(k, f) for k, f in enumerate(frames) if f]
        pts = fx.locate([f for _, f in ok], [golas[k][2] for k, _ in ok], gkey) if gkey and ok else []
        where = {k: p for (k, _), p in zip(ok, pts)}
        for k, (a, b, subj) in enumerate(golas):
            p = where.get(k)
            cx, cy = (int(p[0] * W), int(p[1] * H)) if p else (W // 2, int(H * (0.45 if H > W else 0.5)))
            out += fx.gola_events(a, b, cx, cy, W, H, at); busy.append((a, b))
        log(f"   gola: {len(golas)} ({sum(1 for k in range(len(golas)) if where.get(k))} pe Gemini ne jagah dhoondhi)", show=False)
    # v2.17: ink (laal dhuan) band
    if busy:                                          # bada number text label/gola ke upar na aaye
        events[:] = [e for e in events if e["kind"] != "number"
                     or not any(a - 0.8 < e["t0"] < b + 0.2 for a, b in busy)]
    if out:
        log(f"   pro effects: {len(busy)} graphics, {len(ink_times)} ink transitions ✓")
    return out


def main():
    t0 = time.time()
    no_console_freeze()
    LOG_FILE.write_text(f"=== {datetime.datetime.now()} ===\n", encoding="utf-8")
    print("\n" + "=" * 56)
    print("   VG FACT VIDEO TOOL  –  video ban rahi hai, ruko...")
    print("=" * 56 + "\n")
    check_ffmpeg()

    style = read_style(TOOL / "style.txt")
    BOT = bool(os.environ.get("VG_BOT"))
    import json
    if os.environ.get("VG_STYLE_JSON"):                      # v2.8: bot se aayi setting (voice=meri waghera)
        try: style.update(json.loads(os.environ["VG_STYLE_JSON"]))
        except Exception: pass
    if os.environ.get("VG_SAFE"):                 # v2.14: pichhli koshish fail – sabse seedha, pakka tareeka
        # v3.13 FIX (Bug A): SAFE MODE sirf Gemini footage-check band karta hai – offline CLIP (ai_aankh) aur
        # download ke baad wali clip_jaanch CHALU rehti hai (pehle CHECK off -> AANKH bhi off ho jaata tha)
        style.update({"footage_check": "nahi", "ai_aankh": "haan", "clip_jaanch": "haan",
                      "layer": "nahi", "check_bot": "nahi", "photo_3d": "nahi",
                      "beat_cut": "nahi", "punch_shuru": "nahi", "loop_ending": "nahi", "stabilize": "nahi",
                      "pro_effects": "nahi", "awaaz_check": "nahi"})
        log("   SAFE MODE: seedhe tareeke se bana raha hoon")
    PREV = None
    if os.environ.get("VG_PREV") and Path(os.environ["VG_PREV"]).exists():   # v2.8: sudhaar (feedback)
        PREV = json.loads(Path(os.environ["VG_PREV"]).read_text(encoding="utf-8"))
        style.update(PREV.get("style_over") or {})
    if BOT:                                   # phone se chal raha hai: laptop pe kuch mat kholo
        style["youtube_kholo"] = "nahi"; style["script_pehle_dikhao"] = "nahi"
    keys = read_keys()
    try:                                          # v3.12: Gemini ki limit khatam -> Groq / OpenRouter backup
        import ai as _ai_b
        _ai_b.BACKUP["keys"] = {k_: keys[k_] for k_ in ("GROQ", "OPENROUTER") if keys.get(k_)}
    except Exception:
        pass
    try:                                          # v3.1: laptop ke hisaab se settings (RAM/VRAM/CPU)
        import hardware
        HW = hardware.load_profile()
        if not style.get("ek_saath_shots"):
            style["ek_saath_shots"] = str(HW.get("parallel_shots", 2))
        try:                                      # v3.6 TEZ: Whisper ek hi baar, 'small' (Hindi pe 'base' fail hota tha)
            import align as _al
            _w1 = style.get("whisper_ek_model") or ("small" if (HW.get("ram_gb") or hardware.ram_gb() or 0) >= 6 else "base")
            if yes(style.get("whisper_ek_baar", "haan")): _al.ONE["size"] = _w1
        except Exception:
            pass
        log(f"   🏷 VideoTool version: {(Path(__file__).parent / 'VERSION').read_text(encoding='utf-8').strip()}  "
            f"(folder: {Path(__file__).resolve().parent.parent})")
        log(f"   💻 hardware profile: {HW.get('parallel_shots')} shots ek saath, Blender {HW.get('blender_engine')} "
            f"x{HW.get('blender_scale')}, FreeVideo local: {'haan' if HW.get('freevideo_ok') else 'nahi'}", show=False)
    except Exception as e:
        HW = {}; log(f"   (hardware profile skip: {e})", show=False)
    sp = Path(os.environ["VG_SCRIPT"]) if os.environ.get("VG_SCRIPT") else find_script()   # v2.8: Telegram bot
    if not sp:
        fail("script.txt kahin nahi mili (tool folder / Documents / Downloads / Desktop). Script Notepad me 'script.txt' naam se save karo.")
    log(f"1) Script: {sp}")
    # v2.6: script.txt me "TOPIC: ..." ho to Gemini poori script likhega
    import writer
    script_data = None
    topic = writer.read_topic(sp)
    if topic:
        script_data = writer.write_script(topic, keys.get("GEMINI"), sp)
        if not script_data:
            fail("Script nahi ban payi. Gemini key check karo ya thodi der baad chalao.")
        if yes(style.get("script_pehle_dikhao", "nahi")):
            log("\n   Script script.txt me likh di hai. Padh lo, kuch badalna ho to badlo, phir 2_VIDEO_BANAO dobara chalao.")
            if os.name == "nt":
                try: os.startfile(sp)
                except Exception: pass
            return
    lines, hints, title, topic_kw = read_script(sp)
    if not lines:
        fail("script.txt khaali hai.")
    if FORMAT["v"]:
        style["format"] = FORMAT["v"]
    LEARN = {}; LEARN_NOTE = ""
    if yes(style.get("seekha_style", "haan")):          # v2.16: bot ne reels se jo seekha – uska mel
        try:
            import seekho
            LEARN, LEARN_NOTE = seekho.learned_style(style.get("format", "short"))
            mine = set(json.loads(os.environ.get("VG_STYLE_JSON") or "{}")) | set((PREV or {}).get("style_over") or {})
            LEARN = {k: v for k, v in LEARN.items() if k not in mine}
            if LEARN:
                style.update(LEARN)
                log(f"   🧠 seekhi hui editing laga raha hoon ({LEARN_NOTE}): " +
                    ", ".join(f"{k}={v}" for k, v in list(LEARN.items())[:8]))
        except Exception as e:
            log(f"   (seekha style skip: {e})", show=False)
    try:
        import ai as _ai
        _ai.MAX_TRY["n"] = int(num(style, "gemini_try", 0, 3)) + 1 if style.get("gemini_try") not in (None, "") else 3
    except Exception:
        pass
    LONG = style.get("format") == "lambi"
    if LONG:
        # v3.56 Dedicated LONG News + Fact Documentary Mode (Dhruv Rathee / Nitish Rajput style; Shorts untouched)
        for k, v in {"visual_badle_har": style.get("lambi_clip_har", "5"), "line_max_clips": "2",
                     "flash_har_clip": "nahi", "caption_size": style.get("lambi_caption_size", "46"),
                     "caption_jagah": "neeche", "caption_shabd": "5", "effect_har": "0", "shake": "nahi",
                     "documentary_mode": "haan"}.items():
            style[k] = v
        # Auto-create clean chapter sections for long scripts (12+ lines) if user didn't add ## headings
        if not SECTIONS and len(lines) >= 12:
            _step = max(6, len(lines) // min(5, max(2, len(lines) // 6)))
            SECTIONS.append((0, "शुरुआत"))
            _pnum = 2
            for _si in range(_step, len(lines) - 2, _step):
                SECTIONS.append((_si, f"भाग {_pnum}"))
                _pnum += 1
        log(f"   LAMBI NEWS+FACT DOCUMENTARY mode ✓  (16:9, {len(SECTIONS)} chapters, calm 5s pacing)")
    FB = None
    if PREV and os.environ.get("VG_FEEDBACK"):
        import feedback
        FB = feedback.parse(keys.get("GEMINI"), lines, os.environ["VG_FEEDBACK"])
        style.update(FB["style"])
        if FB["text_fixes"]:
            raw = sp.read_text(encoding="utf-8").splitlines(); k = -1; outl = []
            body = [l for l in raw]
            # script me sirf asli lines badlo (comment / TITLE chhod ke)
            for l in body:
                st_ = l.strip()
                if st_ and not st_.startswith("#") and not st_.upper().startswith(("TITLE:", "KEYWORDS:")):
                    k += 1
                    if k in FB["text_fixes"]:
                        hint = l.split("||", 1)[1] if "||" in l else ""
                        l = FB["text_fixes"][k] + (f" ||{hint}" if hint else "")
                outl.append(l)
            sp.write_text("\n".join(outl) + "\n", encoding="utf-8")
            lines, hints, title, topic_kw = read_script(sp)
        log(f"   SUDHAAR: {FB['note']}")
        log(f"   footage badlegi: {'sab lines' if FB['all_footage'] else ', '.join(str(i+1) for i in FB['bad_lines']) or '-'}"
            f" | setting: {FB['style'] or '-'} | shabd: {len(FB['text_fixes'])} line")
    log(f"   {len(lines)} lines mili.")
    if KEY_SOURCE: log(f"   keys file: {KEY_SOURCE[0]}")
    log(f"   Pixabay key: {'mili ✓' if keys.get('PIXABAY') else 'NAHI MILI ✗  (videos ghatiya aayengi!)'}")
    log(f"   Gemini key : {'mili ✓' if keys.get('GEMINI') else 'NAHI MILI ✗'}")
    if not keys.get("PIXABAY") or not keys.get("GEMINI"):
        log("   -> Documents\\api keys.txt me likho:  PIXABAY=...  aur  GEMINI=...  (har ek nayi line pe)")
        log("      (file ka naam 'api keys.txt' ho, aur wo Documents ya VideoTool folder me ho)")

    # v3.40 CHECKPOINT & RESUME: deterministic work folder per script so crashes resume from exact stage!
    import hashlib as _hl_res
    _s_sig = _hl_res.sha1(("|".join(lines) + ("|LONG" if LONG else "|SHORT")).encode("utf-8", errors="ignore")).hexdigest()[:12]
    if yes(style.get("resume_checkpoint", "haan")) and not PREV:
        work = WORK / f"resume_{_s_sig}"
    else:
        work = WORK / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    (work / "shots").mkdir(parents=True, exist_ok=True)
    (work / "fonts").mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    try:                                          # v2.15: font pehle hi (map/news card ke Hindi akshar ke liye)
        from common import ASSETS
        from common import copy_font
        copy_font(ASSETS / "fonts" / "VTBaloo.ttf", work / "fonts" / "VTBaloo.ttf")
    except Exception:
        pass

    # ---------------- 2) voice
    import voice, sources, render
    res = None
    FACE = os.environ.get("VG_FACE") if os.environ.get("VG_FACE") and yes(style.get("chehra", "haan")) else None
    cache = (PREV or {}).get("voice_cache") if PREV else None
    reuse = bool(cache and FB is not None and not FB["text_fixes"] and not (set(FB["style"]) & {"ai_speed", "awaaz_bhaari"})
                 and Path(cache.get("wav", "")).exists())
    _vcp = work / "voice_checkpoint.json"
    if not reuse and yes(style.get("resume_checkpoint", "haan")) and (work / "voice.wav").exists() and _vcp.exists():
        try:
            _saved_s = json.loads(_vcp.read_text(encoding="utf-8"))
            if isinstance(_saved_s, list) and len(_saved_s) == len(lines):
                log("2) ♻️ Resume Checkpoint: purani awaaz aur Whisper timing mil gayi ✓ (dobara nahi banegi)")
                wav = work / "voice.wav"; sents = _saved_s; res = (wav, sents); reuse = True
        except Exception:
            pass
    if reuse and not res:
        log("2) Pichhli awaaz hi use kar raha hoon (shabd nahi badle)...")
        shutil.copy(cache["wav"], work / "voice.wav"); wav = work / "voice.wav"
        sents = json.loads(Path(cache["sents"]).read_text(encoding="utf-8")); res = (wav, sents)
    elif FACE:
        log("2) Aapki video ki awaaz le raha hoon (chehra mode)...")
        res = voice.sync_voice(Path(FACE), lines, style, work)
    elif style.get("voice") == "meri":
        log("2) Aapki recording le raha hoon...")
        wav, sents = voice.my_voice(lines, style, work)
        res = (wav, sents)
    if res and not reuse and (FACE or style.get("voice") == "meri") and lines:
        # captions script ki sahi spelling me, lekin time aapki awaaz ka
        try:
            import align
            ss = [{"text": l, "script": l, "start": 0, "end": 0,
                   "words": [{"w": w, "start": 0, "end": 0} for w in voice.split_words(l)]} for l in lines]
            if align.align(ss, res[0], style.get("whisper_model_meri", "small")):
                res = (res[0], ss)
        except Exception as e:
            log(f"   (script spelling skip: {e})", show=False)
    elif style.get("voice") == "gemini":
        if keys.get("GEMINI"):
            log(f"2) Gemini ki natural awaaz bana raha hoon ({style.get('gemini_awaaz','charon')})...")
            res = None
            if LONG and len(SECTIONS) >= 2:
                res = section_voice(lines, style, work, keys["GEMINI"])
            if not res:
                res = voice.gemini_voice_checked(lines, style, work, keys["GEMINI"])   # v2.15: chhooti line pakdo
            if not res and voice.TTS_BUSY["flag"] and not voice.TTS_QUOTA["out"]:
                res = gemini_wait(lambda: (section_voice(lines, style, work, keys["GEMINI"]) if LONG and len(SECTIONS) >= 2
                                           else None) or voice.gemini_voice_checked(lines, style, work, keys["GEMINI"]),
                                  style, "awaaz")
            if not res and yes(style.get("awaaz_gate", "haan")) and not os.environ.get("VG_ALLOW_MS"):
                # v2.17c: awaaz chupchaap nahi badlegi – rukko aur poochho
                why = ("Aapki Gemini key ki AAJ ki awaaz limit khatam ho gayi hai." if voice.TTS_QUOTA["out"]
                       else "Gemini ki awaaz abhi nahi mil rahi (busy / internet).")
                log("   ⛔ " + why + " Video nahi bana raha (awaaz badalni nahi chahiye).")
                if os.environ.get("VG_RESULT"):
                    Path(os.environ["VG_RESULT"]).write_text(json.dumps({"gate": "awaaz", "why": why,
                                                                          "quota": voice.TTS_QUOTA["out"]}), encoding="utf-8")
                sys.exit(43)
            if not res:
                log("   Gemini awaaz nahi bani (limit/internet) – Microsoft awaaz use kar raha hoon.")
        else:
            log("2) GEMINI key nahi mili (api keys.txt) – Microsoft awaaz use kar raha hoon.")
    if res:
        wav, sents = res
    else:
        log(f"2) AI awaaz bana raha hoon ({style.get('ai_awaaz','madhur')})...")
        wav, sents = voice.ai_voice(lines, style, work)
    total = voice.load_wav(wav).shape[0] / voice.SR + 0.6
    log(f"   awaaz ready: {total:.1f} second")
    # v2.6: Gemini/apni awaaz me shabdon ka time andaze se hota hai -> Whisper se sahi karo
    if res and not reuse and not FACE and style.get("voice") != "meri" and yes(style.get("caption_timing_sahi", "haan")):
        try:
            import align
            align.align(sents, wav, style.get("whisper_model", "base"))
            if yes(style.get("resume_checkpoint", "haan")) and (work / "voice.wav").exists() and len(sents) == len(lines):
                (work / "voice_checkpoint.json").write_text(json.dumps(sents, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log(f"   (captions timing sudhaar skip: {e})", show=False)

    # ---------------- 3) visuals
    log("3) Har line ke liye visuals dhoond raha hoon...")
    W, H = render.size_for(style)
    cut = num(style, "visual_badle_har", 0.4, 6)
    # translate all lines (for search)
    if os.environ.get("VG_NO_GEMINI_WAIT"):
        sources.CHECK["on"] = False
    gq = sources.gemini_queries([s.get("script") or s["text"] for s in sents], keys.get("GEMINI"))
    import ai
    GEM_NOTE = ""
    if keys.get("GEMINI") and not gq and ai.BUSY["flag"] and not os.environ.get("VG_NO_GEMINI_WAIT"):
        gq = gemini_wait(lambda: sources.gemini_queries([s.get("script") or s["text"] for s in sents],
                                                       keys.get("GEMINI")), style, "footage")
        if not gq:
            sources.CHECK["on"] = False
            GEM_NOTE = ("⚠️ Gemini kaafi der tak nahi mila, isliye footage bina Gemini check ke lagi hai. "
                        "Sahi karwani ho to bas likho: footage sahi karo")
            log("   " + GEM_NOTE)
    if gq: log("   Gemini ne har line ke liye search shabd chune ✓")
    eng = []
    sources.WHO_ON["on"] = yes(style.get("asli_photos", "haan"))
    for i, s in enumerate(sents):
        txt = s.get("script") or s["text"]
        h = hints[i] if i < len(hints) and hints[i] else ""
        urls = re.findall(r"https?://\S+", h)                 # v2.10: script me link
        if urls:
            import footageflow_engine
            sources.LINKS[i] = urls
            sources.LINK_POLICIES[i] = footageflow_engine.parse_link_hint(h)
            h = re.sub(r"https?://\S+", "", h).strip(" ,|")
        if h and re.match(r"^\s*(follow|subscribe|cta|follow karo|like|share|end)\s*[.!]?\s*$", h, re.I):
            h = ""                                               # v3.18: '|| follow' = CTA line, search shabd nahi
        if h and re.search(r"[\u0900-\u097F]", h):          # v3.18: Hindi me likha hint -> English (search ke liye)
            try:
                h = sources.translate(h) or h
            except Exception:
                pass
        if h and re.match(r"^\s*ai\s*:\s*", h, re.I):
            _aip = re.sub(r"^\s*ai\s*:\s*", "", h, flags=re.I).strip()
            if _aip:
                USER_AI_HINT[i] = _aip
                h = _aip
        if h: USER_HINT[i] = h                                       # v3.18: aapka hint = is line ka sabse pakka nirdesh
        e = h or sources.SHOW.get(i) or sources.translate(txt)      # v2.17: Edit Director ka "kya dikhe"
        if h:                                                       # v3.1: hint ke English naam se caption spelling
            try:
                import translit
                for nm_ in re.findall(r"\b[A-Z][A-Za-z]{3,}(?:\s[A-Z][a-z]{2,})?\b", h):
                    translit.learn_name(txt, nm_)
            except Exception:
                pass
        eng.append(e)
        log(f"   line {i+1}: {e[:60]} | {gq[i] if gq and i < len(gq) else ''}", show=False)
    try:                                           # v3.1: mukhya insaan/brand (2+ lines me, ya Gemini 'who')
        from collections import Counter
        cw = Counter(v for v in sources.WHO.values() if v)
        for h_ in hints:                                           # hint me baar-baar aane wala naam (CarryMinati x8)
            for nm_ in re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b|\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b", h_ or ""):
                cw[nm_] += 1
        if cw:
            nm_, c_ = cw.most_common(1)[0]
            bio = sum(1 for x in sources.RAW_PLAN.values() if str((x or {}).get("domain", "")).lower() == "biography")
            if c_ >= 2 or bio >= max(2, len(sents) // 3):
                sources.MAIN.update(name=nm_, all_lines=bio >= len(sents) // 2 or c_ >= len(sents) // 2)
                log(f"   👤 video ka mukhya naam: {nm_} – baaki lines pe bhi isi ki clip/photo dhoondhunga", show=False)
        import yt_clips
        yt_clips.ON["on"] = yes(style.get("youtube_clips", "haan"))
        yt_clips.ON["max_per_video"] = int(num(style, "youtube_clips_max", 1, 40)) if style.get("youtube_clips_max") else 24
        yt_clips.ON["budget"] = float(num(style, "youtube_clips_time", 30, 900)) if style.get("youtube_clips_time") else (180.0 if yes(style.get("jaldi", "nahi")) else 420.0)
        yt_clips.reset()
    except Exception as e:
        log(f"   (main entity skip: {e})", show=False)
    if not topic_kw and sources.GTOPIC:
        topic_kw = list(sources.GTOPIC)                       # v2.10: Gemini ka topic ("brother" jaisa galat nahi)
    if not topic_kw:
        # topic = strongest words of the first two lines
        topic_kw = (sources.keywords(eng[0]) + (sources.keywords(eng[1]) if len(eng) > 1 else []))[:3]
    log(f"   topic: {', '.join(topic_kw) or '-'}")
    # v3.1: SCENE PLANNER – har line ka validate kiya hua scene (subject, camera, transition, sfx, avoid, template)
    SCENES = []
    try:
        import scene_plan
        SCENES = scene_plan.build([s_.get("script") or s_["text"] for s_ in sents], eng, sents, sources.RAW_PLAN,
                                  sources.WHO, work)
        for i_, sc_ in enumerate(SCENES):
            if sc_.get("avoid") and i_ not in sources.AVOID:
                sources.AVOID[i_] = tuple(sc_["avoid"][:3])
        log(f"   🎬 scene plan: {len(SCENES)} scenes ({'Gemini' if sources.RAW_PLAN else 'offline'}) – "
            + scene_plan.summary(SCENES)[:200], show=False)
    except Exception as e:
        log(f"   (scene plan skip: {e})", show=False)
    # v3.1: v3.0 CINE layer ab sach me juda hai (pehle sirf changelog me tha): Style Bible + Storyboard ->
    # reference-reel jaisa keyword typography (POISON / 30-35% / naam), auto 3D map, count-up, stamps
    SB = []; BIBLE = None
    if yes(style.get("cine", "haan")):
        try:
            from cine import bible as _bible, storyboard as _sb
            _lines = [s_.get("script") or s_["text"] for s_ in sents]
            BIBLE = _bible.build(_lines, eng, style, work)
            SB = _sb.build(_lines, eng, keys, style, who={i_: [n_] for i_, n_ in sources.WHO.items()}, fx_tags=FX,
                           use_llm=yes(style.get("storyboard_ai", "nahi")), work=work)
            _bible.copy_fonts(work / "fonts")
            log(f"   🎬 storyboard: {sum(1 for x in SB if x.get('kw'))} keyword, "
                f"{sum(1 for x in SB if x.get('graphic') == 'map')} map, theme {BIBLE['theme']}", show=False)
        except Exception as e:
            SB = []; log(f"   (storyboard skip: {e})", show=False)
    # v3.2: GLOBAL VISUAL IDENTITY LOCK – poori script samajh ke, koi visual dhoondhne se PEHLE
    LOCK = None
    SHOTS = []                                         # v3.8: har line ka shot list
    try:
        import identity_lock
        LOCK = identity_lock.build([s_.get("script") or s_["text"] for s_ in sents], eng, hints, sources.WHO,
                                   sources.GEMINI_RAW, SCENES, work)
        log("   🔒 identity lock: " + identity_lock.summary(LOCK))
        sources.LOCK_REF["v"] = LOCK
        if LOCK["main_subject"] and LOCK["main_type"] in ("person", "brand"):
            n_main = sum(1 for x in LOCK["scenes"] if x["uses_main"])
            sources.MAIN.update(name=LOCK["main_subject"], all_lines=n_main >= max(2, len(sents) // 2))
        forb = tuple(LOCK["forbidden_subjects"][:3])
        for i_, sc_ in enumerate(LOCK["scenes"]):
            sources.AVOID[i_] = tuple(dict.fromkeys(tuple(sources.AVOID.get(i_, ())) + forb))[:5]
            if sc_["uses_main"] and LOCK["main_type"] == "person":
                sources.NO_AI_PHOTO.add(i_)            # asli insaan ki nakli AI photo nahi (misleading)
        try:                                           # v3.8: har line ka shot list + doosre kirdaar (rivals)
            SHOTS[:] = identity_lock.shot_plan(LOCK, eng)
            for i_, sp_ in enumerate(SHOTS):
                if sp_["rivals"]:
                    sources.AVOID[i_] = tuple(dict.fromkeys(tuple(sp_["rivals"]) + tuple(sources.AVOID.get(i_, ()))))[:5]
            _rv = [f"{i_+1}:{sp_['subject'] or '-'} (na: {', '.join(sp_['rivals']) or '-'})" for i_, sp_ in enumerate(SHOTS)]
            log("   🎯 line ka subject: " + "; ".join(_rv[:6]) + (" ..." if len(_rv) > 6 else ""), show=False)
        except Exception as _se:
            log(f"   (shot list skip: {_se})", show=False)
        if SCENES:                                     # Blender sirf lock-allowed templates
            for i_, sc_ in enumerate(SCENES):
                if i_ < len(LOCK["scenes"]) and not identity_lock.allows_template(LOCK, sc_.get("blender_template"),
                                                                                  LOCK["scenes"][i_]):
                    sc_["blender_template"] = None
    except Exception as e:
        LOCK = None; log(f"   (identity lock skip: {e})", show=False)

    FILM = None                                        # v3.6: script ka topic koi film hai? -> uska official trailer
    if yes(style.get("film_trailer", "haan")):
        try:
            import entity as _ent
            from translit import word as _tw
            _names = list((LOCK or {}).get("secondary_subjects") or [])
            if title: _names.append(" ".join(_tw(x) for x in title[0].split()))
            if LOCK and LOCK.get("topic"): _names.append(" ".join(LOCK["topic"].split()[:3]))
            _names += [h for h in hints if h][:2]
            # v3.18 FIX (Voyager 1 video me film trailer): pehle 'रोल' jaisa shabd 'कंट्रोल' ke andar bhi mil jaata tha.
            # Ab POORE shabd milte hain; 'फिल्म/मूवी/ट्रेलर' = pakka saboot, 'सीन/शूट/रोल/किरदार' = kamzor (2 chahiye).
            _toks = set(t_.lower() for t_ in re.findall(r"[\u0900-\u097F]+|[A-Za-z]+", " ".join(lines)))
            _strong = _toks & {"फिल्म", "फ़िल्म", "फिल्मों", "मूवी", "film", "films", "movie", "movies", "trailer",
                               "ट्रेलर", "vfx", "वीएफएक्स", "सिनेमा"}
            _weak = _toks & {"सीन", "शूट", "शूटिंग", "रोल", "किरदार", "एक्टर", "डायरेक्टर"}
            if _strong or len(_weak) >= 2:
                FILM = _ent.find_film(list(dict.fromkeys(_names)), strong=bool(_strong))
        except Exception as _fe:
            log(f"   (film check skip: {_fe})", show=False)

    try:                                               # v3.17: Copilot/Teams/Outlook/Apple... ka SAHI (brand) matlab
        import brand_sense
        _all = " ".join([s_.get("script") or s_["text"] for s_ in sents] + list(eng))
        for i_, s_ in enumerate(sents):
            _sn = brand_sense.detect(s_.get("script") or s_["text"], eng[i_] if i_ < len(eng) else "", _all)
            if not _sn: continue
            _neg = [d_ for _, d_ in brand_sense.negatives(_sn)]
            if _neg:
                sources.AVOID[i_] = tuple(dict.fromkeys(tuple(_neg) + tuple(sources.AVOID.get(i_, ()))))[:6]
            if LOCK and i_ < len(LOCK["scenes"]):
                _q = LOCK["scenes"][i_].get("query") or ""
                LOCK["scenes"][i_]["query"] = brand_sense.fix_query(_q, _sn) if _q else brand_sense.queries(_sn)[0]
            if gq and i_ < len(gq) and isinstance(gq[i_], list):
                gq[i_] = list(dict.fromkeys(brand_sense.queries(_sn)[:2] + [brand_sense.fix_query(q_, _sn) for q_ in gq[i_]
                                                                             if isinstance(q_, str)]))
            log(f"   🏷 line {i_+1}: {', '.join(_sn)} = brand/app (galat matlab NAHI: {'; '.join(_neg)[:80] or '-'})", show=False)
    except Exception as _bse:
        log(f"   (brand sense skip: {_bse})", show=False)
    VBRAIN = None
    if yes(style.get("visual_brain", "haan")):
        try:                                           # v3.66: UNIVERSAL VISUAL BRAIN (category + asli insaan/event)
            import visual_brain as _vbm
            _vl = [s_.get("script") or s_["text"] for s_ in sents]
            _vbm.build(_vl, eng, keys, mode=CONTENT_MODE["v"] or style.get("content_mode", "auto"),
                       main=(LOCK or {}).get("main_subject") or "", raw_plan=sources.RAW_PLAN,
                       use_ai=yes(style.get("visual_brain_ai", "haan")), work=work)
            for i_ in range(len(sents)):
                if _vbm.is_real_line(i_):
                    sources.NO_AI_PHOTO.add(i_)        # asli insaan/event ki nakli AI photo kabhi nahi
                _w = _vbm.who_for(i_)
                if _w and not sources.WHO.get(i_) and _vbm.SCRIPT["how"] == "AI" and (_vbm.PLAN.get(i_) or {}).get("how") == "AI":
                    sources.WHO[i_] = _w               # Wikidata/Commons/YouTube (asli) path chalu
            _vbm.fact_check_async(_vl, keys, style)    # background – sirf report me (script kabhi nahi badalti)
            VBRAIN = _vbm
        except Exception as _vbe:
            VBRAIN = None; log(f"   (visual brain skip: {_vbe})", show=False)
    AIPLAN = {}
    if yes(style.get("ai_plan", "haan")):
        try:                                           # v3.16: AI app (ChatGPT/Claude/Gemini) ka copy-paste plan
            import ai_bridge
            AIPLAN = ai_bridge.load_for(sents, work)
            if AIPLAN:
                log(f"   🤝 AI plan mila (aapke ChatGPT/Claude/Gemini app se): {len(AIPLAN)} lines ke visual/editing nirdesh")
                for i_, x_ in AIPLAN.items():
                    if x_.get("avoid"):
                        sources.AVOID[i_] = tuple(dict.fromkeys(tuple(x_["avoid"]) + tuple(sources.AVOID.get(i_, ()))))[:6]
                    if x_.get("show"):
                        sources.SHOW[i_] = x_["show"][:158]       # har jaanch (CLIP/Gemini) isi se milayegi
                    if x_.get("visual") == "map" and x_.get("entity") and not FX.get(i_) and \
                            not (SB and i_ < len(SB) and SB[i_].get("graphic") == "map"):
                        FX.setdefault(i_, []).append(("map", x_["entity"]))
                _g = next((x_.get("_genre") for x_ in AIPLAN.values() if x_.get("_genre")), "")
                if _g in edit_style.PRESETS and str(style.get("edit_style", "auto")).strip().lower() == "auto":
                    style["edit_style"] = _g
        except Exception as _abe:
            AIPLAN = {}; log(f"   (AI plan skip: {_abe})", show=False)
    try:                                               # v3.16: Editing Style Library (vishay ke hisaab se pro niyam)
        edit_style.apply(style, [s_.get("script") or s_["text"] for s_ in sents], eng, LOCK, SCENES, log)
    except Exception as _ese:
        log(f"   (edit style skip: {_ese})", show=False)

    plan = []      # (start, end, item)
    EDL_CUTS = []  # v3.6
    line_start = {}  # shot index -> sentence index (naye line ka pehla shot)
    credits = []
    spans = []
    for i, s in enumerate(sents):
        st = s["start"] if i else 0.0
        en = sents[i + 1]["start"] if i + 1 < len(sents) else total
        k = max(1, int(round((en - st) / cut)))
        spans.append((st, en, min(k, int(num(style, "line_max_clips", 1, 6)))))   # v2.7: ek line pe max 3 clips

    # v2: 4 lines ek saath dhoondhta hai (pehle se ~3-4 guna tez)
    sources.PHOTO_MODE["v"] = style.get("photo", "kam")
    from concurrent.futures import ThreadPoolExecutor
    sources.CHECK["on"] = yes(style.get("footage_check", "haan"))
    if os.environ.get("VG_AVOID") and Path(os.environ["VG_AVOID"]).exists():     # v2.17c: dobara try – purani clips nahi
        sources._used.update(u for u in Path(os.environ["VG_AVOID"]).read_text(encoding="utf-8").split() if u)
    sources.GEM_FOOTAGE["on"] = yes(style.get("gemini_footage", "nahi"))
    # v3.15 FIX (15 Nov video: green-screen clip ka hara hatane pe sab gayab -> khaali sunset/baadal background):
    # default ab green screen clip NAHI lagti. style.txt: green_screen = key -> purana tareeka.
    sources.GREEN["mode"] = style.get("green_screen", "nahi")
    # v3.13 FIX (Bug A): CLIP (offline AI aankh) Gemini / footage_check se ALAG – sirf ai_aankh = nahi se band
    sources.AANKH["on"] = yes(style.get("ai_aankh", "haan"))     # v2.15: CLIP
    sources.VERIFY["on"] = yes(style.get("clip_jaanch", "haan"))        # v2.17: download ke baad 3 frame jaanch
    sources.AI_PHOTO["on"] = yes(style.get("ai_photo", "haan"))         # v2.17: sahi footage na mile -> AI photo
    sources.STRICT_SCORE["v"] = num(style, "footage_sakhti", 3, 10) if style.get("footage_sakhti") else 7.0
    if sources.AANKH["on"]:
        try:
            import aankh
            if not aankh.ready(): sources.AANKH["on"] = False
        except Exception as e:
            sources.AANKH["on"] = False; log(f"   (AI aankh band: {e})", show=False)
    sources.STRICT["on"] = yes(style.get("khali_line_pichhli_clip", "haan"))
    sources.brave_setup(keys)                          # v3.13: Brave (1-2 keys)
    VPICK = yes(style.get("visual_pick", "haan"))
    try:
        import visual_pick
        visual_pick.TRACE.clear(); visual_pick.USE.clear()
        visual_pick.SCRIPT["all"] = " ".join([s_.get("script") or s_["text"] for s_ in sents] + list(eng))   # v3.17
        visual_pick.ON.update(on=VPICK, any_channel=yes(style.get("youtube_kisi_bhi_channel", "nahi")),
                              topic_yt=yes(style.get("youtube_topic_clips", "haan")),
                              n=int(num(style, "visual_kitne", 4, 20)) if style.get("visual_kitne") else 12,
                              video_bonus=float(num(style, "video_bonus", 0, 10)) / 100 if style.get("video_bonus") else 0.03)
        if VPICK:
            log(f"   🎯 visual picker: poori line padh ke {visual_pick.ON['n']} visual/line, video pehle"
                + (f", Brave keys: {len(sources.BRAVE_KEYS)}" if sources.BRAVE_KEYS else ", Brave key nahi"))
            _mn = (LOCK or {}).get("main_subject") or ""
            _fl = (FILM or {}).get("label", "") if FILM else ""
            visual_pick.TOPIC.update(lock=bool(yes(style.get("topic_lock", "haan")) and (
                (_mn and (LOCK or {}).get("main_type") in ("person", "brand")) or _fl)), main=_mn, film=_fl)
            if visual_pick.TOPIC["lock"]:
                log(f"   🔒 topic lock: video '{_mn or _fl}' ke baare me – random stock (anjaan log, janwar, baadal, "
                    f"abstract) nahi; sahi na mile to '{_mn or _fl}' ki apni official video ka naya hissa")
                if yes(style.get("subject_pool", "haan")):
                    try:
                        import subject_pool
                        subject_pool.build(_mn, _fl, keys, context=" ".join(list(eng) + list(topic_kw or [])))
                    except Exception as _spe:
                        log(f"   (subject pool skip: {_spe})", show=False)
            visual_pick.HINT.clear(); visual_pick.HINT.update(USER_HINT)   # v3.18
            if yes(style.get("line_brief", "haan")):          # v3.13 ADD-ON: AI poori line ka matlab -> search
                visual_pick.make_brief([s_.get("script") or s_["text"] for s_ in sents], eng, keys,
                                       (LOCK or {}).get("main_subject") or "", (FILM or {}).get("label", "") if FILM else "")
    except Exception as _vpe:
        VPICK = False; log(f"   (visual picker band: {_vpe})", show=False)
    done_n = [0]
    def job(i):
        if USER_AI_HINT.get(i) and yes(style.get("ai_visual_auto", "haan")):
            # v3.58: Explicit "|| AI: ..." hint -> skip slow stock search, route straight to cinematic AI scene!
            log(f"   line {i+1}: ✨ direct AI scene hint -> {USER_AI_HINT[i][:55]}", show=False)
            return [{"kind": "image", "path": "", "credit": "", "src": "pending_ai_hint", "score": 0.0}], ""
        extra = gq[i] if gq and i < len(gq) else None
        if VBRAIN is not None:                              # v3.66: is line ki category ke hisaab se AI aankh
            try:
                import aankh as _ak
                _ak.set_line_relax(VBRAIN.neg_relax(i))
            except Exception:
                pass
        if LOCK and i < len(LOCK["scenes"]):               # v3.2: kahani ke context wali query sabse pehle
            extra = [LOCK["scenes"][i]["query"]] + [q_ for q_ in (extra or []) if q_ != LOCK["scenes"][i]["query"]]
        if SHOTS and i < len(SHOTS):                        # v3.8: shot list (action / close-up / wide) aage
            extra = list(dict.fromkeys(SHOTS[i]["queries"] + list(extra or [])))[:6]
        if VBRAIN is not None:                              # v3.66: exact person/event queries, heuristics se pehle
            try:
                _bq = VBRAIN.queries(i)
                if _bq:
                    extra = list(dict.fromkeys(_bq[:3] + list(extra or [])))[:7]
            except Exception:
                pass
        if AIPLAN.get(i, {}).get("queries"):                # v3.16: aapke AI app ka plan SABSE pehle
            extra = list(dict.fromkeys(AIPLAN[i]["queries"] + list(extra or [])))[:7]
        if USER_HINT.get(i):                                # v3.18: script ka '/' ya '||' hint – sabse pehle, AI se bhi pehle
            try:
                import visual_pick as _vh
                _ld = _vh.hint_ladder(USER_HINT[i])
            except Exception:
                _ld = [USER_HINT[i]]
            extra = list(dict.fromkeys(_ld + list(extra or [])))[:7]
        try:
            import visual_pick as _vq
            _vq.EXTRA_Q[i] = [q_ for q_ in ((gq[i] if gq and i < len(gq) else []) or []) if isinstance(q_, str)][:4]
        except Exception:
            pass
        r = sources.find_visuals(i, eng[i], topic_kw, spans[i][2], keys, extra_queries=extra,
                                 line=sents[i].get("script") or sents[i]["text"])
        _yk = keys.get("YOUTUBE") or keys.get("YOUTUBEAPI") or keys.get("YOUTUBEAPIKEY")
        _cta = bool(LOCK and i < len(LOCK["scenes"]) and LOCK["scenes"][i].get("cta"))
        if FILM and not _cta and isinstance(r, tuple) and isinstance(r[0], list):   # v3.13b: key na ho to yt-dlp
            try:                                       # v3.6: film ki line -> uske official trailer ka hissa sabse pehle
                import yt_clips
                _kw = [q_ for q_ in (extra or []) if isinstance(q_, str)][:3]
                _sp = SHOTS[i] if SHOTS and i < len(SHOTS) else {}
                _fc = yt_clips.film_clip(FILM, _yk, _kw, verify_text=_sp.get("verify", ""), avoid=_sp.get("rivals", ()))
                if _fc:
                    r = ([dict(c_, entity=FILM["label"], src=f"film trailer: {FILM['label']}") for c_ in _fc] + r[0], r[1])
            except Exception as _fe:
                log(f"   (film trailer clip skip: {_fe})", show=False)
        if VPICK and isinstance(r, tuple) and not (LOCK and i < len(LOCK["scenes"]) and LOCK["scenes"][i].get("cta")):
            try:                                       # v3.13: POORI LINE se 10-12 visual -> score -> video pehle
                import visual_pick
                r = visual_pick.improve(i, r, eng[i], sents[i].get("script") or sents[i]["text"], keys, spans[i][2],
                                        LOCK, FILM, SHOTS[i] if SHOTS and i < len(SHOTS) else None)
                r = (sources.green_fix(r[0], i, topic_kw, keys, eng[i]), r[1])
            except Exception as _ve:
                log(f"   (visual picker skip line {i+1}: {str(_ve)[:120]})", show=False)
        done_n[0] += 1
        log(f"   visuals: {min(done_n[0], len(sents))}/{len(sents)} lines ✓")      # v2.6: progress, taaki ruka hua na lage
        return r
    # v2.8: aapki apni footage (Telegram / Drive) pehle
    user_assign = {}
    if os.environ.get("VG_FOOTAGE"):
        try:
            import footage
            user_assign = footage.assign(os.environ["VG_FOOTAGE"], [s.get("script") or s["text"] for s in sents],
                                         os.environ.get("VG_NOTES", ""), keys.get("GEMINI"), work)
        except Exception as e:
            log(f"   (aapki footage nahi lag payi: {e})")
    prev_items = {int(k): v for k, v in ((PREV or {}).get("items") or {}).items()} if PREV else {}
    redo = set(range(len(sents))) if FB and FB["all_footage"] else set(FB["bad_lines"]) if FB else set()
    if FB:
        for i, its in prev_items.items():            # purani (galat) clips dobara nahi aayengi
            if i in redo:
                for it in its:
                    if it.get("url"): sources._used.add(it["url"])
    face_lines = set()
    if FACE:
        want = style.get("chehra_lines", "shuru,twist,aakhir")
        if "shuru" in want: face_lines.add(0)
        if "aakhir" in want: face_lines.add(len(sents) - 1)
        if "twist" in want:
            for i, s in enumerate(sents):
                if 0 < i < len(sents) - 1 and re.search(r"(लेकिन|सोचो|इमैजिन|असली)", s.get("script") or s["text"]):
                    face_lines.add(i); break

    def job2(i):
        txt_i = (sents[i].get("script") or sents[i]["text"]).lower()
        if i == len(sents) - 1 and i > 0 and i not in user_assign and re.search(r"(फॉलो|फोलो|सब्सक्राइब|subscribe|follow)", txt_i):
            return ([], [])       # v2.17c: aakhri "follow" line – pichhli achhi clip + ek hi subscribe button (stock nahi)
        if i in face_lines:
            return ([{"kind": "video", "path": Path(FACE), "credit": "", "src": "chehra", "face": True}], [])
        if i in user_assign:
            its = [{"kind": "video" if Path(p).suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp") else "image",
                    "path": Path(p), "credit": "", "src": "aapki footage"} for p in user_assign[i]]
            return (its, [])
        if i in prev_items and i not in redo:
            its = [dict(it, path=Path(it["path"])) for it in prev_items[i] if Path(it["path"]).exists()]
            if its: return (its, [])
        if SB and i < len(SB) and SB[i].get("graphic") == "map" and SB[i].get("place") and i not in user_assign \
                and i not in face_lines and yes(style.get("map", "haan")):
            try:                                   # v3.1: jagah wali line -> 3D map animation (reference jaisa)
                from cine import mapanim
                mout = work / "shots" / f"cmap_{i:02d}.mp4"
                dur_m = spans[i][1] - spans[i][0] + 0.3
                mapanim.render(SB[i]["place"], dur_m, mout, W, H, style, BIBLE["palette"] if BIBLE else {}, fps=render.FPS)
                log(f"   line {i+1}: 3D map – {SB[i]['place'].get('name')}")
                return ([{"kind": "video", "path": mout, "credit": "Map data: OpenStreetMap / Natural Earth",
                          "src": "map", "whole": True, "ss": 0.0}], [])
            except Exception as e:
                log(f"   (map line {i+1} skip: {e})", show=False)
        if blender_first(i):
            log(f"   line {i+1}: 3D Blender scene pehle ({SCENES[i]['blender_template']}) – footage nahi dhoondh raha")
            return ([], [])
        r = fx_line(i)
        return r if r else job(i)
    import threading as _th
    _BF = {"n": 0, "lock": _th.Lock()}
    try:
        from cine import blender_engine as _be
        _BL_OK = bool(_be.find_blender() or os.environ.get("VG_BPY_PYTHON"))
    except Exception:
        _BL_OK = False

    def blender_first(i):
        """v3.1: kab Blender 3D footage se PEHLE:  auto = number/stat wali line (3D chart, max 2)  |
        haan = science/space/ocean/tech/number lines (max blender_max). Naam wali (insaan/brand) line pe kabhi nahi."""
        mode = (style.get("blender3d") or "nahi").strip().lower()
        if not _BL_OK or mode != "haan" or not SCENES or i >= len(SCENES):   # v3.4: 3D sirf "haan" pe
            return False
        sc = SCENES[i]; tpl = sc.get("blender_template")
        if not tpl or tpl == "abstract" or sources.WHO.get(i) or i in user_assign or i in face_lines:
            return False
        if mode == "haan":
            ok = sc.get("domain") in ("space", "ocean", "biology", "science", "technology", "geography") or tpl == "infographic"
            lim = int(num(style, "blender_max", 0, 20)) if style.get("blender_max") else 4
        else:
            ok = tpl == "infographic" and bool(re.search(r"[0-9०-९]", sents[i].get("script") or sents[i]["text"])); lim = 2
        if not ok: return False
        with _BF["lock"]:
            if _BF["n"] >= lim: return False
            _BF["n"] += 1
        return True
    import fx
    PRO = yes(style.get("pro_effects", "haan"))
    def fx_line(i):
        """v2.15: [map: ..] / [news: ..] wali line -> poori line ek khaas graphic shot."""
        if not PRO: return None
        for name, val in FX.get(i, []):
            dur = spans[i][1] - spans[i][0] + 0.4
            if name == "map" and val and yes(style.get("map", "haan")):
                place, _, lab = val.partition("|")
                out = work / "shots" / f"map_{i:02d}.mp4"
                log(f"   line {i+1}: map bana raha hoon – {place.strip()}")
                if fx.map_clip(place.strip(), lab.strip() or place.split(",")[0].strip(), dur, out, W, H, style, work):
                    return ([{"kind": "video", "path": out, "credit": "", "src": "map", "whole": True, "ss": 0.0}], [])
            if name == "news" and val and yes(style.get("news_card", "haan")):
                head, _, srcn = val.partition("|")
                base = job(i)
                photo = None
                for it in (base[0] if base else []):
                    p_ = Path(it["path"])
                    if it["kind"] == "image": photo = p_; break
                    fp = work / "shots" / f"newsph_{i:02d}.jpg"
                    try:
                        d_ = duration(p_) or 2
                        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d_*0.4:.2f}", "-i", p_, "-frames:v", "1", "-q:v", "2", fp])
                        photo = fp; break
                    except Exception:
                        continue
                out = work / "shots" / f"news_{i:02d}.mp4"
                log(f"   line {i+1}: news card bana raha hoon")
                try:
                    fx.news_clip(head.strip(), srcn.strip(), photo, dur, out, W, H, style, work)
                    cr = [it for it in (base[0] if base else [])][:1]
                    return ([{"kind": "video", "path": out, "credit": cr[0].get("credit", "") if cr else "",
                              "src": "news card", "whole": True, "ss": 0.0}], [])
                except Exception as e:
                    log(f"   (news card nahi bana: {str(e)[:100]})", show=False)
                    return base
        return None
    def job3(i):                                   # v2.14: ek line ki galti se poori video na ruke
        try:
            return job2(i)
        except Exception as e:
            log(f"   line {i+1}: footage me galti ({str(e)[:80]}) – pichhli line ki clip lagegi")
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                import traceback; f.write(traceback.format_exc())
            return ([], [])
    with ThreadPoolExecutor(max_workers=int(HW.get("visual_search_threads", 4)) if HW else 4) as ex:
        found = list(ex.map(job3, range(len(sents))))
    log(f"   visuals: {len(sents)}/{len(sents)} lines ✓ (sab lines ki khoj poori)")   # v3.5: "9/10 pe atki" jaisa na dikhe
    try:                                               # v3.15 TOPIC LOCK: khaali line -> kinetic card/Blender se PEHLE
        import visual_pick as _vp, subject_pool as _sp  # mukhya insaan/film ki apni video ka naya hissa
        if VPICK and _vp.TOPIC["lock"]:
            for i_, (its_, kw_) in enumerate(found):
                if its_ or (LOCK and i_ < len(LOCK["scenes"]) and LOCK["scenes"][i_].get("cta")): continue
                _pc = _sp.next_clip(i_, "", sources.AVOID.get(i_, ()))
                if _pc: found[i_] = ([_pc], kw_)
    except Exception as _fe:
        log(f"   (topic fill skip: {_fe})", show=False)
    # v3.1: jin lines ki sahi footage nahi mili -> (local AI video) -> Blender 3D -> animated kinetic card
    # (pehle seedha static text card lagta tha jo "atka hua frame" jaisa dikhta tha)
    FALLBACK_SRC = {}
    try:
        import fallback_visuals
        FALLBACK_SRC = fallback_visuals.fill(found, sents, spans, SCENES, style, keys, work, W, H, render.FPS,
                                             sources.KEYW, last_follow_skip=True)
    except Exception as e:
        log(f"   (fallback visuals skip: {e})", show=False)
    VREP = {}
    if LOCK and yes(style.get("visual_gate", "haan")):
        try:                                           # v3.2: PRE-RENDER VISUAL GATE (verify -> reject -> replace)
            import visual_verify
            log("   🎯 visual jaanch: har scene kahani + lock se mila raha hoon...")
            VREP = visual_verify.gate(found, sents, LOCK, keys, style, work, spans, W, H, render.FPS,
                                      rounds=int(num(style, "visual_gate_round", 0, 3)) if style.get("visual_gate_round") else 2,
                                      plan_scenes=SCENES)
            log(f"   🎯 visual relevance: {VREP['relevance_pct']}% sahi ({VREP['relevant']}/{VREP['scenes_total']}), "
                f"safe fallback {VREP['safe_fallback']}, fail lines: {VREP['failed_lines'] or 'koi nahi'}")
        except Exception as e:
            log(f"   (visual gate skip: {e})", show=False)
    try:                                               # v3.4: YouTube clips ka saaf haal
        import yt_clips
        _ys = yt_clips.status()
        log(f"   🎞 YouTube clips: {_ys['n']} lagi, {_ys['fail']} nahi kati" +
            (f" – wajah: {_ys['why'][-140:]}" if _ys["fail"] and not _ys["n"] else ""))
        if _ys["fail"] and not _ys["n"]:
            log("   ⚠️ YouTube clip ek bhi nahi kati – INSTALL_DEPENDENCIES.bat dobara chalao (yt-dlp + Deno update)")
    except Exception:
        pass
    if yes(style.get("jaldi", "nahi")):                # v3.6: sabse tez mode
        style["check_bot"] = "nahi"; style["visual_gate_round"] = "1"
        log("   ⚡ jaldi mode: Gemini poori-video review + dobara render band")
    qc_rounds = int(num(style, "check_bot_round", 0, 3)) if yes(style.get("check_bot", "haan")) else 0
    if FB and (FB["all_footage"] or FB["bad_lines"]): qc_rounds = max(qc_rounds, 2)
    name = None
    BEATS = []
    if yes(style.get("beat_cut", "haan")) and style.get("music_awaaz", "22") != "0":
        try:
            mf = render.pick_music(style); style["_music"] = str(mf)
            BEATS = render.music_beats(mf, total)
            log(f"   music beats: {len(BEATS)} (cut beat pe)", show=False)
        except Exception as e:
            log(f"   (beat skip: {e})", show=False)
    DPLAN = {"v": None}

    def _cta_visual(i_cta):
        """v3.16: CTA / follow line ke liye mukhya vishay ka best visual."""
        main_lines = [j_ for j_ in range(i_cta) if LOCK and j_ < len(LOCK["scenes"]) and LOCK["scenes"][j_].get("uses_main")
                      and not LOCK["scenes"][j_].get("cta")]
        order_ = list(dict.fromkeys(main_lines + [0] + list(range(i_cta - 1, -1, -1))))
        best_ = None
        # v3.18 (user 17 Nov: "end me wahi shuru wali clip dobara") – pehle aisa visual jo video me abhi tak NAHI laga
        used_ = {str((x_[2] or {}).get("path")) for x_ in plan if len(x_) > 2 and isinstance(x_[2], dict)}
        for fresh_only in (True, False):
            for want_kind in ("video", "image"):
                for j_ in order_:
                    for x in (found[j_][0] if j_ < len(found) else []):
                        if x.get("face") or x.get("whole") or x.get("kind") != want_kind: continue
                        if x.get("src") in ("map", "news card"): continue
                        if fresh_only and str(x.get("path")) in used_: continue
                        if best_ is None or (x.get("score") or 0) > (best_.get("score") or 0):
                            best_ = x
                    if best_: break
                if best_: break
            if best_: break
        if best_:
            log(f"   line {i_cta+1}: follow/CTA line – mukhya vishay ka shot wapas ({best_.get('src', '')})", show=False)
            return [dict(best_, show_name=False, crop_v=int(best_.get("crop_v") or 0) + 1)]
        return []
    PREV_TR = {}; SHOT_DONE = {}                       # v3.6: dobara round me sirf badle shots dobara banenge
    for qc_round in range(qc_rounds + 1):
        plan = []; line_start = {}; credits = []; KW_BEHIND = set(); NAME_SHOWN = set(); HERO_N = [-1]
        NAME_T = []                                    # v3.17: naam patti kab dikhi (keyword se takraav nahi)
        prev_items = []
        IMG_USED = {}                                  # v3.13: photo path -> kitni baar lagi (repeat NAHI)
        def _ukey(x): return str(x.get("path"))
        for i, s in enumerate(sents):
            st, en, k = spans[i]
            d = en - st
            items, kw = found[i]
            # v3.13 FIX ("ek photo 4 baar" + "chehra zoom"): jo photo pehle lag chuki – dobara nahi. Line ke liye sirf
            # purani photo bachi ho to: pichhli line ki video ka ALAG hissa, warna doosri line ki koi na-lagi photo/video.
            fresh = [x for x in items if x["kind"] != "image" or IMG_USED.get(_ukey(x), 0) == 0]
            if items and not fresh:
                alt = [x for x in prev_items if x["kind"] == "video"]
                if not alt:
                    pool_ = [x for j_, (its_, _) in enumerate(found) if j_ != i for x in its_
                             if x["kind"] == "video" and not x.get("face") and not x.get("whole")]
                    pool_ += [x for j_, (its_, _) in enumerate(found) if j_ != i for x in its_
                              if x["kind"] == "image" and IMG_USED.get(_ukey(x), 0) == 0 and
                              (x.get("entity") and x.get("entity") == items[0].get("entity"))]
                    alt = pool_[:1]
                if alt:
                    log(f"   line {i+1}: photo pehle lag chuki – repeat ki jagah doosra visual ({alt[0].get('src', '')})", show=False)
                    fresh = [dict(alt[0])]
                else:
                    log(f"   ⚠️ line {i+1}: koi naya visual nahi – wahi photo dobara (alag camera move)", show=False)
                    fresh = items[:1]
            items = fresh
            imgs_only = items and all(x["kind"] == "image" for x in items)
            if imgs_only and len(items) < k:
                k = max(1, len(items))                    # photo dohraane ki jagah kam (lambe) shot
                if len(items) == 1 and items[0].get("hero") and d > 3.6:
                    k = 2                                 # v3.17 (NVIDIA video: ek photo 5-7 sec khadi) – alag crop + move
            if any(x.get("part") == 1 for x in items) and d >= 2.4:
                k = max(k, 2)                             # v3.13: line 2 hisse me -> kam se kam 2 shot
            is_follow = (i == len(sents) - 1 and i > 0 and
                         bool(re.search(r"(फॉलो|फोलो|सब्सक्राइब|subscribe|follow)", (s.get("script") or s["text"]).lower())))
            if not items and is_follow:
                # v3.16 FIX (log 16 Nov: "follow karo" line pe Thekua (mithai) ki photo – kyunki pichhli line ki
                # photo chalti rehti thi). Ab: video ke MUKHYA vishay ka sabse achha visual (hook / main-subject line ki
                # video pehle) – jaise pro editor end me hook wala shot wapas laata hai. Map / chehra / text nahi.
                items = _cta_visual(i)
            if not items and not is_follow:
                try:                                  # v3.15 TOPIC LOCK: khaali line pe text card nahi – mukhya
                    import visual_pick as _vp        # insaan/film ki apni video (doosri line wali, naya hissa)
                    if _vp.TOPIC["lock"]:
                        _own = [x for j_, (its_, _) in enumerate(found) if j_ != i for x in its_
                                if x["kind"] == "video" and (x.get("pool") or x.get("entity")) and not x.get("face")]
                        if not _own:
                            import subject_pool
                            _pc = subject_pool.next_clip(i, "", sources.AVOID.get(i, ()))
                            _own = [_pc] if _pc else []
                        if _own:
                            items = [dict(random.choice(_own), show_name=False)]
                            log(f"   line {i+1}: koi sahi visual nahi – '{_vp.TOPIC['main'] or _vp.TOPIC['film']}' ki apni "
                                f"video ka doosra hissa (text card nahi)", show=False)
                except Exception as _te:
                    log(f"   (topic fill skip: {_te})", show=False)
            if not items and prev_items and yes(style.get("khali_line_pichhli_clip", "haan")):
                items = [dict(x, credit=x.get("credit", "")) for x in prev_items]   # v2.7: galat clip se behtar
            if any(x["kind"] == "video" and not x.get("whole") for x in items):
                prev_items = [x for x in items if x["kind"] == "video" and not x.get("whole")]
            src_names = ", ".join(sorted({x.get("src", "my_clips") for x in items})) or "text card"
            log(f"   line {i+1}/{len(sents)}: {len(items)}/{k} visuals ({src_names})")
            if items and (items[0].get("face") or items[0].get("whole")):
                k = 1                                     # chehra / map / news: poori line ek shot
            elif i == 0 and items and d >= 2.2 and yes(style.get("hook_tez_cut", "haan")):
                k = max(k, min(int(style.get("_hook_cuts", "3") or 3), int(d // 1.1)))   # v3.6 HOOK (v3.16: genre se)
                if imgs_only: k = max(1, min(k, len(items)))   # v3.15 FIX: hook ke chakkar me wahi photo 2 baar nahi
            _nd = len({str(x.get("path") or x.get("url")) for x in items})
            if items and _nd < k and not (items[0].get("face") or items[0].get("whole") or
                                          (imgs_only and items[0].get("hero"))) and \
                    yes(style.get("jump_cut_kam", "haan")):
                # v3.16 PRO NIYAM (log 16 Nov: ek hi clip ad98a.. line 1 me 3 baar kaat ke = 'jump cut', amateur
                # lagta hai): jitne ALAG visual hain utne hi cut. Ek clip ho to ek lamba shot (camera move ke saath),
                # sirf tab tukde jab shot 4.2 sec se lamba ho jaaye.
                k_new = max(_nd, int(-(-d // 4.2)), 1)
                if k_new < k:
                    log(f"   line {i+1}: {_nd} alag visual – {k} ki jagah {k_new} shot (jump cut nahi)", show=False)
                    k = k_new
            seg = d / k
            pts = [st + q * seg for q in range(k + 1)]
            if k == 2 and len(items) >= 2 and items[1].get("part") == 1:
                _pc = part_cut_time(s, eng[i] if i < len(eng) else "", st, en)   # v3.18: hissa-2 tab jab uski baat shuru
                if _pc: pts[1] = _pc
            if BEATS and k > 1:                         # v2.14: line ke andar ke cut music ki beat pe
                for q in range(1, k):
                    near = [b for b in BEATS if abs(b - pts[q]) <= 0.3 and b - pts[q - 1] >= 1.0 and pts[q + 1] - b >= 1.0]
                    if near: pts[q] = min(near, key=lambda b: abs(b - pts[q]))
            if "_UG" not in locals():
                from unique_guard import UniqueAssetGuard
                _UG = UniqueAssetGuard()
            if "_DOC_BEATS" not in locals():
                _DOC_BEATS = {"stat": 0, "news": 0, "parallax": 0, "last_line": -9}
            for j in range(k):
                # v3.25 INTENTIONAL DOCUMENTARY DIRECTOR: insert up to 3 high-impact motion-graphics beats
                # (StatCounterPro, NewsHighlight yellow sweep, 2.5D CutoutParallax) directly into the story timeline!
                _doc_forced = None
                if (yes(style.get("documentary_mode", "haan")) and W < H and j == 0
                        and 1 <= i <= len(sents) - 2 and (i - _DOC_BEATS["last_line"]) >= 2):
                    _ltxt = str(s.get("script") or s["text"] or "")
                    _kw_i = str(sources.KEYW.get(i) or "")
                    _dur_b = max(1.4, pts[j + 1] - pts[j] + 0.15)
                    try:
                        from cine import doc_cards as _dc, bible as _bible
                        _pal_b = _bible.build(lines, eng, style)["palette"]
                        # v3.62: In Shorts (or when real footage exists), NEVER black-out real footage with a dark Stat card —
                        # let the real footage play full-screen with animated stat overlay on top! (Use Stat card only if no footage or LONG mode)
                        _stat_cap = (3 if LONG else 0) if (items and not yes(style.get("black_stat_cards", "nahi"))) else (3 if LONG else 1)
                        _news_cap = 3 if LONG else 1
                        _px_cap = 2 if LONG else 1
                        # Beat A: Big number / money / percent -> StatCounterProCard
                        if _DOC_BEATS["stat"] < _stat_cap and re.search(r"(\d[\d,.]*\s*(?:%|प्रतिशत|लाख|करोड़|अरब|मिलियन|बिलियन|हजार|फीट|किलोमीटर|°C|डिग्री))", _ltxt):
                            _mnum = re.search(r"(-?\d[\d,.]*\s*(?:%|प्रतिशत|लाख|करोड़|अरब|मिलियन|बिलियन|हजार|फीट|किलोमीटर|°C|डिग्री)?)", _ltxt)
                            _val_s = (_kw_i if re.search(r"\d", _kw_i) else (_mnum.group(1) if _mnum else _kw_i)).strip()
                            if _val_s:
                                _bc = work / "shots" / f"doc_stat_{i:02d}.mp4"
                                if not _bc.exists():
                                    _stmp = "ALERT" if re.search(r"(खतरनाक|स्कैम|scam|danger|हमला|माइनस|-\d)", _ltxt, re.I) else ""
                                    _rem_ok = None
                                    _t_clean = (title[0] if isinstance(title, (list, tuple)) and title else str(title or "KEY FACT")).strip()
                                    _sub_clean = _ltxt[:56].rsplit(" ", 1)[0] if len(_ltxt) > 56 else _ltxt
                                    if yes(style.get("remotion_beats", "haan")):
                                        from cine import remotion_bridge as _rb
                                        _rem_ok = _rb.render_beat("stat_slam", {"value": _val_s[:18], "label": _t_clean[:26], "sub": _sub_clean, "stamp": _stmp}, _dur_b, _bc, W, H, render.FPS)
                                    if not _rem_ok:
                                        _dc.render_stat_pro(_val_s[:18], _t_clean[:26], _dur_b, _bc, W, H, style, _pal_b,
                                                            sub=_sub_clean, stamp=_stmp, trend="up", fps=render.FPS)
                                _doc_forced = {"kind": "video", "path": _bc, "credit": "", "src": "kinetic card", "ss": 0.0}
                                _DOC_BEATS["stat"] += 1; _DOC_BEATS["last_line"] = i
                        # Beat B: Historical year OR breaking news/report/court/survey proof -> NewsHighlightCard (yellow highlighter sweep!)
                        elif _DOC_BEATS["news"] < _news_cap and (
                            re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", _ltxt)
                            or (LONG and re.search(r"(रिपोर्ट|रिसर्च|सर्वे|अदालत|कोर्ट|सुप्रीम|सरकार|ब्रेकिंग|न्यूज़|खबर|वैज्ञानिक|अध्ययन|स्टडी|घोषणा|कानून|फैसला|report|study|survey|court|breaking|news|research|government|official|confirmed)", _ltxt, re.I))
                        ):
                            _ym = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", _ltxt)
                            _nm = re.search(r"(रिपोर्ट|रिसर्च|सर्वे|अदालत|कोर्ट|सुप्रीम|सरकार|ब्रेकिंग|न्यूज़|खबर|वैज्ञानिक|अध्ययन|स्टडी|घोषणा|कानून|फैसला|report|study|survey|court|breaking|news|research|government|official|confirmed)", _ltxt, re.I)
                            _hl = (_ym.group(1) if _ym else (_kw_i[:20] if _kw_i else (_nm.group(1) if _nm else "FACT"))).strip()
                            _dtag = f"ARCHIVE • {_ym.group(1)}" if _ym else "NEWS & FACT BRIEF"
                            _bc = work / "shots" / f"doc_news_{i:02d}.mp4"
                            if not _bc.exists():
                                _rem_ok = None
                                _t_clean = (title[0] if isinstance(title, (list, tuple)) and title else str(title or "FACT BRIEF")).strip()
                                if yes(style.get("remotion_beats", "haan")):
                                    from cine import remotion_bridge as _rb
                                    _rem_ok = _rb.render_beat("news_highlight", {"source": _t_clean[:28], "headline": _ltxt[:115], "highlight": _hl, "dateStr": _dtag}, _dur_b, _bc, W, H, render.FPS)
                                if not _rem_ok:
                                    _dc.render_news_highlight(_t_clean[:28], _ltxt[:115],
                                                              _hl, _dur_b, _bc, W, H, style, _pal_b, date_str=_dtag, fps=render.FPS)
                            _doc_forced = {"kind": "video", "path": _bc, "credit": "", "src": "kinetic card", "ss": 0.0}
                            _DOC_BEATS["news"] += 1; _DOC_BEATS["last_line"] = i
                        # Beat C: Archival/entity photo -> Real Blender 3D Documentary Stage (if Blender available), else 2.5D CutoutParallax!
                        elif _DOC_BEATS["parallax"] < _px_cap and items and items[0].get("kind") == "image" and Path(str(items[0].get("path", ""))).exists():
                            _bc = work / "shots" / f"doc_px_{i:02d}.mp4"
                            if not _bc.exists():
                                _bl_ok = None
                                _bdoc_def = "haan" if (HW and HW.get("cycles_ok")) else "nahi"
                                if yes(style.get("blender_doc_stage", _bdoc_def)):
                                    try:
                                        from cine import blender_engine as _be
                                        _bl_ok = _be.render(_bc, max(30, int(round(_dur_b * render.FPS))), W, H,
                                                            "doc_stage", camera="orbit", palette=_pal_b,
                                                            image_path=items[0]["path"], log=log)
                                    except Exception:
                                        _bl_ok = None
                                if not _bl_ok:
                                    _dc.render_cutout_parallax(items[0]["path"], (_kw_i or str(title or "FACT"))[:14],
                                                               _dur_b, _bc, W, H, style, _pal_b, fps=render.FPS)
                            _doc_forced = {"kind": "video", "path": _bc, "credit": "", "src": "kinetic card", "ss": 0.0}
                            _DOC_BEATS["parallax"] += 1; _DOC_BEATS["last_line"] = i
                    except Exception as _dbe:
                        log(f"   (doc beat skip: {_dbe})", show=False)
                if _doc_forced is not None:
                    it = _doc_forced
                    continue_normal = False
                else:
                    continue_normal = True
                if not continue_normal:
                    pass
                elif j < len(items):
                    cand_it = items[j]
                    # v3.21 NO-REPEAT GUARD: if this source video was already used in an earlier scene, pick unused or doc card
                    if cand_it.get("kind") == "video" and not str(cand_it.get("src", "")).startswith(("kinetic", "map", "blender")):
                        if _UG.is_duplicate(cand_it) and not (i == len(sents) - 1 and is_follow):
                            alt_unused = [x for x in items[j + 1:] if not _UG.is_duplicate(x)]
                            if alt_unused:
                                cand_it = alt_unused[0]
                            else:
                                # v3.39 CRASH FIX: NEVER leave it=None (caused AttributeError -> SAFE MODE!).
                                # Build a clean Documentary card instead of repeating or crashing.
                                try:
                                    from cine import doc_cards as _dcd, bible as _bibd
                                    _dup_mp4 = work / "shots" / f"doc_uniq_{i:02d}_{j}.mp4"
                                    if not _dup_mp4.exists():
                                        _pal_d = _bibd.build(lines, eng, style)["palette"]
                                        _lt = str(s.get("script") or s["text"] or "")
                                        _kw_d = str(sources.KEYW.get(i) or "")
                                        _dcd.render_news_highlight(str(title or "FACT BRIEF")[:28], _lt[:110],
                                                                   _kw_d, max(1.0, pts[j + 1] - pts[j] + 0.15),
                                                                   _dup_mp4, W, H, style, _pal_d, fps=render.FPS)
                                    cand_it = {"kind": "video", "path": _dup_mp4, "credit": "", "src": "kinetic card", "ss": 0.0}
                                except Exception:
                                    cand_it = items[j]  # guaranteed non-None safe fallback
                    it = cand_it if cand_it is not None else items[j]
                    # v3.34 EXACT-SCENE UPGRADE: if stock clip has weak relevance (<0.23) and Cloud Flux is ON,
                    # generate the EXACT scene demanded by the script line instead of showing generic trees/flags!
                    # v3.55 UNIVERSAL ANY-TOPIC VISUAL ROUTER (zero hardcoded topics — works for ANY niche!)
                    _rp_i = sources.RAW_PLAN.get(i) or {}
                    _ft_ai = str(_rp_i.get("footage_type") or "").lower()
                    _vmode = str(_rp_i.get("visual_mode") or "").upper()
                    _needs_ai = bool(USER_AI_HINT.get(i)) or (_vmode == "AI_SCENE") or (_ft_ai in ("3d", "graphic", "ai"))
                    _weak_stock = (it is not None and it.get("score") is not None and float(it.get("score") or 1.0) < 0.30)
                    # v3.66 FIX (sabse badi wajah "visual match nahi"): pehle score < 0.30 pe ASLI clip bhi AI photo se
                    # badal jaati thi (CLIP me sahi clip bhi 0.22-0.30 hoti hai). Ab visual_brain tay karta hai.
                    _ai_ok = (_needs_ai or _weak_stock)
                    if _ai_ok and it is not None:
                        try:
                            import visual_brain as _vbr
                            _ai_ok = _vbr.allow_ai_override(i, it, _needs_ai, bool(USER_AI_HINT.get(i)), style)
                        except Exception:
                            _ai_ok = bool(USER_AI_HINT.get(i))
                    if (it is not None and yes(style.get("ai_visual_auto", "haan"))
                            and j == 0 and _ai_ok
                            and not str(it.get("src", "")).startswith(("kinetic", "map", "blender", "nasa", "cloud"))):
                        try:
                            import cloud_visuals as _cv2
                            from cine import doc_cards as _dc2, bible as _bib2
                            _q_exact = str(USER_AI_HINT.get(i) or _rp_i.get("ai_prompt") or sources.SHOW.get(i) or (eng[i] if i < len(eng) and eng[i] else s.get("script") or s["text"]))
                            _ai_ex = _cv2.generate_scene_image(_q_exact, work / "ai_visuals", topic=str(title or ""), W=W, H=H, keys=keys)
                            if _ai_ex:
                                # v3.59: Full-screen immersive AI scene (smooth Ken Burns, no repetitive dark box!)
                                it = {"kind": "image", "path": _ai_ex, "credit": "", "src": "cloud flux", "fullbleed": True}
                        except Exception:
                            pass
                    if it is not None:
                        _UG.register(it)
                elif items:
                    vids = [x for x in items if x["kind"] == "video"] or items
                    it = dict(vids[j % len(vids)])     # video ka alag hissa (photo nahi)
                    if it.get("hero"):                 # v3.1: wahi photo isi line me dobara -> alag crop
                        it["crop_v"] = int(it.get("crop_v") or 0) + j
                else:
                    # v3.1: static Hindi text card NAHI (upar faltu Hindi likha aata tha) -> chalta kinetic keyword card
                    it = None
                    try:
                        from fallback_visuals import key_phrase
                        from cine import cards as _cards, doc_cards as _dc, bible as _bible
                        kc = work / "shots" / f"kcard_{i:02d}_{j}.mp4"
                        if not kc.exists():
                            _pal = _bible.build(lines, eng, style)["palette"]
                            _kw = sources.KEYW.get(i) or key_phrase(s.get("script") or s["text"])
                            _dur_k = max(0.8, pts[j + 1] - pts[j] + 0.2)
                            _txt_line = str(s.get("script") or s["text"] or "")
                            # v3.22 FREE CLOUD AI VISUAL: generate exact scene visual (0% GPU load) + 2.5D Parallax!
                            _ai_img = None
                            _fill_ok = True
                            try:
                                import visual_brain as _vbf
                                _fill_ok = _vbf.allow_ai_fill(i, style)   # v3.66: asli insaan ki nakli photo nahi
                            except Exception:
                                pass
                            if _fill_ok and yes(style.get("ai_visual_auto", "haan")) and not re.search(r"\d", str(_kw)):
                                try:
                                    import cloud_visuals as _cv
                                    _q_desc = (eng[i] if i < len(eng) and eng[i] else _txt_line)
                                    _ai_img = _cv.generate_scene_image(_q_desc, work / "ai_visuals", topic=str(title or ""), W=W, H=H, keys=keys)
                                except Exception as _cve:
                                    log(f"   (cloud visual skip: {_cve})", show=False)
                            if _ai_img:
                                _dc.render_cutout_parallax(_ai_img, str(_kw)[:14], _dur_k, kc, W, H, style, _pal, fps=render.FPS)
                            elif yes(style.get("documentary_mode", "haan")):
                                if re.search(r"\d", str(_kw)):
                                    _stmp = "ALERT" if re.search(r"(खतरनाक|danger|scam|बैन|ban)", _txt_line, re.I) else ""
                                    _dc.render_stat_pro(str(_kw), (title[0] if isinstance(title, (list, tuple)) and title else str(title or "KEY FACT")).strip()[:28], _dur_k, kc, W, H, style, _pal,
                                                        sub=_txt_line[:52], stamp=_stmp, fps=render.FPS)
                                else:
                                    _dc.render_news_highlight(str(title or "FACT REPORT")[:30], _txt_line[:110],
                                                              str(_kw), _dur_k, kc, W, H, style, _pal, fps=render.FPS)
                            else:
                                _cards.render_word(_kw, "", _dur_k, kc, W, H, style, _pal, fps=render.FPS)
                        it = {"kind": "video", "path": kc, "credit": "", "src": "kinetic card", "ss": 0.0}
                    except Exception as _ke:
                        log(f"   (kinetic card fail: {_ke})", show=False)
                    if it is None:
                        card = work / "shots" / f"card_{i:02d}_{j}.jpg"
                        render.text_card("", card, W, H, i)
                        it = {"kind": "image", "path": card, "credit": ""}
                if not isinstance(it, dict):
                    _fb_card = work / "shots" / f"card_safe_{i:02d}_{j}.jpg"
                    if not _fb_card.exists():
                        render.text_card("", _fb_card, W, H, i)
                    it = {"kind": "image", "path": _fb_card, "credit": "", "src": "safe fallback"}
                _hook_on = yes(style.get("hf_hook", "haan")) or yes(style.get("hook_text", "haan"))
                if it.get("hero"):
                    # v3.1: naam patti sirf video me PEHLI baar; har hero shot alag camera move (ek jaisa nahi)
                    en_ = it.get("entity") or ""
                    if en_ in NAME_SHOWN or j > 0: it = dict(it, show_name=False)
                    # v3.15 FIX (15 Nov: shuru me 3 text ek saath – hook title + bada naam + naam patti, Yash ka
                    # chehra dhak gaya): hook ke 3.2 sec tak naam patti / peeche wala bada text NAHI
                    if _hook_on and pts[j] < 3.2: it = dict(it, show_name=False)
                    NAME_SHOWN.add(en_)
                    if it.get("show_name", True) is not False and en_:
                        NAME_T.append((pts[j], pts[j] + 2.8))
                    HERO_N[0] += 1
                    it = dict(it, motion=("depth_push", "pan", "pull_out")[HERO_N[0] % 3], seed=HERO_N[0])   # card-frame nahi
                if (it.get("hero") and it.get("role") != "logo" and j == 0 and SB and i < len(SB) and SB[i].get("kw")
                        and not (_hook_on and pts[j] < 3.2)
                        and SB[i].get("kind") != "name" and re.match(r"^[A-Z0-9%₹ .,-]+$", str(SB[i]["kw"]))):
                    it = dict(it, kw_behind=SB[i]["kw"]); KW_BEHIND.add(i)   # v3.1: keyword subject ke peechhe
                if it.get("face"): it = dict(it, ss=pts[j])
                if it.get("whole"): it = dict(it, ss=0.0)
                if it.get("kind") == "image":
                    IMG_USED[_ukey(it)] = IMG_USED.get(_ukey(it), 0) + 1
                    if not it.get("focus_text"):          # v3.13: crop/camera line ke subject ki taraf
                        try:
                            import identity_lock as _il
                            _mn = (LOCK or {}).get("main_subject") or ""
                            it = dict(it, focus_text=(it.get("entity") or _il.kw_show(eng[i], _mn) or _mn)[:70])
                        except Exception:
                            pass
                plan.append((pts[j], pts[j + 1], it))
                if j == 0: line_start[len(plan) - 1] = i
                if it.get("credit") and it["credit"] not in credits:
                    credits.append(it["credit"])

        # ---------------- 4) render shots
        log(f"4) {len(plan)} scenes edit kar raha hoon (zoom, flash)...")
        files = []
        eh = int(num(style, "effect_har", 0, 10))
        import motion
        tb = motion.TransitionBank() if yes(style.get("transition", "haan")) else None
        # v2.1: references jaisa – line ke andar seedhe fast cuts; transition sirf jab baat badle
        gap = num(style, "transition_gap", 1.5, 30)
        lo_g, hi_g = max(1.5, gap - 0.5), gap + 0.5
        if tb and tb.all:
            log(f"   transitions: {len(tb.all)} " + ("(lambi video: sirf naya section shuru hone pe)" if LONG
                                                    else f"(har {lo_g:.1f}-{hi_g:.1f} second, clip badalne pe)"))
        else:
            tb = None
        FACT = re.compile(r"(पहला|पहली|दूसरा|दूसरी|तीसरा|तीसरी|चौथा|आखिरी|लेकिन|पर असली|और सुनो|सुनो|फैक्ट|fact)", re.I)
        cycle = [e for e, k in (("punch", "zoom"), ("shake", "shake")) if yes(style.get(k, "haan"))]
        if not tb and yes(style.get("flash", "haan")):
            cycle = ["flash"] + cycle
        effects = []   # (time, effect, sound-flag/transition)
        jobs = []      # v2.18: shots baad me ek saath banenge
        last_tr = -99.0; inner = 0
        INK = []; last_ink = -99.0                   # v2.15: laal ink-splash transition ke time
        try:                                          # v2.17: pro motion recipes (3D photo, card flip, whip...)
            import recipe
            recipe.CARD_EFFECTS["on"] = style.get("card_effects", "nahi")
            _rall = recipe.load_all() if PRO else {}
            _blk = edit_style.fx_blocked(style)              # v3.16: tyohaar pe 'mystery_dust' jaisa effect nahi
            CH = recipe.Chooser(style, {k_: v_ for k_, v_ in _rall.items() if k_ not in _blk})
            if CH.on and CH.r and yes(style.get("effect_director", "haan")):      # v2.17b: line ka matlab/mood
                if qc_round == 0 or DPLAN.get("v") is None:
                    DPLAN["v"] = recipe.director_plan([s_.get("script") or s_["text"] for s_ in sents], CH.r,
                                                      keys.get("GEMINI"), CH.max)
                CH.plan = DPLAN["v"]
                if AIPLAN:                                  # v3.16: aapke AI app ka effect chunav pehle
                    _map = {"3d_photo": "3d_photo", "glow": "cinematic_glow", "punch_zoom": "zoom_hit",
                            "slow_zoom_out": "zoom_out_reveal"}
                    _ap = {i_: _map[x_["effect"]] for i_, x_ in AIPLAN.items()
                           if _map.get(x_.get("effect")) in CH.r and i_ < len(sents) - 1}
                    if _ap: CH.plan = dict(list(_ap.items())[:CH.max])
                if CH.plan is not None:
                    log(f"   🎬 Edit Director ne {len(CH.plan)} jagah effect chune (line ka matlab dekh ke)")
        except Exception as e:
            CH = None; log(f"   (motion effects band: {e})", show=False)
        used_fx = []; plan_look = {}

        def _ai_tr(li):
            return str((AIPLAN.get(li) or {}).get("transition") or "") if li is not None else ""

        def _cur_line(n_):
            ks_ = [k_ for k_ in line_start if k_ <= n_]
            return line_start[max(ks_)] if ks_ else 0
        ink_on = False                               # v2.17: laal ink/dhuan effect hata diya (user: kaam ka nahi)
        ink_gap = num(style, "ink_gap", 3, 60) if style.get("ink_gap") else 8.0
        lo_g, hi_g = max(1.5, gap - 0.5), gap + 0.5      # v2.5: gap=2.5 -> har 2-3 second
        next_gap = random.uniform(lo_g, hi_g)
        # v3.47 PRO J-CUT FLOW: shift visual cut 0.18s earlier on clean sentence starts so video flows smoothly
        if yes(style.get("pro_editing", "haan")) and len(plan) >= 3:
            _jplan = list(plan)
            for _jn in range(1, len(_jplan)):
                if _jn in line_start:
                    _pa, _pb, _pit = _jplan[_jn - 1]
                    _ca, _cb, _cit = _jplan[_jn]
                    _is_card_c = str(_cit.get("src", "")).lower().startswith(("kinetic", "doc", "remotion", "blender", "news", "map", "cloud"))
                    if not _is_card_c and _ca > 2.8 and (_pb - _pa) >= 1.4 and (_cb - _ca) >= 1.2:
                        _shift = 0.14
                        _jplan[_jn - 1] = (_pa, round(_pb - _shift, 3), _pit)
                        _jplan[_jn] = (round(_ca - _shift, 3), _cb, _cit)
            plan = _jplan
        for n, (a, b, it) in enumerate(plan):
            eff = None; trans = None
            t_cut = round(a * render.FPS) / render.FPS
            new_line = n in line_start
            big = new_line and bool(FACT.search(sents[line_start[n]]["text"]))
            # v3.42 PRO DOCUMENTARY PACING: no random flash/transition spam!
            # Clean hard cuts on normal shots; real transitions ONLY at motivated narrative beats (min 6.5s gap)
            # and ALWAYS paired with a clean synced whoosh sound.
            every_cut = yes(style.get("flash_har_clip", "nahi"))
            sec_start = new_line and line_start[n] in {i for i, _ in SECTIONS}
            li_ = line_start.get(n)
            _pro_ed = yes(style.get("pro_editing", "haan"))
            _min_tr_gap = num(style, "transition_min_gap", 2.0, 20.0) if style.get("transition_min_gap") else (6.5 if _pro_ed else 3.0)
            _in_safe_win = (t_cut >= 2.5) and (t_cut <= max(3.0, total - 4.0))
            _scene_shift = False
            if new_line and SCENES and li_ is not None and li_ > 0 and li_ < len(SCENES):
                _prev_m = SCENES[li_ - 1].get("emotion") or SCENES[li_ - 1].get("domain")
                _curr_m = SCENES[li_].get("emotion") or SCENES[li_].get("domain")
                _scene_shift = bool(_curr_m and _curr_m != _prev_m)
            _motivated_beat = new_line and _in_safe_win and (
                sec_start or big or _scene_shift or (_ai_tr(li_) not in ("", "cut"))
            )
            want_ink = ink_on and n > 0 and new_line and (
                any(nm == "ink" for nm, _ in FX.get(li_, [])) or bool(it.get("whole"))
                or (big and not LONG and t_cut - last_ink >= ink_gap))
            if want_ink and t_cut - last_ink >= 2.0:
                INK.append(t_cut); last_ink = t_cut; last_tr = t_cut
                effects.append((t_cut, "mark", "whoosh"))
            elif LONG:
                if sec_start and n > 0 and (t_cut - last_tr >= _min_tr_gap):
                    if tb:
                        trans = dict(tb.pick()); trans["gain"] = 1.0
                        effects.append((t_cut, "transition", trans))
                    last_tr = t_cut
                it = dict(it, kb=True)
            elif n > 0 and _motivated_beat and (t_cut - last_tr >= _min_tr_gap):
                want_tr = None
                if new_line and SCENES and line_start[n] < len(SCENES):
                    want_tr = SCENES[line_start[n]].get("transition")
                if new_line and _ai_tr(li_) == "cut":
                    want_tr = "cut"
                if tb and want_tr != "cut":
                    _tk = (n, str(it.get("path")))
                    trans = dict(PREV_TR[_tk]) if _tk in PREV_TR else dict(tb.pick(want_tr))
                    PREV_TR[_tk] = dict(trans)
                    trans["gain"] = 1.0
                    effects.append((t_cut, "transition", trans))
                    last_tr = t_cut
                elif every_cut and cycle and want_tr != "cut":
                    eff = cycle[0]
                    effects.append((t_cut, eff, "whoosh"))
                    last_tr = t_cut
            rc = None
            if CH and new_line:
                li = line_start[n]; fl = FX.get(li, [])
                forced = next((v for nm, v in fl if nm == "fx" and v), None)
                busy = any(nm in ("label", "bubble", "list", "gola", "map", "news") for nm, _ in fl)
                rc = CH.pick(li, t_cut, sents[li].get("script") or sents[li]["text"], it,
                             who=sources.WHO.get(li), forced=forced, busy=busy)
                if rc and rc["transition"] and trans:           # pro niyam: ek cut pe ek hi transition
                    effects = [e_ for e_ in effects if e_[2] is not trans]; trans = None
                if rc and rc.get("sound") and yes(style.get("effect_sfx", "nahi")):
                    effects.append((t_cut, "mark", rc["sound"]))
            # v3.42: Only script-motivated AI SFX (boom/riser/ding) when no transition is already firing
            if n > 0 and new_line and not trans and AIPLAN.get(li_, {}).get("sfx") in ("impact", "boom", "riser", "ding") \
                    and not any(abs(e_[0] - t_cut) < 2.2 for e_ in effects):
                _sx = {"impact": "boom"}.get(AIPLAN[li_]["sfx"], AIPLAN[li_]["sfx"])
                effects.append((t_cut, "sfx", (_sx, 0.48)))
            if new_line and SCENES and line_start[n] < len(SCENES) and yes(style.get("scene_look", "haan")):
                _sc = SCENES[line_start[n]]                         # v3.1: itihaas = B&W archive, khatra = laal tint
                # v3.16 FIX (log 16 Nov: Chhath Puja ki sunehri shaam B&W ho gayi – Gemini ne 'history' bola tha):
                # B&W archive look sirf jab line me sach me PURANA daur ho (saal <= 1995 / British / azadi /
                # world war / emergency...) aur edit style isse allow kare (tyohaar / tech / science me nahi).
                if _sc.get("domain") == "history" and not it.get("hero") and \
                        edit_style.archive_ok(sents[line_start[n]].get("script") or sents[line_start[n]]["text"],
                                              eng[line_start[n]] if line_start[n] < len(eng) else "", style):
                    it = dict(it, look="archive")
                elif _sc.get("emotion") == "danger": it = dict(it, look="danger")
                plan_look[line_start[n]] = it.get("look")
            elif not new_line and plan_look.get(_cur_line(n)):
                it = dict(it, look=plan_look[_cur_line(n)])
            fa = int(round(a * render.FPS)); fb = int(round(b * render.FPS))
            d = max(2, fb - fa) / render.FPS
            out = work / "shots" / f"shot_{n:03d}.mp4"
            jobs.append((n, it, d, out, eff, trans, rc, line_start.get(n)))
            files.append(out)

        # v2.18: shots EK SAATH (2-3) bante hain – pehle ek-ek karke banta tha (dheema)
        def _shot_key(job):
            n_, it_, d_, out_, eff_, trans_, rc_, li_ = job
            import hashlib as _hl
            keep = {k_: str(v_) for k_, v_ in (it_ or {}).items() if k_ in (
                "kind", "path", "ss", "crop_v", "motion", "kw_behind", "look", "show_name", "seed", "whole", "face", "kb")}
            raw = json.dumps([n_, keep, round(d_, 3), eff_, (trans_ or {}).get("file") and str(trans_.get("file")),
                              (trans_ or {}).get("ss"), (rc_ or {}).get("name"), li_], sort_keys=True, default=str)
            return _hl.md5(raw.encode()).hexdigest()[:16]

        def do_shot(job):
            n_, it_, d_, out_, eff_, trans_, rc_, li_ = job
            _k = _shot_key(job)
            if _k in SHOT_DONE and Path(SHOT_DONE[_k]).exists():   # v3.6: pichhle round ka wahi shot – dobara mat banao
                shutil.copy(SHOT_DONE[_k], out_)
                done_s[0] += 1; REUSED[0] += 1
                return
            _do_shot(job)
            try:
                if Path(out_).exists() and n_ not in SHOT_FAIL:
                    keep_ = Path(out_).with_name(f"done_{_k}.mp4"); shutil.copy(out_, keep_); SHOT_DONE[_k] = str(keep_)
            except Exception:
                pass

        def _do_shot(job):
            n_, it_, d_, out_, eff_, trans_, rc_, li_ = job
            # Optional script-aware Blender scene rendering. Stock footage remains the
            # default; Blender failure safely falls back to the existing renderer.
            r_ = None
            blender_on = yes(style.get("blender3d_purana", "nahi"))   # v3.1: naya engine fallback_visuals.py me
            if blender_on and li_ is not None:
                try:
                    from cine import blender3d as _b3
                    _line = sents[li_].get("script") or sents[li_]["text"]
                    _kind = _b3.visual_type(_line)
                    if _kind != "cinematic":
                        _b_out = _b3.render_scene(out_, duration=d_, resolution=(W, H), kind=_kind)
                        r_ = bool(_b_out)
                        if r_: log(f"   🧊 Blender scene: {_kind} (shot {n_+1})", show=False)
                except Exception as _be:
                    log(f"   Blender fallback shot {n_+1}: {_be}", show=False)
            if not r_ and yes(style.get("resume_checkpoint", "haan")) and Path(out_).exists() and Path(out_).stat().st_size > 8000:
                log(f"   ♻️ shot {n_+1} checkpoint se liya ✓", show=False)
                r_ = out_
            if not r_:
                r_ = render.render_shot(it_, d_, out_, style, n_, eff_, trans_)
            if r_ and rc_ and li_ is not None:
                newp = recipe.apply(rc_, it_, out_, d_, W, H, style, work,
                                    sents[li_].get("script") or sents[li_]["text"], sources.KEYW.get(li_, ""))
                if newp:
                    os.replace(newp, out_); used_fx.append(f"line {li_+1}: {rc_['name']}")
            if not r_:
                card = work / "shots" / f"card_fix_{n_}.jpg"
                render.text_card("", card, W, H, n_)
                render.render_shot({"kind": "image", "path": card}, d_, out_, style, n_)
                log(f"   ⚠️ shot {n_+1} nahi bana – fallback card laga (QC me likha jayega)")
                SHOT_FAIL.append(n_)
            try:                                       # v3.1 SHOT GUARD: exact frames/size/fps – atka frame nahi
                import shotfix
                ok_, _ = shotfix.ensure(out_, max(2, int(round(d_ * render.FPS))), W, H, render.enc_args(style), log)
                if not ok_: SHOT_FAIL.append(n_)
            except Exception as _se:
                log(f"   (shot guard skip: {_se})", show=False)
            done_s[0] += 1
            if done_s[0] % 5 == 0 or done_s[0] == len(jobs):
                log(f"   {done_s[0]}/{len(jobs)} scenes ✓")
        done_s = [0]; SHOT_FAIL = []; REUSED = [0]
        nw = int(num(style, "ek_saath_shots", 1, 4)) if style.get("ek_saath_shots") else \
            max(1, min(3, (os.cpu_count() or 2) // 2))
        if nw > 1:
            from concurrent.futures import ThreadPoolExecutor as _TPE
            with _TPE(max_workers=nw) as ex_:
                list(ex_.map(do_shot, jobs))
        else:
            for j_ in jobs: do_shot(j_)
        if REUSED[0]: log(f"   ⚡ {REUSED[0]}/{len(jobs)} shots pichhle round se wahi rakhe (dobara nahi banaye)")
        if used_fx: log("   🎬 motion effects: " + ", ".join(used_fx))
        try:                                           # v3.6: EDL – har cut ki list (review + DaVinci ke liye)
            import edl as _edl
            EDL_CUTS[:] = _edl.build(plan, line_start, sents, render.SHOT_SS, files, effects)
        except Exception as _ee:
            log(f"   (EDL skip: {_ee})", show=False)
        lst = work / "list.txt"
        lst.write_text("".join(f"file 'shots/{f.name}'\n" for f in files), encoding="utf-8")
        joined = work / "joined.mp4"
        _cam_ok = False
        if yes(style.get("continuous_camera", "nahi")) and len(files) >= 2:
            try:
                from cine import continuous_cam as _ccam
                _cam_ok = _ccam.join_continuous(files, joined, work, style, fps=render.FPS)
            except Exception as _ce:
                log(f"   (continuous cam skip: {_ce})", show=False)
        if not _cam_ok:
            run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", joined.name], cwd=work)

        # ---------------- 5) captions, overlay, audio
        log("5) Captions, logo, sound effects, music laga raha hoon...")
        events = motion.find_events(sents, style, total)
        # v3.61: Suppress duplicate big number/year overlays during doc_stat / doc_news card windows (no 2011 stacked on News Card!)
        _card_wins = [(a_, b_) for (a_, b_, it_) in plan if it_ and any(k in str(it_.get("path", "")) for k in ("doc_stat_", "doc_news_"))]
        if _card_wins and events:
            events = [ev for ev in events if not (ev.get("type") in ("number", "year", "stat") and any((a_ - 0.5) <= float(ev.get("time", -9)) <= (b_ + 0.5) for a_, b_ in _card_wins))]
        try:
            if yes(style.get("emotion_memes", "nahi")) and (not LONG or yes(style.get("long_memes", "nahi"))):
                import emotion_fx as _efx
                _efx.plan_emotion_overlays(sents, total, work, busy=[(s_["start"], s_["end"]) for s_ in sents if any(str(x.get("src", "")).startswith(("kinetic", "map", "blender", "name card")) for x in (found[sents.index(s_)][0] if sents.index(s_) < len(found) else []))])
        except Exception as _efe:
            log(f"   (emotion fx skip: {_efe})", show=False)
        fx_ev = build_fx(sents, events, eng, total, W, H, style, work, joined, keys.get("GEMINI"), INK, PRO)
        if SB and BIBLE and yes(style.get("keyword_text", "haan")):
            try:                                   # v3.1: reference jaisa bada keyword (POISON / 30-35% / naam)
                from cine import kinetic
                own = set()                         # jin lines ka visual khud text dikhata hai -> wahan keyword nahi
                for i_, (its_, _k) in enumerate(found):
                    if any(str(x.get("src", "")).startswith(("kinetic card", "name card", "map", "blender3d"))
                           or x.get("role") == "logo" for x in its_):
                        own.add(i_)
                own |= KW_BEHIND
                seen_kw = set(); SBk = []
                for x in SB:                       # v3.1: ek keyword poori video me EK hi baar (CARRYMINATI x3 nahi)
                    k_ = str(x.get("kw") or "").upper()
                    if x["i"] in own or (k_ and k_ in seen_kw) or (k_ and k_.replace(" ", "") in
                                                                     {e_.upper().replace(" ", "") for e_ in NAME_SHOWN}):
                        SBk.append(dict(x, kw=None))
                    else:
                        SBk.append(x); seen_kw.add(k_)
                # v3.17 FIX (dono videos: "Internet Ka Jhatka" hook + "WORLD", "NVIDIA" naam patti + "12", "JENSEN Huang"
                # slide ke upar – ek saath 2-3 text). PRO NIYAM: screen pe ek waqt EK bada text.
                busy_k = list(NAME_T)
                if yes(style.get("hf_hook", "haan")) or yes(style.get("hook_text", "haan")):
                    busy_k.append((0.0, 3.4))
                # v3.51 ZERO DOUBLE-TEXT FIX: never draw kinetic/number ASS text on top of Documentary/Stat/News/Polaroid cards!
                for _pa, _pb, _pit in plan:
                    _psrc = str((_pit or {}).get("src") or "").lower()
                    _ppath = str((_pit or {}).get("path") or "").lower()
                    if any(k in _psrc or k in _ppath for k in ("kinetic", "doc_", "kcard_", "remotion", "blender", "polaroid", "news", "stat", "card_")):
                        busy_k.append((max(0.0, _pa - 0.15), _pb + 0.15))
                GENERIC = {"WORLD", "DUNIYA", "SHOCKING", "AMAZING", "BIG", "BADA", "BADI", "HUGE", "NEW", "REAL", "TRUTH",
                           "SACH", "SECRET", "MYSTERY", "FACT", "FACTS", "INTERNET", "VIDEO", "PEOPLE", "LOG", "THING",
                           "SURPRISE", "HAIRAAN", "CHAUKANE", "UNBELIEVABLE", "INCREDIBLE", "WOW", "TODAY", "AAJ"}
                SBk = [dict(x, kw=None) if str(x.get("kw") or "").strip().upper() in GENERIC else x for x in SBk]
                kin = kinetic.events(SBk, sents, total, W, H, BIBLE, render.ass_time, style, busy_k)
                fx_ev = list(fx_ev) + kin
                for x in (SBk if yes(style.get("keyword_sfx", "haan")) else []):
                    if x.get("kw") and x["i"] < len(sents):   # v3.1: bade keyword pe saaf DING (boom kharab laga)
                        # v3.45: Script-aware keyword SFX (numbers/money -> click/ding, archival/text -> paper; never random)
                        _ktxt = str(sents[x["i"]].get("script") or sents[x["i"]]["text"] or "")
                        _kw_snd = style.get("keyword_sound") or ("ding" if re.search(r"[0-9०-९₹$%]|करोड़|लाख|मिलियन|बिलियन", _ktxt) else "paper")
                        effects.append((sents[x["i"]]["start"] + 0.08, "sfx", (_kw_snd, 0.38)))
                log(f"   🔤 keyword typography: {sum(1 for x in SBk if x.get('kw'))} lines", show=False)
            except Exception as e:
                log(f"   (keyword typography skip: {e})", show=False)
        if PRO:                                   # v2.15: purane PNG arrow/gola ki jagah naya pro gola
            events = [e for e in events if e["kind"] not in ("arrow", "circle")
                      and (e["kind"] != "x" or yes(style.get("x_nishaan", "nahi")))]     # v2.17: laal ❌ bhi band
        # v3.51: Remove `number` ASS popups that would overlap Documentary/Fact/Stat cards!
        _card_wins = [(max(0.0, _pa - 0.15), _pb + 0.15) for _pa, _pb, _pit in plan
                      if any(k in (str((_pit or {}).get("src") or "").lower() + " " + str((_pit or {}).get("path") or "").lower())
                             for k in ("kinetic", "doc_", "kcard_", "remotion", "blender", "polaroid", "news", "stat", "card_"))]
        events = [e for e in events if not (e["kind"] == "number" and any(e["t0"] < wb and e["t1"] > wa for wa, wb in _card_wins))]
        if events:
            log("   motion graphics: " + ", ".join(e["kind"] for e in events))
        ass = work / "subs.ass"
        hook = (title[:2] if title else None) if yes(style.get("upar_text", "nahi")) else None   # v2.17: upar ka text band
        if not hook and yes(style.get("upar_text", "nahi")):
            w0 = re.sub(r"[।,!?\"'“”]", "", lines[0]).split()
            hook = [" ".join(w0[:4])] + ([" ".join(w0[4:8])] if len(w0) > 4 else [])
        for i, s_ in enumerate(sents):
            if sources.KEYW.get(i): s_["key"] = sources.KEYW[i]
        sec_t = [(sents[i]["start"], nm) for i, nm in SECTIONS if 0 < i < len(sents)]
        cards = sec_t if (LONG and yes(style.get("section_card", "haan"))) else []
        HFH = work / "hook_hf.webm"
        if HFH.exists(): HFH.unlink()
        if title and not LONG and yes(style.get("hf_hook", "haan")) and W < H:   # v3.6: HyperFrames hook title
            try:
                import hf_hook
                from translit import word as _tw
                _t1 = " ".join(_tw(x) for x in title[0].split())
                _t2 = " ".join(_tw(x) for x in (title[1] if len(title) > 1 else title[0]).split())
                if hf_hook.render_hook(_t1, _t2, HFH, hl=sources.KEYW.get(0, "")):
                    hook = None                      # ASS wala upar ka text nahi (do title ek saath nahi)
            except Exception as _he:
                log(f"   (HyperFrames hook skip: {_he})", show=False)
        cap_times = render.write_ass(sents, ass, style, total, events, hook, cards,
                                     endscreen=LONG and yes(style.get("end_screen", "haan")), extra=fx_ev)
        from common import copy_font
        copy_font(render.FONT, work / "fonts" / render.FONT.name)
        for _fn in ("Poppins-ExtraBold.ttf", "Mukta-ExtraBold.ttf", "BebasNeue-Regular.ttf", "Poppins-SemiBold.ttf"):
            if (ASSETS / "fonts" / _fn).exists():            # v3.1: viral caption fonts libass ke liye
                copy_font(ASSETS / "fonts" / _fn, work / "fonts" / _fn)
        overlay = work / "overlay.png"
        render.overlay_png(style, overlay, title)
        audio = work / "mix.wav"
        if SCENES and yes(style.get("scene_sfx", "nahi")):   # v3.1: mood wali sound (riser/shimmer), max 3, awaaz ke neeche
            nsfx = 0
            for li, sc_ in enumerate(SCENES):
                if nsfx >= 3 or li == 0 or li >= len(sents): continue
                if sc_.get("sfx") in ("riser", "shimmer") and not MARKS.get(li):
                    t_ = sents[li]["start"] + (0.0 if sc_["sfx"] == "riser" else 0.1)
                    effects.append((t_, "mark", sc_["sfx"])); nsfx += 1
        for li, names in MARKS.items():
            if li < len(sents):
                for nm in names:
                    effects.append((sents[li]["start"] + 0.05, "mark", nm))
        render.mix_audio(wav, sents, effects, cap_times, style, audio, total, motion.sounds_for(events),
                         [t for t, _ in sec_t] if LONG else [])
        if render.BROKEN_SFX and "mere_sounds ke" not in GEM_NOTE:   # v3.5: kharab sound files (sirf click) – user ko saaf batao
            _bc = sorted({b_.split("/")[0] for b_ in render.BROKEN_SFX})
            log(f"   ⚠️ mere_sounds ki {len(render.BROKEN_SFX)} files kharab (andar sirf ~5 ms awaaz = 'bat' click), "
                f"chhod di: {', '.join(_bc)}")
            GEM_NOTE = (GEM_NOTE + "\n" if GEM_NOTE else "") + (
                f"🔊 mere_sounds ke in folders ki files kharab hain (andar awaaz hi nahi, sirf click): {', '.join(_bc)}. "
                "Pixabay se dobara download karke daalo – tab transition whoosh bhi bajegi.")

        # ---------------- 6) final
        if not name:
            first = re.sub(r"[^\wऀ-ॿ ]", "", lines[0])
            name = f"{datetime.datetime.now():%Y-%m-%d_%H%M}_{safe_name(first, 30)}"
        out = OUT / f"{name}.mp4"
        log("6) Final video bana raha hoon (2-5 minute, neeche % dikhega – band mat karna)...")
        render.final_mux(joined, overlay, ass, audio, out, style, total, work, events)
        # v2.7: check bot – kharab lines ki footage badal ke dobara
        if qc_round >= qc_rounds:
            break
        try:
            import qc
            bad = qc.check(out, sents, keys.get("GEMINI"), work, complaint=os.environ.get("VG_FEEDBACK", ""))
            bad = {i: w for i, w in bad.items() if i not in face_lines and i not in user_assign
                   and not (found[i][0] and found[i][0][0].get("whole"))}
        except Exception as e:
            log(f"   (check bot skip: {e})", show=False); bad = {}
        if not bad:
            break
        log(f"   {len(bad)} line(s) ki footage badal ke dobara bana raha hoon (round {qc_round+1})...")
        done_n[0] = len(sents) - len(bad)
        for i in bad:
            for it in found[i][0]:
                if it.get("url"): sources._used.add(it["url"])
            found[i] = job(i)                  # purani clips _used me hain -> nayi clips aayengi
        if LOCK and yes(style.get("visual_gate", "haan")):
            try:                               # v3.2: badli hui lines ki bhi jaanch
                import visual_verify
                VREP = visual_verify.gate(found, sents, LOCK, keys, style, work, spans, W, H, render.FPS, rounds=1,
                                          only=set(bad), plan_scenes=SCENES)
            except Exception as e:
                log(f"   (visual gate skip: {e})", show=False)
        try:                                   # v3.1: dobara bhi khali -> Blender / kinetic (static card nahi)
            import fallback_visuals
            FALLBACK_SRC.update(fallback_visuals.fill(found, sents, spans, SCENES, style, keys, work, W, H, render.FPS,
                                                      sources.KEYW))
        except Exception as e:
            log(f"   (fallback visuals skip: {e})", show=False)

    try:                                          # v2.15: map ki photo ka credit
        import fx
        for c in sorted(fx.MAP_CREDIT):
            if f"Map – {c}" not in credits: credits.append(f"Map – {c}")
        if fx.MAP_CREDIT and "Map – place data © OpenStreetMap contributors (ODbL)" not in credits:
            credits.append("Map – place data © OpenStreetMap contributors (ODbL)")
    except Exception:
        pass
    # ---------------- v2.17c: QUALITY GATE – bane to sahi bane, warna mat bhejo
    GATE = {"ok": True, "why": []}; QC_REPORT = {}; REVIEW = {}
    try:
        import qc as _qc
        nl = len(sents)
        last_follow = bool(re.search(r"(फॉलो|फोलो|सब्सक्राइब|subscribe|follow)", (sents[-1].get("script") or sents[-1]["text"]).lower()))
        empty = [i for i, (its, _k) in enumerate(found) if not its and not (last_follow and i == nl - 1)]
        cards = [i for i, (its, _k) in enumerate(found) if its and all("card_" in str(x.get("path", "")) for x in its)]
        weak = len(set(empty) | set(cards))
        if nl and weak / nl > num(style, "gate_khali_had", 0.1, 0.9) if style.get("gate_khali_had") else (nl and weak / nl > 0.34):
            GATE["why"].append(f"{weak}/{nl} lines ki sahi footage nahi mili (pichhli clip / text lagana pada)")
        tech = _qc.technical(out, sents)
        if len(tech) >= 2:
            GATE["why"].append(f"{len(tech)} jagah kaala / atka hua shot")
        if _qc.LAST.get("gemini") and _qc.LAST.get("lines") and _qc.LAST["bad"] / _qc.LAST["lines"] > 0.5:
            GATE["why"].append(f"Gemini review: {_qc.LAST['bad']}/{_qc.LAST['lines']} lines ka visual kamzor tha")
        if not sources.CHECK["on"] or (not sources.AANKH["on"] and not keys.get("GEMINI")):
            GATE["why"].append("footage ki jaanch band thi (AI aankh / Gemini dono nahi)")
        if style.get("voice") == "gemini" and os.environ.get("VG_ALLOW_MS") and not (res and not reuse):
            pass
        # v3.1: FINAL MP4 QC (streams, lambai, size, fps, kaala/atka frame, clipping, A/V farak)
        try:
            import final_qc
            last_follow2 = last_follow
            scene_info = [{"line": i + 1, "source": (FALLBACK_SRC.get(i) or ", ".join(sorted({str(x.get("src", "footage"))
                           for x in its})) or ("previous clip" if (last_follow2 and i == nl - 1) else "none"))}
                          for i, (its, _k) in enumerate(found)]
            for i_, sc_ in enumerate(SCENES or []):
                if i_ < len(scene_info): scene_info[i_].update(domain=sc_.get("domain"), want=sc_.get("subject"))
            ok_q, probs, qrep = final_qc.check(out, W, H, total, render.FPS, sents, work / "subs.ass", scene_info,
                                               last_line_ok=not last_follow2)
            if not ok_q and any("lambai" in p_ for p_ in probs) and not qrep.get("probe_failed"):   # v3.5: galat jaanch pe re-encode nahi
                if final_qc.repair(out, audio, total, work):
                    ok_q, probs, qrep = final_qc.check(out, W, H, total, render.FPS, sents, work / "subs.ass",
                                                       scene_info, last_line_ok=not last_follow2)
                    log("   🛠 QC repair: video ki lambai theek ki")
            QC_REPORT.update(qrep)
            QC_REPORT["audio_mix_qa"] = dict(render.MIX_QA)          # v3.5: peak / clipping / chatak (local)
            if EDL_CUTS:
                import edl as _edl
                _base = Path(out).with_suffix("")
                _edl.write(EDL_CUTS, _base, render.FPS, Path(out).stem)
                log(f"   📋 EDL: {len(EDL_CUTS)} cuts ({_base.name}_EDL.edl)")
            try:                                                      # v3.13 (Bug D): asset trace
                import asset_trace as _trace, visual_pick as _vp
                _td = _trace.build(sents, found, plan, files, line_start, EDL_CUTS, _vp.TRACE, sources.REJECTED,
                                   render.FPS)
                _tp = _trace.write(_td, Path(out).with_suffix(""))
                log(f"   🧭 Asset trace: {_trace.one_line(_td)} ({_tp.name})")
                QC_REPORT["trace_summary"] = _td["summary"]
            except Exception as _te:
                log(f"   (asset trace skip: {_te})", show=False)
            try:                                                      # v3.6: VIDEO REVIEW – poori video ki jaanch
                import video_review
                RV = video_review.review(out, EDL_CUTS, sents, work / "subs.ass", W, H, total, style, LOCK)
                REVIEW.update(RV)
                log("   🧐 Video Review: " + video_review.summary(RV))
            except Exception as _re_:
                log(f"   (video review skip: {_re_})", show=False)
            if SHOT_FAIL: probs = probs + [f"{len(SHOT_FAIL)} shot(s) render fail – fallback laga"]
            log("   🧪 Final QC: " + ("PASS ✓" if ok_q and not SHOT_FAIL else "FAIL – " + "; ".join(probs)))
            if not ok_q:
                GATE["why"] += ["QC: " + p_ for p_ in probs]
        except Exception as e:
            log(f"   (final QC skip: {e})", show=False)
        if VREP:
            tgt = num(style, "relevance_target", 50, 100) if style.get("relevance_target") else 95.0
            if VREP.get("relevance_incl_safe_pct", 0) < tgt or VREP.get("failed_lines"):
                GATE["why"].append(f"visual relevance {VREP['relevance_pct']}% (fallback ke saath "
                                   f"{VREP['relevance_incl_safe_pct']}%) < {tgt:.0f}% – fail lines {VREP['failed_lines']}")
        GATE["ok"] = not GATE["why"]
        log("   🧪 Quality gate: " + ("PASS ✓" if GATE["ok"] else "FAIL – " + "; ".join(GATE["why"])))
    except Exception as e:
        log(f"   (quality gate skip: {e})", show=False)
    VREPORT = {}
    try:                                               # v3.66: VISUAL REPORT – har line: samjha kya, chuna kya, kyun
        import visual_brain as _vbw, visual_pick as _vpw
        if _vbw.PLAN:
            _vbw.fact_wait(40)
            _jp, _mp, _vs = _vbw.write_report(Path(out).with_suffix(""), sents, plan, line_start, found, _vpw.TRACE,
                                              sources.REJECTED, VREP)
            VREPORT = {"json": str(_jp), "md": str(_mp), "summary": _vs}
            QC_REPORT["visual_report"] = _vs
            log("   🧾 Visual report: " + _vbw.one_line(_vs) + f" ({_mp.name})")
    except Exception as _vre:
        log(f"   (visual report skip: {_vre})", show=False)
    STYLE_NOTE = ""
    if LEARN.get("visual_badle_har") and not LONG:      # v2.16: bani video seekhe style se mili?
        try:
            import seekho
            STYLE_NOTE = seekho.style_check(out, style.get("visual_badle_har"))
            log("   " + STYLE_NOTE)
        except Exception:
            pass
    # v2.6: title, description, hashtags, thumbnail, upload kit
    kit = None; drive_day = None
    try:
        import meta
        log("7) Thumbnail, title, description bana raha hoon...")
        md = meta.make_meta(keys.get("GEMINI"), lines, script_data, style, credits)
        chapters = []
        if LONG and SECTIONS:
            first = SECTIONS[0][1] if SECTIONS[0][0] == 0 else "शुरुआत"
            chapters = [(0.0, first)] + [(sents[i]["start"], nm) for i, nm in SECTIONS if 0 < i < len(sents)]
        tsrc = []
        for its, _k in found:
            for it in its:
                if it.get("face") or str(it.get("path", "")).find("card_") >= 0 or it.get("src") == "news card": continue
                if (str(it["path"]), it["kind"]) not in tsrc: tsrc.append((str(it["path"]), it["kind"]))
        kit = meta.upload_kit(out, md, credits, style, work, ai_voice=style.get("voice") != "meri", frame_src=joined,
                              chapters=chapters, srcs=tsrc, key=keys.get("GEMINI"),
                              topic=", ".join([e for e in eng[:2] if e] + list(topic_kw)[:2]))
        drive_day = meta.to_drive(out, style)
    except Exception as e:
        log(f"   (upload kit nahi bana: {e})")

    if yes(style.get("edit_kit", "haan")) and render.LAST_FINAL.get("cmd"):
        try:                                           # v3.16: Edit Kit – galat visual khud badlo (CapCut / BADLO folder)
            import edit_kit
            edit_kit.export(out, work, files, plan, line_start, sents, render.FPS, W, H, render.LAST_FINAL, voice_wav=wav)
        except Exception as _eke:
            log(f"   (edit kit nahi bana: {str(_eke)[:120]})", show=False)
    for fn_ in ("VISUAL_RELEVANCE_REPORT.json", "VISUAL_RELEVANCE_REPORT.md", "SCENE_VERIFICATION_REPORT.json",
                "identity_lock.json"):
        try:                                           # v3.2: report video ke saath
            if (work / fn_).exists(): shutil.copy(work / fn_, OUT / f"{name}_{fn_}")
        except Exception:
            pass
    cr = OUT / f"{name}_credits.txt"
    body = ["Description me ye paste kar sakte ho:", "",
            "Visuals: " + ", ".join(sorted({c.split(' – ')[0] for c in credits})) if credits else "Visuals: own graphics", "",
            "Poori list:"] + [f"- {c}" for c in credits]
    if style.get("voice") != "meri":
        body += ["", "Note: is video me AI awaaz hai. Upload ke time YouTube 'altered/synthetic content' ka sawaal poochhe to sach batana."]
    cr.write_text("\n".join(body), encoding="utf-8")

    # cleanup old temp folders (keep last 3)
    olds = sorted([p for p in WORK.glob("2*") if p.is_dir()])[:-3]
    for p in olds: shutil.rmtree(p, ignore_errors=True)

    mins = (time.time() - t0) / 60
    print("\n" + "=" * 56)
    print(f"  VIDEO TAIYAAR!  ({mins:.1f} minute lage)")
    print(f"  {out}")
    print("  output folder khol raha hoon...")
    print("=" * 56 + "\n")
    try:                                               # v3.6: samay ka hisaab (kahan time gaya)
        tot_, parts_ = stage_report()
        log("   ⏱ kul " + f"{tot_/60:.1f} min – " + ", ".join(f"{n_} {t_/60:.1f}" for n_, t_ in parts_[:6] if t_ >= 5))
    except Exception:
        pass
    try:                                               # v3.15: providers ka haal + mahine ka hisaab
        import providers as _pv
        log("   🌐 providers: " + _pv.health_line())
        _m = _pv.save_usage()
        if _m.get("_brave_dollar_estimate"):
            log(f"   🌐 Brave is mahine ~${_m['_brave_dollar_estimate']} ka use (free credit ~$5/mahina)")
    except Exception:
        pass
    log(f"DONE {out}", show=False)
    if os.environ.get("VG_RESULT"):
        base = str(out.with_suffix(""))
        jd = Path(os.environ["VG_RESULT"]).parent / (Path(os.environ["VG_RESULT"]).stem + "_data")
        jd.mkdir(parents=True, exist_ok=True)
        shutil.copy(wav, jd / "voice.wav")
        (jd / "sents.json").write_text(json.dumps(sents, ensure_ascii=False), encoding="utf-8")
        items = {str(i): [{"kind": it["kind"], "path": str(it["path"]), "url": it.get("url"), "credit": it.get("credit", ""),
                           "src": it.get("src", ""), "whole": bool(it.get("whole"))}
                          for it in found[i][0] if not it.get("face")] for i in range(len(found))}
        over = {k: v for k, v in style.items() if k in ("voice",) or (FB and k in FB["style"])}
        if PREV: over = dict(PREV.get("style_over") or {}, **over)
        Path(os.environ["VG_RESULT"]).write_text(json.dumps({
            "video": str(out), "upload": str(kit) if kit else None, "drive": str(drive_day) if drive_day else None,
            "thumbs": [base + x for x in ("_thumbnail_short.jpg", "_thumbnail_ai_short.jpg", "_thumbnail_16x9.jpg",
                                          "_thumbnail_ai_16x9.jpg") if Path(base + x).exists()],
            "minutes": round(mins, 1), "script": str(sp), "items": items, "style_over": over,
            "visual_report": VREPORT.get("md"), "visual_summary": VREPORT.get("summary"),
            "format": style.get("format", "short"), "gate": GATE, "qc": QC_REPORT,
            "review": {k: REVIEW.get(k) for k in ("score", "verdict", "issues", "not_done")} if REVIEW else {},
            "timing": (lambda tp: f"⏱ {tp[0]/60:.1f} min: " + ", ".join(f"{n_} {t_/60:.1f}" for n_, t_ in tp[1][:4] if t_ >= 5))(stage_report()),
            "voice_cache": {"wav": str(jd / "voice.wav"), "sents": str(jd / "sents.json")},
            "note": "\n".join(x for x in ((FB["note"] if FB else ""), GEM_NOTE,
                                           (f"🧠 {LEARN_NOTE} laga" if LEARN else ""), STYLE_NOTE) if x),
            "env": {k: os.environ[k] for k in ("VG_FOOTAGE", "VG_NOTES", "VG_VOICE", "VG_FACE", "VG_STYLE_JSON")
                    if os.environ.get(k)}}, ensure_ascii=False, default=_jsafe), encoding="utf-8")
    if os.name == "nt" and not BOT:
        try: os.startfile(OUT)
        except Exception: pass
    if not GATE["ok"] and yes(style.get("quality_gate", "haan")) and BOT:
        sys.exit(44)                                   # bot video nahi bhejega – wajah + buttons


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        fail(f"{type(e).__name__}: {e}")
