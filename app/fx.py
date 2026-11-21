"""v2.15 PRO EFFECTS (reference video jaisa "news explainer" look).

Script me kisi bhi line ke andar likho (line ke text me nahi bola jaata):
  [map: Chamoli, Uttarakhand]      satellite map zoom, jagah LAAL highlight + pin + naam
  [label: 1:14 PM]                 laal patti, typewriter jaise (time / date / naam / number)
  [news: headline | NASA]          akhbaar ka kaagaz, headline peeli highlight, line ki footage photo ke saath
  [gola]   ya  [gola: helicopter]  laal dashed gola + arrow jo cheez pe point kare (Gemini jagah dhoondhta hai)
  [bubble: Ye abhi tak saaf nahi hai]   speech bubble, typing
  [list: Ram, Shyam, Mohan]        list ek-ek karke aati hai
  [ink]                            is line pe laal ink-splash transition
Bina marker ke bhi: time/date (1:14, 30 अक्टूबर) pe label khud aata hai (style: auto_label).
"""
import math, random, re, io, json, threading
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from common import log, run, yes, num, UA

NAMES = {"map": "map", "naksha": "map", "nakshaa": "map",
         "label": "label", "patti": "label", "tag": "label",
         "news": "news", "khabar": "news", "akhbaar": "news", "report": "news",
         "gola": "gola", "circle": "gola", "point": "gola",
         "bubble": "bubble", "sawaal": "bubble", "bolo": "bubble",
         "list": "list", "suchi": "list",
         "ink": "ink", "splash": "ink", "fx": "fx", "effect": "fx"}

RED = (226, 30, 36)
TAG_RE = re.compile(r"\[\s*([A-Za-z_]+)\s*(?::\s*([^\]]*))?\]")


def parse_tags(s):
    """Line me se [..] nikaalo. Returns (saaf_line, fx_list[(name, value)], sound_marks[])."""
    fx, marks = [], []
    def rep(m):
        n = m.group(1).lower(); v = (m.group(2) or "").strip()
        if n in NAMES:
            fx.append((NAMES[n], v))
        elif m.group(2) is None:
            marks.append(n)
        else:
            return m.group(0)
        return " "
    s2 = TAG_RE.sub(rep, s)
    return re.sub(r"\s{2,}", " ", s2).strip(), fx, marks


# ------------------------------------------------------------------ automatic (bina marker)
MONTHS = ("जनवरी", "फरवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "सितम्बर",
          "अक्टूबर", "अक्तूबर", "नवंबर", "नवम्बर", "दिसंबर", "दिसम्बर")
EN_M = ("January February March April May June July August September October November December").split()
HI2EN = dict(zip(("जनवरी", "फरवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "सितम्बर",
                  "अक्टूबर", "अक्तूबर", "नवंबर", "नवम्बर", "दिसंबर", "दिसम्बर"),
                 ("January", "February", "February", "March", "April", "May", "June", "July", "August", "September",
                  "September", "October", "October", "November", "November", "December", "December")))


def auto_label(text):
    """Line me time / date ho to label ka text (English, jaise reference: '1:14 PM', '30 October')."""
    m = re.search(r"(\d{1,2})[:.](\d{2})\s*(AM|PM|am|pm)?", text)
    if m and int(m.group(1)) <= 24 and int(m.group(2)) < 60:
        h = int(m.group(1)); ap = (m.group(3) or "").upper()
        if not ap:
            ap = "PM" if (re.search(r"(दोपहर|शाम|रात)", text) or h >= 12) else ("AM" if re.search(r"सुबह", text) else "")
        if h > 12: h -= 12
        return f"{h}:{m.group(2)}" + (f" {ap}" if ap else "")
    m = re.search(r"(\d{1,2})\s*(" + "|".join(MONTHS) + r")(?:\s*(\d{4}))?", text)
    if m:
        return f"{int(m.group(1))} {HI2EN.get(m.group(2), m.group(2))}" + (f" {m.group(3)}" if m.group(3) else "")
    m = re.search(r"(\d{1,2})\s*(" + "|".join(EN_M) + r")", text, re.I)
    if m:
        return f"{int(m.group(1))} {m.group(2).capitalize()}"
    return None


# ------------------------------------------------------------------ ASS drawing helpers
def ac(rgb, a=0):
    r, g, b = rgb
    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"


def c3(rgb):
    r, g, b = rgb
    return f"&H{b:02X}{g:02X}{r:02X}&"


def _f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def rrect(w, h, r):
    r = min(r, h / 2, w / 2); k = r * 0.45
    p = [f"m {_f(r)} 0", f"l {_f(w-r)} 0", f"b {_f(w-k)} 0 {_f(w)} {_f(k)} {_f(w)} {_f(r)}", f"l {_f(w)} {_f(h-r)}",
         f"b {_f(w)} {_f(h-k)} {_f(w-k)} {_f(h)} {_f(w-r)} {_f(h)}", f"l {_f(r)} {_f(h)}",
         f"b {_f(k)} {_f(h)} 0 {_f(h-k)} 0 {_f(h-r)}", f"l 0 {_f(r)}", f"b 0 {_f(k)} {_f(k)} 0 {_f(r)} 0"]
    return " ".join(p)


def dashed_circle(R, t, n=16, fill=0.58):
    out = []
    for k in range(n):
        a0 = 2 * math.pi * k / n; a1 = a0 + 2 * math.pi / n * fill
        pts = [(R + R * math.cos(a0 + (a1 - a0) * q / 4), R + R * math.sin(a0 + (a1 - a0) * q / 4)) for q in range(5)]
        pts += [(R + (R - t) * math.cos(a1 - (a1 - a0) * q / 4), R + (R - t) * math.sin(a1 - (a1 - a0) * q / 4))
                for q in range(5)]
        out.append(f"m {_f(pts[0][0])} {_f(pts[0][1])} l " + " ".join(f"{_f(x)} {_f(y)}" for x, y in pts[1:]))
    return " ".join(out)


def arrow_shape(L, s, hw, hl):
    pts = [(0, hw - s), (L - hl, hw - s), (L - hl, 0), (L, hw), (L - hl, 2 * hw), (L - hl, hw + s), (0, hw + s)]
    return f"m {_f(pts[0][0])} {_f(pts[0][1])} l " + " ".join(f"{_f(x)} {_f(y)}" for x, y in pts[1:])


def blob(R, n=90, seed=0):
    """Ink jaisa gol-matol dhabba (organic kinare)."""
    rnd = random.Random(seed); ph = [rnd.uniform(0, 6.3) for _ in range(4)]
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = R * (0.80 + 0.10 * math.sin(3 * a + ph[0]) + 0.07 * math.sin(7 * a + ph[1])
                 + 0.05 * math.sin(13 * a + ph[2]) + 0.03 * math.sin(23 * a + ph[3]))
        pts.append((R * 1.4 + r * math.cos(a), R * 1.4 + r * math.sin(a)))
    return f"m {_f(pts[0][0])} {_f(pts[0][1])} l " + " ".join(f"{_f(x)} {_f(y)}" for x, y in pts[1:])


_fonts = {}


def text_w(text, size, font_path):
    """Text ki lambai (andaza – Devanagari me thoda farak, isliye padding zyada)."""
    try:
        k = (str(font_path), size)
        if k not in _fonts:                       # v2.16b: bytes se – Windows pe font file khuli (lock) na rahe
            _fonts[k] = ImageFont.truetype(io.BytesIO(Path(font_path).read_bytes()), size)
        return _fonts[k].getlength(text)
    except Exception:
        return len(text) * size * 0.55


def _units(text):
    """Typewriter ke tukde: English = akshar, Hindi = shabd (matra na tootein)."""
    if re.search(r"[ऀ-ॿ]", text):
        ws = text.split(" "); return [" ".join(ws[:k]) for k in range(1, len(ws) + 1)]
    return [text[:k] for k in range(1, len(text) + 1) if text[k - 1] != " "]


def esc(t):
    return t.replace("{", "(").replace("}", ")").replace("\\", "/")


# ------------------------------------------------------------------ ASS styles + events
def ass_styles(W, H):
    short = H > W
    fs = int(H * (0.031 if short else 0.045))
    return (f"Style: FxLbl,VT Baloo,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,10,10,0,1\n"
            f"Style: FxBub,VT Baloo,{int(fs*1.05)},&H00141414,&H00141414,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,10,10,0,1\n"
            f"Style: FxLst,VT Baloo,{int(fs*1.12)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,{max(3,fs//12)},{max(2,fs//16)},7,10,10,0,1\n"
            f"Style: FxShp,VT Baloo,20,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n")


def label_events(text, t0, t1, W, H, font, ass_time, y=None, layer=6):
    short = H > W
    fs = int(H * (0.031 if short else 0.045))
    text = esc(text.strip())
    if not text: return []
    tw = text_w(text, fs, font) * (1.12 if re.search(r"[ऀ-ॿ]", text) else 1.0)
    bw, bh = tw + fs * 1.3, fs * 1.55
    cx = W // 2; cy = int(y if y is not None else H * (0.63 if short else 0.80))
    ev = []
    box = (f"{{\\an5\\pos({cx},{cy})\\p1\\bord0\\shad0\\1c{c3(RED)}\\fscx0\\t(0,160,\\fscx100)\\fad(0,180)}}"
           + rrect(bw, bh, fs * 0.28))
    sh = (f"{{\\an5\\pos({cx+4},{cy+6})\\p1\\bord0\\shad0\\1c&H000000&\\1a&H90&\\blur6\\fscx0\\t(0,160,\\fscx100)"
          f"\\fad(0,180)}}" + rrect(bw, bh, fs * 0.28))
    ev.append(f"Dialogue: {layer},{ass_time(t0)},{ass_time(t1)},FxShp,,0,0,0,,{sh}")
    ev.append(f"Dialogue: {layer+1},{ass_time(t0)},{ass_time(t1)},FxShp,,0,0,0,,{box}")
    us = _units(text); dt = min(0.045, 0.5 / max(1, len(us))) if len(us) > 3 else 0.09
    a = t0 + 0.18
    for k, u in enumerate(us):
        b = a + dt if k + 1 < len(us) else t1
        # poora text chhupa ke (alpha) likho taaki text apni jagah se na hile
        rest = text[len(u):]
        body = u + ("{\\alpha&HFF&}" + rest if rest.strip() else "")
        ev.append(f"Dialogue: {layer+2},{ass_time(a)},{ass_time(b)},FxLbl,,0,0,0,,"
                  f"{{\\q2\\an5\\pos({cx},{cy})" + ("\\fad(0,180)" if k + 1 == len(us) else "") + "}" + body)
        a = b
    return ev


def bubble_events(text, t0, t1, W, H, font, ass_time):
    short = H > W
    fs = int(H * (0.031 if short else 0.045) * 1.05)
    text = esc(text.strip())
    if not text: return []
    maxw = W * (0.50 if short else 0.36)
    words = text.split(); lines = []; cur = ""
    for w in words:
        tst = (cur + " " + w).strip()
        if text_w(tst, fs, font) * 1.1 > maxw and cur: lines.append(cur); cur = w
        else: cur = tst
    lines.append(cur)
    tw = max(text_w(l, fs, font) * 1.1 for l in lines)
    bw, bh = tw + fs * 1.4, fs * 1.25 * len(lines) + fs * 1.0
    cx = int(W * (0.64 if short else 0.70)); cy = int(H * (0.24 if short else 0.25))
    tail = (f"m 0 0 l {_f(fs*1.1)} 0 l {_f(-fs*0.5)} {_f(fs*1.3)}")
    ev = []
    pop = "\\fscx30\\fscy30\\t(0,140,\\fscx106\\fscy106)\\t(140,220,\\fscx100\\fscy100)\\fad(0,200)"
    ev.append(f"Dialogue: 6,{ass_time(t0)},{ass_time(t1)},FxShp,,0,0,0,,{{\\an5\\pos({cx},{cy})\\p1\\bord5\\3c&H101010&"
              f"\\1c&HFFFFFF&\\shad0{pop}\\org({cx},{cy})}}" + rrect(bw, bh, fs * 0.6))
    tx, ty = cx - bw * 0.30, cy + bh / 2 - 2
    ev.append(f"Dialogue: 7,{ass_time(t0+0.08)},{ass_time(t1)},FxShp,,0,0,0,,{{\\an7\\pos({_f(tx)},{_f(ty)})\\p1\\bord0"
              f"\\1c&HFFFFFF&\\shad0\\fad(60,200)}}" + tail)
    allw = " ".join(lines).split(" "); n = len(allw)
    dur = min(1.2, max(0.4, (t1 - t0) * 0.45)); a = t0 + 0.2
    for k in range(1, n + 1):
        b = a + dur / n if k < n else t1
        shown = []; left = k
        for l in lines:
            lw = l.split(" ")
            if left <= 0: shown.append("{\\alpha&HFF&}" + l + "{\\alpha&H00&}")
            elif left >= len(lw): shown.append(l)
            else: shown.append(" ".join(lw[:left]) + "{\\alpha&HFF&} " + " ".join(lw[left:]) + "{\\alpha&H00&}")
            left -= len(lw)
        ev.append(f"Dialogue: 8,{ass_time(a)},{ass_time(b)},FxBub,,0,0,0,,{{\\q2\\an5\\pos({cx},{cy})"
                  + ("\\fad(0,200)" if k == n else "") + "}" + "\\N".join(shown))
        a = b
    return ev


def list_events(items, t0, t1, W, H, ass_time):
    short = H > W
    fs = int(H * (0.031 if short else 0.045) * 1.12)
    items = [esc(x.strip()) for x in items if x.strip()][:7]
    if not items: return []
    x = int(W * 0.08); y0 = int(H * (0.20 if short else 0.18)); gap = fs * 1.25
    step = min(0.55, max(0.18, (t1 - t0 - 0.4) / len(items)))
    ev = []
    for k, it in enumerate(items):
        a = t0 + 0.15 + k * step
        ev.append(f"Dialogue: 6,{ass_time(a)},{ass_time(t1)},FxLst,,0,0,0,,{{\\q2\\an7\\pos({x},{int(y0 + k*gap)})"
                  f"\\fad(120,200)\\fscx80\\fscy80\\t(0,120,\\fscx100\\fscy100)}}-  {it}")
    return ev


def gola_events(t0, t1, cx, cy, W, H, ass_time):
    short = H > W
    R = int(W * (0.12 if short else 0.075)); th = max(6, R // 14)
    d = t1 - t0
    ev = []
    circ = dashed_circle(R, th)
    pop = "\\fscx0\\fscy0\\t(0,160,\\fscx112\\fscy112)\\t(160,260,\\fscx100\\fscy100)"
    ev.append(f"Dialogue: 6,{ass_time(t0)},{ass_time(t1)},FxShp,,0,0,0,,{{\\an5\\pos({cx},{cy})\\org({cx},{cy})"
              f"\\p1\\bord2\\3c&H000000&\\3a&HA0&\\1c{c3(RED)}\\shad0{pop}\\t(0,{int(d*1000)},\\frz-{int(40*d)})\\fad(0,150)}}"
              + circ)
    # arrow: neeche-baayein se gole ki taraf
    L = R * 1.05; s = max(5, R * 0.07); hw = R * 0.20; hl = R * 0.32
    side = -1 if cx > W * 0.35 else 1
    tip = (cx + side * R * 0.95 * 0.80, cy + R * 0.95 * 0.60)
    ang = math.atan2(0.60, side * 0.80)                         # tail -> tip direction (tip se bahar ki taraf)
    tail = (tip[0] + side * L * 0.80, tip[1] + L * 0.60)
    mx, my = (tip[0] + tail[0]) / 2, (tip[1] + tail[1]) / 2
    deg = math.degrees(math.atan2(-(tip[1] - tail[1]), tip[0] - tail[0]))
    dx, dy = (tail[0] - tip[0]) * 0.35, (tail[1] - tip[1]) * 0.35
    ev.append(f"Dialogue: 7,{ass_time(t0+0.12)},{ass_time(t1)},FxShp,,0,0,0,,{{\\an5"
              f"\\move({_f(mx+dx)},{_f(my+dy)},{_f(mx)},{_f(my)},0,200)\\org({_f(mx)},{_f(my)})\\frz{_f(deg)}"
              f"\\p1\\bord2\\3c&H000000&\\3a&HA0&\\1c{c3(RED)}\\shad0\\fad(80,150)}}" + arrow_shape(L, s, hw, hl))
    return ev


def ink_events(t_cut, W, H, ass_time, seed=0):
    R = math.hypot(W, H) * 0.62
    ev = []
    for k, (col, dl, sc) in enumerate((((150, 10, 14), 0.0, 1.0), (RED, 0.03, 0.92))):
        a = t_cut - 0.20 + dl; b = t_cut + 0.30
        ev.append(f"Dialogue: 9,{ass_time(a)},{ass_time(b)},FxShp,,0,0,0,,{{\\an5\\pos({W//2},{H//2})\\org({W//2},{H//2})"
                  f"\\p1\\bord0\\shad0\\blur{8+k*6}\\1c{c3(col)}\\fscx2\\fscy2\\t(0,190,\\fscx{int(100*sc)}\\fscy{int(100*sc)}"
                  f"\\frz{25+k*20})\\t(230,{int((b-a)*1000)},\\alpha&HFF&\\fscx{int(130*sc)}\\fscy{int(130*sc)})}}"
                  + blob(R, seed=seed + k))
    return ev


# ------------------------------------------------------------------ gola ki jagah (Gemini)
def locate(frames, subjects, key):
    """frames: [jpg bytes]; subjects: [English]. Returns [(x,y) 0..1 ya None]."""
    out = [None] * len(frames)
    if not key or not frames:
        return out
    try:
        from ai import ask_json
        parts = ["For each numbered image, give the CENTER point of the main subject named for it "
                 "(the thing a news editor would circle). Coordinates 0-1000 (x from left, y from top). "
                 "If the subject is not visible, give the most important object. "
                 'Return ONLY JSON: {"points": [{"image": number, "x": 0-1000, "y": 0-1000}]}']
        for i, (b, s) in enumerate(zip(frames, subjects)):
            parts += [f"Image {i} – subject: {s or 'main subject'}", {"jpg": b}]
        r = ask_json(key, parts, temperature=0.0, timeout=60, budget=120)
        for p in (r or {}).get("points") or []:
            try:
                i = int(p["image"]); x = float(p["x"]) / 1000; y = float(p["y"]) / 1000
                if 0 <= i < len(out) and 0.05 <= x <= 0.95 and 0.05 <= y <= 0.95: out[i] = (x, y)
            except Exception:
                continue
    except Exception as e:
        log(f"   (gola jagah skip: {e})", show=False)
    return out


def frame_at(video, t, work, k):
    fp = Path(work) / f"gola_{k}.jpg"
    try:
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0, t):.2f}", "-i", video, "-frames:v", "1",
             "-vf", "scale=432:-2", fp])
        return fp.read_bytes()
    except Exception:
        return None


# ------------------------------------------------------------------ text -> PNG (Hindi akshar sahi, libass se)
def text_mask(text, size, work, font_dir_name="fonts"):
    """Safed text ka alpha mask (PIL 'L'), libass se – Hindi matra bilkul sahi. None on fail."""
    work = Path(work)
    text = esc(text)
    cw, ch = int(max(200, len(text) * size * 0.9 + size * 2)), int(size * 2.2)
    ass = work / f"tm_{abs(hash((text, size))) % 10**8}.ass"
    png = ass.with_suffix(".png")
    if png.exists():
        try: return Image.open(png).convert("L")
        except Exception: pass
    ass.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {cw}
PlayResY: {ch}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,VT Baloo,{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,T,,0,0,0,,{{\\an4\\pos({size//2},{ch//2})}}{text}
""", encoding="utf-8")
    try:
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={cw}x{ch}:d=1",
             "-vf", f"ass={ass.name}:fontsdir={font_dir_name},format=gray", "-frames:v", "1", png.name], cwd=work)
        m = Image.open(png).convert("L")
        bb = m.getbbox()
        if not bb: return None
        m = m.crop((max(0, bb[0] - 2), 0, min(cw, bb[2] + 2), ch))
        m.save(png)
        return m
    except Exception as e:
        log(f"   (text mask fail: {str(e)[:100]})", show=False); return None


def put_text(canvas, mask, xy, color, shadow=None):
    """mask ko canvas (RGBA) pe color me chipkao. xy = top-left."""
    if mask is None: return
    if shadow:
        sh = mask.filter(ImageFilter.GaussianBlur(shadow[2]))
        layer = Image.new("RGBA", mask.size, shadow[3])
        canvas.paste(layer, (xy[0] + shadow[0], xy[1] + shadow[1]), sh)
    layer = Image.new("RGBA", mask.size, color)
    canvas.paste(layer, xy, mask)


def _ease(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)


def _pipe_frames(frames_fn, n, W, H, out, style, fps):
    import subprocess
    from render import enc_args
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-an", "-frames:v", str(n)] + enc_args(style) + [str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            p.stdin.write(frames_fn(i).convert("RGB").tobytes())
        p.stdin.close()
    except Exception:
        try: p.kill()
        except Exception: pass
        raise
    err = p.stderr.read().decode(errors="replace")
    if p.wait() != 0:
        raise RuntimeError(err[-400:])
    return out


# ------------------------------------------------------------------ NEWS CARD
def _cover(im, W, H):
    r = max(W / im.width, H / im.height)
    x = im.resize((max(W, int(im.width * r) + 1), max(H, int(im.height * r) + 1)), Image.LANCZOS)
    l = (x.width - W) // 2; t = (x.height - H) // 2
    return x.crop((l, t, l + W, t + H))


def news_clip(headline, source, photo, dur, out, W, H, style, work, fps=30):
    """Akhbaar jaisa card: kaagaz, masthead, headline peeli highlight (sweep), photo, halka 3D tilt."""
    work = Path(work)
    try:
        ph = Image.open(photo).convert("RGB") if photo and Path(photo).exists() else None
    except Exception:
        ph = None
    short = H > W
    bg = (_cover(ph, W, H) if ph else Image.new("RGB", (W, H), (60, 60, 60)))
    bg = bg.convert("L").convert("RGB").filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.62))
    cw = int(W * (0.80 if short else 0.46))
    pad = int(cw * 0.06)
    hs = int(cw * 0.062)                                   # headline size
    # headline -> lines (andaze se wrap), har line ka mask libass se
    words = headline.split(); lines = []; cur = ""
    fnt = Path(work) / "fonts" / "VTBaloo.ttf"
    for w_ in words:
        tst = (cur + " " + w_).strip()
        if text_w(tst, hs, fnt) * 1.08 > cw - 2 * pad and cur: lines.append(cur); cur = w_
        else: cur = tst
    if cur: lines.append(cur)
    lines = lines[:4]
    masks = [text_mask(l, hs, work) for l in lines]
    src = (source or "NEWS REPORT").strip().upper()[:28]
    mmask = text_mask(src, int(hs * 0.95), work)
    small = text_mask(f"{src.title()}  •  Report", int(hs * 0.42), work)
    lh = int(hs * 1.32)
    ph_h = int(cw * 0.56) if ph else 0
    ch = pad + int(hs * 1.2) + int(pad * 0.5) + len(lines) * lh + int(pad * 0.6) + ph_h + int(pad * 0.6) + int(hs * 2.4) + pad
    card = Image.new("RGBA", (cw, ch), (250, 248, 242, 255)); d = ImageDraw.Draw(card)
    y = pad
    if mmask is not None:
        mw = min(mmask.width, cw - 2 * pad)
        mm = mmask.resize((mw, int(mmask.height * mw / mmask.width))) if mw < mmask.width else mmask
        put_text(card, mm, ((cw - mm.width) // 2, y - int(hs * 0.45)), (25, 25, 25, 255))
    y += int(hs * 1.2)
    d.rectangle((pad, y, cw - pad, y + 3), fill=(30, 30, 30, 255))
    if small is not None: put_text(card, small, (pad, y + 6 - int(small.height * 0.25)), (110, 110, 110, 255))
    y += int(pad * 0.9)
    hl_boxes = []
    for k, m in enumerate(masks):
        if m is None: continue
        mw = min(m.width, cw - 2 * pad)
        m2 = m.resize((mw, m.height)) if mw < m.width else m
        top = y + k * lh
        hl_boxes.append((pad - 6, top + int(lh * 0.10), pad + mw + 6, top + int(lh * 0.98), m2, (pad, top + (lh - m2.height) // 2)))
    y += len(lines) * lh + int(pad * 0.6)
    if ph:
        pic = _cover(ph, cw - 2 * pad, ph_h); card.paste(pic, (pad, y)); y += ph_h + int(pad * 0.6)
    for q in range(4):                                     # chhoti lines (article ka text)
        ww = (cw - 2 * pad) * (0.95 if q < 3 else 0.6)
        d.rounded_rectangle((pad, y + q * int(hs * 0.55), pad + ww, y + q * int(hs * 0.55) + int(hs * 0.22)), 4,
                            fill=(170, 170, 170, 255))
    # page curl (neeche-daayein kona)
    cs = int(cw * 0.10)
    d.polygon([(cw - cs, ch), (cw, ch - cs), (cw, ch)], fill=(0, 0, 0, 0))
    d.polygon([(cw - cs, ch), (cw - int(cs * 0.15), ch - int(cs * 0.85)), (cw, ch - cs)], fill=(215, 212, 205, 255))
    base_card = card
    n = max(2, int(round(dur * fps)))
    shadow = Image.new("L", (cw + 80, ch + 80), 0)
    ImageDraw.Draw(shadow).rectangle((40, 40, cw + 40, ch + 40), fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    sweep0, sweep1 = 0.35, 0.95
    cy0 = H * (0.47 if short else 0.5)

    def frame(i):
        t = i / fps
        e = _ease(t / 0.4)
        c = base_card.copy(); dc = ImageDraw.Draw(c, "RGBA")
        for k, (x0, y0, x1, y1, m2, pos) in enumerate(hl_boxes):
            st = sweep0 + k * 0.22
            p = _ease((t - st) / (sweep1 - sweep0))
            if p > 0:
                dc.rectangle((x0, y0, x0 + (x1 - x0) * p, y1), fill=(255, 232, 40, 235))
            put_text(c, m2, pos, (15, 15, 15, 255))
        sc = (0.86 + 0.14 * e) * (1 + 0.035 * t / max(dur, 0.5))
        ang = -4.0 * (1 - e) - 1.2
        cc = c.resize((int(cw * sc), int(ch * sc)), Image.BICUBIC).rotate(ang, Image.BICUBIC, expand=True)
        sh = shadow.resize((int((cw + 80) * sc), int((ch + 80) * sc))).rotate(ang, expand=True)
        f = bg.copy()
        zoom = 1 + 0.06 * t / max(dur, 0.5)
        if zoom > 1.001:
            zw, zh = int(W / zoom), int(H / zoom)
            f = f.crop(((W - zw) // 2, (H - zh) // 2, (W - zw) // 2 + zw, (H - zh) // 2 + zh)).resize((W, H))
        cx = W // 2; cy = int(cy0 + 70 * (1 - e))
        f.paste((0, 0, 0), (cx - sh.width // 2 + 14, cy - sh.height // 2 + 22), sh)
        f.paste(cc, (cx - cc.width // 2, cy - cc.height // 2), cc)
        return f
    return _pipe_frames(frame, n, W, H, out, style, fps)


# ------------------------------------------------------------------ MAP
TILE_SRC = [
    ("Sentinel-2 cloudless 2016 by EOX IT Services GmbH (CC BY 4.0, contains modified Copernicus Sentinel data)",
     "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2016_3857/default/g/{z}/{y}/{x}.jpg"),
    ("Esri World Imagery (Esri, Maxar, Earthstar Geographics)",
     "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
]
_geo_lock = threading.Lock()
MAP_CREDIT = set()


def geocode(place):
    import requests, time
    with _geo_lock:                                       # Nominatim: 1 request / second
        time.sleep(1.1)
        try:
            r = requests.get("https://nominatim.openstreetmap.org/search",
                             params={"q": place, "format": "json", "limit": 1, "polygon_geojson": 1,
                                     "polygon_threshold": 0.003},
                             headers={"User-Agent": UA, "Accept-Language": "en"}, timeout=25)
            js = r.json()
        except Exception as e:
            log(f"   map: jagah nahi mili ({e})", show=False); return None
    if not js:
        return None
    j = js[0]
    try:
        bb = [float(x) for x in j["boundingbox"]]          # s, n, w, e
        return {"lat": float(j["lat"]), "lon": float(j["lon"]), "bbox": bb, "geo": j.get("geojson"),
                "name": (j.get("display_name") or place).split(",")[0]}
    except Exception:
        return None


def _wm(lat, lon, z):
    lat = max(-85.0, min(85.0, lat)); s = 256 * (2 ** z)
    x = (lon + 180) / 360 * s
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * s
    return x, y


def _tile(url_t, z, x, y, cache):
    import requests
    n = 2 ** z; x %= n
    if y < 0 or y >= n: return Image.new("RGB", (256, 256), (20, 30, 40))
    fp = cache / f"{abs(hash(url_t)) % 9999}_{z}_{x}_{y}.jpg"
    if fp.exists():
        try: return Image.open(fp).convert("RGB")
        except Exception: pass
    r = requests.get(url_t.format(z=z, x=x, y=y), headers={"User-Agent": UA}, timeout=20)
    if r.status_code != 200 or len(r.content) < 500:
        raise RuntimeError(f"tile {r.status_code}")
    fp.write_bytes(r.content)
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def _mosaic(cx, cy, w, h, z, cache):
    """Pixel centre (cx,cy) @zoom z ke aas-paas w*h ka satellite photo."""
    from concurrent.futures import ThreadPoolExecutor
    x0, y0 = cx - w / 2, cy - h / 2
    tx0, ty0 = int(math.floor(x0 / 256)), int(math.floor(y0 / 256))
    tx1, ty1 = int(math.floor((x0 + w) / 256)), int(math.floor((y0 + h) / 256))
    for credit, url in TILE_SRC:
        try:
            im = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
            jobs = [(tx, ty) for ty in range(ty0, ty1 + 1) for tx in range(tx0, tx1 + 1)]
            with ThreadPoolExecutor(max_workers=6) as ex:
                tiles = list(ex.map(lambda p: _tile(url, z, p[0], p[1], cache), jobs))
            for (tx, ty), t in zip(jobs, tiles):
                im.paste(t, ((tx - tx0) * 256, (ty - ty0) * 256))
            ox, oy = x0 - tx0 * 256, y0 - ty0 * 256
            MAP_CREDIT.add(credit)
            return im.crop((int(ox), int(oy), int(ox + w), int(oy + h))), (x0, y0)
        except Exception as e:
            log(f"   map tiles ({credit.split(' ')[0]}) nahi mile: {str(e)[:80]}", show=False)
            continue
    return None, None


def _polys(geo):
    if not geo: return []
    t = geo.get("type"); c = geo.get("coordinates") or []
    if t == "Polygon": return [c[0]] if c else []
    if t == "MultiPolygon": return [p[0] for p in c if p]
    return []


def map_clip(place, label, dur, out, W, H, style, work, fps=30):
    """Satellite map: door se zoom-in, jagah laal (terrain dikhe), safed pin + naam."""
    work = Path(work)
    g = geocode(place)
    if not g:
        log(f"   map: '{place}' nahi mila – normal footage lagegi"); return None
    s, nn, w_, e = g["bbox"]
    polys = _polys(g["geo"])
    # final view: jagah frame ki ~55% chaudai le
    fit = W * 0.78
    zf = None
    for z in range(16, 2, -1):
        x1, y1 = _wm(nn, w_, z); x2, y2 = _wm(s, e, z)
        if abs(x2 - x1) <= fit and abs(y2 - y1) <= H * 0.50:
            zf = z; break
    zf = zf or 4
    zf = min(zf, 13)
    zm = max(2, zf - 1)                                   # mosaic ek zoom kam (kam tiles)
    k = 2 ** (zm - zf)                                    # final px -> mosaic px
    START = 3.2                                           # shuru me kitna door
    cxm, cym = _wm(g["lat"], g["lon"], zm)
    if polys:
        allp = [pt for p in polys for pt in p]
        xs = [_wm(la, lo, zm)[0] for lo, la in allp]; ys = [_wm(la, lo, zm)[1] for lo, la in allp]
        cxm, cym = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        rw, rh = max(xs) - min(xs), max(ys) - min(ys)
    else:
        x1, y1 = _wm(nn, w_, zm); x2, y2 = _wm(s, e, zm); rw, rh = abs(x2 - x1), abs(y2 - y1)
    # v2.15: aakhri frame me jagah screen ki ~72% chaudai bhare (reference jaisa bada)
    fw = max(rw / 0.72, rh * W / H / 0.50, W * k * 0.55)
    fw = min(fw, W * k * 1.6)
    mw, mh = int(fw * START) + 4, int(fw * H / W * START) + 4
    cache = work / "map_tiles"; cache.mkdir(exist_ok=True)
    mos, (ox, oy) = _mosaic(cxm, cym, mw, mh, zm, cache)
    if mos is None:
        log("   map: satellite photo nahi mila (internet?) – normal footage lagegi"); return None
    mos = mos.convert("RGB")
    from PIL import ImageEnhance
    mos = ImageEnhance.Color(mos).enhance(0.85)
    mos = ImageEnhance.Contrast(mos).enhance(1.08)
    if polys:
        mask = Image.new("L", mos.size, 0); dm = ImageDraw.Draw(mask)
        for p in polys:
            pts = [(_wm(la, lo, zm)[0] - ox, _wm(la, lo, zm)[1] - oy) for lo, la in p]
            if len(pts) >= 3: dm.polygon(pts, fill=255)
        a = np.asarray(mos).astype(np.float32)
        lum = a.mean(axis=2, keepdims=True)
        red = np.clip(lum * np.array([1.55, 0.16, 0.16]) + np.array([40, 0, 0]), 0, 255)
        mk = (np.asarray(mask.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255)[..., None]
        outside = a * 0.78
        a2 = outside * (1 - mk) + red * mk
        mos = Image.fromarray(a2.astype("uint8"))
        edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
        mos.paste((255, 235, 235), (0, 0), edge.point(lambda v: 200 if v > 40 else 0))
    else:
        mos = Image.fromarray((np.asarray(mos).astype(np.float32) * 0.85).astype("uint8"))
    # pin + naam
    lab = (label or g["name"] or place).strip().upper()
    lsize = int(W * (0.075 if H > W else 0.045))
    lmask = text_mask(lab, lsize, work)
    pin_c = _wm(g["lat"], g["lon"], zm)
    px, py = pin_c[0] - ox, pin_c[1] - oy
    n = max(2, int(round(dur * fps)))
    vw0, vh0 = mw - 4, mh - 4
    vw1, vh1 = fw, fw * H / W
    ccx, ccy = mos.width / 2, mos.height / 2

    def frame(i):
        t = i / fps
        p = _ease(min(1.0, t / max(0.8, dur * 0.55)))
        z = (vw0 / vw1) ** (1 - p)                         # log-zoom (smooth)
        vw, vh = vw1 * z, vh1 * z
        cx = ccx + (px - ccx) * p * 0.35; cy = ccy + (py - ccy) * p * 0.35
        box = (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2)
        f = mos.resize((W, H), Image.BICUBIC, box=box)
        f = f.filter(ImageFilter.UnsharpMask(2, 60, 2)) if p > 0.6 else f
        # pin
        sx = (px - box[0]) / vw * W; sy = (py - box[1]) / vh * H
        q = _ease((t - dur * 0.38) / 0.25)
        if q > 0:
            fr = f.convert("RGBA"); d = ImageDraw.Draw(fr, "RGBA")
            r1 = int(W * 0.022 * (0.6 + 0.4 * q)); r2 = int(r1 * (1.9 + 0.6 * math.sin(t * 5)))
            d.ellipse((sx - r2, sy - r2, sx + r2, sy + r2), outline=(255, 255, 255, int(150 * q)), width=4)
            d.ellipse((sx - r1, sy - r1, sx + r1, sy + r1), fill=(255, 255, 255, int(255 * q)))
            if lmask is not None:
                lm = lmask
                if lm.width > W * 0.9:
                    lm = lm.resize((int(W * 0.9), int(lm.height * W * 0.9 / lm.width)))
                lx = int(max(10, min(W - lm.width - 10, sx - lm.width / 2)))
                ly = int(sy + r2 + 4 - lm.height * 0.15)
                al = lm.point(lambda v: int(v * q))
                put_text(fr, al, (lx, ly), (255, 255, 255, 255), shadow=(3, 5, 6, (0, 0, 0, 200)))
            f = fr.convert("RGB")
        return f
    try:
        return _pipe_frames(frame, n, W, H, out, style, fps)
    except Exception as e:
        log(f"   map video nahi bani ({str(e)[:100]})", show=False); return None
