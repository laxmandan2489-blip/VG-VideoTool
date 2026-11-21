"""v3.20 DOCUMENTARY & EXPLAINER MOTION-GRAPHICS CARDS (PIL + NumPy -> FFmpeg pipe).

After Effects / Documentary / Dhruv Rathee-style animated scenes rendered at native
1080x1920 30fps without requiring Node.js or external renderers:

  1. render_news_highlight  : Dark grunge canvas + crisp newspaper/fact card + animated yellow
                              marker highlighter sweep (left-to-right ease-out).
  2. render_polaroid_archival: Blueprint/vintage textured backdrop + tilted Polaroid archival
                              photo + masking tape + soft shadow + ease-out slide-in.
  3. render_stat_pro        : Rolling number counter + glowing neon accent + up/down trend
                              chevrons + optional red STAMP SLAM with micro camera shake.
  4. render_data_table      : Dark comparison table with staggered rows & yellow row highlight.
"""
import math
import random
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .bible import font_path
from .cards import NUM_RE, _fit_font, latin

STAMP_WORDS = {
    "SCAM", "DANGER", "ALERT", "BANNED", "ILLEGAL", "FAKE", "SHOCKING",
    "WARNING", "CRISIS", "REJECT", "INVALID", "ARRESTED", "GUILTY", "BIGGEST",
}


def _ease_out(t):
    t = max(0.0, min(1.0, float(t)))
    return 1.0 - (1.0 - t) ** 3


def _ease_back(t):
    """Subtle spring overshoot (After Effects style) without cartoonish bounce."""
    t = max(0.0, min(1.0, float(t)))
    c1 = 1.35
    c3 = c1 + 1.0
    return 1.0 + c3 * ((t - 1.0) ** 3) + c1 * ((t - 1.0) ** 2)


def _grunge_bg(W, H, pal, seed=0, grid=False):
    """Dark textured documentary background with vignette, film grain, and optional blueprint grid."""
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    c1 = np.array(pal.get("bg1", (14, 18, 26)), dtype=np.float32) * 0.78
    c2 = np.array(pal.get("bg2", (26, 36, 52)), dtype=np.float32) * 0.85
    r = np.sqrt((x - 0.5) ** 2 * 1.45 + (y - 0.45) ** 2 * 1.25)
    k = np.clip(1.0 - r * 1.35, 0.0, 1.0)[..., None]
    img = c1 * (1.0 - k) + c2 * k

    # Soft vignette darkening at edges
    vig = np.clip(1.0 - (r ** 2) * 0.55, 0.45, 1.0)[..., None]
    img *= vig

    # Subtle paper/film grain
    rng = np.random.default_rng(seed)
    img += rng.normal(0, 4.2, (H, W, 1)).astype(np.float32)
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")

    if grid:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        step = max(48, W // 18)
        for gx in range(0, W, step):
            d.line([(gx, 0), (gx, H)], fill=(140, 185, 230, 18), width=1)
        for gy in range(0, H, step):
            d.line([(0, gy), (W, gy)], fill=(140, 185, 230, 18), width=1)
        # Stronger major grid lines every 4 cells
        for gx in range(0, W, step * 4):
            d.line([(gx, 0), (gx, H)], fill=(140, 185, 230, 32), width=2)
        for gy in range(0, H, step * 4):
            d.line([(0, gy), (W, gy)], fill=(140, 185, 230, 32), width=2)
        base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
    return base


def _wrap_text(text, font, max_w):
    words = (text or "").split()
    if not words:
        return []
    lines, cur = [], words[0]
    for w in words[1:]:
        test = cur + " " + w
        if font.getlength(test) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _draw_shadow_box(canvas, box, radius=20, fill=(248, 245, 238, 255), shadow_alpha=115, blur=22):
    W, H = canvas.size
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    x0, y0, x1, y1 = box
    sd.rounded_rectangle((x0 + 8, y0 + 18, x1 + 8, y1 + 18), radius=radius, fill=(0, 0, 0, shadow_alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh)
    cd = ImageDraw.Draw(canvas)
    cd.rounded_rectangle(box, radius=radius, fill=fill)


# ------------------------------------------------------------------ 1. News / Fact Highlighter Card
class NewsHighlightCard:
    def __init__(self, source, headline, highlight_phrase, W, H, pal, dur, date_str=""):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.source = latin(source or "FACT REPORT").upper()
        self.headline = latin(headline or "").strip()
        self.hl = latin(highlight_phrase or "").strip()
        self.date_str = latin(date_str or "VERIFIED FACT BRIEF")
        self.bg = _grunge_bg(W, H, pal, seed=len(self.headline) * 13 + 7, grid=True).filter(ImageFilter.GaussianBlur(3))
        self.f_src = _fit_font("bold", self.source, W * 0.72, int(W * 0.044))
        self.f_date = _fit_font("serif", self.date_str, W * 0.72, int(W * 0.028))
        self.f_head = _fit_font("bold", "W" * 18, W * 0.76, int(W * 0.056))
        self.lines = _wrap_text(self.headline, self.f_head, int(W * 0.74))[:5]
        # Pick which line gets the yellow marker sweep
        self.hl_idx = -1
        if self.hl:
            hll = self.hl.lower()
            for idx, ln in enumerate(self.lines):
                if any(tok in ln.lower() for tok in hll.split() if len(tok) > 2):
                    self.hl_idx = idx
                    break
        if self.hl_idx < 0 and self.lines:
            self.hl_idx = min(1, len(self.lines) - 1)

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")

        # Slow documentary zoom-drift on card
        enter = _ease_back(t / 0.48)
        y_slide = int((1.0 - _ease_out(t / 0.45)) * (H * 0.08))
        card_w = int(W * 0.86)
        line_h = int(self.f_head.size * 1.38)
        card_h = int(W * 0.24 + max(2, len(self.lines)) * line_h + W * 0.12)
        cx, cy = W // 2, int(H * 0.46) + y_slide
        x0, y0 = cx - card_w // 2, cy - card_h // 2
        x1, y1 = x0 + card_w, y0 + card_h

        # Render card onto its own layer so we can scale/fade smoothly
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _draw_shadow_box(layer, (x0, y0, x1, y1), radius=24, fill=(249, 246, 239, 255))
        d = ImageDraw.Draw(layer)

        # Top crimson/accent masthead bar
        acc_bar = (196, 38, 38, 255)
        d.rounded_rectangle((x0, y0, x1, y0 + 14), radius=6, fill=acc_bar)

        # Source masthead + date + divider
        pad = int(W * 0.055)
        d.text((x0 + pad, y0 + 34), self.source, font=self.f_src, fill=(185, 28, 28, 255))
        d.text((x0 + pad, y0 + 34 + self.f_src.size + 8), self.date_str, font=self.f_date, fill=(105, 105, 112, 255))
        div_y = y0 + 34 + self.f_src.size + self.f_date.size + 26
        d.line([(x0 + pad, div_y), (x1 - pad, div_y)], fill=(210, 206, 196, 255), width=2)

        # Headline text + animated yellow marker highlighter sweep
        hl_prog = _ease_out((t - 0.55) / 0.65)
        ty = div_y + 28
        for idx, ln in enumerate(self.lines):
            if idx == self.hl_idx and hl_prog > 0.01:
                tw = int(self.f_head.getlength(ln))
                hx0 = x0 + pad - 10
                hx1 = hx0 + int((tw + 20) * hl_prog)
                hy0 = ty - 4
                hy1 = ty + self.f_head.size + 10
                d.rounded_rectangle((hx0, hy0, max(hx0 + 4, hx1), hy1), radius=8, fill=(255, 224, 54, 235))
            d.text((x0 + pad, ty), ln, font=self.f_head, fill=(22, 24, 30, 255))
            ty += line_h

        # Subtle scale entrance + slow zoom drift
        sc = (0.90 + 0.10 * min(1.03, enter)) * (1.0 + 0.025 * (t / self.dur))
        if abs(sc - 1.0) > 0.002:
            nw, nh = max(2, int(W * sc)), max(2, int(H * sc))
            scaled = layer.resize((nw, nh), Image.Resampling.BILINEAR)
            ox, oy = (W - nw) // 2, (H - nh) // 2
            base.alpha_composite(scaled, (ox, oy))
        else:
            base.alpha_composite(layer)

        # v3.47 VOX/JOHNNY HARRIS SUBTLE FLOATING TILT (2.0 -> 0.6 deg)
        try:
            _ang = 2.0 - 1.4 * min(1.0, t / max(0.8, self.dur * 0.7))
            _rot = base.rotate(_ang, resample=Image.BICUBIC, expand=False)
            _z = 1.04
            _zw, _zh = int(W * _z), int(H * _z)
            _rot = _rot.resize((_zw, _zh), Image.BILINEAR)
            _x0, _y0 = (_zw - W) // 2, (_zh - H) // 2
            return _rot.crop((_x0, _y0, _x0 + W, _y0 + H)).convert("RGB")
        except Exception:
            return base.convert("RGB")


# ------------------------------------------------------------------ 2. Polaroid Archival Card
class PolaroidArchivalCard:
    def __init__(self, img_path, caption, W, H, pal, dur, angle=-2.6):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.angle = angle
        self.caption = latin(caption or "").strip()[:56]
        self.bg = _grunge_bg(W, H, pal, seed=len(str(img_path)) * 11, grid=True)
        self.photo = Image.open(img_path).convert("RGB")
        self.f_cap = _fit_font("serif", self.caption or "ARCHIVE", W * 0.72, int(W * 0.036))

        # Pre-render the Polaroid card once for fast frame compositing
        pw = int(W * 0.80)
        pad = int(W * 0.032)
        bot_pad = int(W * 0.12)
        img_w = pw - 2 * pad
        ar = self.photo.height / max(1, self.photo.width)
        img_h = int(min(H * 0.44, max(W * 0.45, img_w * ar)))
        ph = pad + img_h + bot_pad

        # Center-crop photo cleanly to (img_w, img_h)
        scale = max(img_w / self.photo.width, img_h / self.photo.height)
        rw, rh = max(img_w, int(self.photo.width * scale)), max(img_h, int(self.photo.height * scale))
        crop_p = self.photo.resize((rw, rh), Image.Resampling.LANCZOS)
        left, top = (rw - img_w) // 2, (rh - img_h) // 2
        crop_p = crop_p.crop((left, top, left + img_w, top + img_h))

        # Build Polaroid frame + masking tape
        canvas_pad = 90
        card = Image.new("RGBA", (pw + canvas_pad * 2, ph + canvas_pad * 2), (0, 0, 0, 0))
        # Shadow
        sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            (canvas_pad + 10, canvas_pad + 20, canvas_pad + pw + 10, canvas_pad + ph + 20),
            radius=10, fill=(0, 0, 0, 140),
        )
        sh = sh.filter(ImageFilter.GaussianBlur(22))
        card.alpha_composite(sh)

        # Cream archival paper border
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle(
            (canvas_pad, canvas_pad, canvas_pad + pw, canvas_pad + ph),
            radius=8, fill=(246, 242, 232, 255),
        )
        card.paste(crop_p, (canvas_pad + pad, canvas_pad + pad))

        # Masking tape strip on top-center
        tape_w, tape_h = int(pw * 0.28), int(W * 0.048)
        tx0 = canvas_pad + pw // 2 - tape_w // 2
        ty0 = canvas_pad - tape_h // 2 + 6
        cd.polygon(
            [(tx0 + 6, ty0), (tx0 + tape_w, ty0 + 3), (tx0 + tape_w - 5, ty0 + tape_h), (tx0, ty0 + tape_h - 3)],
            fill=(232, 212, 162, 195),
        )

        # Caption in bottom Polaroid margin
        if self.caption:
            tw = cd.textlength(self.caption, font=self.f_cap)
            cd.text(
                (canvas_pad + pw / 2 - tw / 2, canvas_pad + pad + img_h + (bot_pad - self.f_cap.size) / 2),
                self.caption, font=self.f_cap, fill=(45, 42, 38, 240),
            )

        self.card_rgba = card.rotate(self.angle, resample=Image.Resampling.BICUBIC, expand=True)

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")

        p = _ease_out(t / 0.55)
        drift_sc = 1.0 + 0.045 * (t / self.dur)
        y_off = int((1.0 - p) * H * 0.14)
        cw, ch = self.card_rgba.size
        nw, nh = max(2, int(cw * drift_sc)), max(2, int(ch * drift_sc))
        c_img = self.card_rgba.resize((nw, nh), Image.Resampling.BILINEAR)

        ox = (W - nw) // 2
        oy = int(H * 0.45) - nh // 2 + y_off
        base.alpha_composite(c_img, (ox, oy))
        return base.convert("RGB")


# ------------------------------------------------------------------ 3. Pro Stat Counter + Stamp Slam
class StatCounterProCard:
    def __init__(self, value, label, W, H, pal, dur, sub="", stamp="", trend=""):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.value = latin(value or "").upper()
        self.label = latin(label or "").upper()
        self.sub = latin(sub or "")
        self.stamp = latin(stamp or "").upper()
        self.trend = (trend or "").lower()  # "up" | "down" | ""
        self.bg = _grunge_bg(W, H, pal, seed=len(self.value) * 19 + 3, grid=True)
        self.f_num = _fit_font("head", self.value or "0", W * 0.80, int(W * 0.24))
        self.f_lab = _fit_font("bold", self.label or "DATA", W * 0.84, int(W * 0.068))
        self.f_sub = _fit_font("serif", self.sub, W * 0.82, int(W * 0.045)) if self.sub else None
        self.f_st = _fit_font("impact", self.stamp or "ALERT", W * 0.58, int(W * 0.11)) if self.stamp else None

    def _count(self, p):
        def rep(mo):
            s = mo.group(1)
            v = float(s.replace(",", ""))
            dec = len(s.split(".")[1]) if "." in s else 0
            cur = v * p
            return f"{cur:,.{dec}f}" if "," in s else f"{cur:.{dec}f}"
        return NUM_RE.sub(rep, self.value)

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")

        # Micro camera shake right after stamp slam (t in 0.65..0.88)
        sx, sy = 0, 0
        if self.stamp and 0.65 <= t <= 0.88:
            decay = 1.0 - (t - 0.65) / 0.23
            sx = int(14 * decay * math.sin(t * 95))
            sy = int(10 * decay * math.cos(t * 110))

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        cy = int(H * 0.42)

        # Accent color by trend
        if self.trend == "down":
            acc = (64, 232, 130)
        elif self.trend == "up":
            acc = (255, 84, 74)
        else:
            acc = tuple(self.pal.get("accent", (255, 212, 0)))

        # Rolling counter
        p = _ease_out((t - 0.08) / 0.85)
        val = self._count(p) if p < 0.999 else self.value
        tw = d.textlength(val, font=self.f_num)
        tx, ty = W / 2 - tw / 2, cy - self.f_num.size * 0.55

        # Neon glow behind number
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).text((tx, ty), val, font=self.f_num, fill=acc + (175,))
        gl = gl.filter(ImageFilter.GaussianBlur(max(8, self.f_num.size // 10)))
        layer.alpha_composite(gl)
        d.text((tx + 5, ty + 6), val, font=self.f_num, fill=(0, 0, 0, 150))
        d.text((tx, ty), val, font=self.f_num, fill=acc + (255,))

        # Animated trend chevrons next to number
        if self.trend in ("up", "down") and t > 0.35:
            cx_a = int(tx + tw + W * 0.045)
            bob = int(8 * math.sin(t * 7))
            for k in range(2):
                ay = int(cy - 18 + k * 28 + (bob if self.trend == "down" else -bob))
                pts = ([(cx_a - 18, ay - 8), (cx_a, ay + 10), (cx_a + 18, ay - 8)]
                       if self.trend == "down"
                       else [(cx_a - 18, ay + 10), (cx_a, ay - 8), (cx_a + 18, ay + 10)])
                d.line(pts, fill=acc + (235,), width=7, joint="curve")

        # Label pill below number
        la = _ease_out((t - 0.30) / 0.35)
        if la > 0.02 and self.label:
            lw = d.textlength(self.label, font=self.f_lab)
            ly = int(cy + self.f_num.size * 0.62 + (1.0 - la) * 26)
            d.rounded_rectangle(
                (W / 2 - lw / 2 - 26, ly - 10, W / 2 + lw / 2 + 26, ly + self.f_lab.size + 14),
                radius=14, fill=(255, 255, 255, int(24 * la)), outline=acc + (int(120 * la),), width=2,
            )
            d.text((W / 2 - lw / 2, ly), self.label, font=self.f_lab, fill=(255, 255, 255, int(255 * la)))
            if self.f_sub:
                sub_lines = _wrap_text(self.sub, self.f_sub, int(W * 0.84))[:2]
                for si, sl in enumerate(sub_lines):
                    sw = d.textlength(sl, font=self.f_sub)
                    d.text((W / 2 - sw / 2, ly + self.f_lab.size + 30 + si * int(self.f_sub.size * 1.32)), sl,
                           font=self.f_sub, fill=(215, 220, 230, int(230 * la)))

        # Slanted red STAMP SLAM (Dhruv Rathee SCAM / DANGER style)
        if self.stamp and self.f_st and t >= 0.55:
            sp = _ease_out((t - 0.55) / 0.14)
            st_sc = 1.65 - 0.65 * sp
            stw = int(self.f_st.getlength(self.stamp)) + 64
            sth = int(self.f_st.size * 1.45)
            st_im = Image.new("RGBA", (stw, sth), (0, 0, 0, 0))
            sd = ImageDraw.Draw(st_im)
            red = (225, 42, 42, int(245 * sp))
            sd.rounded_rectangle((4, 4, stw - 4, sth - 4), radius=12, fill=(180, 20, 20, int(65 * sp)), outline=red, width=8)
            sd.text((32, int(sth * 0.15)), self.stamp, font=self.f_st, fill=red)
            st_im = st_im.rotate(11, resample=Image.Resampling.BICUBIC, expand=True)
            sw2, sh2 = max(2, int(st_im.width * st_sc)), max(2, int(st_im.height * st_sc))
            st_im = st_im.resize((sw2, sh2), Image.Resampling.BILINEAR)
            layer.alpha_composite(st_im, (W // 2 - sw2 // 2, int(H * 0.22) - sh2 // 2))

        base.alpha_composite(layer, (sx, sy))
        return base.convert("RGB")


# ------------------------------------------------------------------ 4. Comparison Data Table Card
class DataTableCard:
    def __init__(self, title, rows, highlight_row, W, H, pal, dur):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.title = latin(title or "COMPARISON").upper()
        self.rows = [(latin(str(a)), latin(str(b))) for a, b in (rows or [])[:6]]
        self.hl_row = highlight_row
        self.bg = _grunge_bg(W, H, pal, seed=len(self.title) * 23, grid=True)
        self.f_t = _fit_font("bold", self.title, W * 0.82, int(W * 0.06))
        self.f_r = _fit_font("bold", "W" * 20, W * 0.78, int(W * 0.042))

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")
        d = ImageDraw.Draw(base)

        tw = d.textlength(self.title, font=self.f_t)
        y_top = int(H * 0.25)
        d.text((W / 2 - tw / 2, y_top), self.title, font=self.f_t, fill=(255, 224, 64, 255))

        row_h = int(H * 0.068)
        margin_x = int(W * 0.08)
        y = y_top + self.f_t.size + 42
        for idx, (c1, c2) in enumerate(self.rows):
            rp = _ease_out((t - 0.12 * idx) / 0.32)
            if rp <= 0.01:
                continue
            dx = int((1.0 - rp) * 40)
            box = (margin_x + dx, y, W - margin_x + dx, y + row_h - 10)
            is_hl = (idx == self.hl_row)
            hl_p = _ease_out((t - 0.55) / 0.45) if is_hl else 0.0
            d.rounded_rectangle(box, radius=12, fill=(28, 34, 46, int(220 * rp)), outline=(255, 255, 255, 30), width=1)
            if is_hl and hl_p > 0.01:
                hx1 = box[0] + int((box[2] - box[0]) * hl_p)
                d.rounded_rectangle((box[0], box[1], max(box[0] + 8, hx1), box[3]), radius=12, fill=(255, 220, 48, 240))
            txt_col = (20, 22, 28, int(255 * rp)) if (is_hl and hl_p > 0.35) else (240, 242, 248, int(255 * rp))
            d.text((box[0] + 24, y + (row_h - 10 - self.f_r.size) // 2 - 2), c1, font=self.f_r, fill=txt_col)
            w2 = d.textlength(c2, font=self.f_r)
            d.text((box[2] - w2 - 24, y + (row_h - 10 - self.f_r.size) // 2 - 2), c2, font=self.f_r, fill=txt_col)
            y += row_h
        return base.convert("RGB")


# ------------------------------------------------------------------ Public Render Helpers
def render_news_highlight(source, headline, highlight_phrase, dur, out, W, H, style, pal, date_str="", fps=30):
    import fx
    c = NewsHighlightCard(source, headline, highlight_phrase, W, H, pal, dur, date_str)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)


def render_polaroid_archival(img_path, caption, dur, out, W, H, style, pal, angle=-2.6, fps=30):
    import fx
    c = PolaroidArchivalCard(img_path, caption, W, H, pal, dur, angle)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)


def render_stat_pro(value, label, dur, out, W, H, style, pal, sub="", stamp="", trend="", fps=30):
    import fx
    c = StatCounterProCard(value, label, W, H, pal, dur, sub, stamp, trend)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)


def render_data_table(title, rows, highlight_row, dur, out, W, H, style, pal, fps=30):
    import fx
    c = DataTableCard(title, rows, highlight_row, W, H, pal, dur)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)


# ------------------------------------------------------------------ 5. 2.5D Cutout Parallax Card (Ref Video 1 & 2)
class CutoutParallaxCard:
    """3-layer 2.5D depth parallax: dark grunge/grid bg -> glowing radar ring & big text -> subject cutout/spotlight."""
    def __init__(self, img_path, bg_word, W, H, pal, dur):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.bg_word = latin(bg_word or "").upper()[:14]
        self.bg = _grunge_bg(W, H, pal, seed=len(str(img_path)) * 17, grid=True)
        self.f_bg = _fit_font("head", self.bg_word or "FACT", W * 0.90, int(W * 0.24))

        raw = Image.open(img_path).convert("RGBA")
        # Try rembg automatic background cutout if installed; otherwise crisp elliptical vignette portrait/subject mask
        cut = None
        try:
            from rembg import remove
            cut = remove(raw)
        except Exception:
            cut = None

        if cut is None:
            # Clean rounded-spotlight subject card so it looks sharp even without rembg
            sw = int(W * 0.84)
            ar = raw.height / max(1, raw.width)
            sh = int(min(H * 0.56, max(W * 0.72, sw * ar)))
            sc = max(sw / raw.width, sh / raw.height)
            rw, rh = max(sw, int(raw.width * sc)), max(sh, int(raw.height * sc))
            resized = raw.resize((rw, rh), Image.Resampling.LANCZOS)
            l0, t0 = (rw - sw) // 2, (rh - sh) // 2
            resized = resized.crop((l0, t0, l0 + sw, t0 + sh))
            mask = Image.new("L", (sw, sh), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, sw, sh), radius=34, fill=255)
            resized.putalpha(mask)
            cut = resized
        else:
            sc = min((W * 0.86) / max(1, cut.width), (H * 0.62) / max(1, cut.height))
            cut = cut.resize((max(2, int(cut.width * sc)), max(2, int(cut.height * sc))), Image.Resampling.LANCZOS)
        self.fg = cut

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        p = _ease_out(t / 0.55)
        prog = t / self.dur

        # Layer 1: Background zooms slowly (1.0 -> 1.04)
        bg_sc = 1.0 + 0.04 * prog
        bw, bh = int(W * bg_sc), int(H * bg_sc)
        base = self.bg.resize((bw, bh), Image.Resampling.BILINEAR).crop(
            ((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H)
        ).convert("RGBA")

        # Layer 2: Glowing radar ring + bold background text behind subject
        mid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        md = ImageDraw.Draw(mid)
        acc = tuple(self.pal.get("accent", (80, 195, 255)))
        cy = int(H * 0.46)
        R = int(W * (0.34 + 0.03 * math.sin(t * 2.5)))
        md.ellipse((W // 2 - R, cy - R, W // 2 + R, cy + R), outline=acc + (135,), width=6)
        md.ellipse((W // 2 - R - 26, cy - R - 26, W // 2 + R + 26, cy + R + 26), outline=acc + (55,), width=3)
        if self.bg_word:
            tw = md.textlength(self.bg_word, font=self.f_bg)
            md.text((W / 2 - tw / 2, int(H * 0.19)), self.bg_word, font=self.f_bg, fill=(255, 255, 255, int(65 * p)))
        base.alpha_composite(mid)

        # Layer 3: Foreground subject zooms slightly faster (2.5D parallax!) + soft shadow
        fg_sc = (0.92 + 0.08 * p) * (1.0 + 0.075 * prog)
        fw, fh = max(2, int(self.fg.width * fg_sc)), max(2, int(self.fg.height * fg_sc))
        fg_s = self.fg.resize((fw, fh), Image.Resampling.BILINEAR)
        ox = (W - fw) // 2
        oy = int(H * 0.48) - fh // 2 + int((1.0 - p) * H * 0.06)
        base.alpha_composite(fg_s, (ox, oy))
        return base.convert("RGB")


# ------------------------------------------------------------------ 6. Chart + Animated Red Circle (Ref Video 3)
class ChartCalloutCard:
    """Dhruv Rathee-style animated line chart with a glowing red hand-drawn circle on the key point."""
    def __init__(self, title, points, callout_idx, callout_label, W, H, pal, dur):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.title = latin(title or "TREND ANALYSIS").upper()
        self.points = points or [40, 62, 55, 88, 30, 74, 92]
        self.c_idx = max(0, min(len(self.points) - 1, callout_idx))
        self.c_label = latin(callout_label or "KEY DROP").upper()
        self.bg = _grunge_bg(W, H, pal, seed=len(self.title) * 31, grid=True)
        self.f_t = _fit_font("bold", self.title, W * 0.82, int(W * 0.056))
        self.f_c = _fit_font("bold", self.c_label, W * 0.48, int(W * 0.044))

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")
        d = ImageDraw.Draw(base)

        # White/cream chart card
        cw, ch = int(W * 0.86), int(H * 0.34)
        x0, y0 = (W - cw) // 2, int(H * 0.30)
        x1, y1 = x0 + cw, y0 + ch
        _draw_shadow_box(base, (x0, y0, x1, y1), radius=20, fill=(248, 249, 252, 255))
        d = ImageDraw.Draw(base)

        tw = d.textlength(self.title, font=self.f_t)
        d.text((W / 2 - tw / 2, y0 - self.f_t.size - 28), self.title, font=self.f_t, fill=(255, 224, 64, 255))

        # Plot coordinates
        pad = 54
        lo, hi = min(self.points), max(self.points)
        span = max(1e-5, hi - lo)
        coords = []
        for idx, val in enumerate(self.points):
            px = x0 + pad + (cw - 2 * pad) * (idx / max(1, len(self.points) - 1))
            py = y1 - pad - (ch - 2 * pad) * ((val - lo) / span)
            coords.append((px, py))

        # Draw subtle chart grid lines
        for k in range(4):
            gy = int(y0 + pad + (ch - 2 * pad) * k / 3)
            d.line([(x0 + pad, gy), (x1 - pad, gy)], fill=(215, 222, 232, 255), width=2)

        # Animate blue line left-to-right
        lp = _ease_out(t / 0.85)
        n_segs = len(coords) - 1
        cur_f = lp * n_segs
        draw_pts = [coords[0]]
        for s in range(n_segs):
            if cur_f >= s + 1:
                draw_pts.append(coords[s + 1])
            elif cur_f > s:
                frac = cur_f - s
                nx = coords[s][0] + (coords[s + 1][0] - coords[s][0]) * frac
                ny = coords[s][1] + (coords[s + 1][1] - coords[s][1]) * frac
                draw_pts.append((nx, ny))
                break
        if len(draw_pts) >= 2:
            d.line(draw_pts, fill=(32, 128, 218, 255), width=7, joint="curve")

        # Animate glowing red hand-drawn circle around callout point
        if t > 0.70:
            cp = _ease_out((t - 0.70) / 0.50)
            cx, cy = coords[self.c_idx]
            rx, ry = 54, 68
            d.arc((cx - rx, cy - ry, cx + rx, cy + ry), start=-90, end=-90 + 355 * cp, fill=(225, 32, 32, 245), width=9)
            if cp > 0.5:
                lw = d.textlength(self.c_label, font=self.f_c)
                ly = y1 + 32
                d.rounded_rectangle((W / 2 - lw / 2 - 22, ly - 8, W / 2 + lw / 2 + 22, ly + self.f_c.size + 12),
                                    radius=12, fill=(225, 32, 32, 235))
                d.text((W / 2 - lw / 2, ly), self.c_label, font=self.f_c, fill=(255, 255, 255, 255))
        return base.convert("RGB")


# ------------------------------------------------------------------ 7. Documentary Timeline Card
class TimelineCard:
    """Animated milestone timeline (e.g. 2014 -> 2020 -> 2026) with glowing active node."""
    def __init__(self, title, milestones, active_idx, W, H, pal, dur):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.title = latin(title or "TIMELINE").upper()
        self.milestones = [(latin(str(y)), latin(str(lbl))) for y, lbl in (milestones or [])[:4]]
        self.active = max(0, min(len(self.milestones) - 1, active_idx)) if self.milestones else 0
        self.bg = _grunge_bg(W, H, pal, seed=len(self.title) * 41, grid=True)
        self.f_t = _fit_font("bold", self.title, W * 0.82, int(W * 0.058))
        self.f_y = _fit_font("head", "2026", W * 0.30, int(W * 0.072))
        self.f_l = _fit_font("bold", "W" * 18, W * 0.62, int(W * 0.042))

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")
        d = ImageDraw.Draw(base)

        tw = d.textlength(self.title, font=self.f_t)
        d.text((W / 2 - tw / 2, int(H * 0.21)), self.title, font=self.f_t, fill=(255, 224, 64, 255))

        lx = int(W * 0.22)
        y_start, y_end = int(H * 0.31), int(H * 0.68)
        lp = _ease_out(t / 0.65)
        d.line([(lx, y_start), (lx, int(y_start + (y_end - y_start) * lp))], fill=(120, 150, 195, 160), width=6)

        n = max(1, len(self.milestones))
        for idx, (yr, lbl) in enumerate(self.milestones):
            mp = _ease_out((t - 0.16 * idx) / 0.35)
            if mp <= 0.01:
                continue
            ny = int(y_start + (y_end - y_start) * (idx / max(1, n - 1))) if n > 1 else (y_start + y_end) // 2
            is_act = (idx == self.active)
            col = (255, 212, 0, int(255 * mp)) if is_act else (180, 200, 225, int(210 * mp))
            r = 20 if is_act else 13
            d.ellipse((lx - r, ny - r, lx + r, ny + r), fill=col, outline=(255, 255, 255, 220), width=3)
            dx = int((1.0 - mp) * 32)
            d.text((lx + 42 + dx, ny - self.f_y.size // 2 - 14), yr, font=self.f_y, fill=col)
            d.text((lx + 42 + dx, ny + self.f_y.size // 2 - 10), lbl[:34], font=self.f_l, fill=(235, 238, 245, int(235 * mp)))
        return base.convert("RGB")


def render_cutout_parallax(img_path, bg_word, dur, out, W, H, style, pal, fps=30):
    import fx
    c = CutoutParallaxCard(img_path, bg_word, W, H, pal, dur)
    return fx._pipe_frames(lambda i: c.frame(i, fps), max(2, int(round(dur * fps))), W, H, out, style, fps)


def render_chart_callout(title, points, callout_idx, callout_label, dur, out, W, H, style, pal, fps=30):
    import fx
    c = ChartCalloutCard(title, points, callout_idx, callout_label, W, H, pal, dur)
    return fx._pipe_frames(lambda i: c.frame(i, fps), max(2, int(round(dur * fps))), W, H, out, style, fps)


def render_timeline(title, milestones, active_idx, dur, out, W, H, style, pal, fps=30):
    import fx
    c = TimelineCard(title, milestones, active_idx, W, H, pal, dur)
    return fx._pipe_frames(lambda i: c.frame(i, fps), max(2, int(round(dur * fps))), W, H, out, style, fps)
