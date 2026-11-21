"""3D MAP ANIMATION (trending motion-graphics style) – bina internet, bina tiles.

Kya dikhta hai (3-5 sec):
  1) Andhere stylish background pe India (ya duniya) ki outline "draw" hoti hai, glow ke saath
  2) Camera ghoomta hua (3D tilt) us rajya / desh pe zoom karta hai
  3) Wo rajya UPAR uthta hai (3D extrude) accent rang me, baaki halke
  4) Shehar ho to pin girta hai (bounce), pulse rings, naam ka card typewriter se aata hai
Map data: official India boundary (Jammu & Kashmir + Ladakh poore), isliye galat naksha nahi aata.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import places
from .bible import font_path


def _merc(lat):
    lat = max(-80.0, min(80.0, lat))
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def _ease(t):
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def _out_back(t):
    t = max(0.0, min(1.0, t)); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _rings_xy(rings):
    out = []
    for r in rings:
        a = np.array(r, dtype=np.float64)
        if len(a) < 3: continue
        y = np.degrees(np.log(np.tan(np.pi / 4 + np.radians(np.clip(a[:, 1], -80, 80)) / 2)))
        out.append(np.stack([a[:, 0], y], axis=1))
    return out


def _bbox(rings_xy, pad=0.12):
    a = np.concatenate(rings_xy)
    x0, y0 = a.min(0); x1, y1 = a.max(0)
    w, h = x1 - x0, y1 - y0
    return (x0 - w * pad, y0 - h * pad, x1 + w * pad, y1 + h * pad)


def _bg(W, H, pal):
    """Gehra gradient + halki roshni + bindiyon wala grid (3D studio jaisa)."""
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    c1 = np.array(pal["bg1"], float); c2 = np.array(pal["bg2"], float)
    r = np.sqrt((x - 0.5) ** 2 * 1.6 + (y - 0.42) ** 2)
    k = np.clip(1.0 - r * 1.25, 0, 1)[..., None]
    img = c1 * (1 - k) + c2 * k
    img = np.clip(img, 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "RGB")
    d = ImageDraw.Draw(im, "RGBA")
    step = max(28, W // 30)
    for gx in range(0, W, step):
        for gy in range(0, H, step):
            d.point((gx, gy), fill=(255, 255, 255, 22))
    return im


class MapAnim:
    def __init__(self, place, W, H, pal, dur, label=None, sub=None):
        self.p = place; self.W = W; self.H = H; self.pal = pal; self.dur = max(2.2, dur)
        self.label = (label or place["name"]).upper(); self.sub = sub
        ind = places.india()
        self.kind = place["kind"]
        self.world_mode = place.get("country") not in ("India",) or (self.kind == "country" and place["name"] == "India")
        self.states = {k: _rings_xy(v["rings"]) for k, v in ind["states"].items()}
        self.india = _rings_xy(ind["india"])
        if self.world_mode:
            w = places.world()
            self.countries = {k: _rings_xy(v["rings"]) for k, v in w.items() if k != "India"}
        else:
            self.countries = {}
        # target
        if self.kind == "country":
            tgt = self.india if place["name"] == "India" else _rings_xy(places.world()[place["name"]]["rings"])
            self.target = tgt
        else:
            self.target = self.states.get(place.get("state") or "", [])
        lon, lat = place["lonlat"]
        self.pin = (lon, _merc(lat)) if self.kind in ("city", "district") else None
        # camera: start (wide) -> end (target)
        if self.world_mode:
            tb = _bbox(self.target, 0.6) if self.target else (lon - 20, _merc(lat) - 15, lon + 20, _merc(lat) + 15)
            self.v1 = self._fit(tb)
            self.v0 = (self.v1[0] + 6.0, self.v1[1] - 4.0, self.v1[2] * 0.33)     # door se (space jaisa) zoom-in
        else:
            ib = _bbox(self.india, 0.06)
            self.v0 = self._fit(ib)
            if self.target:
                tb = _bbox(self.target, 0.35 if self.pin else 0.25)
            else:
                tb = (lon - 3, _merc(lat) - 3, lon + 3, _merc(lat) + 3)
            if self.pin:          # shehar: rajya + thoda zoom, pin beech ke paas
                cx = (tb[0] + tb[2]) / 2 * 0.55 + self.pin[0] * 0.45
                cy = (tb[1] + tb[3]) / 2 * 0.55 + self.pin[1] * 0.45
                w = tb[2] - tb[0]; h = tb[3] - tb[1]
                tb = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            self.v1 = self._fit(tb)
        self.bg = _bg(W, H, pal)
        sc = W / 1080
        self.f_big = ImageFont.truetype(str(font_path("head")), int(150 * sc))
        self.f_sub = ImageFont.truetype(str(font_path("serif")), int(62 * sc))
        self.f_tag = ImageFont.truetype(str(font_path("semi")), int(34 * sc))
        self.cy_screen = H * (0.47 if H > W else 0.5)
        self.seed = random.Random(len(self.label))

    def _fit(self, b):
        w = max(1e-3, b[2] - b[0]); h = max(1e-3, b[3] - b[1])
        s = min(self.W * 0.86 / w, self.H * (0.52 if self.H > self.W else 0.78) / h)
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, s)

    # ----------------------------------------------------------------- projection
    def _proj(self, pts, cam, tilt, rot):
        cx, cy, s = cam
        X = (pts[:, 0] - cx) * s
        Y = -(pts[:, 1] - cy) * s
        cr, sr = math.cos(rot), math.sin(rot)
        X, Y = X * cr - Y * sr, X * sr + Y * cr
        f = self.H * 1.25
        Y3 = Y * math.cos(tilt); Z = Y * math.sin(tilt)
        k = f / np.maximum(f * 0.25, f + Z)
        return np.stack([self.W / 2 + X * k, self.cy_screen + Y3 * k], axis=1)

    def frame(self, i, fps=30):
        t = i / fps; T = self.dur
        pal = self.pal
        acc = tuple(pal["accent"]); acc2 = tuple(pal["accent2"])
        mv = _ease((t - 0.35) / 1.45)                       # camera move
        drift = (t / T) * 0.035
        cx = self.v0[0] + (self.v1[0] - self.v0[0]) * mv
        cy = self.v0[1] + (self.v1[1] - self.v0[1]) * mv
        s = math.exp(math.log(self.v0[2]) + (math.log(self.v1[2]) - math.log(self.v0[2])) * mv) * (1 + drift)
        tilt = math.radians(8 + 26 * mv)
        rot = math.radians(-4 * (1 - mv) + 2.0 * math.sin(t * 0.6) * mv)
        cam = (cx, cy, s)
        im = self.bg.copy()
        lay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        land = tuple(pal["map_land"]); line = tuple(pal["map_line"])
        appear = _ease(t / 0.55)
        # duniya ke baaki desh (sirf world mode)
        for nm, rings in self.countries.items():
            for r in rings:
                P = self._proj(r, cam, tilt, rot)
                if P[:, 0].max() < -50 or P[:, 0].min() > self.W + 50 or P[:, 1].max() < -50 or P[:, 1].min() > self.H + 50:
                    continue
                d.polygon([tuple(p) for p in P], fill=land + (int(150 * appear),), outline=line + (int(120 * appear),))
        # India ke rajya
        dim = 1.0 - 0.45 * mv if self.kind != "country" else 1.0
        tname = self.p.get("state") if self.kind != "country" else None
        for nm, rings in self.states.items():
            for r in rings:
                P = self._proj(r, cam, tilt, rot)
                fill = tuple(int(c * dim) for c in land)
                d.polygon([tuple(p) for p in P], fill=fill + (int(235 * appear),),
                          outline=line + (int(200 * appear) if not self.world_mode else int(70 * appear),))
        im.paste(lay, (0, 0), lay)
        # India outline draw-on + glow
        draw_p = _ease(t / 0.9)
        glow = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); g = ImageDraw.Draw(glow)
        for r in (self.target if (self.world_mode and self.target) else self.india):
            P = self._proj(r, cam, tilt, rot)
            n = max(2, int(len(P) * draw_p))
            pts = [tuple(p) for p in P[:n]]
            if len(pts) > 1:
                g.line(pts, fill=acc + (230,), width=max(3, self.W // 300), joint="curve")
        gb = glow.filter(ImageFilter.GaussianBlur(self.W / 120))
        im.paste(gb, (0, 0), gb); im.paste(glow, (0, 0), glow)
        # target: 3D uthta hua (extrude)
        if self.target and (self.kind != "country" or self.p["name"] != "India" or self.world_mode):
            up = _ease((t - 0.9) / 0.8)
            if up > 0:
                lift = int(self.H * 0.022 * up)
                ex = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); e = ImageDraw.Draw(ex)
                projs = [self._proj(r, cam, tilt, rot) for r in self.target]
                side = tuple(int(c * 0.45) for c in acc)
                for k in range(0, lift + 1, 2):
                    for P in projs:
                        e.polygon([(p[0], p[1] - k) for p in P], fill=side + (255,))
                top = tuple(int(c * (0.78 + 0.22 * up)) for c in acc)
                for P in projs:
                    e.polygon([(p[0], p[1] - lift) for p in P], fill=top + (int(255 * min(1, up * 1.4)),),
                              outline=(255, 255, 255, int(220 * up)))
                sh = ex.filter(ImageFilter.GaussianBlur(self.W / 70))
                shadow = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
                shadow.paste((0, 0, 0, 150), (0, 0), sh.split()[3].point(lambda v: int(v * 0.55)))
                im.paste(shadow, (int(self.W * 0.012), int(self.H * 0.012)), shadow)
                im.paste(ex, (0, 0), ex)
        # pin + pulse
        lab_anchor = None
        if self.pin:
            P = self._proj(np.array([self.pin]), cam, tilt, rot)[0]
            lift = int(self.H * 0.022 * _ease((t - 0.9) / 0.8))
            px, py = float(P[0]), float(P[1]) - lift
            drop = _out_back((t - 1.55) / 0.45)
            if t > 1.55:
                pl = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); q = ImageDraw.Draw(pl)
                for kk in range(3):
                    ph = ((t - 1.9) * 0.9 - kk * 0.33) % 1.0 if t > 1.9 else -1
                    if ph >= 0:
                        rr = self.W * 0.02 + self.W * 0.11 * ph
                        q.ellipse((px - rr, py - rr * 0.45, px + rr, py + rr * 0.45),
                                  outline=(255, 255, 255, int(200 * (1 - ph))), width=max(2, self.W // 360))
                hy = py - self.H * 0.06 * (1 - drop) - self.W * 0.075
                R = self.W * 0.034
                q.ellipse((px - R * 0.5, py - R * 0.22, px + R * 0.5, py + R * 0.22), fill=(0, 0, 0, 120))
                q.polygon([(px - R * 0.62, hy + R * 0.55), (px + R * 0.62, hy + R * 0.55), (px, py - (1 - drop) * self.H * 0.06)],
                          fill=acc2 + (255,))
                q.ellipse((px - R, hy - R, px + R, hy + R), fill=acc2 + (255,), outline=(255, 255, 255, 255),
                          width=max(3, self.W // 300))
                q.ellipse((px - R * 0.38, hy - R * 0.38, px + R * 0.38, hy + R * 0.38), fill=(255, 255, 255, 255))
                im.paste(pl, (0, 0), pl)
                lab_anchor = (px, hy - R * 1.6)
        # naam ka card
        lt = t - (1.85 if self.pin else 1.45)
        if lt > 0:
            self._label(im, lt, lab_anchor)
        return im

    def _label(self, im, lt, anchor):
        W, H = self.W, self.H
        acc = tuple(self.pal["accent"])
        txt = self.label
        nshow = min(len(txt), int(lt / 0.045) + 1)
        sub = (self.sub or (self.p.get("state") if self.kind in ("city", "district") else
                            ("INDIA" if self.p.get("country") == "India" and self.kind == "state" else ""))) or ""
        d = ImageDraw.Draw(im, "RGBA")
        full_w = d.textlength(txt, font=self.f_big)
        sub_w = d.textlength(sub, font=self.f_sub) if sub else 0
        bw = max(full_w, sub_w) + W * 0.09
        bh = self.f_big.size * 1.05 + (self.f_sub.size * 1.1 if sub else 0) + H * 0.02
        if anchor:
            cx = min(max(anchor[0], bw / 2 + W * 0.04), W - bw / 2 - W * 0.04)
            top = anchor[1] - bh
            top = max(H * 0.10, min(top, H * 0.80 - bh))
        else:
            cx = W / 2; top = H * 0.14
        a = min(1.0, lt / 0.25)
        sl = (1 - _ease(lt / 0.35)) * W * 0.04
        x0 = cx - bw / 2; y0 = top + sl
        d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=int(W * 0.025), fill=(10, 10, 14, int(170 * a)),
                            outline=acc + (int(200 * a),), width=max(2, W // 400))
        shown = txt[:nshow]
        tx = cx - full_w / 2
        d.text((tx + 3, y0 + H * 0.008 + 3), shown, font=self.f_big, fill=(0, 0, 0, int(160 * a)))
        d.text((tx, y0 + H * 0.008), shown, font=self.f_big, fill=acc + (int(255 * a),))
        if sub:
            sa = _ease((lt - 0.35) / 0.4)
            if sa > 0:
                d.text((cx - sub_w / 2, y0 + self.f_big.size * 1.02 + H * 0.004), sub, font=self.f_sub,
                       fill=(255, 255, 255, int(235 * sa)))


def render(place, dur, out, W, H, style, pal, fps=30, label=None, sub=None):
    """place: places.find/resolve ka dict. Video file banata hai, path lautata hai."""
    import fx
    m = MapAnim(place, W, H, pal, dur, label, sub)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: m.frame(i, fps), n, W, H, out, style, fps)
