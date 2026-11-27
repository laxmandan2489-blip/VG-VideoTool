"""v2: transitions (light leak), layers (dust/grain), motion graphics (❌, arrow, circle, big number), subscribe outro.

User folders (VideoTool\\...):
  mere_transitions\\  kaale background wali light-leak / film-burn videos (screen blend)
  mere_layers\\       kaale background wali dust / grain / particles videos (poori video pe halki)
  mere_motion\\       PNG (transparent) jaise red_arrow.png, red_circle.png, aur green screen videos (subscribe)
"""
import random, re, subprocess
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from common import TOOL, log, yes, num

VID = (".mp4", ".mov", ".webm", ".mkv")
IMG = (".png", ".webp")


def files(folder, exts=VID):
    d = TOOL / folder
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in exts)


# ------------------------------------------------------------------ transitions
_peak = {}


def peak_time(path):
    """Time of the brightest frame (so the flash lands on the cut)."""
    if path in _peak:
        return _peak[path]
    t = 0.0
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "scale=32:18,format=gray",
                            "-f", "rawvideo", "-"], capture_output=True, timeout=30)
        a = np.frombuffer(r.stdout, np.uint8)
        n = len(a) // (32 * 18)
        if n:
            m = a[:n * 576].reshape(n, 576).mean(1)
            fps = 30.0
            rr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                 "stream=r_frame_rate", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
            try:
                x, y = rr.stdout.strip().split("/"); fps = float(x) / float(y)
            except Exception:
                pass
            t = int(np.argmax(m)) / fps
    except Exception:
        pass
    _peak[path] = t
    return t


def transition_ok(path):
    """v2.17: sirf light-leak / flash jaisi (kaale background wali) transitions. Paper-cut / safed texture / poora
    rangeen overlay wali files hata do – wo screen-blend me 'paper ki layer' jaisi dikhti hain."""
    import json
    cache_f = TOOL / "temp" / "cache" / "transitions_jaanch.json"
    try:
        cache = json.loads(cache_f.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    key = f"{path.name}|{path.stat().st_size}"
    if key in cache:
        return cache[key]
    ok = True
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf", "fps=6,scale=64:36,format=rgb24",
                            "-f", "rawvideo", "-"], capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        a = np.frombuffer(r.stdout, np.uint8)
        n = len(a) // (64 * 36 * 3)
        if n:
            f = a[:n * 64 * 36 * 3].reshape(n, 36, 64, 3).astype(np.float32)
            lum = f.mean(axis=3); mx = f.max(axis=3); mn = f.min(axis=3)
            sat = (mx - mn) / (mx + 1e-6)
            paper = ((lum > 165) & (sat < 0.20)).mean(axis=(1, 2))         # safed/gray kaagaz
            ml = float(np.median(lum.mean(axis=(1, 2))))
            ok = not (ml > 85 or (paper > 0.22).sum() >= max(2, n // 4))
    except Exception:
        ok = True
    cache[key] = ok
    try:
        cache_f.parent.mkdir(parents=True, exist_ok=True); cache_f.write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass
    if not ok:
        log(f"   transition hata di (paper/safed/bhari overlay): {path.name}", show=False)
    return ok


class TransitionBank:
    def __init__(self):
        allf = files("mere_transitions")
        self.all = [p for p in allf if transition_ok(p)]      # v2.17: paper-cut jaisi files nahi
        self.bag = []

    KIND = {"light_leak": ("light_leak", "leak", "glow"), "flash": ("flash",),
            "fade": ("film", "projector", "celluloid", "retro", "melt", "light_leak"),
            "whip": ("pack_",), "glitch": ("glitch", "flash", "pack_"), "zoom": ("pack_", "flash")}

    def pick(self, kind=None):
        """v3.1: scene ke mood wala transition (light_leak / flash / fade / whip / glitch), lagaataar same file nahi."""
        if not self.all:
            return None
        if kind in self.KIND:
            pool = [p for p in self.all if any(k in p.stem.lower() for k in self.KIND[kind])]
            pool = [p for p in pool if p != getattr(self, "_last", None)] or pool
            if pool:
                p = random.choice(pool); self._last = p
                if p in self.bag: self.bag.remove(p)
                return {"file": p, "ss": max(0.0, peak_time(p) - 0.12)}
        if not self.bag:
            self.bag = [p for p in self.all if p != getattr(self, "_last", None)] or self.all[:]
            random.shuffle(self.bag)
        p = self.bag.pop(); self._last = p
        ss = max(0.0, peak_time(p) - 0.12)
        return {"file": p, "ss": ss}


# ------------------------------------------------------------------ motion events from script words
NO_WORDS = ("बंद", "मना", "बैन", "प्रतिबंध", "गैरकानूनी", "गैर-कानूनी", "नामुमकिन", "असंभव", "झूठ", "गलत", "रोक")
DANGER = ("खतरनाक", "खतरा", "जहर", "ज़हर", "जहरीला", "जहरीली", "ज़हरीली", "मौत", "मर", "जानलेवा", "डरावना", "डरावनी", "खौफनाक")
MULT = ("सौ", "हजार", "हज़ार", "लाख", "करोड़", "करोड", "अरब", "मिलियन", "बिलियन", "प्रतिशत", "परसेंट", "%")
UNITS = ("गुना", "साल", "सालों", "किलो", "किलोमीटर", "मीटर", "फीट", "डिग्री", "नैनोमीटर", "रुपये", "रुपए", "लोग",
         "लोगों", "दिन", "घंटे", "मिनट", "सेकंड", "टन", "प्रजाति") + MULT
FOLLOW = ("फॉलो", "फोलो", "सब्सक्राइब", "subscribe", "follow")


def _clean(w):
    return re.sub(r"[।,.!?\"'“”‘’()]", "", w)


def find_events(sents, style, total):
    """Return list of motion events: {kind, t0, t1, text?}."""
    if not yes(style.get("motion", "nahi")):
        return []
    ev = []
    gap = num(style, "motion_gap", 1, 15)
    last = -99
    for si, s in enumerate(sents):
        words = s["words"]
        is_last = si == len(sents) - 1
        if is_last and yes(style.get("subscribe_end", "haan")) and any(f in s["text"].lower() for f in FOLLOW):
            continue          # outro handles it
        done = False
        for i, w in enumerate(words):
            if done: break
            c = _clean(w["w"])
            if not c: continue
            t = w["start"]
            if t - last < gap: continue
            has_num = bool(re.search(r"[0-9०-९]", c))
            _nxt = _clean(words[i + 1]["w"]) if i + 1 < len(words) else ""
            if has_num and (re.search(r"(वीं|वी|वां|वा|वें|th|st|nd|rd)$", c, re.I) or
                            re.match(r"(सदी|शताब्दी|century|centuries)", _nxt or "", re.I)):
                continue      # v5.1: "19वीं सदी" ginti nahi (pehle laal "14 -> 19" counter aa jaata tha)
            if has_num or c in MULT:
                a = i - 1 if (c in MULT and i > 0 and not has_num) else i
                b = i
                while b + 1 < len(words) and _clean(words[b + 1]["w"]) in UNITS and b - a < 2:
                    b += 1
                txt = " ".join(_clean(x["w"]) for x in words[a:b + 1])
                ev.append({"kind": "number", "t0": words[a]["start"], "t1": min(total, words[a]["start"] + 1.3),
                           "text": txt})
                last = t; done = True
            elif c.startswith(NO_WORDS) and len(c) <= len(max(NO_WORDS, key=len)) + 3:
                ev.append({"kind": "x", "t0": t, "t1": min(total, t + 1.0)}); last = t; done = True
            elif c.startswith(DANGER) and c not in ("मरना",) and yes(style.get("pointer_highlight", "nahi")):
                kind = "arrow" if sum(e["kind"] in ("arrow", "circle") for e in ev) % 2 == 0 else "circle"
                ev.append({"kind": kind, "t0": t, "t1": min(total, t + 1.1)}); last = t; done = True
    if yes(style.get("subscribe_end", "haan")) and sents and files("mere_motion", VID):
        s = sents[-1]
        if any(f in s["text"].lower() for f in FOLLOW) or yes(style.get("subscribe_hamesha", "nahi")):
            ev.append({"kind": "subscribe", "t0": max(0, s["start"] - 0.1), "t1": total})
    return ev


# ------------------------------------------------------------------ PNG assets
def red_x(path, size=520):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    m = int(size * 0.12); w = int(size * 0.16)
    for col, ww in (((0, 0, 0, 255), w + 22), ((235, 20, 20, 255), w)):
        d.line([(m, m), (size - m, size - m)], fill=col, width=ww)
        d.line([(size - m, m), (m, size - m)], fill=col, width=ww)
    im.save(path); return path


def motion_png(kind, work):
    want = {"arrow": "arrow", "circle": "circle", "x": "cross"}[kind]
    cands = [p for p in files("mere_motion", IMG) if want in p.stem.lower() or (kind == "x" and "x" == p.stem.lower()[-1:])]
    if cands:
        return random.choice(cands)
    if kind == "x":
        p = work / "red_x.png"
        return p if p.exists() else red_x(p)
    if kind == "circle":
        p = work / "red_circle.png"
        if not p.exists():
            im = Image.new("RGBA", (520, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.ellipse((20, 20, 500, 500), outline=(235, 20, 20, 255), width=26); im.save(p)
        return p
    return None


def key_color(video):
    """Read the green-screen colour from the top-left corner of the first frame."""
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", "crop=8:8:4:4,scale=1:1",
                            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=20)
        c = r.stdout[:3]
        if len(c) == 3 and c[1] > 150 and c[1] > c[0] + 60:
            return "0x%02X%02X%02X" % (c[0], c[1], c[2])
    except Exception:
        pass
    return "0x00FF00"


# ------------------------------------------------------------------ ffmpeg graph pieces for final_mux
def build(events, style, W, H, FPS, total, work, first_input):
    """Returns (extra_input_args, filter_text_fn, sounds). filter_text_fn(last_label)->(chain, new_label)."""
    inputs = []; parts = []; sounds = []
    idx = first_input
    S = int(W * 0.42)

    def pop_scale(t0, base):
        # pop: 0.3 -> 1.15 -> 1.0 ; uses global t
        tt = f"max(0,t-{t0:.3f})"
        return f"{base}*if(lt({tt},0.12),0.3+0.85*{tt}/0.12,if(lt({tt},0.24),1.15-0.15*({tt}-0.12)/0.12,1))"

    # ---- layer (poori video pe)
    layer = None
    if yes(style.get("layer", "haan")):
        lf = files("mere_layers")
        try:                                       # v3.16: vishay ke hisaab se layer (tyohaar pe purani film scratch nahi)
            import edit_style
            lf2 = [f for f in lf if edit_style.layer_ok(f.stem, style)]
            if lf and not lf2:
                log(f"   layer: koi '{style.get('_genre')}' ke laayak layer nahi – bina layer (saaf)", show=False)
            lf = lf2
        except Exception:
            pass
        if lf and float(num(style, "layer_taakat", 0, 100)) > 0:
            layer = random.choice(lf)
            inputs += ["-stream_loop", "-1", "-i", str(layer)]
            op = num(style, "layer_taakat", 0, 100) / 100
            parts.append(("layer", idx, op)); idx += 1

    for e in events:
        k = e["kind"]; t0, t1 = e["t0"], e["t1"]; d = max(0.3, t1 - t0)
        if k in ("x", "arrow", "circle"):
            png = motion_png(k, work)
            if not png: continue
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(png)]
            parts.append(("png", idx, e, png)); idx += 1
            sounds.append(("wrong" if k == "x" else "click", t0 + 0.02, 0.5))
            if k != "x": sounds.append(("whoosh", t0, 0.3))
        elif k == "number":
            sounds.append(("pop", t0 + 0.02, 0.45)); sounds.append(("whoosh", t0 - 0.05, 0.3))
        elif k == "subscribe":
            sv = files("mere_motion", VID)
            sub = next((p for p in sv if "sub" in p.stem.lower() and "pro" in p.stem.lower()), next((p for p in sv if "sub" in p.stem.lower()), sv[0]))
            inputs += ["-t", f"{d + 0.2:.3f}", "-i", str(sub)]
            parts.append(("sub", idx, e, sub)); idx += 1
            sounds.append(("@file", t0, 0.8, sub))

    def chain(last):
        out = []; cur = last; n = 0
        for p in parts:
            n += 1; lab = f"m{n}"
            if p[0] == "layer":
                _, i, op = p
                # v2.1 speed: sirf roshni (luma) pe screen blend, rang waise hi -> ~2.5 guna tez, dikhne me same
                out.append(f"[{i}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=fast_bilinear,"
                           f"crop={W}:{H},format=yuv420p[ly];[{cur}]format=yuv420p[bs];"
                           f"[bs][ly]blend=c0_mode=screen:c0_opacity={op:.2f}:c1_mode=normal:c2_mode=normal:"
                           f"shortest=1[{lab}]")
            elif p[0] == "png":
                _, i, e, png = p
                k = e["kind"]; t0 = e["t0"]
                base = {"x": S * 1.1, "circle": S * 1.25, "arrow": S * 0.75}[k]
                if k == "arrow":
                    xx, yy = f"{W*0.30:.0f}-w/2", f"{H*0.55:.0f}-h/2"   # neeche-left se beech ki taraf
                else:
                    xx, yy = f"{W/2:.0f}-w/2", f"{H*0.42:.0f}-h/2"
                wexp = pop_scale(t0, f"{base:.0f}")
                out.append(f"[{i}:v]format=rgba,setpts=PTS-STARTPTS+{t0:.3f}/TB,"
                           f"scale=w='{wexp}':h=-1:eval=frame[pg{n}];"
                           f"[{cur}][pg{n}]overlay=x='{xx}':y='{yy}':eval=frame:eof_action=pass[{lab}]")
            elif p[0] == "sub":
                _, i, e, sub = p
                kc = key_color(sub)
                sz = float(style.get("subscribe_size", "1.2") or 1.2)
                if W > H:                                   # v2.11 lambi video: button beech me, sahi size
                    sh = int(H * 0.75 * sz) // 2 * 2
                    out.append(f"[{i}:v]scale=-2:{sh},fps={FPS},"
                               f"colorkey={kc}:0.30:0.10,despill=green,setpts=PTS-STARTPTS+{e['t0']:.3f}/TB[sb{n}];"
                               f"[{cur}][sb{n}]overlay=(W-w)/2:(H-h)/2+{int(H*0.12)}:eof_action=pass[{lab}]")
                else:
                    sw = int(W * sz) // 2 * 2               # v2.5: bada button
                    out.append(f"[{i}:v]scale={sw}:-2,crop={W}:{H},fps={FPS},"
                               f"colorkey={kc}:0.30:0.10,despill=green,setpts=PTS-STARTPTS+{e['t0']:.3f}/TB[sb{n}];"
                               f"[{cur}][sb{n}]overlay=0:-{int(H*0.12)}:eof_action=pass[{lab}]")
            cur = lab
        return ";".join(out), cur

    if layer: log(f"   layer: {layer.name}", show=False)
    return inputs, chain, sounds


def sounds_for(events):
    """(category, time, gain[, file]) for every motion event."""
    out = []
    for e in events:
        k, t0 = e["kind"], e["t0"]
        if k == "x": out.append(("wrong", t0 + 0.02, 0.5))
        elif k in ("arrow", "circle"): out += [("click", t0 + 0.02, 0.5), ("whoosh", t0, 0.3)]
        elif k == "number": pass                     # v2.17: number pe ding (render.mix_audio), pop/whoosh nahi
        elif k == "subscribe":
            sv = files("mere_motion", VID)
            if sv:
                sub = next((p for p in sv if "sub" in p.stem.lower() and "pro" in p.stem.lower()), next((p for p in sv if "sub" in p.stem.lower()), sv[0]))
                out.append(("@file", t0, 0.8, sub))
    return out


def number_ass_events(events, W, H, ass_time, hw=None, upper=True, counter=True):
    """Big 3D-style yellow text for numbers (ASS lines, style 'Big')."""
    out = []
    for e in events:
        if e["kind"] != "number": continue
        t = e["text"]
        if hw: t = " ".join(hw(x) for x in t.split())
        if upper: t = t.upper()
        t = t.replace("{", "").replace("}", "")
        pop = "{\\fscx40\\fscy40\\t(0,120,\\fscx112\\fscy112)\\t(120,220,\\fscx100\\fscy100)}"
        pos = "{\\an5\\pos(" + f"{W//2},{int(H*0.40)}" + ")}"
        m = re.search(r"\d[\d,]*(?:\.\d+)?", t)
        if counter and m and e["t1"] - e["t0"] > 0.9:
            # v2.14: number 0 se badhta hua (counter), phir asli number par ruk jaata hai
            raw = m.group(0); val = float(raw.replace(",", "")); dec = len(raw.split(".")[1]) if "." in raw else 0
            steps = 12; dur = min(0.7, (e["t1"] - e["t0"]) * 0.45)
            for k in range(steps):
                v = val * (1 - (1 - (k + 1) / steps) ** 3)          # ease-out
                txt = f"{v:,.{dec}f}" if "," in raw else f"{v:.{dec}f}"
                a = e["t0"] + dur * k / steps; b = e["t0"] + dur * (k + 1) / steps
                out.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Big,,0,0,0,,{pos}"
                           + (pop if k == 0 else "") + t[:m.start()] + txt + t[m.end():])
            out.append(f"Dialogue: 1,{ass_time(e['t0'] + dur)},{ass_time(e['t1'])},Big,,0,0,0,,{pos}"
                       "{\\fscx108\\fscy108\\t(0,120,\\fscx100\\fscy100)}" + t)
            continue
        out.append(f"Dialogue: 1,{ass_time(e['t0'])},{ass_time(e['t1'])},Big,,0,0,0,,"
                   + pos + pop + t)
    return out
