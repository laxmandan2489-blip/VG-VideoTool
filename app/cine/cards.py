"""GRAPHIC CARDS – jab sahi footage na mile (ya number/stat dikhana ho) to RANDOM photo ki jagah
design kiya hua motion-graphics scene. Style Bible ke rang + font.

  stat_card   : bada number 0 se count-up (30-35%, 2.5 LAKH, 1000 SAAL) + percent ho to ring bharti hai
  word_card   : 1-2 shabd ka kinetic headline (tracking-in + light sweep) + chhoti serif line
"""
import math, re, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .bible import font_path


def _ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _bg(W, H, pal, seed=0):
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    c1 = np.array(pal["bg1"], float); c2 = np.array(pal["bg2"], float)
    r = np.sqrt((x - 0.5) ** 2 * 1.4 + (y - 0.45) ** 2)
    k = np.clip(1.0 - r * 1.3, 0, 1)[..., None]
    img = np.clip(c1 * (1 - k) + c2 * k, 0, 255)
    rng = np.random.default_rng(seed)
    img += rng.normal(0, 3.0, (H, W, 1))                     # film grain (flat AI look nahi)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


class _Base:
    def __init__(self, W, H, pal, dur, seed=0):
        self.W, self.H, self.pal, self.dur = W, H, pal, dur
        self.bg = _bg(W, H, pal, seed)
        rnd = random.Random(seed)
        self.parts = [(rnd.random() * W, rnd.random() * H, rnd.uniform(1.5, 4.5), rnd.uniform(8, 30)) for _ in range(46)]

    def base(self, t):
        im = self.bg.copy()
        d = ImageDraw.Draw(im, "RGBA")
        for (x, y, r, sp) in self.parts:                      # dheere upar uthte kan (depth)
            yy = (y - sp * t * 3) % self.H
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 255, 255, int(18 + r * 6)))
        # light sweep
        sx = -self.W * 0.6 + (self.W * 2.2) * ((t / max(self.dur, 0.1)) % 1.0)
        sw = Image.new("L", (self.W, self.H), 0); sd = ImageDraw.Draw(sw)
        sd.polygon([(sx, 0), (sx + self.W * 0.18, 0), (sx - self.W * 0.25, self.H), (sx - self.W * 0.43, self.H)], fill=26)
        sw = sw.filter(ImageFilter.GaussianBlur(self.W / 25))
        im.paste((255, 255, 255), (0, 0), sw)
        return im

    def text_center(self, im, txt, font, y, fill, track=0.0, alpha=255, glow=True):
        d = ImageDraw.Draw(im, "RGBA")
        chars = list(txt) if track > 0.005 else [txt]           # tracking na ho to poora shabd ek saath
        ws = [d.textlength(c, font=font) for c in chars]
        gap = font.size * track
        tw = sum(ws) + gap * (len(chars) - 1)
        x = self.W / 2 - tw / 2
        if glow:
            gl = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
            xx = x
            for c, w in zip(chars, ws):
                gd.text((xx, y), c, font=font, fill=tuple(fill[:3]) + (int(alpha * 0.7),)); xx += w + gap
            gl = gl.filter(ImageFilter.GaussianBlur(font.size / 9))
            im.paste(gl, (0, 0), gl)
        xx = x
        for c, w in zip(chars, ws):
            d.text((xx + 4, y + 5), c, font=font, fill=(0, 0, 0, int(alpha * 0.55)))
            d.text((xx, y), c, font=font, fill=tuple(fill[:3]) + (alpha,)); xx += w + gap
        return tw


def latin(txt):
    """PIL Hindi (matra) theek se nahi jodta – card par Hinglish (Roman) likho."""
    if not re.search("[\u0900-\u097F]", txt or ""): return txt or ""
    try:
        from translit import word as tw
        return " ".join(tw(w) for w in txt.split())
    except Exception:
        return re.sub("[\u0900-\u097F]+", "", txt).strip()


def _fit_font(kind, txt, max_w, start):
    size = start
    while size > 40:
        f = ImageFont.truetype(str(font_path(kind)), size)
        if f.getlength(txt) <= max_w: return f
        size = int(size * 0.9)
    return ImageFont.truetype(str(font_path(kind)), 40)


NUM_RE = re.compile(r"(\d[\d,]*\.?\d*)")


class StatCard(_Base):
    def __init__(self, value, label, W, H, pal, dur, sub=""):
        super().__init__(W, H, pal, dur, seed=len(value) + len(label))
        self.value = latin(value).upper(); self.label = latin(label).upper(); sub = latin(sub); self.sub = sub
        self.pct = None
        m = NUM_RE.findall(self.value)
        try:
            if "%" in self.value and m: self.pct = min(100.0, float(m[-1].replace(",", "")))
        except Exception:
            self.pct = None
        self.f_num = _fit_font("head", self.value, W * 0.82, int(W * (0.30 if not self.pct else 0.24)))
        self.f_lab = _fit_font("bold", self.label, W * 0.86, int(W * 0.075))
        self.f_sub = _fit_font("serif", sub, W * 0.86, int(W * 0.055)) if sub else None

    def _count(self, p):
        """'30-35%' -> '17-20%' (har number p guna)."""
        def rep(mo):
            s = mo.group(1); v = float(s.replace(",", ""))
            dec = len(s.split(".")[1]) if "." in s else 0
            cur = v * p
            out = f"{cur:,.{dec}f}" if "," in s else f"{cur:.{dec}f}"
            return out
        return NUM_RE.sub(rep, self.value)

    def frame(self, i, fps=30):
        t = i / fps
        im = self.base(t)
        cy = self.H * (0.42 if self.H > self.W else 0.45)
        acc = tuple(self.pal["accent"])
        if self.pct is not None:                               # ring bharti hai
            R = self.W * 0.36
            ring = Image.new("RGBA", im.size, (0, 0, 0, 0)); rd = ImageDraw.Draw(ring)
            wdt = int(self.W * 0.035)
            box = (self.W / 2 - R, cy - R, self.W / 2 + R, cy + R)
            rd.arc(box, 0, 360, fill=(255, 255, 255, 40), width=wdt)
            p = _ease((t - 0.15) / 1.1) * self.pct / 100.0
            if p > 0: rd.arc(box, -90, -90 + 360 * p, fill=acc + (255,), width=wdt)
            gl = ring.filter(ImageFilter.GaussianBlur(self.W / 80)); im.paste(gl, (0, 0), gl); im.paste(ring, (0, 0), ring)
        p = _ease((t - 0.1) / 1.0)
        val = self._count(p) if p < 0.999 else self.value
        sc = 0.85 + 0.15 * _ease(t / 0.35)
        f = self.f_num if sc > 0.999 else ImageFont.truetype(str(font_path("head")), max(20, int(self.f_num.size * sc)))
        a = int(255 * min(1, t / 0.2))
        self.text_center(im, val, f, cy - f.size * 0.55, acc, 0.02, a)
        la = _ease((t - 0.45) / 0.4)
        if la > 0:
            y = cy + (self.W * 0.40 if self.pct is not None else f.size * 0.55) + (1 - la) * 30
            self.text_center(im, self.label, self.f_lab, y, (255, 255, 255), 0.06 + 0.25 * (1 - la), int(255 * la), glow=False)
            if self.f_sub:
                sa = _ease((t - 0.8) / 0.4)
                if sa > 0:
                    self.text_center(im, self.sub, self.f_sub, y + self.f_lab.size * 1.35, (235, 235, 235), 0.0,
                                     int(230 * sa), glow=False)
        return im


class WordCard(_Base):
    def __init__(self, word, sub, W, H, pal, dur):
        super().__init__(W, H, pal, dur, seed=len(word) * 7 + len(sub))
        self.word = latin(word).upper(); sub = latin(sub); self.sub = sub
        self.f = _fit_font("head", self.word, W * 0.86, int(W * 0.24))
        self.fs = _fit_font("serif", sub, W * 0.86, int(W * 0.06)) if sub else None

    def frame(self, i, fps=30):
        t = i / fps
        im = self.base(t)
        cy = self.H * 0.44
        a = _ease(t / 0.45)
        track = 0.35 * (1 - a) + 0.03
        zoom_drift = 1 + 0.04 * (t / max(self.dur, 0.1))
        f = ImageFont.truetype(str(font_path("head")), max(20, int(self.f.size * zoom_drift)))
        self.text_center(im, self.word, f, cy - f.size * 0.6, tuple(self.pal["accent"]), track, int(255 * a))
        if self.fs:
            sa = _ease((t - 0.4) / 0.45)
            if sa > 0:
                self.text_center(im, self.sub, self.fs, cy + f.size * 0.55 + (1 - sa) * 24, (255, 255, 255), 0.0,
                                 int(240 * sa), glow=False)
        # patli accent line
        lw = self.W * 0.22 * _ease((t - 0.25) / 0.5)
        if lw > 2:
            d = ImageDraw.Draw(im, "RGBA")
            y = cy - f.size * 0.75
            d.rounded_rectangle((self.W / 2 - lw / 2, y, self.W / 2 + lw / 2, y + max(4, self.W // 180)),
                                radius=3, fill=tuple(self.pal["accent2"]) + (230,))
        return im


def render_stat(value, label, dur, out, W, H, style, pal, sub="", fps=30):
    import fx
    c = StatCard(value, label, W, H, pal, dur, sub)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)


def render_word(word, sub, dur, out, W, H, style, pal, fps=30):
    import fx
    c = WordCard(word, sub, W, H, pal, dur)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)
