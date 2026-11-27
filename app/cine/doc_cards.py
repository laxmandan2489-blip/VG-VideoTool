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
    """v4.13 Realistic 2-Column Broadsheet Newspaper Clipping (Nitish Rajput / Dhruv Rathee style)."""

    def __init__(self, source, headline, highlight_phrase, W, H, pal, dur, date_str=""):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(0.8, dur)
        self.source = latin(source or "THE DAILY CHRONICLE").upper()
        self.headline = latin(headline or "").strip()
        self.hl = latin(highlight_phrase or "").strip()
        self.date_str = latin(date_str or "SPECIAL INVESTIGATION EDITION").upper()
        self.bg = _grunge_bg(W, H, pal, seed=len(self.headline) * 13 + 7, grid=True).filter(ImageFilter.GaussianBlur(3))
        self.f_mast = _fit_font("serif", self.source, W * 0.72, int(W * 0.052))
        self.f_meta = _fit_font("bold", self.date_str + "  |  PAGE A1", W * 0.76, int(W * 0.022))
        self.f_head = _fit_font("bold", "W" * 18, W * 0.76, int(W * 0.048))
        self.f_sub = _fit_font("serif", "SPECIAL REPORT & PUBLIC RECORD ARCHIVE", W * 0.76, int(W * 0.023))
        self.f_body = _fit_font("serif", "W" * 34, W * 0.36, int(W * 0.020))
        self.lines = _wrap_text(self.headline, self.f_head, int(W * 0.72))[:4]
        # Build topic-contextual surrounding newsprint columns (no blank space, no repetitive dots)
        _kw = " ".join(re.findall(r"[A-Za-z0-9]{3,}", self.headline)[:5]) or "the latest development"
        _src_lbl = self.source.title()
        self.col_left = _wrap_text(
            f"NEW DELHI — Official records and independent analysts reviewing {_kw} confirmed new details "
            f"earlier this week. According to documents cited by {_src_lbl}, timelines and public filings "
            f"point to major shifts across the sector as observers track the unfolding story closely.",
            self.f_body, int(W * 0.34),
        )[:6]
        self.col_right = _wrap_text(
            f"Further verification from industry trackers highlights how {_kw} drew widespread attention "
            f"nationwide. Experts quoted in the briefing noted that verified numbers and archival reports "
            f"remain central to understanding the full impact on audiences and stakeholders alike.",
            self.f_body, int(W * 0.34),
        )[:6]
        self.top_ticker = f"VOL. XLII  •  {self.date_str[:28]}  •  NATIONAL EDITION  •  P. 01"
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
        # Pre-generate warm realistic newsprint paper texture once
        self._paper_tex = self._make_paper_base()

    def _make_paper_base(self):
        W, H = self.W, self.H
        card_w = int(W * 0.88)
        card_h = int(H * (0.58 if H > W else 0.76))
        rng = np.random.default_rng(abs(hash(self.headline)) % 100000 + 413)
        # Warm aged newsprint cream with organic subtle paper grain
        base_rgb = np.zeros((card_h, card_w, 3), dtype=np.float32)
        base_rgb[:, :, 0] = 242.0
        base_rgb[:, :, 1] = 236.0
        base_rgb[:, :, 2] = 223.0
        grain = rng.normal(0.0, 4.2, (card_h, card_w, 1)).astype(np.float32)
        # Soft horizontal paper crease near middle
        yy = np.linspace(-1.0, 1.0, card_h, dtype=np.float32)[:, None]
        crease = -7.0 * np.exp(-((yy - 0.04) / 0.018) ** 2)
        # Gentle edge ageing vignette
        xx = np.linspace(-1.0, 1.0, card_w, dtype=np.float32)[None, :]
        edge = -10.0 * (xx ** 4 + yy ** 4) * 0.5
        arr = np.clip(base_rgb + grain + crease[:, :, None] + edge[:, :, None], 190, 252).astype(np.uint8)
        return Image.fromarray(arr, "RGB").convert("RGBA")

    def frame(self, i, fps=30):
        t = i / fps
        W, H = self.W, self.H
        base = self.bg.copy().convert("RGBA")

        enter = _ease_back(t / 0.48)
        y_slide = int((1.0 - _ease_out(t / 0.45)) * (H * 0.07))
        paper = self._paper_tex.copy()
        card_w, card_h = paper.size
        cx, cy = W // 2, int(H * 0.47) + y_slide
        x0, y0 = cx - card_w // 2, cy - card_h // 2

        d = ImageDraw.Draw(paper)
        pad = int(card_w * 0.055)
        ink_dark = (22, 22, 26, 255)
        ink_dim = (88, 84, 78, 220)
        ink_faint = (120, 115, 106, 195)
        rule_col = (46, 44, 42, 230)

        # Top crimson news strip + classic double masthead border
        d.rectangle((0, 0, card_w, 10), fill=(178, 28, 28, 255))
        y = 22
        # Centered newspaper masthead
        mw = int(self.f_mast.getlength(self.source))
        d.text(((card_w - mw) // 2, y), self.source, font=self.f_mast, fill=ink_dark)
        y += self.f_mast.size + 10
        d.line([(pad, y), (card_w - pad, y)], fill=rule_col, width=3)
        d.line([(pad, y + 5), (card_w - pad, y + 5)], fill=rule_col, width=1)
        y += 12
        # Edition/date ticker line
        tw_m = int(self.f_meta.getlength(self.top_ticker))
        d.text((max(pad, (card_w - tw_m) // 2), y), self.top_ticker, font=self.f_meta, fill=ink_dim)
        y += self.f_meta.size + 8
        d.line([(pad, y), (card_w - pad, y)], fill=(150, 145, 136, 220), width=1)
        y += 14

        # Subtle dimmed lead-in kicker above main headline
        d.text((pad, y), "SPECIAL REPORT  •  VERIFIED ARCHIVE", font=self.f_sub, fill=(168, 32, 32, 230))
        y += self.f_sub.size + 12

        # Main Headline + Animated Yellow Highlighter Sweep
        hl_prog = _ease_out((t - 0.50) / 0.65)
        line_h = int(self.f_head.size * 1.32)
        for idx, ln in enumerate(self.lines):
            if idx == self.hl_idx and hl_prog > 0.01:
                tw = int(self.f_head.getlength(ln))
                hx0 = pad - 8
                hx1 = hx0 + int((tw + 16) * hl_prog)
                hy0 = y - 3
                hy1 = y + self.f_head.size + 8
                d.rounded_rectangle((hx0, hy0, max(hx0 + 4, hx1), hy1), radius=6, fill=(255, 224, 48, 230))
            d.text((pad, y), ln, font=self.f_head, fill=ink_dark)
            y += line_h

        y += 10
        d.line([(pad, y), (card_w - pad, y)], fill=(165, 158, 148, 220), width=2)
        y += 14

        # Realistic 2-Column Newsprint Article Body (fills remaining broadsheet cleanly)
        mid_x = card_w // 2
        col_gap = int(card_w * 0.03)
        col1_x = pad
        col2_x = mid_x + col_gap // 2
        body_lh = int(self.f_body.size * 1.38)
        max_body_y = card_h - pad
        # Vertical column divider rule
        d.line([(mid_x, y), (mid_x, max(y + 10, max_body_y - 6))], fill=(180, 174, 162, 190), width=1)

        cy1 = y
        for bl in self.col_left:
            if cy1 + body_lh > max_body_y:
                break
            d.text((col1_x, cy1), bl, font=self.f_body, fill=ink_faint)
            cy1 += body_lh

        cy2 = y
        for bl in self.col_right:
            if cy2 + body_lh > max_body_y:
                break
            d.text((col2_x, cy2), bl, font=self.f_body, fill=ink_faint)
            cy2 += body_lh

        # Composite shadow + realistic newspaper clipping onto dark grunge backdrop
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _draw_shadow_box(layer, (x0, y0, x0 + card_w, y0 + card_h), radius=6, fill=(238, 232, 218, 255), shadow_alpha=145, blur=26)
        layer.alpha_composite(paper, (x0, y0))

        sc = (0.91 + 0.09 * min(1.03, enter)) * (1.0 + 0.03 * (t / self.dur))
        if abs(sc - 1.0) > 0.002:
            nw, nh = max(2, int(W * sc)), max(2, int(H * sc))
            scaled = layer.resize((nw, nh), Image.Resampling.BILINEAR)
            ox, oy = (W - nw) // 2, (H - nh) // 2
            base.alpha_composite(scaled, (ox, oy))
        else:
            base.alpha_composite(layer)

        try:
            _ang = 1.8 - 1.2 * min(1.0, t / max(0.8, self.dur * 0.7))
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
        _raw_v = re.sub(r"\s*(?:प्रतिशत|प्रतीशत|percent|per\s*cent|pratisht|pratishat)\b", "%", str(value or ""), flags=re.I)
        _raw_v = re.sub(r"\s+%", "%", _raw_v).strip()
        self.value = latin(_raw_v).upper()
        self.value = re.sub(r"\s*(?:PRATISHT|PRATISHAT|PERCENT)\b", "%", self.value).replace(" %", "%")
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
def _dc_font(name, size):
    from common import ASSETS
    for p in (
        ASSETS / "fonts" / name,
        Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"),
        ASSETS / "fonts" / "Mukta-ExtraBold.ttf",
        ASSETS / "fonts" / "Poppins-ExtraBold.ttf",
    ):
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()



_DEV_RUN_RE = re.compile(r"([\u0900-\u097F]+(?:\s+[\u0900-\u097F]+)*)")


def _draw_mixed_text(draw, xy, text, f_hi, f_en, fill):
    """v4.14: Render mixed Devanagari + English/Digits seamlessly with ZERO □□□□□ missing-glyph boxes."""
    x, y = xy
    parts = _DEV_RUN_RE.split(str(text or ""))
    for part in parts:
        if not part:
            continue
        is_dev = bool(re.search(r"[\u0900-\u097F]", part))
        fnt = f_hi if is_dev else f_en
        # Slight vertical baseline alignment for English font next to Devanagari
        dy = 0 if is_dev else max(0, int((getattr(f_hi, "size", 32) - getattr(f_en, "size", 32)) * 0.25))
        draw.text((x, y + dy), part, fill=fill, font=fnt)
        try:
            x += int(draw.textlength(part, font=fnt))
        except Exception:
            x += int(fnt.getlength(part))
    return x


def _wrap_mixed(text, f_hi, f_en, max_w):
    """Word-wrap mixed Devanagari + English text accurately."""
    words = str(text or "").split()
    lines, cur = [], ""
    def _wlen(s):
        tot = 0
        for part in _DEV_RUN_RE.split(s):
            if not part: continue
            fnt = f_hi if re.search(r"[\u0900-\u097F]", part) else f_en
            tot += fnt.getlength(part)
        return tot
    for w in words:
        cand = (cur + " " + w).strip() if cur else w
        if _wlen(cand) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _dc_persp(src_pts, dst_pts):
    m = []
    for s, d in zip(src_pts, dst_pts):
        m.append([d[0], d[1], 1, 0, 0, 0, -s[0] * d[0], -s[0] * d[1]])
        m.append([0, 0, 0, d[0], d[1], 1, -s[1] * d[0], -s[1] * d[1]])
    return np.linalg.solve(np.array(m, dtype=np.float64), np.array([c for pt in src_pts for c in pt], dtype=np.float64)).tolist()


class RealisticNewsProofCard:
    """v3.93 3 Realistic Documentary News Proof Styles (auto-rotated by category/headline):
      - broadsheet : Aged newsprint + halftone photo + warm amber multiply highlighter + macro DOF + dust motes
      - portal     : Modern Dark Digital News Portal (BBC/Reuters dark glass browser article)
      - broadcast  : 3D Paper-Cutout Headline Clipping + Breaking Broadcast Lower-Third Glass Bar
    """
    def __init__(self, source, headline, highlight_phrase, W, H, pal, dur, date_str="", variant="broadsheet"):
        self.W, self.H, self.pal, self.dur = W, H, pal, max(1.0, dur)
        self.source = (source or "VERIFIED ARCHIVE").strip()[:36].upper()
        self.headline = (headline or "Verified Documentary Record").strip()[:120]
        self.highlight = (highlight_phrase or self.headline).strip()[:160]
        self.date_str = (date_str or "DOCUMENTARY RECORD").strip()[:32].upper()
        self.variant = variant
        self.rng = np.random.default_rng(abs(hash(self.headline + variant)) % 10000)

        self.f_serif = _dc_font("DMSerifDisplay-Regular.ttf", max(28, int(W * 0.058)))
        self.f_sans = _dc_font("Poppins-ExtraBold.ttf", max(24, int(W * 0.044)))
        self.f_sm = _dc_font("Poppins-SemiBold.ttf", max(14, int(W * 0.024)))
        self.f_hi = _dc_font("NotoSansDevanagari-Bold.ttf", max(24, int(W * 0.040)))
        self.f_hi_lg = _dc_font("NotoSansDevanagari-Bold.ttf", max(30, int(W * 0.052)))
        self.motes = [(self.rng.uniform(0, W), self.rng.uniform(0, H), self.rng.uniform(1.5, 3.8),
                       self.rng.uniform(-10, 10), self.rng.uniform(-16, -4)) for _ in range(24)]

        if variant in ("broadsheet", "broadcast"):
            self._prep_broadsheet()

    def _prep_broadsheet(self):
        PW, PH = 960, 1280
        self.PW, self.PH = PW, PH
        yy, _ = np.mgrid[0:PH, 0:PW].astype(np.float32)
        p = np.zeros((PH, PW, 3), dtype=np.float32)
        p[..., 0] = 238 - 10 * (yy / PH)
        p[..., 1] = 231 - 12 * (yy / PH)
        p[..., 2] = 214 - 15 * (yy / PH)
        p = np.clip(p + self.rng.normal(0, 4.2, (PH, PW, 1)), 0, 255).astype(np.uint8)
        page = Image.fromarray(p, "RGB")
        d = ImageDraw.Draw(page, "RGBA")
        f_m = _dc_font("DMSerifDisplay-Regular.ttf", 48)
        f_s = _dc_font("Poppins-SemiBold.ttf", 17)
        f_sub = _dc_font("DMSerifDisplay-Regular.ttf", 22)
        f_body = _dc_font("Poppins-SemiBold.ttf", 14)

        # Classic Double-Rule Newspaper Masthead
        d.line([(55, 58), (PW - 55, 58)], fill=(25, 22, 20, 235), width=4)
        d.line([(55, 65), (PW - 55, 65)], fill=(25, 22, 20, 210), width=1)
        d.text((PW // 2, 108), self.source[:28], fill=(20, 18, 16, 245), font=f_m, anchor="mm")
        d.text((62, 148), self.date_str, fill=(65, 60, 54, 215), font=f_s)
        d.text((PW - 62, 148), "VOL. XLIV  •  NATIONAL & WORLD EDITION  •  P. 01", fill=(65, 60, 54, 215), font=f_s, anchor="ra")
        d.line([(55, 178), (PW - 55, 178)], fill=(25, 22, 20, 225), width=2)

        # TOP 2-COLUMN DISTINCT SURROUNDING NEWS STORIES (NO repeated placeholder lines!)
        d.line([(PW // 2, 194), (PW // 2, 386)], fill=(140, 132, 120, 185), width=1)
        d.text((62, 196), "GLOBAL MARKETS REACT TO POLICY SHIFT", fill=(48, 44, 40, 205), font=f_sub)
        top_left = _wrap_text(
            "NEW DELHI — Trade analysts and regional desks monitored diplomatic cables throughout the "
            "morning session as parliamentary committees reviewed freshly released briefs and archival filings.",
            f_body, 400,
        )[:5]
        for idx, tl in enumerate(top_left):
            d.text((62, 230 + idx * 26), tl, fill=(75, 70, 64, 175), font=f_body)

        d.text((PW // 2 + 24, 196), "REGIONAL SUMMIT AGENDA FINALIZED", fill=(48, 44, 40, 205), font=f_sub)
        top_right = _wrap_text(
            "GENEVA — Senior envoys confirmed bilateral talks will focus on border stability, energy "
            "corridors, and joint verification mechanisms scheduled for review later this quarter.",
            f_body, 400,
        )[:5]
        for idx, tr in enumerate(top_right):
            d.text((PW // 2 + 24, 230 + idx * 26), tr, fill=(75, 70, 64, 175), font=f_body)

        d.line([(55, 396), (PW - 55, 396)], fill=(30, 28, 25, 210), width=2)
        d.text((62, 420), f"SPECIAL INVESTIGATION  •  {self.source[:22]}", fill=(165, 28, 24, 240), font=f_s)

        # BOTTOM 2-COLUMN DISTINCT NEWSPRINT ARTICLES (zero repeated lines!)
        d.line([(55, 785), (PW - 55, 785)], fill=(30, 28, 25, 200), width=2)
        d.line([(PW // 2, 800), (PW // 2, 1210)], fill=(140, 132, 120, 185), width=1)
        d.text((62, 804), "PUBLIC ARCHIVES & OFFICIAL TIMELINE", fill=(48, 44, 40, 205), font=f_sub)
        bot_left = _wrap_text(
            "Declassified memos and contemporary press dispatches offer a detailed chronology of events "
            "leading up to the decisive announcement. Independent historians cross-checked parliamentary "
            "transcripts alongside broadcast recordings preserved in national libraries.",
            f_body, 400,
        )[:11]
        for idx, bl in enumerate(bot_left):
            d.text((62, 840 + idx * 28), bl, fill=(75, 70, 64, 175), font=f_body)

        d.text((PW // 2 + 24, 804), "EXPERTS WEIGH LONG-TERM IMPACT", fill=(48, 44, 40, 205), font=f_sub)
        bot_right = _wrap_text(
            "Observers note that decisions made during moments of intense pressure frequently reshape "
            "alliances for decades. Editorial boards across major capitals published follow-up analyses "
            "examining how institutional accountability and public scrutiny evolved in the aftermath.",
            f_body, 400,
        )[:11]
        for idx, br in enumerate(bot_right):
            d.text((PW // 2 + 24, 840 + idx * 28), br, fill=(75, 70, 64, 175), font=f_body)

        self.page_base = page
        self.f_pg_hi = _dc_font("NotoSansDevanagari-Bold.ttf", 40)
        self.f_pg_en = _dc_font("Poppins-ExtraBold.ttf", 38)
        self.f_art_hi = _dc_font("NotoSansDevanagari-Bold.ttf", 30)
        self.f_art_en = _dc_font("Poppins-SemiBold.ttf", 28)
        # v4.34: Support BOTH Bold Headline AND real 2-3 line highlighted article paragraph (zero blank space!)
        self.hl_lines = _wrap_mixed(self.headline, self.f_pg_hi, self.f_pg_en, PW - 140)[:2]
        _art_src = self.highlight if (self.highlight and self.highlight.lower() != self.headline.lower() and len(self.highlight) >= 18) else ""
        self.art_lines = _wrap_mixed(_art_src, self.f_art_hi, self.f_art_en, PW - 140)[:3] if _art_src else []

    def frame(self, i, fps):
        W, H = self.W, self.H
        t = min(1.0, max(0.0, i / max(1.0, self.dur * fps - 1.0)))
        ent = _ease_out(min(1.0, t / 0.24))
        hl = _ease_out(max(0.0, min(1.0, (t - 0.22) / 0.42)))

        if self.variant == "broadsheet":
            pg = self.page_base.copy()
            # v4.34: Draw Bold Headline + Real Article Paragraph below it (yellow highlighter sweeps the key fact!)
            if self.art_lines:
                if hl > 0.01:
                    arr = np.asarray(pg, dtype=np.float32)
                    art_y0 = 472 + len(self.hl_lines) * 66 + 18
                    for li, ln in enumerate(self.art_lines):
                        y0 = art_y0 + li * 56
                        xe = int(62 + (self.PW - 124) * min(1.0, max(0.0, hl * len(self.art_lines) - li)))
                        if xe > 68:
                            arr[y0:y0 + 48, 62:xe, 0] *= 0.99
                            arr[y0:y0 + 48, 62:xe, 1] *= 0.85
                            arr[y0:y0 + 48, 62:xe, 2] *= 0.34
                    pg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
                dp = ImageDraw.Draw(pg, "RGBA")
                for li, ln in enumerate(self.hl_lines):
                    _draw_mixed_text(dp, (74, 466 + li * 66), ln, self.f_pg_hi, self.f_pg_en, fill=(14, 12, 10, 255))
                art_y0 = 472 + len(self.hl_lines) * 66 + 24
                for li, ln in enumerate(self.art_lines):
                    _draw_mixed_text(dp, (74, art_y0 + li * 56), ln, self.f_art_hi, self.f_art_en, fill=(22, 20, 18, 250))
            else:
                if hl > 0.01:
                    arr = np.asarray(pg, dtype=np.float32)
                    for li, ln in enumerate(self.hl_lines):
                        y0 = 490 + li * 82
                        xe = int(62 + (self.PW - 124) * min(1.0, max(0.0, hl * len(self.hl_lines) - li)))
                        if xe > 68:
                            arr[y0:y0 + 68, 62:xe, 0] *= 0.99
                            arr[y0:y0 + 68, 62:xe, 1] *= 0.84
                            arr[y0:y0 + 68, 62:xe, 2] *= 0.36
                    pg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
                dp = ImageDraw.Draw(pg, "RGBA")
                for li, ln in enumerate(self.hl_lines):
                    _draw_mixed_text(dp, (74, 500 + li * 82), ln, self.f_pg_hi, self.f_pg_en, fill=(18, 16, 14, 252))

            # v4.32: Crisp fixed-frame broadsheet (no over-zoom or heavy edge slide!)
            tilt = -0.015 + 0.03 * (3 * t * t - 2 * t * t * t)
            z = 0.88 + 0.05 * ent + 0.02 * t
            pws = W * 0.92 * z; phs = pws * (self.PH / self.PW)
            cx, cy = W * 0.50, H * 0.50 + (1 - ent) * 42 - t * 6
            dst = [
                (cx - pws * (0.5 - tilt * 0.6), cy - phs * 0.5 - tilt * 38),
                (cx + pws * (0.5 - tilt * 0.6), cy - phs * 0.5 + tilt * 38),
                (cx + pws * (0.5 + tilt * 0.6), cy + phs * 0.5 - tilt * 26),
                (cx - pws * (0.5 + tilt * 0.6), cy + phs * 0.5 + tilt * 26),
            ]
            warped = pg.convert("RGBA").transform((W, H), Image.PERSPECTIVE, _dc_persp([(0, 0), (self.PW, 0), (self.PW, self.PH), (0, self.PH)], dst), Image.BICUBIC)
            comp = Image.alpha_composite(Image.new("RGBA", (W, H), (16, 15, 18, 255)), warped)
            # Macro Depth-of-Field blur at top & bottom edges
            blurred = comp.filter(ImageFilter.GaussianBlur(5.0))
            dof_y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
            sharp = np.repeat(np.clip(1.0 - np.maximum(0.0, np.abs(dof_y - 0.50) - 0.16) / 0.24, 0.0, 1.0), W, axis=1)
            out_arr = np.asarray(comp.convert("RGB"), dtype=np.float32) * sharp[..., None] + np.asarray(blurred.convert("RGB"), dtype=np.float32) * (1.0 - sharp[..., None])
            frame = Image.fromarray(np.clip(out_arr, 0, 255).astype(np.uint8), "RGB")
            df = ImageDraw.Draw(frame, "RGBA")
            for mx, my, mr, vx, vy in self.motes:
                px = (mx + vx * t * self.dur) % W; py = (my + vy * t * self.dur) % H
                df.ellipse([px - mr, py - mr, px + mr, py + mr], fill=(255, 225, 175, 42))
            return frame

        if self.variant == "portal":
            # Style 2 (v4.30): Modern Dark Digital News Portal with 2-3 surrounding stories + highlighted lead story
            frame = Image.new("RGBA", (W, H), (10, 14, 22, 255))
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            cw = int(W * 0.90); ch = int(H * 0.68 if H > W else H * 0.78)
            cx0 = (W - cw) // 2; cy0 = int((H - ch) * 0.44 + (1 - ent) * 70 - t * 12)
            d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=22,
                                fill=(16, 22, 34, 248), outline=(85, 110, 145, 125), width=2)
            d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 58], radius=22, fill=(24, 32, 48, 255))
            for ki, kc in enumerate(((235, 75, 68), (240, 185, 65), (75, 200, 115))):
                d.ellipse([cx0 + 22 + ki * 22, cy0 + 21, cx0 + 36 + ki * 22, cy0 + 35], fill=(*kc, 255))
            _src_clean = self.source.rsplit(" ", 1)[0] if len(self.source) > 22 else self.source
            d.text((cx0 + 102, cy0 + 18), f"DAILY BRIEF  •  NATIONAL & POLICY DESK", fill=(160, 178, 200, 215), font=self.f_sm)

            # Top muted surrounding ticker story (gives authentic multi-story news portal look)
            ty_top = cy0 + 74
            d.rounded_rectangle([cx0 + 24, ty_top, cx0 + cw - 24, ty_top + 66], radius=10, fill=(255, 255, 255, 10))
            d.text((cx0 + 40, ty_top + 12), "ALSO TODAY  •  MARKETS & INFRASTRUCTURE", fill=(130, 148, 172, 180), font=self.f_sm)
            d.text((cx0 + 40, ty_top + 38), "Regional transit networks update quarterly schedules across major hubs.", fill=(165, 178, 198, 150), font=self.f_sm)

            # Highlighted Main Lead Story Box
            my0 = ty_top + 84
            d.rectangle([cx0 + 28, my0, cx0 + 236, my0 + 36], fill=(205, 36, 36, 255))
            d.text((cx0 + 132, my0 + 18), "KEY REPORT", fill=(255, 255, 255, 255), font=self.f_sm, anchor="mm")
            d.text((cx0 + 252, my0 + 8), _src_clean, fill=(245, 204, 95, 235), font=self.f_sm)
            lines = _wrap_mixed(self.headline, self.f_hi, self.f_sans, cw - 72)[:4]
            ly_end = my0 + 56
            for li, ln in enumerate(lines):
                ly = my0 + 54 + li * int(self.f_hi.size * 1.44)
                ly_end = ly + int(self.f_hi.size * 1.44)
                if hl > 0.01:
                    hw = int((cw - 64) * min(1.0, max(0.0, hl * len(lines) - li)))
                    if hw > 8:
                        d.rounded_rectangle([cx0 + 26, ly - 6, cx0 + 26 + hw, ly + int(self.f_hi.size * 1.18)], radius=8, fill=(250, 204, 21, 72))
                        d.rectangle([cx0 + 26, ly + int(self.f_hi.size * 1.14), cx0 + 26 + hw, ly + int(self.f_hi.size * 1.20)], fill=(250, 204, 21, 240))
                _draw_mixed_text(d, (cx0 + 34, ly), ln, self.f_hi, self.f_sans, fill=(250, 246, 234, 255))

            # Bottom 2 surrounding news cards (never an empty box!)
            by_grid = max(ly_end + 24, cy0 + ch - 210)
            if by_grid + 110 < cy0 + ch - 20:
                col_w = (cw - 64) // 2
                cards_bg = [
                    ("PUBLIC POLICY", "Parliamentary review panels issue new guidelines on consumer rights."),
                    ("SPECIAL DESK", "Data analysts compare annual trends across key national sectors."),
                ]
                for ci, (ctag, ctxt) in enumerate(cards_bg):
                    bx = cx0 + 24 + ci * (col_w + 16)
                    d.rounded_rectangle([bx, by_grid, bx + col_w, by_grid + 126], radius=12,
                                        fill=(255, 255, 255, 11), outline=(95, 115, 145, 70), width=1)
                    d.text((bx + 16, by_grid + 14), ctag, fill=(140, 175, 215, 195), font=self.f_sm)
                    for wi, wl in enumerate(_wrap_text(ctxt, self.f_sm, col_w - 32)[:3]):
                        d.text((bx + 16, by_grid + 44 + wi * 26), wl, fill=(175, 188, 206, 165), font=self.f_sm)

            d.rounded_rectangle([cx0 + 24, cy0 + ch - 62, cx0 + cw - 24, cy0 + ch - 16], radius=10, fill=(255, 255, 255, 14))
            d.text((cx0 + 42, cy0 + ch - 48), f"{self.date_str}  •  VERIFIED ARCHIVE", fill=(140, 195, 255, 230), font=self.f_sm)
            return Image.alpha_composite(frame, ov).convert("RGB")

        # Style 3 (v4.30): Full Multi-Column Broadsheet Front-Page (never a bare single-headline box!)
        pg = self.page_base.copy()
        if hl > 0.01:
            arr = np.asarray(pg, dtype=np.float32)
            for li, ln in enumerate(self.hl_lines):
                y0 = 490 + li * 82
                xe = int(62 + (self.PW - 124) * min(1.0, max(0.0, hl * len(self.hl_lines) - li)))
                if xe > 68:
                    arr[y0:y0 + 68, 62:xe, 0] *= 0.99
                    arr[y0:y0 + 68, 62:xe, 1] *= 0.85
                    arr[y0:y0 + 68, 62:xe, 2] *= 0.34
            pg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        dp = ImageDraw.Draw(pg, "RGBA")
        for li, ln in enumerate(self.hl_lines):
            _draw_mixed_text(dp, (74, 500 + li * 82), ln, self.f_pg_hi, self.f_pg_en, fill=(18, 16, 14, 252))
        z = 0.88 + 0.05 * ent + 0.02 * t
        pws = int(W * 0.92 * z); phs = int(pws * (self.PH / self.PW))
        scaled = pg.resize((max(10, pws), max(10, phs)), Image.LANCZOS).convert("RGBA")
        frame = Image.new("RGBA", (W, H), (14, 15, 20, 255))
        px0 = (W - pws) // 2
        py0 = int((H - phs) // 2 + (1 - ent) * 36 - t * 6)
        frame.alpha_composite(scaled, (px0, py0))
        return frame.convert("RGB")


class ComparisonVSCard:
    """v3.93 3 Cinematic Comparison & Scale Styles: split_vs | towers."""
    def __init__(self, left_title, left_val, right_title, right_val, W, H, dur, sub="", variant="split_vs"):
        self.W, self.H, self.dur = W, H, max(1.2, dur)
        self.lt, self.lv = str(left_title or "A")[:28], str(left_val or "1x")[:18]
        self.rt, self.rv = str(right_title or "B")[:28], str(right_val or "2x")[:18]
        self.sub = str(sub or "")[:55]
        self.variant = variant
        self.f_big = _dc_font("Anton-Regular.ttf", max(42, int(W * 0.085)))
        self.f_med = _dc_font("Poppins-ExtraBold.ttf", max(20, int(W * 0.038)))
        self.f_sm = _dc_font("Poppins-SemiBold.ttf", max(16, int(W * 0.026)))
        self.f_hi = _dc_font("NotoSansDevanagari-Bold.ttf", max(22, int(W * 0.036)))

    def frame(self, i, fps):
        W, H = self.W, self.H
        t = min(1.0, max(0.0, i / max(1.0, self.dur * fps - 1.0)))
        c1 = _ease_out(min(1.0, t / 0.26))
        c2 = _ease_out(max(0.0, min(1.0, (t - 0.16) / 0.28)))
        bp = _ease_out(max(0.0, min(1.0, (t - 0.26) / 0.42)))
        frame = Image.new("RGBA", (W, H), (10, 14, 22, 255))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        if self.variant == "towers":
            base_y = int(H * 0.74)
            d.line([(int(W * 0.08), base_y), (int(W * 0.92), base_y)], fill=(255, 255, 255, 80), width=3)
            h1 = int(H * 0.22 * bp); h2 = int(H * 0.44 * bp)
            if h1 > 10:
                d.rounded_rectangle([int(W * 0.16), base_y - h1, int(W * 0.42), base_y], radius=14, fill=(65, 155, 235, 240))
                d.text((int(W * 0.29), base_y - h1 - 46), self.lv, fill=(155, 215, 255, 255), font=self.f_big, anchor="mm")
            if h2 > 10:
                d.rounded_rectangle([int(W * 0.58), base_y - h2, int(W * 0.84), base_y], radius=14, fill=(235, 155, 45, 245))
                d.text((int(W * 0.71), base_y - h2 - 46), self.rv, fill=(255, 215, 110, 255), font=self.f_big, anchor="mm")
            d.text((int(W * 0.29), base_y + 42), self.lt[:16], fill=(195, 210, 228, 240), font=self.f_med, anchor="mm")
            d.text((int(W * 0.71), base_y + 42), self.rt[:16], fill=(255, 225, 150, 245), font=self.f_med, anchor="mm")
            if self.sub:
                d.text((W // 2, int(H * 0.85)), self.sub, fill=(245, 248, 252, 235), font=self.f_hi, anchor="mm")
            return Image.alpha_composite(frame, ov).convert("RGB")

        # Default: Split-Screen Glass Clash (VS)
        pad = int(W * 0.065)
        y1 = int(H * 0.18 + (1 - c1) * 55); ch = int(H * 0.25)
        d.rounded_rectangle([pad, y1, W - pad, y1 + ch], radius=22,
                            fill=(18, 28, 44, int(235 * c1)), outline=(95, 175, 255, int(160 * c1)), width=2)
        d.text((pad + 34, y1 + 30), self.lt, fill=(125, 195, 255, 240), font=self.f_sm)
        d.text((pad + 34, y1 + 70), self.lv, fill=(250, 252, 255, 255), font=self.f_big)
        bw1 = int((W - pad * 2 - 68) * 0.42 * bp)
        d.rounded_rectangle([pad + 34, y1 + ch - 64, W - pad - 34, y1 + ch - 34], radius=12, fill=(255, 255, 255, 22))
        if bw1 > 10:
            d.rounded_rectangle([pad + 34, y1 + ch - 64, pad + 34 + bw1, y1 + ch - 34], radius=12, fill=(70, 170, 255, 245))

        vs_y = int(H * 0.48)
        d.ellipse([W // 2 - 42, vs_y - 42, W // 2 + 42, vs_y + 42], fill=(16, 20, 30, 250), outline=(235, 185, 95, 240), width=3)
        d.text((W // 2, vs_y + 2), "VS", fill=(248, 210, 125, 255), font=self.f_med, anchor="mm")

        y2 = int(H * 0.54 + (1 - c2) * 55)
        d.rounded_rectangle([pad, y2, W - pad, y2 + ch], radius=22,
                            fill=(36, 20, 24, int(235 * c2)), outline=(245, 115, 90, int(160 * c2)), width=2)
        d.text((pad + 34, y2 + 30), self.rt, fill=(250, 155, 130, 240), font=self.f_sm)
        d.text((pad + 34, y2 + 70), self.rv, fill=(255, 245, 240, 255), font=self.f_big)
        bw2 = int((W - pad * 2 - 68) * 0.86 * bp)
        d.rounded_rectangle([pad + 34, y2 + ch - 64, W - pad - 34, y2 + ch - 34], radius=12, fill=(255, 255, 255, 22))
        if bw2 > 10:
            d.rounded_rectangle([pad + 34, y2 + ch - 64, pad + 34 + bw2, y2 + ch - 34], radius=12, fill=(235, 88, 65, 245))
        return Image.alpha_composite(frame, ov).convert("RGB")


def render_news_highlight(source, headline, highlight_phrase, dur, out, W, H, style, pal, date_str="", fps=30):
    """v3.93: Auto-rotates across 3 Realistic News Proof Styles (Broadsheet Macro DOF | Dark News Portal | 3D Cutout Broadcast)."""
    import fx
    cat = str((style or {}).get("category") or "").strip().lower()
    seed = abs(hash((headline or "") + (source or "") + cat)) % 3
    if cat in ("news", "business", "technology"):
        variant = ("portal", "broadcast", "broadsheet")[seed]
    elif cat in ("history", "general", "geography"):
        variant = ("broadsheet", "broadcast", "portal")[seed]
    else:
        variant = ("broadcast", "broadsheet", "portal")[seed]
    c = RealisticNewsProofCard(source, headline, highlight_phrase, W, H, pal, dur, date_str, variant=variant)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: c.frame(i, fps), n, W, H, out, style, fps)


def render_vs_card(left_title, left_val, right_title, right_val, dur, out, W, H, style, pal, sub="", variant="split_vs", fps=30):
    """v3.93: Cinematic VS Comparison / Stat Towers card."""
    import fx
    c = ComparisonVSCard(left_title, left_val, right_title, right_val, W, H, dur, sub=sub, variant=variant)
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


# =========================================================================
# v4.28: VIRAL SOCIAL TWEET / POST PROOF CARD WITH ANIMATED YELLOW HIGHLIGHTER
# =========================================================================
def render_tweet_card(author, handle, body_text, highlight_phrase, dur, out, W, H, style, pal, fps=30):
    """Render a crisp white social-media post/tweet proof card with animated yellow highlighter sweep."""
    from PIL import Image, ImageDraw
    import subprocess
    author = str(author or "Verified Source").strip()[:38]
    handle = str(handle or "@verified").strip()[:32]
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    body_text = str(body_text or "").strip()[:220]
    hi_phrase = str(highlight_phrase or "").strip()
    dur = max(2.2, min(7.0, float(dur or 3.5)))
    total_frames = max(20, int(round(dur * fps)))

    bg_base = _grunge_bg(W, H, pal or {}, seed=abs(hash(body_text)) % 97, grid=True).convert("RGBA")
    cw = int(W * (0.86 if W < H else 0.62))
    ch = int(H * (0.34 if W < H else 0.44))
    cx0 = (W - cw) // 2
    cy0 = (H - ch) // 2 - (int(H * 0.04) if W < H else 0)

    f_auth = _dc_font("bold", max(26, int(cw * 0.042)))
    f_hnd = _dc_font("reg", max(20, int(cw * 0.031)))
    f_body_en = _dc_font("reg", max(26, int(cw * 0.040)))
    f_body_hi = _dc_font("hi", max(26, int(cw * 0.040)))

    pad_x = int(cw * 0.065)
    pad_y = int(ch * 0.11)
    av_r = max(28, int(cw * 0.048))
    wrapped = _wrap_mixed(body_text, f_body_hi, f_body_en, cw - pad_x * 2)[:5]
    line_h = int(max(26, int(cw * 0.040)) * 1.42)

    # Pre-render static card base
    card_bg = bg_base.copy()
    _draw_shadow_box(card_bg, (cx0, cy0, cx0 + cw, cy0 + ch), radius=26, fill=(252, 252, 250, 255), shadow_alpha=145, blur=28)
    d0 = ImageDraw.Draw(card_bg)
    # Avatar circle with initial
    ax = cx0 + pad_x + av_r
    ay = cy0 + pad_y + av_r
    d0.ellipse((ax - av_r, ay - av_r, ax + av_r, ay + av_r), fill=(26, 115, 232, 255))
    init_ch = (author[0].upper() if author else "V")
    d0.text((ax - av_r // 3, ay - av_r // 2), init_ch, font=f_auth, fill=(255, 255, 255, 255))
    # Author + Verified blue check + handle
    tx = ax + av_r + 18
    d0.text((tx, cy0 + pad_y + 2), author, font=f_auth, fill=(18, 22, 28, 255))
    d0.text((tx, cy0 + pad_y + int(av_r * 1.05)), handle, font=f_hnd, fill=(100, 112, 128, 255))
    # Subtle divider
    div_y = cy0 + pad_y + av_r * 2 + 18
    d0.line((cx0 + pad_x, div_y, cx0 + cw - pad_x, div_y), fill=(228, 232, 238, 255), width=2)

    body_y0 = div_y + 20
    # Determine which line gets the yellow highlighter sweep
    hi_line_idx = 0
    if hi_phrase:
        for idx_l, ln_t in enumerate(wrapped):
            if hi_phrase.lower()[:12] in ln_t.lower():
                hi_line_idx = idx_l
                break

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f_idx in range(total_frames):
            t_norm = f_idx / max(1, total_frames - 1)
            # Highlighter sweeps smoothly from 15% to 55% of clip duration
            hl_p = max(0.0, min(1.0, (t_norm - 0.15) / 0.40))
            hl_e = _ease_out(hl_p)
            frame = card_bg.copy()
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dov = ImageDraw.Draw(ov)
            if wrapped and hl_e > 0.01:
                hy = body_y0 + hi_line_idx * line_h - 4
                hw = int((cw - pad_x * 2) * 0.92 * hl_e)
                dov.rounded_rectangle((cx0 + pad_x - 6, hy, cx0 + pad_x - 6 + hw, hy + line_h - 6), radius=8, fill=(255, 225, 53, 165))
            frame = Image.alpha_composite(frame, ov)
            df = ImageDraw.Draw(frame)
            for idx_l, ln_t in enumerate(wrapped):
                _draw_mixed_text(df, (cx0 + pad_x, body_y0 + idx_l * line_h), ln_t, f_body_hi, f_body_en, (22, 26, 32, 255))
            # Gentle documentary zoom-in (1.00 -> 1.045)
            sc = 1.0 + 0.045 * t_norm
            nw, nh = int(W * sc), int(H * sc)
            rgb = frame.convert("RGB").resize((nw, nh), Image.BILINEAR)
            lx = (nw - W) // 2; ly = (nh - H) // 2
            rgb = rgb.crop((lx, ly, lx + W, ly + H))
            proc.stdin.write(rgb.tobytes())
        proc.stdin.close()
        proc.wait(timeout=60)
    except Exception:
        try: proc.kill()
        except Exception: pass
        return None
    return str(out) if out.exists() and out.stat().st_size > 4000 else None


# =========================================================================
# v4.29: VIRAL GIANT YEAR REVEAL + OPTIONAL RED ARCHIVAL STAMP (Shorts & Longs)
# =========================================================================
def render_year_reveal(year_str, subtitle, dur, out, W, H, style, pal, stamp="", fps=30):
    """Render a giant bold animated year slam (e.g. 1972, 1975, 2015) with timeline ticks & optional red stamp."""
    from PIL import Image, ImageDraw
    import subprocess
    year_str = str(year_str or "").strip()[:10]
    subtitle = str(subtitle or "").strip()[:90]
    stamp = str(stamp or "").strip().upper()[:18]
    if not year_str:
        return None
    dur = max(1.8, min(6.0, float(dur or 2.8)))
    total_frames = max(18, int(round(dur * fps)))
    is_short = H > W

    bg_base = _grunge_bg(W, H, pal or {}, seed=abs(hash(year_str + subtitle)) % 97, grid=True).convert("RGBA")
    # Pre-draw subtle horizontal documentary timeline ruler ticks
    d_bg = ImageDraw.Draw(bg_base)
    ty_top = int(H * (0.31 if is_short else 0.25))
    ty_bot = int(H * (0.64 if is_short else 0.72))
    d_bg.line((int(W * 0.08), ty_top, int(W * 0.92), ty_top), fill=(255, 255, 255, 42), width=2)
    d_bg.line((int(W * 0.08), ty_bot, int(W * 0.92), ty_bot), fill=(255, 255, 255, 42), width=2)
    step = max(24, W // 28)
    for tx in range(int(W * 0.08), int(W * 0.92), step):
        th = 16 if ((tx // step) % 5 == 0) else 8
        d_bg.line((tx, ty_top - th, tx, ty_top), fill=(250, 204, 21, 90), width=2)
        d_bg.line((tx, ty_bot, tx, ty_bot + th), fill=(250, 204, 21, 90), width=2)

    f_year = _dc_font("bold", max(110, int(W * (0.23 if is_short else 0.145))))
    f_sub_en = _dc_font("bold", max(28, int(W * (0.040 if is_short else 0.025))))
    f_sub_hi = _dc_font("hi", max(28, int(W * (0.040 if is_short else 0.025))))
    f_stamp = _dc_font("bold", max(32, int(W * (0.046 if is_short else 0.028))))
    sub_lines = _wrap_mixed(subtitle, f_sub_hi, f_sub_en, int(W * (0.82 if is_short else 0.66)))[:2] if subtitle else []

    # Pre-render giant year text layer for clean scale slam
    yb = ImageDraw.Draw(bg_base).textbbox((0, 0), year_str, font=f_year)
    yw, yh = yb[2] - yb[0], yb[3] - yb[1]
    pad = 40
    yr_img = Image.new("RGBA", (yw + pad * 2, yh + pad * 2), (0, 0, 0, 0))
    dy = ImageDraw.Draw(yr_img)
    dy.text((pad - yb[0] + 6, pad - yb[1] + 8), year_str, font=f_year, fill=(0, 0, 0, 185))
    dy.text((pad - yb[0], pad - yb[1]), year_str, font=f_year, fill=(250, 204, 21, 255), stroke_width=4, stroke_fill=(20, 16, 10, 220))

    # Optional tilted red archival stamp layer
    st_img = None
    if stamp:
        sb = ImageDraw.Draw(bg_base).textbbox((0, 0), stamp, font=f_stamp)
        sw, sh = (sb[2] - sb[0]) + 44, (sb[3] - sb[1]) + 26
        raw_st = Image.new("RGBA", (sw + 20, sh + 20), (0, 0, 0, 0))
        ds = ImageDraw.Draw(raw_st)
        ds.rounded_rectangle((10, 10, 10 + sw, 10 + sh), radius=10, outline=(239, 68, 68, 240), width=6, fill=(239, 68, 68, 36))
        ds.text((10 + 22 - sb[0], 10 + 13 - sb[1]), stamp, font=f_stamp, fill=(248, 82, 82, 248))
        st_img = raw_st.rotate(10, expand=True, resample=Image.BICUBIC)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for fi in range(total_frames):
            t_norm = fi / max(1, total_frames - 1)
            t_sec = fi / float(fps)
            frame = bg_base.copy()

            # Giant year slam-in (1.35x -> 1.00x in 0.35s)
            p_yr = _ease_back(min(1.0, t_sec / 0.36))
            sc_yr = 1.35 - 0.35 * min(1.06, p_yr)
            nw_y = max(8, int(yr_img.width * sc_yr))
            nh_y = max(8, int(yr_img.height * sc_yr))
            y_res = yr_img.resize((nw_y, nh_y), Image.BILINEAR)
            yx = (W - nw_y) // 2
            yy = int(H * (0.43 if is_short else 0.42)) - nh_y // 2
            frame.alpha_composite(y_res, (max(0, yx), max(0, yy)))

            # Subtitle fade-in (0.22s - 0.55s)
            sub_a = int(255 * _ease_out(max(0.0, min(1.0, (t_sec - 0.22) / 0.32))))
            if sub_lines and sub_a > 5:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                do = ImageDraw.Draw(ov)
                sy0 = int(H * (0.55 if is_short else 0.59))
                lh = int(max(28, int(W * (0.040 if is_short else 0.025))) * 1.38)
                for idx_s, ln_s in enumerate(sub_lines):
                    lb = do.textbbox((0, 0), ln_s, font=f_sub_hi if any("\u0900" <= c <= "\u097F" for c in ln_s) else f_sub_en)
                    lx = (W - (lb[2] - lb[0])) // 2
                    _draw_mixed_text(do, (max(24, lx), sy0 + idx_s * lh), ln_s, f_sub_hi, f_sub_en, (242, 244, 248, sub_a))
                frame = Image.alpha_composite(frame, ov)

            # Red archival stamp slam at t=0.52s
            if st_img is not None and t_sec >= 0.50:
                sp = _ease_out(min(1.0, (t_sec - 0.50) / 0.22))
                sc_s = 1.45 - 0.45 * sp
                nsw, nsh = max(8, int(st_img.width * sc_s)), max(8, int(st_img.height * sc_s))
                s_res = st_img.resize((nsw, nsh), Image.BILINEAR)
                sx = int(W * (0.64 if is_short else 0.66)) - nsw // 2
                sy = int(H * (0.34 if is_short else 0.30)) - nsh // 2
                frame.alpha_composite(s_res, (max(0, min(W - nsw, sx)), max(0, min(H - nsh, sy))))

            # Subtle documentary drift zoom (1.00 -> 1.04)
            zsc = 1.0 + 0.04 * t_norm
            zw, zh = int(W * zsc), int(H * zsc)
            rgb = frame.convert("RGB").resize((zw, zh), Image.BILINEAR)
            cx, cy = (zw - W) // 2, (zh - H) // 2
            rgb = rgb.crop((cx, cy, cx + W, cy + H))
            proc.stdin.write(rgb.tobytes())
        proc.stdin.close()
        proc.wait(timeout=60)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        return None
    return out if (out.exists() and out.stat().st_size > 8000) else None


# ==============================================================================
# v4.30: KINETIC FULL-FORM / TERM CALLOUT CARD (e.g. RAC -> Reservation Against Cancellation)
# ==============================================================================
def render_fullform_card(acronym, full_form, context, dur, out, W, H, style, pal, fps=30):
    """Render a crisp, high-impact animated Full-Form / Term Callout card (Shorts 9:16 & Longs 16:9)."""
    import fx
    is_short = H > W
    acr = str(acronym or "INFO").strip().upper()[:14]
    ff = str(full_form or "").strip()
    ctx = str(context or "").strip()
    if not ff:
        return None

    has_dev_ff = bool(re.search(r"[\u0900-\u097F]", ff))
    f_badge = _dc_font("Poppins-ExtraBold.ttf", max(24, int(W * (0.028 if is_short else 0.017))))
    f_acr = _dc_font("Poppins-ExtraBold.ttf", max(74, int(W * (0.125 if is_short else 0.075))))
    f_ff_hi = _dc_font("NotoSansDevanagari-Bold.ttf", max(44, int(W * (0.052 if is_short else 0.034))))
    f_ff_en = _dc_font("Poppins-ExtraBold.ttf", max(44, int(W * (0.054 if is_short else 0.035))))
    f_ctx_hi = _dc_font("NotoSansDevanagari-Bold.ttf", max(28, int(W * (0.032 if is_short else 0.020))))
    f_ctx_en = _dc_font("Poppins-SemiBold.ttf", max(26, int(W * (0.030 if is_short else 0.019))))

    # Shrink acronym if too wide
    while f_acr.size > 46 and ImageDraw.Draw(Image.new("RGBA", (10, 10))).textlength(acr, font=f_acr) > W * 0.72:
        f_acr = _dc_font("Poppins-ExtraBold.ttf", f_acr.size - 8)

    max_cw = int(W * (0.82 if is_short else 0.68))
    ff_lines = _wrap_mixed(ff, f_ff_hi, f_ff_en, max_cw)[:3]
    ctx_lines = _wrap_mixed(ctx, f_ctx_hi, f_ctx_en, max_cw)[:2] if ctx else []

    bg = _grunge_bg(W, H, pal, seed=abs(hash(acr + ff)) % 997, grid=True)
    acc = tuple(pal.get("accent", (250, 204, 21)))
    if len(acc) < 3:
        acc = (250, 204, 21)

    n = max(2, int(round(dur * fps)))

    def _frame(i):
        t = min(1.0, max(0.0, i / max(1.0, n - 1)))
        ent = _ease_back(min(1.0, t / 0.22))
        ent2 = _ease_out(max(0.0, min(1.0, (t - 0.16) / 0.24)))
        hl = _ease_out(max(0.0, min(1.0, (t - 0.28) / 0.40)))

        base = bg.copy().convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)

        # Clean center editorial card
        cw = int(W * (0.88 if is_short else 0.74))
        ch = int(H * (0.46 if is_short else 0.60))
        cx0 = (W - cw) // 2
        cy0 = int(H * (0.23 if is_short else 0.18) + (1.0 - min(1.0, ent)) * 55)

        d.rounded_rectangle([cx0 + 10, cy0 + 14, cx0 + cw + 10, cy0 + ch + 14], radius=26, fill=(0, 0, 0, 145))
        d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=26,
                            fill=(14, 20, 32, 245), outline=(*acc[:3], 170), width=3)

        # Top "FULL FORM" pill badge
        pill = "FULL FORM"
        pw = int(d.textlength(pill, font=f_badge)) + 44
        ph = int(f_badge.size * 1.55)
        px0 = (W - pw) // 2
        py0 = cy0 + 34
        d.rounded_rectangle([px0, py0, px0 + pw, py0 + ph], radius=ph // 2, fill=(*acc[:3], 255))
        d.text((W // 2, py0 + ph // 2), pill, font=f_badge, fill=(14, 18, 26, 255), anchor="mm")

        # Giant Acronym slam
        ay = py0 + ph + int(f_acr.size * 0.72)
        d.text((W // 2 + 4, ay + 5), acr, font=f_acr, fill=(0, 0, 0, 185), anchor="mm")
        d.text((W // 2, ay), acr, font=f_acr, fill=(255, 255, 255, 255), anchor="mm")

        # Animated accent divider bar
        div_y = ay + int(f_acr.size * 0.56)
        div_w = int((cw * 0.68) * ent2)
        if div_w > 6:
            d.rounded_rectangle([W // 2 - div_w // 2, div_y, W // 2 + div_w // 2, div_y + 7],
                                radius=4, fill=(*acc[:3], 245))

        # Full Form lines with animated yellow highlighter sweep
        fy0 = div_y + 34
        lh = int((f_ff_hi.size if has_dev_ff else f_ff_en.size) * 1.40)
        for li, ln in enumerate(ff_lines):
            ly = fy0 + li * lh
            lw = _mixed_width(ln, f_ff_hi, f_ff_en) if "_mixed_width" in globals() else d.textlength(ln, font=f_ff_hi if has_dev_ff else f_ff_en)
            lx = int((W - lw) // 2)
            if hl > 0.01:
                hw = int((lw + 24) * min(1.0, max(0.0, hl * len(ff_lines) - li)))
                if hw > 6:
                    d.rounded_rectangle([lx - 12, ly - 6, lx - 12 + hw, ly + int(lh * 0.82)],
                                        radius=8, fill=(250, 204, 21, 68))
            _draw_mixed_text(d, (lx, ly), ln, f_ff_hi, f_ff_en, fill=(252, 248, 236, int(255 * ent2)))

        # Optional short context line at bottom of card
        if ctx_lines and ent2 > 0.2:
            cy_ctx = fy0 + len(ff_lines) * lh + 24
            for ci, cln in enumerate(ctx_lines):
                clw = d.textlength(cln, font=f_ctx_hi if re.search(r"[\u0900-\u097F]", cln) else f_ctx_en)
                _draw_mixed_text(d, (int((W - clw) // 2), cy_ctx + ci * int(f_ctx_hi.size * 1.35)),
                                 cln, f_ctx_hi, f_ctx_en, fill=(175, 194, 218, int(220 * ent2)))

        return Image.alpha_composite(base, ov).convert("RGB")

    return fx._pipe_frames(_frame, n, W, H, out, style, fps)
