"""v2.17: PRO MOTION – effect "recipe" (JSON) = building blocks ki list. Code nahi badalta, sirf recipe.

Recipe:
{"name": "card_flip", "about": "photo 3D me ghoom ke aati hai", "use_on": "image|video|any",
 "trigger": ["person", "place"], "transition": false, "sound": "whoosh",
 "steps": [{"block": "card3d", "start": 0, "dur": 0.55, "from": {"rot_y": -65, "scale": 0.75},
            "to": {"rot_y": 0, "scale": 0.96}, "ease": "out"}]}

Blocks: depth3d, card3d, whip, zoomblur, shake, flash, glow, colorpop, vignette, particles, text3d
Triggers: hook, number, person, place, danger, fact, photo, any
Pro niyam: video me max `recipe_max` (4), 5 sec gap, ek hi effect lagaataar nahi, map/news/chehra/graphics wali
line pe nahi. Kuch bhi fail -> normal shot (video kabhi nahi rukti).
"""
import json, math, random, re, subprocess
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops
from common import TOOL, log, yes, num

BUILTIN = Path(__file__).resolve().parent / "recipes"
LEARNED = TOOL / "seekha" / "recipes"
BLOCKS = {"depth3d", "card3d", "whip", "zoomblur", "shake", "flash", "glow", "colorpop", "vignette", "particles", "text3d"}
TRIGGERS = {"hook", "number", "person", "place", "danger", "fact", "photo", "any"}
PROPS = {"rot_x": (-85, 85), "rot_y": (-85, 85), "rot_z": (-30, 30), "scale": (0.3, 2.0), "x": (-0.5, 0.5),
         "y": (-0.5, 0.5), "opacity": (0, 1)}
FPS = 30


def _hex(c, default=(255, 255, 255)):
    try:
        c = str(c).lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def _cl(v, lo, hi, d):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return d


# ------------------------------------------------------------------ recipe padhna / jaanchna
def validate(r):
    """Gemini / file ki recipe saaf karo – sirf jaane-pehchaane blocks, number had me. None = bekaar."""
    if not isinstance(r, dict): return None
    name = re.sub(r"[^a-z0-9_]", "_", str(r.get("name", "")).lower()).strip("_")[:30]
    if not name: return None
    steps = []
    for s in (r.get("steps") or [])[:8]:
        if not isinstance(s, dict) or s.get("block") not in BLOCKS: continue
        st = {"block": s["block"], "start": _cl(s.get("start", 0), 0, 3, 0), "dur": _cl(s.get("dur", 0.4), 0.05, 6, 0.4),
              "ease": s.get("ease") if s.get("ease") in ("in", "out", "inout", "linear") else "out"}
        for k in ("from", "to"):
            st[k] = {p: _cl(v, *PROPS[p], 0) for p, v in (s.get(k) or {}).items() if p in PROPS}
        for k, (lo, hi, d) in {"amount": (0, 1, 0.3), "push": (0, 0.35, 0.12), "strength": (0, 1, 0.4),
                                "sat": (0.5, 2, 1.25), "size": (0.03, 0.4, 0.13), "y": (0.05, 0.95, 0.4),
                                "depth": (0, 40, 14)}.items():
            if k in s: st[k] = _cl(s[k], lo, hi, d)
        for k in ("color", "kind", "dir", "text"):
            if k in s: st[k] = str(s[k])[:40]
        steps.append(st)
    if not steps: return None
    trig = [t for t in (r.get("trigger") or ["any"]) if t in TRIGGERS] if isinstance(r.get("trigger"), list) else \
        ([r["trigger"]] if r.get("trigger") in TRIGGERS else ["any"])
    return {"name": name, "about": str(r.get("about", ""))[:120],
            "use_on": r.get("use_on") if r.get("use_on") in ("image", "video", "any") else "any",
            "trigger": trig or ["any"], "transition": bool(r.get("transition")) or any(
                s["block"] in ("whip", "zoomblur") and s["start"] < 0.1 for s in steps),
            "sound": r.get("sound") if r.get("sound") in ("whoosh", "boom", "ding", "pop", "riser", "click", "glitch") else None,
            "steps": steps}


CARD_EFFECTS = {"on": "nahi"}


def load_all():
    out = {}
    for d in (BUILTIN, LEARNED / "approved"):
        if not d.exists(): continue
        for p in sorted(d.glob("*.json")):
            try:
                r = validate(json.loads(p.read_text(encoding="utf-8")))
                if r: out[r["name"]] = r
            except Exception:
                continue
    if str(CARD_EFFECTS.get("on", "nahi")).lower() not in ("haan", "yes", "1"):
        # v3.2: user feedback – photo/video ka "frame ke andar chhota card" (card3d) look pasand nahi
        for n in [k for k, r in out.items() if any(st.get("block") == "card3d" for st in r.get("steps", []))]:
            out.pop(n, None)
        out.pop("danger_sparks", None)              # "aankh / aag" jaisa decorative effect – subject nahi badalna
    off = LEARNED / "band.txt"
    if off.exists():
        for n in off.read_text(encoding="utf-8").split():
            out.pop(n.strip(), None)
    return out


# ------------------------------------------------------------------ kab lagana (pro niyam)
DANGER = ("खतरनाक", "खतरा", "जहर", "ज़हर", "मौत", "जानलेवा", "डरावना", "विस्फोट", "धमाका", "तबाही", "आग")
FACT = re.compile(r"(पहला|पहली|दूसरा|दूसरी|तीसरा|तीसरी|लेकिन|असली|ट्विस्ट|सुनो|सोचो)")


def director_plan(lines, recipes, key, maxn=4):
    """v2.17b: Gemini (Edit Director) har line ka MATLAB + MOOD samajh ke tay kare kahan kaunsa effect.
    Returns {line_index: name} ya None (Gemini nahi mila -> purane niyam)."""
    if not key or not recipes or not lines:
        return None
    try:
        from ai import ask_json
        cat = "\n".join(f"- {n}: {r.get('about','')} (works on: {r['use_on']})" for n, r in recipes.items())
        numbered = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
        prompt = ("You are a senior PRO video editor for viral Hindi fact Shorts. Decide where (if anywhere) to use a "
                  "motion effect. Understand each line's MEANING and MOOD (shock, mystery, sad, calm, hype, reveal, "
                  "twist, danger, wonder). Pro rules: effects must be MOTIVATED by the story; use at most "
                  f"{maxn} in the whole video, never two lines in a row, never the same effect twice in a row; calm / "
                  "sad / emotional lines get NO flashy effect (or only a gentle one like a slow 3D photo); the strongest "
                  "effect goes to the hook or the biggest reveal; the last line (follow / subscribe) gets none.\n\n"
                  "Available effects:\n" + cat + "\n\nScript lines:\n" + numbered + "\n\n"
                  'Return ONLY JSON: {"plan": [{"line": number, "effect": "name or none", "mood": "1 word", "why": "short"}]}')
        r = ask_json(key, [prompt], temperature=0.3, timeout=90, budget=120)
        if not isinstance(r, dict) or not isinstance(r.get("plan"), list):
            return None
        out = {}; last_line = -9; last_name = None
        for x in sorted(r["plan"], key=lambda x: int(x.get("line", 0)) if str(x.get("line", "")).isdigit() else 0):
            try:
                i = int(x["line"]) - 1; nm = str(x.get("effect", "none")).strip()
            except Exception:
                continue
            if nm not in recipes or not (0 <= i < len(lines) - 1): continue
            if i - last_line < 2 or nm == last_name or len(out) >= maxn: continue     # niyam khud bhi pakke
            out[i] = nm; last_line = i; last_name = nm
            log(f"   Edit Director: line {i+1} [{x.get('mood','')}] -> {nm} ({str(x.get('why',''))[:50]})", show=False)
        return out
    except Exception as e:
        log(f"   (Edit Director plan skip: {e})", show=False)
        return None


class Chooser:
    def __init__(self, style, recipes, seed=None):
        self.on = yes(style.get("recipe_on", "haan"))
        self.max = int(num(style, "recipe_max", 0, 10)) if style.get("recipe_max") else 4
        self.gap = num(style, "recipe_gap", 2, 30) if style.get("recipe_gap") else 5.0
        self.r = recipes; self.used = 0; self.last_t = -99; self.last = None
        self.rnd = random.Random(seed)
        self.plan = None                    # v2.17b: Edit Director ka plan {line: naam}

    def pick(self, i, t, text, item, who=None, forced=None, busy=False):
        if not self.on or not self.r: return None
        if forced:
            return self.r.get(forced)
        if self.plan is not None:           # Gemini ne matlab samajh ke tay kiya – wahi chalega
            nm = self.plan.get(i)
            rc = self.r.get(nm) if nm else None
            if not rc or busy or item.get("whole") or item.get("face") or self.used >= self.max:
                return None
            kind = "image" if item.get("kind") == "image" else "video"
            if rc["use_on"] not in ("any", kind):
                alt = [r for r in self.r.values() if r["use_on"] in ("any", kind) and set(r["trigger"]) & set(rc["trigger"])
                       and r["name"] != self.last]
                rc = alt[0] if alt else None
                if not rc: return None
            self.used += 1; self.last_t = t; self.last = rc["name"]
            return rc
        if busy or item.get("whole") or item.get("face") or self.used >= self.max or t - self.last_t < self.gap:
            return None
        kind = "image" if item.get("kind") == "image" else "video"
        trig = {"any"}
        if i == 0: trig.add("hook")
        if re.search(r"[0-9०-९]", text): trig.add("number")
        if who: trig |= {"person", "place"}
        if any(w in text for w in DANGER): trig.add("danger")
        if FACT.search(text): trig.add("fact")
        if kind == "image": trig.add("photo")
        cands = [r for r in self.r.values() if r["use_on"] in ("any", kind) and r["name"] != self.last
                 and (set(r["trigger"]) & trig) and (set(r["trigger"]) != {"any"} or self.rnd.random() < 0.15)]
        if not cands: return None
        # khaas trigger (hook/number/danger...) wali recipe pehle, "any" wali kam
        cands.sort(key=lambda r: -len((set(r["trigger"]) & trig) - {"any", "photo"}))
        top = [c for c in cands if len((set(c["trigger"]) & trig) - {"any", "photo"}) ==
               len((set(cands[0]["trigger"]) & trig) - {"any", "photo"})]
        rc = self.rnd.choice(top)
        self.used += 1; self.last_t = t; self.last = rc["name"]
        return rc


# ------------------------------------------------------------------ chhote helpers
def ease(p, kind="out"):
    p = max(0.0, min(1.0, p))
    if kind == "in": return p * p
    if kind == "linear": return p
    if kind == "inout": return p * p * (3 - 2 * p)
    return 1 - (1 - p) ** 3


def _lerp(a, b, p): return a + (b - a) * p


def _coeffs(dst, src):
    """PIL PERSPECTIVE: output ke 4 kone (dst) -> input ke kone (src)."""
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, dtype=np.float64), np.array(B, dtype=np.float64)).tolist()


def _project(w, h, W, H, rx, ry, rz, sc, ox, oy):
    f = 1.8 * max(W, H)
    cx, cy = W / 2 + ox * W, H / 2 + oy * H
    pts = []
    for x, y in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x *= sc; y *= sc; z = 0.0
        a = math.radians(rz); x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        a = math.radians(ry); x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
        a = math.radians(rx); y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
        k = f / (f + z)
        pts.append((cx + x * k, cy + y * k))
    return pts


def _vals(st, p):
    e = ease(p, st.get("ease", "out"))
    keys = set(st.get("from", {})) | set(st.get("to", {}))
    base = {"rot_x": 0, "rot_y": 0, "rot_z": 0, "scale": 1, "x": 0, "y": 0, "opacity": 1}
    return {k: _lerp(st.get("from", {}).get(k, st.get("to", {}).get(k, base[k])),
                     st.get("to", {}).get(k, st.get("from", {}).get(k, base[k])), e) for k in keys | set(base)}


# ------------------------------------------------------------------ renderer
class Ctx:
    def __init__(self, W, H, work, text="", number="", keyword=""):
        self.W, self.H, self.work = W, H, Path(work)
        self.text, self.number, self.keyword = text, number, keyword
        self.cache = {}


def _frames_from_video(path, W, H, n):
    # v3.1: -stream_loop -1 -> shot chhota ho to shuru se dobara chalega (pehle aakhri frame atak jaata tha)
    p = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-stream_loop", "-1", "-i", str(path), "-vf",
                          f"scale={W}:{H}", "-frames:v", str(n), "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    sz = W * H * 3; last = None
    for _ in range(n):
        b = p.stdout.read(sz)
        if len(b) == sz:
            last = Image.frombytes("RGB", (W, H), b)
        if last is None:
            last = Image.new("RGB", (W, H))
        yield last
    try: p.kill()
    except Exception: pass


def _cover(im, W, H, over=1.0):
    r = max(W / im.width, H / im.height) * over
    x = im.resize((max(W, int(im.width * r) + 1), max(H, int(im.height * r) + 1)), Image.LANCZOS)
    l = (x.width - W) // 2; t = (x.height - H) // 2
    return x.crop((l, t, l + W, t + H))


def _depth_frame(ctx, st, t, dur, img):
    """Asli 2.5D: photo ki parten – paas wali tez badi hoti hain, door wali dheere -> camera andar jaata lage."""
    W, H = ctx.W, ctx.H
    if "depth" not in ctx.cache:
        import depth
        base = _cover(img, W, H, 1.06)
        d, how = depth.get_depth(base, use_ai=True)
        ctx.cache["depth"] = (base, depth.layers(base, d, 5), how)
        log(f"   3D gehraai: {how}", show=False)
    base, lays, _ = ctx.cache["depth"]
    push = st.get("push", 0.12)
    p = ease(t / max(dur, 0.5), "inout")
    def scaled(im, s):
        w, h = int(W * s), int(H * s)
        x = im.resize((w, h), Image.BICUBIC)
        l, tp = (w - W) // 2, int((h - H) * 0.5)
        return x.crop((l, tp, l + W, tp + H))
    out = scaled(base, 1 + push * 0.25 * p)
    for lay, near in lays:
        s = 1 + push * (0.25 + 0.75 * near) * p
        out.paste(scaled(lay, s), (0, 0), scaled(lay, s))
    return out


def _card3d(ctx, st, frame, p):
    W, H = ctx.W, ctx.H
    v = _vals(st, p)
    bg = frame.resize((W // 8, H // 8)).filter(ImageFilter.GaussianBlur(4)).resize((W, H)).point(lambda x: int(x * 0.45))
    fw, fh = int(W * 0.86), int(H * 0.86)
    if abs(v["rot_x"]) < 0.3 and abs(v["rot_y"]) < 0.3 and abs(v["rot_z"]) < 0.3:      # seedha card – tez raasta
        cw, chh = int(fw * v["scale"]), int(fh * v["scale"])
        card = frame.resize((cw, chh), Image.BILINEAR)
        x0 = (W - cw) // 2 + int(v["x"] * W); y0 = (H - chh) // 2 + int(v["y"] * H)
        if "cshadow" not in ctx.cache or ctx.cache["cshadow"][0] != (cw, chh):
            m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle((x0 + 18, y0 + 30, x0 + cw + 18, y0 + chh + 30), fill=180)
            ctx.cache["cshadow"] = ((cw, chh), m.filter(ImageFilter.GaussianBlur(28)))
        bg.paste((0, 0, 0), (0, 0), ctx.cache["cshadow"][1])
        bg.paste(card, (x0, y0))
        ImageDraw.Draw(bg).rectangle((x0, y0, x0 + cw - 1, y0 + chh - 1), outline=(235, 235, 235), width=3)
        return bg
    card = frame.resize((fw, fh), Image.BICUBIC)
    dst = _project(fw, fh, W, H, v["rot_x"], v["rot_y"], v["rot_z"], v["scale"], v["x"], v["y"])
    try:
        co = _coeffs(dst, [(0, 0), (fw, 0), (fw, fh), (0, fh)])
    except Exception:
        return frame
    warped = card.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
    mask = Image.new("L", (fw, fh), 255).transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
    sh = mask.filter(ImageFilter.GaussianBlur(28)).point(lambda x: int(x * 0.7))
    bg.paste((0, 0, 0), (18, 30), sh)
    if v["opacity"] < 1: mask = mask.point(lambda x: int(x * v["opacity"]))
    bg.paste(warped, (0, 0), mask)
    # halka safed kinara (card jaisa)
    edge = mask.filter(ImageFilter.FIND_EDGES).point(lambda x: 140 if x > 60 else 0)
    bg.paste((255, 255, 255), (0, 0), edge)
    return bg


def _whip(frame, st, p):
    a = np.asarray(frame).astype(np.float32)
    k = math.sin(math.pi * p)
    if k < 0.03: return frame
    sh = int(frame.width * 0.10 * k) or 1
    sign = -1 if st.get("dir", "left") == "left" else 1
    acc = np.zeros_like(a)
    for j in range(8):
        acc += np.roll(a, sign * sh * j // 8, axis=1)
    out = acc / 8
    move = int(sign * frame.width * 0.25 * (1 - ease(p, "out")))
    out = np.roll(out, move, axis=1)
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def _zoomblur(frame, st, p):
    amt = st.get("amount", 0.3) * (1 - ease(p, "out"))
    if amt < 0.01: return frame
    W, H = frame.size; acc = np.zeros((H, W, 3), np.float32); n = 6
    for j in range(n):
        s = 1 + amt * j / n
        w, h = int(W * s), int(H * s)
        x = frame.resize((w, h), Image.BILINEAR).crop(((w - W) // 2, (h - H) // 2, (w - W) // 2 + W, (h - H) // 2 + H))
        acc += np.asarray(x, np.float32)
    return Image.fromarray(np.clip(acc / n, 0, 255).astype("uint8"))


def _shake(frame, st, p, rnd):
    amp = st.get("amount", 0.3) * 40 * (1 - p)
    if amp < 1: return frame
    W, H = frame.size
    big = frame.resize((int(W * 1.05), int(H * 1.05)), Image.BILINEAR)
    dx = int((big.width - W) / 2 + rnd.uniform(-amp, amp)); dy = int((big.height - H) / 2 + rnd.uniform(-amp, amp))
    dx = max(0, min(big.width - W, dx)); dy = max(0, min(big.height - H, dy))
    return big.crop((dx, dy, dx + W, dy + H))


def _flash(frame, st, p):
    a = (1 - ease(p, "out")) * st.get("strength", 0.8)
    if a < 0.01: return frame
    return Image.blend(frame, Image.new("RGB", frame.size, _hex(st.get("color", "#ffffff"))), a)


def _glow(frame, st, p):
    k = math.sin(math.pi * min(1, p)) if st.get("dur", 1) < 1.5 else min(1, p * 3)
    s = st.get("strength", 0.4) * k
    if s < 0.02: return frame
    small = frame.resize((frame.width // 4, frame.height // 4))
    br = small.point(lambda x: 255 if x > 190 else int(x * 0.25)).filter(ImageFilter.GaussianBlur(10)).resize(frame.size)
    if st.get("color"):
        br = ImageChops.multiply(br, Image.new("RGB", frame.size, _hex(st["color"])))
    return Image.blend(frame, ImageChops.screen(frame, br), min(1.0, s * 1.5))


def _colorpop(frame, st, p):
    k = math.sin(math.pi * min(1, p))
    s = 1 + (st.get("sat", 1.25) - 1) * k
    return ImageEnhance.Contrast(ImageEnhance.Color(frame).enhance(s)).enhance(1 + (s - 1) * 0.4)


def _vignette(ctx, frame, st):
    if "vig" not in ctx.cache:
        W, H = frame.size
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        v = 1 - st.get("strength", 0.4) * (((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 2.4)
        ctx.cache["vig"] = np.clip(v, 0.3, 1)[..., None]
    return Image.fromarray(np.clip(np.asarray(frame, np.float32) * ctx.cache["vig"], 0, 255).astype("uint8"))


def _particles(ctx, frame, st, t, key):
    W, H = frame.size
    kind = st.get("kind", "sparks")
    if key not in ctx.cache:
        rnd = random.Random(hash(key) % 9999)
        n = int(20 + st.get("amount", 0.4) * 80)
        ctx.cache[key] = [(rnd.random() * W, rnd.uniform(0.3, 1.1) * H, rnd.uniform(0.5, 1.5), rnd.uniform(2, 7),
                           rnd.uniform(-30, 30), rnd.random()) for _ in range(n)]
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    col = {"sparks": (255, 170, 60), "dust": (255, 255, 255), "embers": (255, 90, 40)}.get(kind, (255, 200, 120))
    if st.get("color"): col = _hex(st["color"])
    for x0, y0, sp, r, drift, ph in ctx.cache[key]:
        life = (t * sp * (0.35 if kind == "dust" else 0.9) + ph) % 1.0
        y = y0 - life * H * (0.25 if kind == "dust" else 0.8)
        x = x0 + drift * life * 3 + (math.sin(t * 2 + ph * 6) * 6 if kind == "dust" else 0)
        a = int(255 * math.sin(math.pi * life) * (0.45 if kind == "dust" else 0.95))
        rr = r * (0.6 if kind == "dust" else 1.0)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col + (a,))
    if kind != "dust":
        ov = Image.alpha_composite(ov.filter(ImageFilter.GaussianBlur(3)), ov)
    out = frame.convert("RGBA"); out.alpha_composite(ov)
    return out.convert("RGB")


def _text3d(ctx, frame, st, p):
    txt = st.get("text", "{number}")
    txt = txt.replace("{number}", ctx.number or "").replace("{keyword}", ctx.keyword or "").strip()
    if not txt: return frame
    W, H = frame.size
    key = ("t3", txt)
    if key not in ctx.cache:
        import fx
        m = fx.text_mask(txt, int(W * st.get("size", 0.13)), ctx.work)
        ctx.cache[key] = m
    m = ctx.cache[key]
    if m is None: return frame
    e = ease(min(1, p * 4), "out")
    sc = 0.4 + 0.68 * e if e < 1 else 1.0
    if p * 4 < 1.3 and e >= 0.99: sc = 1.08 - 0.08 * min(1, (p * 4 - 1) / 0.3)
    mm = m.resize((max(2, int(m.width * sc)), max(2, int(m.height * sc))))
    if mm.width > W * 0.92:
        mm = mm.resize((int(W * 0.92), int(mm.height * W * 0.92 / mm.width)))
    col = _hex(st.get("color", "#ffdd00")); dark = tuple(int(c * 0.35) for c in col)
    depth_px = int(st.get("depth", 14) * sc)
    x = (W - mm.width) // 2; y = int(H * st.get("y", 0.4)) - mm.height // 2
    out = frame.convert("RGBA")
    stroke = mm.filter(ImageFilter.MaxFilter(9))
    for d_ in range(depth_px, 0, -2):                          # gehraai (extrude)
        out.paste((0, 0, 0, 255), (x + d_ + 2, y + d_ + 2), stroke)
        out.paste(dark + (255,), (x + d_, y + d_), mm)
    out.paste((0, 0, 0, 255), (x, y), stroke)
    out.paste(col + (255,), (x, y), mm)
    return out.convert("RGB")


def render(rc, item, shot, dur, out, W, H, style, ctx):
    """Recipe chalao. item = plan ka item (photo path ke liye), shot = normal bana hua shot (video frames ke liye)."""
    from fx import _pipe_frames
    n = max(2, int(round(dur * FPS)))
    has_depth = any(s["block"] == "depth3d" for s in rc["steps"])
    photo = None
    if item.get("kind") == "image" and has_depth:
        try: photo = Image.open(item["path"]).convert("RGB")
        except Exception: photo = None
        # v3.13: chaudi / group photo POORI dikhni chahiye (photo_poora) – depth3d use kaat ke zoom karta tha
        # (Yash ki jagah heroine / sirf background). Aisi photo pe effect bane hue (poori photo wale) shot pe lagega.
        if photo is not None and str((style or {}).get("photo_poora", "haan")).lower() != "nahi" \
                and (photo.width / photo.height) / (W / H) > 1.6:
            photo = None
    src = _frames_from_video(shot, W, H, n) if (photo is None and shot) else None
    rnd = random.Random(7)

    def frame(i):
        t = i / FPS
        f = next(src) if src is not None else None
        for k, st in enumerate(rc["steps"]):
            a = st["start"]; b = a + st["dur"]
            blk = st["block"]
            whole = blk in ("depth3d", "vignette", "particles")
            if not whole and not (a <= t <= b + (0.0 if blk in ("whip", "zoomblur", "flash", "shake") else dur)):
                continue
            p = (t - a) / max(0.01, st["dur"])
            if blk == "depth3d":
                if photo is not None: f = _depth_frame(ctx, st, t, dur, photo)
            elif f is None:
                continue
            elif blk == "card3d": f = _card3d(ctx, st, f, min(1, p))
            elif blk == "whip" and t <= b: f = _whip(f, st, p)
            elif blk == "zoomblur" and t <= b: f = _zoomblur(f, st, p)
            elif blk == "shake" and t <= b: f = _shake(f, st, p, rnd)
            elif blk == "flash" and t <= b: f = _flash(f, st, p)
            elif blk == "glow" and t <= b: f = _glow(f, st, p)
            elif blk == "colorpop" and t <= b: f = _colorpop(f, st, p)
            elif blk == "vignette": f = _vignette(ctx, f, st)
            elif blk == "particles" and a <= t <= b: f = _particles(ctx, f, st, t - a, ("pt", k))
            elif blk == "text3d" and t <= b: f = _text3d(ctx, f, st, p)
        return f if f is not None else Image.new("RGB", (W, H))
    _pipe_frames(frame, n, W, H, out, style, FPS)
    return out


def apply(rc, item, shot, dur, W, H, style, work, text="", keyword=""):
    """Bane hue shot pe recipe – kamyaab to naya path, warna None (shot waise hi)."""
    try:
        m = re.search(r"[0-9०-९][0-9०-९,.]*", text)
        ctx = Ctx(W, H, work, text, m.group(0) if m else "", keyword)
        out = Path(shot).with_name(Path(shot).stem + f"_{rc['name']}.mp4")
        render(rc, item, shot, dur, out, W, H, style, ctx)
        return out if out.exists() and out.stat().st_size > 1000 else None
    except Exception as e:
        log(f"   (effect {rc['name']} nahi laga: {str(e)[:120]})", show=False)
        return None


def demo(rc, image, out, W=1080, H=1920, style=None, work=None):
    """Seekhi recipe ka 3 sec demo (reel ke frame pe)."""
    style = style or {"quality": "tez"}
    work = Path(work or out).parent if work is None else Path(work)
    item = {"kind": "image", "path": image}
    tmp = Path(out).with_suffix(".base.mp4")
    from common import run
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", image, "-vf",
         f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},zoompan=z='1+0.0008*on':d=90:s={W}x{H}:fps=30",
         "-frames:v", "90", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", tmp])
    ctx = Ctx(W, H, work, "", "100", "")
    render(rc, item, tmp, 3.0, out, W, H, style, ctx)
    try: tmp.unlink()
    except Exception: pass
    return out
