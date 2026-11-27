"""v3.1 HERO SHOTS – asli insaan / brand / jagah ki photo ko cinematic 3D motion + pro typography ke saath.

  person / place / thing photo:  2.5D depth parallax (AI depth ya andaza) + dheema camera push + light sweep
                                  + NAAM lower-third (accent bar slide-in, Poppins ExtraBold, chhota description)
  brand LOGO:                     dark brand background, logo 3D tilt-in (perspective), glow, light sweep,
                                  floor reflection, particles, naam typography
  free photo na mile:             NAME CARD – bada kinetic naam (tracking-in), description, particles (galat insaan
                                  ki photo se behtar)
Sab frames PIL se, encoder fx._pipe_frames (same fps/timebase).
"""
import math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

from common import ASSETS

F_BOLD = ASSETS / "fonts" / "Poppins-ExtraBold.ttf"
F_SEMI = ASSETS / "fonts" / "Poppins-SemiBold.ttf"
F_HEAD = ASSETS / "fonts" / "BebasNeue-Regular.ttf"


def _ease(t, k="out"):
    t = max(0.0, min(1.0, t))
    if k == "inout": return t * t * (3 - 2 * t)
    return 1 - (1 - t) ** 3


def _font(p, size):
    try: return ImageFont.truetype(str(p), max(8, int(size)))
    except Exception: return ImageFont.load_default()


def _fit(txt, path, max_w, start, draw):
    s = start
    while s > 18:
        f = _font(path, s)
        if draw.textlength(txt, font=f) <= max_w: return f
        s -= 4
    return _font(path, 18)


def _cover(im, W, H, over=1.0, fx=0.5):
    """fx = subject ka x (0..1) – crop usi ke aas-paas (v3.13: pehle hamesha beech -> Yash ki jagah heroine)."""
    r = max(W / im.width, H / im.height) * over
    x = im.resize((max(W, int(im.width * r) + 1), max(H, int(im.height * r) + 1)), Image.LANCZOS)
    l = int(min(max(0, fx * x.width - W / 2), x.width - W)); t = int((x.height - H) * 0.35)
    return x.crop((l, t, l + W, t + H))


FOCUS = {"on": True}


def focus_x(im, text):
    """v3.13: photo me line ka subject KAHAN hai (x 0..1)? AI aankh (CLIP) photo ke 5 khade hisse dekhti hai.
    'Yash' bola ja raha hai aur photo me Yash + heroine -> crop / camera Yash ki taraf. CLIP na ho -> 0.5."""
    if not (FOCUS["on"] and text) or im.width < im.height * 0.8:
        return 0.5
    try:
        import aankh, sources
        if not (sources.AANKH["on"] and aankh.ready()):
            return 0.5
        w, h = im.size
        cw = int(min(w, h * 0.75))
        xs = [int(i * (w - cw) / 4) for i in range(5)]
        crops = [im.crop((x, 0, x + cw, h)).resize((224, int(224 * h / cw))) for x in xs]
        m, _ = aankh.scores(crops, text)
        import numpy as np
        m = np.asarray(m, dtype=float)
        j = int(m.argmax())
        if float(m.max() - m.min()) < 0.008:       # sab barabar -> beech
            return 0.5
        return (xs[j] + cw / 2) / w
    except Exception:
        return 0.5


def _sweep(im, t, t0=0.15, d=0.9, strength=70):
    """Tirchhi roshni ki patti jo frame ke upar se guzarti hai (premium light sweep)."""
    p = (t - t0) / d
    if not 0 <= p <= 1: return im
    W, H = im.size
    q = 4                                              # v3.6 TEZ: mask chhote size pe bana ke bada (16x kam kaam)
    w4, h4 = max(8, W // q), max(8, H // q)
    m = Image.new("L", (w4, h4), 0); dr = ImageDraw.Draw(m)
    x = (-W * 0.6 + p * W * 2.2) / q; w = W * 0.18 / q
    dr.polygon([(x, 0), (x + w, 0), (x + w - h4 * 0.35, h4), (x - h4 * 0.35, h4)], fill=strength)
    m = m.filter(ImageFilter.GaussianBlur(max(1, W // 25 // q))).resize((W, H), Image.BILINEAR)
    return Image.composite(_WHITE(W, H), im, m)


_WC = {}


def _WHITE(W, H):
    if (W, H) not in _WC: _WC[(W, H)] = Image.new("RGB", (W, H), (255, 255, 255))
    return _WC[(W, H)]


def _vignette(W, H, k=0.55):
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    v = np.clip(1 - (r - 0.55) * k, 0.35, 1.0)
    return Image.fromarray((v * 255).astype("uint8"), "L")


class _Parts:
    def __init__(self, W, H, n=40, seed=3, col=(255, 220, 160)):
        rnd = random.Random(seed); self.col = col
        self.p = [(rnd.random() * W, rnd.random() * H, rnd.uniform(1.2, 3.5), rnd.uniform(10, 40), rnd.random())
                  for _ in range(n)]
        self.W, self.H = W, H

    def draw(self, im, t):
        d = ImageDraw.Draw(im, "RGBA")
        for x, y, r, sp, ph in self.p:
            yy = (y - sp * t) % self.H; a = int(90 + 90 * math.sin(t * 2 + ph * 6))
            d.ellipse((x - r, yy - r, x + r, yy + r), fill=self.col + (a,))
        return im


def _lower_third(im, t, name, desc, accent, W, H, t0=0.35):
    """Pro naam patti: accent bar slide-in, naam tracking, description fade."""
    a = _ease((t - t0) / 0.45)
    if a <= 0: return im
    d = ImageDraw.Draw(im, "RGBA")
    y = int(H * (0.555 if H > W else 0.66)); x0 = int(W * 0.07)       # v3.1: captions (0.745) se upar
    fn = _fit(name.upper(), F_BOLD, W * 0.80, W * 0.085, d)
    fd = _font(F_SEMI, W * 0.034)
    bw = int((d.textlength(name.upper(), font=fn) + W * 0.06) * a)
    # glass panel
    d.rounded_rectangle((x0 - W * 0.02, y - fn.size * 0.25, x0 - W * 0.02 + bw, y + fn.size * 1.45 +
                         (fd.size * 1.3 if desc else 0)), radius=int(W * 0.015), fill=(0, 0, 0, int(140 * a)))
    d.rectangle((x0 - W * 0.02, y - fn.size * 0.25, x0 - W * 0.02 + int(W * 0.012), y + fn.size * 1.45 +
                 (fd.size * 1.3 if desc else 0)), fill=tuple(accent) + (int(255 * a),))
    track = (1 - a) * W * 0.06
    d.text((x0 + W * 0.015 + track, y), name.upper(), font=fn, fill=(255, 255, 255, int(255 * a)))
    if desc:
        b = _ease((t - t0 - 0.25) / 0.4)
        if b > 0:
            d.text((x0 + W * 0.017, y + fn.size * 1.15), desc[:48], font=fd, fill=tuple(accent) + (int(235 * b),))
    return im


# ------------------------------------------------------------------ photo hero (person / place / thing)
class PhotoHero:
    MODES = ("depth_push", "pan", "pull_out", "tilt_card")

    def __init__(self, path, W, H, dur, name="", desc="", accent=(255, 214, 10), seed=1, behind="", mode=None, crop_v=0,
                 whole=None, focus_text=""):
        self.W, self.H, self.dur = W, H, dur
        self.mode = mode if mode in self.MODES else self.MODES[seed % len(self.MODES)]
        self.behind = (behind or "").upper()[:14]
        im = Image.open(path).convert("RGB")
        if crop_v:                                   # v3.1: same photo dobara -> alag frame
            # v3.13 FIX ("chehra bahut zoom"): pehle 40% tak kaat-ta tha (sirf chehra) – ab halka (85%+ photo dikhe)
            w0, h0 = im.size
            boxes = [(0.06, 0.0, 0.94, 0.92), (0.0, 0.05, 0.9, 1.0), (0.1, 0.04, 1.0, 1.0)]
            bx = boxes[(crop_v - 1) % len(boxes)]
            im = im.crop((int(w0 * bx[0]), int(h0 * bx[1]), int(w0 * bx[2]), int(h0 * bx[3])))
        self.name, self.desc, self.accent = name, desc, accent
        # v3.13 (user, 15 Nov): "poori image nahi dikhti / Yash ki jagah heroine" -> photo_poora = haan (default):
        # khadi (9:16 ke paas) photo poori screen; chaudi / group photo POORI dikhti hai (poori chaudai me, upar-neeche
        # usi photo ka blur) + camera dheere subject (CLIP) ki taraf. photo_poora = nahi -> purana (sirf 2:1+ pe card).
        ar = im.width / im.height; ar_out = W / H
        # chaukor (1:1) se chaudi photo -> poori; lagbhag khadi (4:5) -> poori screen, subject ki taraf crop
        # v4.23 FULL-SCREEN 9:16 SHORTS: fill vertical frame with CLIP smart_x tracking for normal 16:9 photos (ar <= 2.2), only letterbox extreme panoramas
        # v5.1 FIX ("frame bahut zoom, poori nahi dikhti"): v4.23 me 9:16 me 16:9 photo ko poori screen bharne ke
        # liye beech se ~70% kaat dete the. Ab chaukor ya chaudi photo (ar > 0.85) POORI dikhti hai (poori chaudai,
        # upar-neeche usi ka blur); sirf lagbhag-khadi (4:5 ya patli) photo screen bharti hai.
        self.fit_whole = (ar > 0.85) if (W < H) else ((ar > 2.0) if whole is False else (ar / ar_out > 1.6 if whole else ar > 2.0))
        self.fx = focus_x(im, focus_text or name) if (focus_text or name) else 0.5
        self.how = "flat"
        base = _cover(im, W, H, 1.03, self.fx)
        self.bg = base.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.45)) if self.fit_whole else None
        if self.fit_whole:
            f = min(W * 1.0 / im.width, H * 0.70 / im.height)        # v3.13: poori chaudai (chhota card nahi)
            self.card = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
            self.lays = None
        else:
            try:
                import depth
                dmap, self.how = depth.get_depth(base, use_ai=True)
                self.lays = (base, depth.layers(base, dmap, 4))     # v3.6 TEZ: 5 ki jagah 4 parat (3D asar same, kam kaam)
            except Exception:
                self.lays = (base, []); self.how = "flat"
        self.vig = _vignette(W, H)
        self.parts = _Parts(W, H, 30, seed)
        self.dir = 1 if seed % 2 else -1

    def _scaled(self, im, s, dx=0):
        """v3.6 TEZ: poori photo bada karke kaatne ki jagah sirf dikhne wala hissa seedha W x H pe (same nateeja,
        ~1.5-2x kam kaam). Depth parat (RGBA) BILINEAR – kinare naram hi hain."""
        W, H = self.W, self.H
        w, h = W * s, H * s
        l = (w - W) / 2 + dx; tp = (h - H) * 0.5
        l = max(0.0, min(w - W, l))
        box = (l / s, tp / s, (l + W) / s, (tp + H) / s)
        rs = Image.BILINEAR if im.mode == "RGBA" else Image.BICUBIC
        return im.resize((W, H), rs, box=box)

    def _card(self, t, p):
        """Photo ek 3D card ki tarah ghoomti hai (peeche usi ka blur) – reference ka poster-card look."""
        from recipe import _project, _coeffs
        W, H = self.W, self.H
        if not hasattr(self, "_cbg"):
            src = self.card if self.fit_whole else self.lays[0]
            self._cbg = _cover(src, W, H, 1.1).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.42))
            c = self.card if self.fit_whole else _cover(self.lays[0], int(W * 0.84), int(H * 0.62), 1.0)
            m = Image.new("L", c.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1),
                                                                                radius=int(W * 0.035), fill=255)
            self._cimg = c; self._cmask = m
        out = self._scaled(self._cbg, 1.03 + 0.04 * p)
        a = _ease(t / 0.7)
        ry = self.dir * (22 * (1 - a) + 5 * math.sin(p * math.pi)); rx = 6 * (1 - a)
        sc = 0.9 + 0.08 * a + 0.03 * p
        cw, ch = self._cimg.size
        dst = _project(cw, ch, W, H, rx, ry, 0, sc, 0, -0.04)
        try:
            co = _coeffs(dst, [(0, 0), (cw, 0), (cw, ch), (0, ch)])
            wimg = self._cimg.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
            wm = self._cmask.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
            out.paste((0, 0, 0), (16, 28), wm.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.7)))
            out.paste(wimg, (0, 0), wm)
        except Exception:
            pass
        return out

    def _text_behind(self, out, t):
        W, H = self.W, self.H
        a = _ease((t - 0.15) / 0.5)
        if a <= 0: return
        d = ImageDraw.Draw(out, "RGBA")
        f = _fit(self.behind, F_HEAD, W * 0.9, W * 0.30, d)
        tw = d.textlength(self.behind, font=f); y = H * 0.20 + (1 - a) * 30
        d.text(((W - tw) / 2 + 6, y + 8), self.behind, font=f, fill=(0, 0, 0, int(110 * a)))
        d.text(((W - tw) / 2, y), self.behind, font=f, fill=tuple(self.accent) + (int(235 * a),))

    def frame(self, i, fps=30):
        t = i / fps; p = _ease(t / max(self.dur, 0.5), "inout")
        W, H = self.W, self.H
        if self.fit_whole:
            # v3.13: POORI photo (koi hissa nahi katta), halka 1.00 -> 1.05 push subject (fx) ki taraf
            out = self._scaled(self.bg, 1.03 + 0.03 * p, self.dir * 12 * p)
            s = 1.0 + 0.05 * p
            c = self.card.resize((int(self.card.width * s), int(self.card.height * s)), Image.BICUBIC)
            x = int((W - c.width) / 2 - (self.fx - 0.5) * (c.width - self.card.width))
            y = int(H * 0.44 - c.height / 2)
            sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rectangle((x + 12, y + 20, x + c.width + 12, y + c.height + 20), fill=150)
            out.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(24)))
            out.paste(c, (x, y))
        elif self.mode == "pan" and not self.fit_whole:
            base = self.lays[0]
            out = self._scaled(base, 1.10, self.dir * (-0.5 + p) * W * 0.09)        # side pan (v3.13: kam zoom)
        elif self.mode == "pull_out" and not self.fit_whole:
            base, lays = self.lays
            out = self._scaled(base, 1.10 - 0.08 * p)
            for lay, near in lays:
                s_ = 1.10 - 0.08 * p + 0.04 * near * (1 - p)
                L = self._scaled(lay, s_); out.paste(L, (0, 0), L)
        elif False:
            out = self._scaled(self.bg, 1.04 + 0.05 * p, self.dir * 20 * p)
            s = 0.94 + 0.08 * _ease(t / 0.6) + 0.04 * p
            c = self.card.resize((int(self.card.width * s), int(self.card.height * s)), Image.BICUBIC)
            x = (W - c.width) // 2; y = int(H * 0.40 - c.height / 2)
            sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rectangle((x + 16, y + 26, x + c.width + 16, y + c.height + 26), fill=170)
            out.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(26)))
            out.paste(c, (x, y))
        else:
            base, lays = self.lays
            push = 0.10
            out = self._scaled(base, 1 + push * 0.25 * p, -self.dir * 12 * p)
            for li_, (lay, near) in enumerate(lays):                  # paas wali parat tez -> asli gehraai
                if self.behind and self.how == "AI" and li_ == max(0, len(lays) - 2):
                    self._text_behind(out, t)                        # v3.1: TEXT SUBJECT KE PEECHHE (reference: POISON)
                s = 1 + push * (0.25 + 0.85 * near) * p
                L = self._scaled(lay, s, self.dir * 30 * near * p)
                out.paste(L, (0, 0), L)
        if self.behind and (self.fit_whole or getattr(self, "how", "") != "AI"):
            self._text_behind(out, t)            # AI depth nahi -> galat kata text nahi, seedha upar
        if not hasattr(self, "_black"): self._black = Image.new("RGB", (W, H), (0, 0, 0))
        out = Image.composite(out, self._black, self.vig)
        out = _sweep(out, t, 0.1, 0.8, 55)
        self.parts.draw(out, t)
        if self.name:
            _lower_third(out, t, self.name, self.desc, self.accent, W, H)
        return out


# ------------------------------------------------------------------ brand logo reveal
class LogoHero:
    def __init__(self, path, W, H, dur, name="", desc="", accent=(118, 185, 0), seed=2):
        self.W, self.H, self.dur, self.name, self.desc, self.accent = W, H, dur, name, desc, tuple(accent)
        lg = Image.open(path).convert("RGBA")
        bbox = lg.getbbox()
        if bbox: lg = lg.crop(bbox)
        # safed background wala logo -> safed ko transparent (dark bg pe saaf dikhe)
        arr = np.asarray(lg).astype(np.int16)
        if arr[..., 3].min() > 250:
            white = (arr[..., :3].min(axis=2) > 235)
            arr[..., 3] = np.where(white, 0, 255); lg = Image.fromarray(arr.astype("uint8"), "RGBA")
        arr = np.asarray(lg).copy()                                # dark-mode logo: kaale/gehre hisse safed
        lum = arr[..., :3].astype(float) @ np.array([0.299, 0.587, 0.114])
        dark = (lum < 75) & (arr[..., 3] > 20)
        arr[..., :3] = np.where(dark[..., None], 245, arr[..., :3]); lg = Image.fromarray(arr, "RGBA")
        f = min(W * 0.72 / lg.width, H * 0.24 / lg.height)
        self.logo = lg.resize((max(2, int(lg.width * f)), max(2, int(lg.height * f))), Image.LANCZOS)
        glow = Image.new("RGBA", self.logo.size, self.accent + (0,))
        glow.putalpha(self.logo.getchannel("A"))
        pad = int(W * 0.12)
        g = Image.new("RGBA", (self.logo.width + pad * 2, self.logo.height + pad * 2), (0, 0, 0, 0))
        g.paste(glow, (pad, pad), glow)
        self.glow = g.filter(ImageFilter.GaussianBlur(pad // 3))
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.42) / H) ** 2)
        c1 = np.array([6, 8, 12], float); c2 = np.array(self.accent, float) * 0.22
        k = np.clip(1 - r * 1.8, 0, 1)[..., None]
        self.bg = Image.fromarray(np.clip(c1 * (1 - k) + c2 * k, 0, 255).astype("uint8"), "RGB")
        self.parts = _Parts(W, H, 45, seed, self.accent)

    def frame(self, i, fps=30):
        from recipe import _project, _coeffs
        t = i / fps; W, H = self.W, self.H
        a = _ease(t / 0.9); p = t / max(self.dur, 0.5)
        out = self.bg.copy(); self.parts.draw(out, t)
        ry = 38 * (1 - a) + 6 * math.sin(p * math.pi * 0.8)          # 3D tilt-in phir halka jhoolna
        rx = 8 * (1 - a); sc = 0.82 + 0.18 * a + 0.04 * p
        lw, lh = self.logo.size
        cy = -0.15
        dst = _project(lw, lh, W, H, rx, ry, 0, sc, 0, cy)
        try:
            co = _coeffs(dst, [(0, 0), (lw, 0), (lw, lh), (0, lh)])
            warped = self.logo.transform((W, H), Image.PERSPECTIVE, co, Image.BICUBIC)
        except Exception:
            warped = Image.new("RGBA", (W, H)); warped.paste(self.logo, ((W - lw) // 2, int(H * 0.42 - lh / 2)))
        gl = self.glow.copy(); gl.putalpha(gl.getchannel("A").point(lambda v: int(v * (0.4 + 0.6 * a))))
        out.paste(gl, ((W - gl.width) // 2, int(H * (0.5 + cy) - gl.height / 2)), gl)
        # farsh pe parchhai (reflection)
        bb = warped.getchannel("A").getbbox()
        if bb:                                                     # farsh pe parchhai, logo ke theek neeche
            refl = warped.crop(bb).transpose(Image.FLIP_TOP_BOTTOM)
            fade = Image.linear_gradient("L").resize(refl.size).point(lambda v: int((255 - v) * 0.25))
            refl.putalpha(ImageChops.multiply(refl.getchannel("A"), fade))
            refl = refl.filter(ImageFilter.GaussianBlur(3))
            out.paste(refl, (bb[0], bb[3] + int(H * 0.01)), refl)
        out.paste(warped, (0, 0), warped)
        # logo pe light sweep (sirf logo ke andar)
        sw = _sweep(Image.new("RGB", (W, H), (0, 0, 0)), t, 0.6, 0.9, 120).convert("L")
        m = ImageChops.multiply(sw, warped.getchannel("A"))
        out = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), out, m)
        if self.name:
            d = ImageDraw.Draw(out, "RGBA"); b = _ease((t - 0.7) / 0.5)
            if b > 0:
                fn = _fit(self.name.upper(), F_HEAD, W * 0.8, W * 0.13, d)
                tw = d.textlength(self.name.upper(), font=fn)
                y = int(H * 0.515)
                d.text(((W - tw) / 2, y + (1 - b) * 30), self.name.upper(), font=fn, fill=(255, 255, 255, int(255 * b)))
                if self.desc:
                    fd = _font(F_SEMI, W * 0.033); dw = d.textlength(self.desc[:44], font=fd)
                    d.text(((W - dw) / 2, y + fn.size * 1.05), self.desc[:44], font=fd, fill=self.accent + (int(220 * b),))
        return out


# ------------------------------------------------------------------ name card (photo nahi mili)
class NameCard:
    def __init__(self, W, H, dur, name, desc="", accent=(255, 214, 10), seed=4):
        self.W, self.H, self.dur, self.name, self.desc, self.accent = W, H, dur, name, desc, tuple(accent)
        y, x = np.ogrid[:H, :W]
        r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.45) / H) ** 2)
        k = np.clip(1 - r * 1.6, 0, 1)[..., None]
        c1 = np.array([8, 8, 12], float); c2 = np.array(self.accent, float) * 0.25
        self.bg = Image.fromarray(np.clip(c1 * (1 - k) + c2 * k, 0, 255).astype("uint8"), "RGB")
        self.parts = _Parts(W, H, 50, seed, self.accent)

    def frame(self, i, fps=30):
        t = i / fps; W, H = self.W, self.H
        out = self.bg.copy(); self.parts.draw(out, t)
        d = ImageDraw.Draw(out, "RGBA")
        a = _ease(t / 0.55); zoom = 1 + 0.05 * t / max(self.dur, 0.5)
        txt = self.name.upper()
        fn = _fit(txt, F_HEAD, W * 0.86, W * 0.2 * zoom, d)
        tw = d.textlength(txt, font=fn); y = H * 0.40
        spacing = (1 - a) * W * 0.03
        x = (W - tw - spacing * (len(txt) - 1)) / 2
        for ch in txt:                                             # tracking-in (akshar paas aate hain)
            d.text((x, y), ch, font=fn, fill=(255, 255, 255, int(255 * a)))
            x += d.textlength(ch, font=fn) + spacing
        lw = W * 0.25 * _ease((t - 0.3) / 0.5)
        if lw > 2:
            d.rounded_rectangle((W / 2 - lw / 2, y - fn.size * 0.25, W / 2 + lw / 2, y - fn.size * 0.25 + W * 0.008),
                                radius=3, fill=self.accent + (230,))
        if self.desc:
            b = _ease((t - 0.45) / 0.45)
            fd = _font(F_SEMI, W * 0.036); dw = d.textlength(self.desc[:46], font=fd)
            d.text(((W - dw) / 2, y + fn.size * 1.05 + (1 - b) * 20), self.desc[:46], font=fd, fill=self.accent + (int(230 * b),))
        return _sweep(out, t, 0.5, 0.9, 40)


BRAND_COLORS = {"nvidia": (118, 185, 0), "google": (66, 133, 244), "apple": (220, 220, 220), "microsoft": (0, 164, 239),
                "amazon": (255, 153, 0), "tesla": (232, 33, 39), "samsung": (20, 40, 160), "netflix": (229, 9, 20),
                "youtube": (255, 0, 0), "meta": (0, 129, 251), "facebook": (24, 119, 242), "openai": (16, 163, 127),
                "intel": (0, 113, 197), "amd": (237, 28, 36), "reliance": (0, 80, 160), "tata": (72, 109, 180)}


def render(item, dur, out, W, H, style, fps=30, accent=None):
    """item: sources ka hero item (path, entity, etype, role). Return out ya None."""
    import fx
    n = max(2, int(round(dur * fps)))
    name = item.get("entity") or ""; desc = item.get("desc") or ""
    acc = accent or BRAND_COLORS.get(name.lower().split()[0] if name else "")
    if not acc and item.get("role") == "logo":                 # logo ka apna rang (sabse chatkila hissa)
        try:
            a = np.asarray(Image.open(item["path"]).convert("RGB").resize((64, 64))).reshape(-1, 3).astype(float)
            sat = a.max(1) - a.min(1); pick = a[sat > 60]
            if len(pick): acc = tuple(int(v) for v in pick.mean(0))
        except Exception:
            pass
    acc = acc or (255, 214, 10)
    if item.get("role") == "logo":
        h = LogoHero(item["path"], W, H, dur, name, desc, acc)
    elif item.get("namecard"):
        h = NameCard(W, H, dur, name, desc, acc)
    else:
        from common import yes as _yes
        h = PhotoHero(item["path"], W, H, dur, name if item.get("show_name", True) else "", desc, acc,
                      seed=int(item.get("seed", abs(hash(str(item.get("path")))) % 97)),
                      behind=item.get("kw_behind", ""), mode=item.get("motion"), crop_v=int(item.get("crop_v") or 0),
                      whole=_yes(style.get("photo_poora", "haan")),
                      focus_text=item.get("focus_text") or (f"{name}, {desc}" if name else ""))
    return fx._pipe_frames(lambda i: h.frame(i, fps), n, W, H, out, style, fps)
