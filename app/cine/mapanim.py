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


def _persp_coeffs(src_pts, dst_pts):
    matrix = []
    for s, d in zip(src_pts, dst_pts):
        matrix.append([d[0], d[1], 1, 0, 0, 0, -s[0] * d[0], -s[0] * d[1]])
        matrix.append([0, 0, 0, d[0], d[1], 1, -s[1] * d[0], -s[1] * d[1]])
    return np.linalg.solve(
        np.array(matrix, dtype=np.float64),
        np.array([c for pt in src_pts for c in pt], dtype=np.float64),
    ).tolist()


def _load_map_font(name, size):
    from common import ASSETS
    for p in (ASSETS / "fonts" / name, ASSETS / "fonts" / "Poppins-ExtraBold.ttf"):
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()


class _DistinctMapBase:
    """Shared crisp cartographic canvas builder for v3.93 Vox Route Glide & Defence Radar Lock maps."""
    def __init__(self, place, W, H, dur, label=None, sub=None, mode="vox"):
        self.p = place
        self.W, self.H, self.dur = W, H, max(2.0, dur)
        self.label = (label or place.get("name") or "LOCATION").upper()[:24]
        self.sub = (sub or "").strip()
        self.mode = mode

        ind = places.india()
        self.states_xy = {k: _rings_xy(v["rings"]) for k, v in ind["states"].items()}
        india_xy = _rings_xy(ind["india"])
        kind = place.get("kind", "state")
        world_mode = place.get("country") not in ("India",) or (kind == "country" and place.get("name") == "India")
        if world_mode:
            w = places.world()
            self.ctx_xy = [r for k, v in w.items() for r in _rings_xy(v["rings"])] + india_xy
            self.tgt_xy = india_xy if place.get("name") == "India" else _rings_xy((w.get(place.get("name")) or {}).get("rings") or [])
        else:
            self.ctx_xy = india_xy
            self.tgt_xy = self.states_xy.get(place.get("state") or "", [])
        if not self.tgt_xy:
            self.tgt_xy = india_xy

        x0, y0, x1, y1 = _bbox(self.ctx_xy, pad=0.20 if not world_mode else 0.05)
        self.MW = max(1080, int(W * 1.45))
        self.MH = max(1280, int(H * 1.25))
        self.bx0, self.by0, self.bx1, self.by1 = x0, y0, x1, y1
        self.scale = min(self.MW / max(1e-6, x1 - x0), self.MH / max(1e-6, y1 - y0))
        self.ox = (self.MW - (x1 - x0) * self.scale) * 0.5
        self.oy = (self.MH - (y1 - y0) * self.scale) * 0.5

        if place.get("lonlat"):
            tx, ty = float(place["lonlat"][0]), _merc(float(place["lonlat"][1]))
        else:
            tx, ty = np.concatenate(self.tgt_xy).mean(0)
        self.tcx = self.ox + (tx - self.bx0) * self.scale
        self.tcy = self.MH - (self.oy + (ty - self.by0) * self.scale)

        self.f_serif = _load_map_font("DMSerifDisplay-Regular.ttf", max(28, int(W * 0.056)))
        self.f_sans = _load_map_font("Poppins-ExtraBold.ttf", max(24, int(W * 0.044)))
        self.f_sm = _load_map_font("Poppins-SemiBold.ttf", max(14, int(W * 0.024)))
        self.base = self._build_canvas()

    def _to_px(self, arr):
        px = self.ox + (arr[:, 0] - self.bx0) * self.scale
        py = self.MH - (self.oy + (arr[:, 1] - self.by0) * self.scale)
        return list(zip(px.tolist(), py.tolist()))

    def _build_canvas(self):
        from PIL import ImageEnhance
        MW, MH = self.MW, self.MH
        rng = np.random.default_rng(abs(hash(self.label)) % 10000)
        grain = rng.normal(0, 2.8, (MH, MW, 1)).astype(np.float32)

        if self.mode == "vox":
            ocean_col, land_col = (26, 44, 62), (228, 217, 195)
            border_col, grid_col = (60, 50, 40, 235), (255, 250, 235, 22)
        else:
            ocean_col, land_col = (7, 12, 20), (22, 29, 41)
            border_col, grid_col = (85, 220, 255, 235), (90, 185, 235, 20)

        base = Image.new("RGB", (MW, MH), ocean_col)
        yy, xx = np.mgrid[0:MH, 0:MW].astype(np.float32)
        rr = np.sqrt(((xx / MW - 0.5) * 1.4) ** 2 + ((yy / MH - 0.5) * 1.3) ** 2)
        arr = np.asarray(base, dtype=np.float32) * np.clip(1.12 - rr * 0.35, 0.65, 1.12)[..., None] + grain
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

        lmask = Image.new("L", (MW, MH), 0)
        dlm = ImageDraw.Draw(lmask)
        for r in self.ctx_xy:
            dlm.polygon(self._to_px(r), fill=255)
        sh = lmask.filter(ImageFilter.GaussianBlur(14))
        base = Image.composite(Image.new("RGB", (MW, MH), (0, 0, 0)), base, ImageEnhance.Brightness(sh).enhance(0.55))
        larr = np.clip(np.asarray(Image.new("RGB", (MW, MH), land_col), dtype=np.float32) + grain * 1.1, 0, 255).astype(np.uint8)
        base = Image.composite(Image.fromarray(larr), base, lmask)

        dm = ImageDraw.Draw(base, "RGBA")
        step = max(80, MW // 12)
        for gx in range(0, MW, step):
            dm.line([(gx, 0), (gx, MH)], fill=grid_col, width=1)
        for gy in range(0, MH, step):
            dm.line([(0, gy), (MW, gy)], fill=grid_col, width=1)
        for r in self.ctx_xy:
            pts = self._to_px(r)
            dm.line(pts + [pts[0]], fill=border_col, width=max(2, MW // 360))
        return base

    def frame(self, i, fps):
        W, H, MW, MH = self.W, self.H, self.MW, self.MH
        t = min(1.0, max(0.0, i / max(1.0, self.dur * fps - 1.0)))

        if self.mode == "vox":
            # MOTION 2: VOX / JOHNNY HARRIS — Diagonal Camera Glide + Animated Dotted Route Arc + Ink Wash
            glide = _ease(min(1.0, t / 0.78))
            arc_p = _ease(max(0.0, min(1.0, (t - 0.10) / 0.58)))
            st_p = _ease(max(0.0, min(1.0, (t - 0.48) / 0.28)))

            start_x = MW * (0.72 if self.tcx < MW * 0.5 else 0.28)
            start_y = MH * (0.72 if self.tcy < MH * 0.5 else 0.28)
            m = self.base.copy()
            d = ImageDraw.Draw(m, "RGBA")
            if st_p > 0.01:
                for r in self.tgt_xy:
                    pts = self._to_px(r)
                    d.polygon(pts, fill=(195, 48, 38, int(175 * st_p)))
                    d.line(pts + [pts[0]], fill=(140, 22, 18, int(255 * st_p)), width=max(3, MW // 240))

            steps = 44
            n_draw = int(steps * arc_p)
            ctrl_x = (start_x + self.tcx) * 0.5 - MW * 0.08
            ctrl_y = (start_y + self.tcy) * 0.5 - MH * 0.08
            for k in range(0, n_draw, 2):
                u0 = k / steps; u1 = min(1.0, (k + 1.2) / steps)
                ax0 = (1 - u0) ** 2 * start_x + 2 * (1 - u0) * u0 * ctrl_x + u0 ** 2 * self.tcx
                ay0 = (1 - u0) ** 2 * start_y + 2 * (1 - u0) * u0 * ctrl_y + u0 ** 2 * self.tcy
                ax1 = (1 - u1) ** 2 * start_x + 2 * (1 - u1) * u1 * ctrl_x + u1 ** 2 * self.tcx
                ay1 = (1 - u1) ** 2 * start_y + 2 * (1 - u1) * u1 * ctrl_y + u1 ** 2 * self.tcy
                d.line([(ax0, ay0), (ax1, ay1)], fill=(190, 38, 30, 240), width=max(3, MW // 240))
            if arc_p > 0.02:
                u = arc_p
                hx = (1 - u) ** 2 * start_x + 2 * (1 - u) * u * ctrl_x + u ** 2 * self.tcx
                hy = (1 - u) ** 2 * start_y + 2 * (1 - u) * u * ctrl_y + u ** 2 * self.tcy
                d.ellipse([hx - 10, hy - 10, hx + 10, hy + 10], fill=(255, 245, 220, 255), outline=(190, 38, 30, 255), width=3)

            cam_x = start_x * (1 - glide) + self.tcx * glide
            cam_y = start_y * (1 - glide) + self.tcy * glide
            zoom = 1.28 + 0.36 * glide
            hw = (W / 2.0) / zoom * (MW / W) * 0.92
            hh = (H / 2.0) / zoom * (MW / W) * 0.92
            x0c = max(0, min(MW - 4, int(cam_x - hw)))
            y0c = max(0, min(MH - 4, int(cam_y - hh)))
            x1c = max(x0c + 4, min(MW, int(cam_x + hw)))
            y1c = max(y0c + 4, min(MH, int(cam_y + hh)))
            frame = m.crop((x0c, y0c, x1c, y1c)).resize((W, H), Image.LANCZOS)

            if st_p > 0.01:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                do = ImageDraw.Draw(ov)
                cw, ch = int(W * 0.68), int(H * 0.095)
                cx0, cy0 = (W - cw) // 2, int(H * 0.72 + (1 - st_p) * 32)
                do.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=10,
                                     fill=(242, 234, 216, int(242 * st_p)), outline=(175, 42, 34, int(235 * st_p)), width=3)
                do.text((cx0 + 26, cy0 + int(ch * 0.16)), self.sub or "ARCHIVAL ATLAS FOCUS", fill=(165, 38, 30, int(235 * st_p)), font=self.f_sm)
                do.text((cx0 + 26, cy0 + int(ch * 0.42)), self.label, fill=(28, 24, 20, int(255 * st_p)), font=self.f_serif)
                frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
            return frame

        # MOTION 3: DEFENCE TACTICAL DARK HUD — Orbital Snap-Zoom + Rotating Radar Sweep + Closing Crosshair Lock!
        lock = _ease(min(1.0, t / 0.58))
        hud_p = _ease(max(0.0, min(1.0, (t - 0.36) / 0.26)))
        m = self.base.copy()
        d = ImageDraw.Draw(m, "RGBA")
        for r in self.tgt_xy:
            pts = self._to_px(r)
            d.polygon(pts, fill=(0, 195, 235, int(170 * lock)))
            d.line(pts + [pts[0]], fill=(160, 245, 255, 255), width=max(3, MW // 280))

        cam_x = MW * 0.50 * (1 - lock) + self.tcx * lock
        cam_y = MH * 0.48 * (1 - lock) + self.tcy * lock
        zoom = 0.95 + 1.38 * lock
        hw = (W / 2.0) / zoom * (MW / W) * 0.96
        hh = (H / 2.0) / zoom * (MW / W) * 0.96
        tf = 0.13 * lock
        src = [
            (cam_x - hw * (1 + tf), cam_y - hh * (1 + tf * 0.5)),
            (cam_x + hw * (1 + tf), cam_y - hh * (1 + tf * 0.5)),
            (cam_x + hw * (1 - tf * 0.6), cam_y + hh * (1 - tf * 0.35)),
            (cam_x - hw * (1 - tf * 0.6), cam_y + hh * (1 - tf * 0.35)),
        ]
        frame = m.transform((W, H), Image.PERSPECTIVE, _persp_coeffs(src, [(0, 0), (W, 0), (W, H), (0, H)]), Image.BICUBIC)

        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        do = ImageDraw.Draw(ov)
        rcx, rcy = W // 2, H // 2
        rad = int(min(W, H) * (0.24 - 0.08 * lock))
        do.ellipse([rcx - rad, rcy - rad, rcx + rad, rcy + rad], outline=(0, 220, 255, 130), width=2)
        do.ellipse([rcx - rad // 2, rcy - rad // 2, rcx + rad // 2, rcy + rad // 2], outline=(0, 220, 255, 85), width=1)
        ang = t * math.pi * 3.0
        do.line([(rcx, rcy), (rcx + math.cos(ang) * rad, rcy + math.sin(ang) * rad)], fill=(0, 240, 255, 210), width=3)
        b_off = int(min(W, H) * (0.19 - 0.09 * lock))
        bl = max(18, int(W * 0.032))
        for sx_i in (-1, 1):
            for sy_i in (-1, 1):
                bx, by = rcx + sx_i * b_off, rcy + sy_i * b_off
                do.line([(bx, by), (bx - sx_i * bl, by)], fill=(255, 200, 85, 245), width=4)
                do.line([(bx, by), (bx, by - sy_i * bl)], fill=(255, 200, 85, 245), width=4)

        if hud_p > 0.01:
            cw, ch = int(W * 0.70), int(H * 0.095)
            cx0, cy0 = (W - cw) // 2, int(H * 0.72 + (1 - hud_p) * 32)
            do.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=12,
                                 fill=(8, 16, 28, int(225 * hud_p)), outline=(0, 220, 255, int(210 * hud_p)), width=2)
            do.rectangle([cx0 + 18, cy0 + 18, cx0 + 24, cy0 + ch - 18], fill=(0, 225, 255, int(255 * hud_p)))
            do.text((cx0 + 40, cy0 + int(ch * 0.16)), self.sub or "TARGET LOCK • TACTICAL RADAR", fill=(0, 225, 255, int(240 * hud_p)), font=self.f_sm)
            do.text((cx0 + 40, cy0 + int(ch * 0.44)), self.label, fill=(248, 252, 255, int(255 * hud_p)), font=self.f_sans)
        return Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")


def _pick_map_style(place, style):
    forced = str((style or {}).get("map_style") or "").strip().lower()
    if forced in ("classic", "vox", "tactical"):
        return forced
    cat = str((style or {}).get("category") or "").strip().lower()
    seed = abs(hash((place.get("name") or "") + cat)) % 3
    if cat in ("army", "science", "technology", "mystery"):
        return ("tactical", "classic", "vox")[seed]
    if cat in ("history", "geography", "business", "general"):
        return ("vox", "classic", "tactical")[seed]
    return ("classic", "vox", "tactical")[seed]


def render(place, dur, out, W, H, style, pal, fps=30, label=None, sub=None):
    """v3.93: 3 Distinct-Motion Maps — Original Classic 3D Extrude + Vox Route Glide + Defence Radar Target Lock."""
    import fx
    mode = _pick_map_style(place, style)
    if mode == "classic":
        m = MapAnim(place, W, H, pal, dur, label, sub)
    else:
        m = _DistinctMapBase(place, W, H, dur, label, sub, mode=mode)
    n = max(2, int(round(dur * fps)))
    return fx._pipe_frames(lambda i: m.frame(i, fps), n, W, H, out, style, fps)
