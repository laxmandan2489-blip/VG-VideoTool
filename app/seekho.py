"""v2.16: BOT KHUD SEEKHE – reel / video bhejo (caption: seekho), bot uski editing NAAPTA + Gemini DEKHTA hai,
"Style Yaaddasht" me jodta hai, aur sound effects nikaal ke mere_sounds me rakhta hai.

Copy nahi: har nayi video me saari seekhi hui videos ka MEL lagta hai (beech ki value + thoda badlaav),
aur jo setting aapne khud badli wo hamesha aapki hi chalti hai.

Chalana:  python seekho.py <video> <result.json> [sounds|style|dono]
"""
import os, sys, re, json, random, datetime, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from pathlib import Path
from common import TOOL, log, yes, num, read_keys, read_style, duration, run

MEM = TOOL / "seekha"
MEMF = MEM / "style_yaad.json"
LOCK = MEM / "aapki_settings.json"       # jo setting aapne khud badli – seekha hua usko nahi chhuega
NEWF = MEM / "naye_effects.txt"
KNOWN = ["map", "label", "news", "gola", "bubble", "list", "ink", "light_leak", "flash", "zoom_punch", "shake",
         "number_counter", "photo_3d", "word_captions", "subscribe", "glitch", "blur_background", "progress_bar",
         "slow_zoom", "arrow", "red_cross", "text_hook"]


# ------------------------------------------------------------------ naap-tol (bina AI)
def scene_cuts(video):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(video), "-vf",
                        "scale=320:-2,select='gt(scene,0.28)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace", stdin=subprocess.DEVNULL, timeout=900)
    ts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    out = []
    for t in ts:                                      # ek transition ke kai frame = ek cut
        if not out or t - out[-1] > 0.25: out.append(t)
    return out


def luma_series(video, fps=15):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vf", f"fps={fps},scale=32:18,format=rgb24",
                        "-f", "rawvideo", "-"], capture_output=True, stdin=subprocess.DEVNULL, timeout=900)
    a = np.frombuffer(r.stdout, np.uint8)
    n = len(a) // (32 * 18 * 3)
    return a[:n * 32 * 18 * 3].reshape(n, 18, 32, 3).astype(np.float32), fps


def measure(video):
    d = duration(video) or 1.0
    m = {"dur": round(d, 2)}
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True)
        w, h = [int(x) for x in r.stdout.strip().split(",")[:2]]; m["shape"] = "short" if h > w else "lambi"
    except Exception:
        m["shape"] = "short"
    cuts = scene_cuts(video)
    m["cuts"] = len(cuts); m["shot_sec"] = round(d / (len(cuts) + 1), 2)
    try:
        fr, fps = luma_series(video)
        lum = fr.mean(axis=(1, 2, 3))
        jump = np.diff(lum)
        fl = 0; i = 0
        while i < len(jump) - 4:                         # achaanak roshni upar aur 0.3s me neeche = flash
            if jump[i] > 35 and lum[min(len(lum) - 1, i + 5)] < lum[i + 1] - 20:
                fl += 1; i += 5
            else:
                i += 1
        m["flash_per_min"] = round(fl / d * 60, 1)
        mx = fr.max(axis=3); mn = fr.min(axis=3)
        sat = ((mx - mn) / (mx + 1e-6)).mean()
        m["sat"] = round(float(sat), 3)
        m["contrast"] = round(float(fr.mean(axis=3).std(axis=(1, 2)).mean()), 1)
        m["warm"] = round(float((fr[..., 0] - fr[..., 2]).mean()), 1)
        m["bw"] = bool(sat < 0.08)
    except Exception as e:
        log(f"   (rang naap skip: {e})", show=False)
    try:
        import sfx_grab
        x = sfx_grab._load(video)
        ons, _ = sfx_grab.onsets(x)
        m["sfx_per_min"] = round(len(ons) / d * 60, 1)
    except Exception:
        pass
    return m


# ------------------------------------------------------------------ Gemini dekhe
PROMPT = ("You are a senior short-form video editor. Study this reference video's EDITING STYLE (not its topic) so another "
          "tool can edit NEW videos in the same style (not copy it). Return ONLY JSON:\n"
          '{"captions": {"has": true/false, "position": "upar|beech|neeche", "size": "chhota|medium|bada", '
          '"highlight_color": "peela|hara|laal|neela|safed", "words_at_once": 1-4, "all_caps": true/false},\n'
          ' "pace": "slow|medium|fast", "zoom": "none|slow|punchy", "shake": true/false,\n'
          ' "color_look": "film|teal|natural|bw", "transition_style": "cut|flash|light_leak|ink|glitch|zoom",\n'
          ' "effects_seen": [{"name": one of ' + json.dumps(KNOWN) + ', "count": number}],\n'
          ' "new_effects": [{"name": "short name", "how": "how it looks / how to make it, 1 line", "time": "m:ss"}],\n'
          ' "sound_style": "kam|medium|bahut", "music": "kam|medium|tez",\n'
          ' "tips": ["3-5 short editing rules this video follows, in Hinglish"],\n'
          ' "summary_hinglish": "2 lines in Hinglish: is video ki editing kaisi hai"}\n'
          "new_effects = only effects that are NOT in the known list. Be specific and honest.")


def small_copy(video, work):
    out = Path(work) / "seekho_small.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-t", "150", "-vf", "scale=-2:426,fps=12", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "32", "-c:a", "aac", "-b:a", "48k", "-ac", "1", out])
    return out


def gemini_watch(video, key, work):
    if not key:
        return None
    from ai import ask_json
    try:
        sm = small_copy(video, work)
        if sm.stat().st_size < 14 * 1024 * 1024:
            r = ask_json(key, [PROMPT, {"mp4": sm.read_bytes()}], temperature=0.2, timeout=180, budget=240)
            if isinstance(r, dict) and r.get("captions") is not None:
                r["_how"] = "poori video (awaaz ke saath)"
                return r
    except Exception as e:
        log(f"   (Gemini video nahi dekh paya: {e})", show=False)
    try:                                              # backup: 10 photos
        d = duration(video) or 10
        parts = [PROMPT + "\n(You get 10 frames instead of the video.)"]
        for k in range(10):
            fp = Path(work) / f"sk_{k}.jpg"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d * (k + 0.5) / 10:.2f}", "-i", video, "-frames:v", "1",
                 "-vf", "scale=-2:480", fp])
            parts += [f"Frame at {d * (k + 0.5) / 10:.1f}s:", {"jpg": fp.read_bytes()}]
        r = ask_json(key, parts, temperature=0.2, timeout=120, budget=180)
        if isinstance(r, dict):
            r["_how"] = "10 photos"
            return r
    except Exception as e:
        log(f"   (Gemini photos bhi nahi dekh paya: {e})", show=False)
    return None


# ------------------------------------------------------------------ v2.17: naye effect ki recipe
RECIPE_PROMPT = """You are a motion designer. The reference video shows these effects that our tool does not have yet:
{effects}
Re-create each one (as close as possible) as a RECIPE using ONLY these building blocks:
 depth3d {{push 0-0.35}}  – 2.5D camera push into a photo (parallax)
 card3d {{from/to: rot_x, rot_y, rot_z (deg), scale, x, y}}  – frame as a 3D card that tilts/flips
 whip {{dir: left|right}} – whip-pan motion blur transition (use start 0, dur 0.2-0.3)
 zoomblur {{amount 0-1}} – radial zoom blur hit
 shake {{amount 0-1}}, flash {{color, strength}}, glow {{color, strength}}, colorpop {{sat 0.5-2}},
 vignette {{strength}}, particles {{kind: sparks|dust|embers, amount, color}},
 text3d {{text: "{{number}}" or "{{keyword}}", color, size 0.05-0.3, y 0-1, depth 0-40}}
Every step: {{"block": name, "start": sec, "dur": sec, "ease": "in|out|inout|linear", ...}}.
trigger: list from hook, number, person, place, danger, fact, photo, any – WHEN a pro editor would use it.
use_on: image | video | any.  sound: whoosh|boom|ding|pop|riser|click|glitch or null.
Keep it tasteful – pro editors use effects briefly. If an effect cannot be built from these blocks, skip it.
Return ONLY JSON: {{"recipes": [{{"name": "snake_case", "about": "1 line Hinglish", "use_on": "...", "trigger": [...],
 "sound": "...", "steps": [...]}}]}}"""


def learn_recipes(video, newe, key, work):
    """Gemini naye effects ko blocks ki recipe me likhe -> jaancho -> reel ke frame pe 3 sec demo -> 'pending'."""
    if not key or not newe:
        return []
    from ai import ask_json
    import recipe
    eff = "\n".join(f"- {e.get('name','?')}: {e.get('how','')} (at {e.get('time','')})" for e in newe[:5])
    parts = [RECIPE_PROMPT.format(effects=eff)]
    try:
        sm = Path(work) / "seekho_small.mp4"
        if sm.exists() and sm.stat().st_size < 14 * 1024 * 1024:
            parts.append({"mp4": sm.read_bytes()})
    except Exception:
        pass
    r = ask_json(key, parts, temperature=0.3, timeout=150, budget=200) or {}
    out = []
    pend = MEM / "recipes" / "pending"; pend.mkdir(parents=True, exist_ok=True)
    have = set(recipe.load_all())
    for raw in (r.get("recipes") or [])[:4]:
        rc = recipe.validate(raw)
        if not rc: continue
        if rc["name"] in have: rc["name"] += "_2"
        try:
            d = duration(video) or 10
            fr = Path(work) / f"demo_src_{rc['name']}.jpg"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d * 0.4:.2f}", "-i", video, "-frames:v", "1", "-q:v", "2", fr])
            mp4 = pend / f"{rc['name']}.mp4"
            (Path(work) / "fonts").mkdir(exist_ok=True)
            try:
                from common import copy_font, ASSETS
                copy_font(ASSETS / "fonts" / "VTBaloo.ttf", Path(work) / "fonts" / "VTBaloo.ttf")
            except Exception:
                pass
            recipe.demo(rc, str(fr), mp4, work=work)
            (pend / f"{rc['name']}.json").write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding="utf-8")
            out.append({"name": rc["name"], "about": rc["about"], "video": str(mp4)})
        except Exception as e:
            log(f"   (recipe demo nahi bana {rc['name']}: {e})", show=False)
    return out


def approve(name, ok=True):
    pend = MEM / "recipes" / "pending"; appr = MEM / "recipes" / "approved"; appr.mkdir(parents=True, exist_ok=True)
    j = pend / f"{name}.json"
    if not j.exists(): return False
    if ok:
        j.replace(appr / j.name)
    else:
        j.unlink()
    try: (pend / f"{name}.mp4").unlink()
    except Exception: pass
    return True


# ------------------------------------------------------------------ yaaddasht
def load_mem():
    try:
        return json.loads(MEMF.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_mem(mem):
    MEM.mkdir(parents=True, exist_ok=True)
    MEMF.write_text(json.dumps(mem[-40:], ensure_ascii=False, indent=1), encoding="utf-8")


def lock_keys(keys):
    """botsys.set_style se: aapne khud ye setting badli – seekha hua isko nahi badlega."""
    try:
        cur = set(json.loads(LOCK.read_text(encoding="utf-8"))) if LOCK.exists() else set()
    except Exception:
        cur = set()
    cur |= set(keys)
    MEM.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(sorted(cur)), encoding="utf-8")


def _vote(vals, rnd):
    vals = [v for v in vals if v not in (None, "")]
    if not vals: return None
    from collections import Counter
    c = Counter(vals); top = c.most_common()
    if len(top) > 1 and top[1][1] >= top[0][1] * 0.6 and rnd.random() < 0.3:
        return top[1][0]                                   # kabhi-kabhi doosra andaaz – har video copy jaisi na lage
    return top[0][0]


def learned_style(fmt="short", seed=None):
    """Seekhi hui videos ka MEL -> style overrides (dict). Sirf usi shape (short/lambi) ki videos se."""
    mem = [m for m in load_mem() if (m.get("measure") or {}).get("shape", "short") == fmt] or []
    if not mem:
        return {}, ""
    rnd = random.Random(seed)
    meas = [m["measure"] for m in mem]; gem = [m.get("gemini") or {} for m in mem]
    o = {}
    def med(key):
        v = [x[key] for x in meas if isinstance(x.get(key), (int, float))]
        return float(np.median(v)) if v else None
    jit = lambda v: v * rnd.uniform(0.9, 1.1)
    ss = med("shot_sec")
    pace = _vote([g.get("pace") for g in gem], rnd)
    if ss:
        lo, hi = (1.2, 3.0) if fmt == "short" else (2.5, 7)
        if fmt == "short" and pace == "fast": hi = 2.2
        elif fmt == "short" and pace == "medium": hi = 2.8
        v = round(min(hi, max(lo, jit(ss))), 1)
        o["visual_badle_har" if fmt == "short" else "lambi_clip_har"] = str(v)
        o["transition_gap"] = str(round(min(8, max(1.8, v * rnd.uniform(1.0, 1.4))), 1))
    fpm = med("flash_per_min")
    if fpm is not None:
        if fpm >= 2: o["flash"] = "haan"
        elif len(meas) >= 2: o["flash"] = "nahi"          # band tabhi jab 2+ videos me flash na ho
    caps = [g.get("captions") or {} for g in gem]
    if caps:
        has = _vote([("haan" if c.get("has") else "nahi") for c in caps if "has" in c], rnd)
        if has == "haan" or (has == "nahi" and len(caps) >= 2): o["captions"] = has   # band: 2+ videos se pakka
        p = _vote([c.get("position") for c in caps], rnd)
        if p in ("upar", "beech", "neeche"): o["caption_jagah"] = p
        sz = _vote([c.get("size") for c in caps], rnd)
        if sz in ("chhota", "medium", "bada"):
            o["caption_size"] = str(int({"chhota": 100, "medium": 122, "bada": 145}[sz] * rnd.uniform(0.95, 1.05)))
        col = _vote([c.get("highlight_color") for c in caps], rnd)
        if col in ("peela", "hara", "laal", "neela", "safed"): o["caption_rang"] = col
        w = [int(c["words_at_once"]) for c in caps if str(c.get("words_at_once", "")).isdigit()]
        if w: o["caption_shabd"] = str(int(min(3, max(1, round(float(np.median(w)))))))
        ac = _vote([("haan" if c.get("all_caps") else "nahi") for c in caps if "all_caps" in c], rnd)
        if ac: o["caption_capital"] = ac
    look = _vote([g.get("color_look") for g in gem], rnd)
    if look in ("film", "teal", "natural"): o["color_look"] = look
    zm = _vote([g.get("zoom") for g in gem], rnd)
    if zm == "punchy": o["effect_har"] = str(rnd.choice([2, 3])); o["zoom"] = "haan"
    elif zm == "slow": o["zoom"] = "haan"; o["effect_har"] = "0"
    elif zm == "none": o["effect_har"] = "0"
    sh = _vote([("haan" if g.get("shake") else "nahi") for g in gem if "shake" in g], rnd)
    if sh: o["shake"] = sh
    # effects: jo seekhi videos me baar-baar dikhe, wo zyada
    seen = {}
    for g in gem:
        for e in g.get("effects_seen") or []:
            try: seen[e["name"]] = seen.get(e["name"], 0) + float(e.get("count", 1))
            except Exception: pass
    n = max(1, len(gem))
    if seen:
        o["pro_effects"] = "haan"
        sure = n >= 3                                      # band tabhi karo jab 3+ videos me bilkul na dikhe
        ink = seen.get("ink", 0) / n
        if ink >= 0.5: o["ink_transition"] = "haan"; o["ink_gap"] = str(int(max(4, min(15, 12 - ink * 2))))
        elif sure and ink == 0: o["ink_transition"] = "nahi"
        lb = seen.get("label", 0) / n
        if lb >= 0.5: o["auto_label"] = "haan"
        elif sure and lb == 0: o["auto_label"] = "nahi"
        if seen.get("light_leak", 0) / n >= 1: o["transition"] = "haan"
        if seen.get("number_counter", 0) / n >= 0.5: o["number_counter"] = "haan"
        if seen.get("photo_3d", 0) / n >= 0.5: o["photo_3d"] = "haan"
    spm = med("sfx_per_min")
    snd = _vote([g.get("sound_style") for g in gem], rnd)
    if snd == "bahut" or (spm and spm > 20): o["sfx_awaaz"] = str(rnd.choice([90, 95, 100]))
    elif snd == "kam" or (spm is not None and spm < 6): o["sfx_awaaz"] = "60"
    mus = _vote([g.get("music") for g in gem], rnd)
    if mus in ("kam", "medium", "tez"): o["music_awaaz"] = {"kam": "15", "medium": "22", "tez": "30"}[mus]
    # aapki apni badli settings + correction
    try:
        locked = set(json.loads(LOCK.read_text(encoding="utf-8"))) if LOCK.exists() else set()
    except Exception:
        locked = set()
    o = {k: v for k, v in o.items() if k not in locked}
    corr = load_corr()
    if "visual_badle_har" in o and corr.get("cut_factor"):
        o["visual_badle_har"] = str(round(min(3.0, max(1.0, float(o["visual_badle_har"]) * corr["cut_factor"])), 1))
    note = f"{len(mem)} seekhi hui videos ka mel"
    return o, note


def load_corr():
    try:
        return json.loads((MEM / "sudhaar.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def style_check(video, target):
    """Bani hui video naapo: cut ki speed seekhe hue style se mili? Na mile to agli video ke liye khud sudhaar."""
    try:
        d = duration(video) or 1
        cuts = scene_cuts(video)
        got = d / (len(cuts) + 1)
        want = float(target)
        corr = load_corr(); f = corr.get("cut_factor", 1.0)
        ratio = got / want
        msg = f"Style check: cut har {got:.1f}s (seekha hua {want:.1f}s)"
        if ratio < 0.75:
            msg += " ✓ (lines chhoti hain, isliye cut aur tez – theek hai)"
        elif ratio > 1.35:                                 # video seekhe style se dheemi – agli baar tez
            f = min(1.0, max(0.6, f / ratio))
            corr["cut_factor"] = round(f, 2)
            MEM.mkdir(parents=True, exist_ok=True)
            (MEM / "sudhaar.json").write_text(json.dumps(corr), encoding="utf-8")
            msg += " – farak zyada hai, agli video me khud theek karunga"
        else:
            msg += " ✓"
        return msg
    except Exception as e:
        return f"(style check skip: {e})"


def describe():
    mem = load_mem()
    if not mem:
        return "Abhi kuch nahi seekha. Koi reel bhejo, caption me likho: seekho"
    lines = [f"🧠 {len(mem)} videos se seekha hai:"]
    for fmt in ("short", "lambi"):
        o, note = learned_style(fmt, seed=1)
        if o:
            lines.append(f"\n{'📱 Shorts' if fmt == 'short' else '🖥️ Lambi'} ({note}):")
            lines += [f"• {k} = {v}" for k, v in sorted(o.items())]
    tips = []
    for m in mem[-5:]:
        tips += (m.get("gemini") or {}).get("tips") or []
    if tips:
        lines.append("\n📝 Editing ke niyam:"); lines += [f"• {t}" for t in tips[-6:]]
    if NEWF.exists():
        nl = [l for l in NEWF.read_text(encoding="utf-8").splitlines() if l.strip()]
        if nl:
            lines.append(f"\n🆕 Naye effects (tool me abhi nahi – Claude ko bhejo): {len(nl)}")
            lines += nl[-6:]
    return "\n".join(lines)


def forget():
    if MEMF.exists():
        bk = MEM / f"style_yaad_backup_{datetime.datetime.now():%Y%m%d_%H%M}.json"
        MEMF.replace(bk)
    for f in ("sudhaar.json",):
        try: (MEM / f).unlink()
        except Exception: pass
    return True


# ------------------------------------------------------------------ main (bot chalata hai)
def main():
    video = Path(sys.argv[1]); outp = Path(sys.argv[2]); mode = sys.argv[3] if len(sys.argv) > 3 else "dono"
    style = read_style(TOOL / "style.txt"); keys = read_keys()
    import ai
    try: ai.MAX_TRY["n"] = int(num(style, "gemini_try", 1, 3) or 3) + 1
    except Exception: pass
    work = TOOL / "temp" / f"seekho_{datetime.datetime.now():%Y%m%d_%H%M%S}"; work.mkdir(parents=True, exist_ok=True)
    res = {"ok": True}
    if mode in ("style", "dono"):
        print("1) Video ki editing naap raha hoon (cuts, flash, rang, sound)...", flush=True)
        m = measure(video)
        print(f"   cut har {m.get('shot_sec')}s, flash/min {m.get('flash_per_min')}, sound/min {m.get('sfx_per_min')}", flush=True)
        print("2) Gemini video dekh raha hai...", flush=True)
        g = gemini_watch(video, keys.get("GEMINI"), work)
        print("   Gemini ne dekh li ✓" if g else "   Gemini nahi mila – sirf naap-tol se seekha", flush=True)
        mem = load_mem()
        mem.append({"time": f"{datetime.datetime.now():%Y-%m-%d %H:%M}", "file": video.name, "measure": m, "gemini": g or {}})
        save_mem(mem)
        newe = (g or {}).get("new_effects") or []
        if newe:
            MEM.mkdir(parents=True, exist_ok=True)
            with open(NEWF, "a", encoding="utf-8") as f:
                for e in newe:
                    f.write(f"- {e.get('name','?')}: {e.get('how','')} ({video.name} {e.get('time','')})\n")
        demos = []
        if newe and yes(style.get("recipe_seekho", "haan")):
            print("   naye effects ki recipe bana raha hoon (Gemini) + demo...", flush=True)
            try:
                demos = learn_recipes(video, newe, keys.get("GEMINI"), work)
            except Exception as e:
                log(f"   (recipe seekhna skip: {e})", show=False)
        o, note = learned_style(m.get("shape", "short"), seed=1)
        res["demos"] = demos
        res.update({"measure": m, "summary": (g or {}).get("summary_hinglish", ""), "tips": (g or {}).get("tips") or [],
                    "new_effects": newe, "learned": o, "note": note, "how": (g or {}).get("_how", "naap-tol")})
    if mode in ("sounds", "dono"):
        print("3) Sound effects nikaal raha hoon...", flush=True)
        try:
            import sfx_grab
            snd = sfx_grab.extract(video, keys.get("GEMINI"), work, style)
            res["sounds"] = snd
            if snd:
                pv = sfx_grab.preview(snd, work / "sounds_preview.mp3")
                res["preview"] = str(pv) if pv else None
            print(f"   {len(snd)} sound effects mile ✓", flush=True)
        except Exception as e:
            res["sounds"] = []; res["sound_err"] = str(e)[:200]
            print(f"   sound nahi nikle: {e}", flush=True)
    outp.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            Path(sys.argv[2]).write_text(json.dumps({"ok": False, "err": str(e)[:300]}), encoding="utf-8")
        except Exception:
            pass
        sys.exit(1)
