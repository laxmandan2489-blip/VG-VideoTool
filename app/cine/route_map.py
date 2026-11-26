"""v4.16 GLOWING SATELLITE ROUTE / FLIGHT / MONEY-FLOW / CABLE ANIMATION (30fps HD MP4).

Triggered by script tag:
  [route: Delhi -> Tokyo | $4 BILLION]
  [flight: New Delhi -> Moscow | PM VISIT]
  [flow: Mumbai -> Europe | 98% INTERNET]
  or [map: India -> USA]

Uses real world/India vector boundaries from app/cine/places.py + dark night-lights canvas +
glowing curved bezier arc + racing light orbs / rotating jet + pulsing radar pins + glassmorphism HUD.
Works 100% offline/fast in both 9:16 (Shorts) and 16:9 (Long). Zero paid APIs.
"""
import math
import re
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import TOOL, log
from . import places
from .bible import font_path

# Built-in fast coordinates for top countries/cities (instant offline fallback before Nominatim)
_FAST_COORDS = {
    "india": (20.6, 78.9), "bharat": (20.6, 78.9), "new delhi": (28.6, 77.2), "delhi": (28.6, 77.2),
    "mumbai": (19.1, 72.9), "bengaluru": (13.0, 77.6), "bangalore": (13.0, 77.6), "chennai": (13.1, 80.3),
    "kolkata": (22.6, 88.4), "hyderabad": (17.4, 78.5), "ladakh": (34.2, 77.6), "kashmir": (34.1, 74.8),
    "usa": (39.8, -98.6), "america": (39.8, -98.6), "united states": (39.8, -98.6), "washington": (38.9, -77.0),
    "new york": (40.7, -74.0), "china": (35.9, 104.2), "beijing": (39.9, 116.4), "shanghai": (31.2, 121.5),
    "pakistan": (30.4, 69.3), "islamabad": (33.7, 73.1), "russia": (61.5, 105.3), "moscow": (55.8, 37.6),
    "ukraine": (48.4, 31.2), "kyiv": (50.5, 30.5), "israel": (31.0, 34.9), "tel aviv": (32.1, 34.8),
    "iran": (32.4, 53.7), "tehran": (35.7, 51.4), "syria": (34.8, 39.0), "damascus": (33.5, 36.3),
    "saudi arabia": (23.9, 45.1), "riyadh": (24.7, 46.7), "uae": (23.4, 53.8), "dubai": (25.2, 55.3),
    "japan": (36.2, 138.3), "tokyo": (35.7, 139.7), "south korea": (35.9, 127.8), "seoul": (37.6, 127.0),
    "europe": (50.1, 10.5), "uk": (55.4, -3.4), "london": (51.5, -0.1), "france": (46.2, 2.2),
    "paris": (48.9, 2.4), "germany": (51.2, 10.5), "berlin": (52.5, 13.4), "italy": (41.9, 12.6),
    "australia": (-25.3, 133.8), "sydney": (-33.9, 151.2), "canada": (56.1, -106.3), "brazil": (-14.2, -51.9),
    "egypt": (26.8, 30.8), "cairo": (30.0, 31.2), "red sea": (20.0, 38.5), "suez": (30.0, 32.5),
    "taiwan": (23.7, 121.0), "singapore": (1.35, 103.8), "vietnam": (14.1, 108.3), "bangladesh": (23.7, 90.4),
    "nepal": (28.4, 84.1), "sri lanka": (7.9, 80.8), "afghanistan": (33.9, 67.7), "turkey": (39.0, 35.2),
    "gaza": (31.5, 34.5), "qatar": (25.3, 51.2), "africa": (1.6, 17.0), "south africa": (-30.6, 22.9),
}


def _ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def _ease_in_out(x):
    x = max(0.0, min(1.0, x))
    return 3 * x * x - 2 * x * x * x


def _resolve_latlon(name):
    nm = re.sub(r"[^a-zA-Z0-9\s]", " ", str(name or "")).strip().lower()
    nm = re.sub(r"\s+", " ", nm)
    if nm in _FAST_COORDS:
        return _FAST_COORDS[nm]
    for k, v in _FAST_COORDS.items():
        if k in nm or nm in k:
            return v
    try:
        info = places.resolve(name)
        if info and info.get("lat") is not None and info.get("lon") is not None:
            return float(info["lat"]), float(info["lon"])
    except Exception:
        pass
    return None


def parse_route_spec(spec):
    """Parse 'Delhi -> Tokyo | $4 BILLION' or 'India to USA | TRADE' into (from_name, to_name, badge_label)."""
    raw = str(spec or "").strip()
    label = ""
    if "|" in raw:
        raw, label = [x.strip() for x in raw.split("|", 1)]
    parts = re.split(r"\s*(?:->|→|=>|\bto\b|\bse\b)\s*", raw, maxsplit=1, flags=re.I)
    if len(parts) < 2:
        return None
    a, b = parts[0].strip(), parts[1].strip()
    if not a or not b:
        return None
    return a, b, label


def _merc_y(lat):
    lat = max(-72.0, min(75.0, float(lat)))
    return math.degrees(math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0)))


def _font(kind, size):
    try:
        p = font_path(kind)
        if p:
            return ImageFont.truetype(str(p), size)
    except Exception:
        pass
    for rel in ("assets/fonts/Poppins-ExtraBold.ttf", "assets/fonts/Poppins-SemiBold.ttf", "assets/fonts/Mukta-ExtraBold.ttf"):
        fp = TOOL / rel
        if fp.exists():
            try:
                return ImageFont.truetype(str(fp), size)
            except Exception:
                pass
    return ImageFont.load_default()


def _build_map_canvas(W, H, lat1, lon1, lat2, lon2):
    """Render dark night-lights satellite-style world map zoomed cleanly around (lat1,lon1) & (lat2,lon2)."""
    y1, y2 = _merc_y(lat1), _merc_y(lat2)
    cx_lon = (lon1 + lon2) * 0.5
    cy_y = (y1 + y2) * 0.5
    span_lon = max(36.0, abs(lon2 - lon1) * 1.95)
    span_y = max(28.0, abs(y2 - y1) * 2.15)
    scale_x = W / span_lon
    scale_y = (H * 0.72) / span_y
    sc = min(scale_x, scale_y)

    def proj(lat, lon):
        px = W * 0.5 + (lon - cx_lon) * sc
        py = H * 0.46 - (_merc_y(lat) - cy_y) * sc
        return px, py

    # Deep dark navy bathymetric ocean background
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r_d = np.sqrt(((xx - W * 0.5) / (W * 0.65)) ** 2 + ((yy - H * 0.45) / (H * 0.60)) ** 2)
    bg = np.zeros((H, W, 3), dtype=np.float32)
    bg[..., 0] = np.clip(14 - 8 * r_d, 4, 22)
    bg[..., 1] = np.clip(26 - 14 * r_d, 8, 36)
    bg[..., 2] = np.clip(46 - 22 * r_d, 14, 62)
    im = Image.fromarray(bg.astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im, "RGBA")

    # Subtle tactical lat/lon grid
    for glon in range(-180, 181, 15):
        x0, _ = proj(0, glon)
        if 0 <= x0 <= W:
            d.line([(x0, 0), (x0, H)], fill=(55, 115, 175, 22), width=1)
    for glat in range(-60, 76, 15):
        _, y0 = proj(glat, 0)
        if 0 <= y0 <= H:
            d.line([(0, y0), (W, y0)], fill=(55, 115, 175, 22), width=1)

    # Draw real world landmass polygons from places.world()
    try:
        world = places.world()
        feats = world.get("features") if isinstance(world, dict) else []
        for feat in feats:
            geom = (feat or {}).get("geometry") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates") or []
            rings = []
            if gtype == "Polygon":
                rings = [coords[0]] if coords else []
            elif gtype == "MultiPolygon":
                rings = [poly[0] for poly in coords if poly]
            for ring in rings:
                if len(ring) < 3:
                    continue
                pts = [proj(pt[1], pt[0]) for pt in ring[::max(1, len(ring) // 120)]]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                if max(xs) < -100 or min(xs) > W + 100 or max(ys) < -100 or min(ys) > H + 100:
                    continue
                d.polygon(pts, fill=(22, 30, 44, 255), outline=(62, 96, 138, 125))
    except Exception:
        pass

    # Subtle golden night-lights city dots across major global hubs
    for _cname, (clat, clon) in _FAST_COORDS.items():
        gx, gy = proj(clat, clon)
        if 10 < gx < W - 10 and 10 < gy < H - 10:
            d.ellipse([gx - 5, gy - 5, gx + 5, gy + 5], fill=(255, 196, 72, 48))
            d.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(255, 222, 128, 135))

    return im, proj


def render_route(spec, dur, out, W, H, style, pal=None, fps=30):
    """Render a glowing 30fps satellite route/flight/money-flow MP4 clip. Returns out path or None."""
    parsed = parse_route_spec(spec)
    if not parsed:
        return None
    name_a, name_b, badge = parsed
    c1 = _resolve_latlon(name_a)
    c2 = _resolve_latlon(name_b)
    if not (c1 and c2):
        return None

    dur = max(2.2, min(7.0, float(dur or 3.8)))
    frames = max(24, int(round(dur * fps)))
    is_money = bool(re.search(r"(\$|₹|€|£|cr|crore|billion|million|deal|fund|trade|aid|paisa|rupee)", badge, re.I))
    is_flight = bool(re.search(r"(flight|pm|visit|trip|jet|plane|air|tour)", f"{spec} {badge}", re.I))
    arc_rgb = (255, 202, 48) if is_money else (35, 230, 255)

    base_map, proj = _build_map_canvas(W, H, c1[0], c1[1], c2[0], c2[1])
    ax, ay = proj(c1[0], c1[1])
    bx, by = proj(c2[0], c2[1])
    dist = math.hypot(bx - ax, by - ay)
    mx, my = (ax + bx) * 0.5, (ay + by) * 0.5
    # Curved bezier control point arcing cleanly upward
    lift = max(80.0, min(H * 0.24, dist * 0.36))
    cx, cy = mx, my - lift

    def qbez(u):
        x = (1 - u) ** 2 * ax + 2 * (1 - u) * u * cx + u ** 2 * bx
        y = (1 - u) ** 2 * ay + 2 * (1 - u) * u * cy + u ** 2 * by
        dx = 2 * (1 - u) * (cx - ax) + 2 * u * (bx - cx)
        dy = 2 * (1 - u) * (cy - ay) + 2 * u * (by - cy)
        return x, y, math.atan2(dy, dx)

    f_city = _font("bold", max(24, int(min(W, H) * 0.032)))
    f_hud = _font("bold", max(36, int(min(W, H) * 0.056)))
    f_sub = _font("bold", max(20, int(min(W, H) * 0.024)))
    num_m = re.search(r"(\d[\d,\.]*)", badge or "")

    from render import enc_args
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-an",
    ] + enc_args(style) + [str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for i in range(frames):
        t = i / fps
        prog = _ease_in_out(t / max(0.8, dur * 0.65))
        im = base_map.copy().convert("RGBA")
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)

        # Glowing curved arc
        n_seg = max(2, int(60 * prog))
        pts = [qbez(k / 59.0)[:2] for k in range(n_seg)]
        if len(pts) >= 2:
            gd.line(pts, fill=(*arc_rgb, 110), width=16, joint="curve")
            gd.line(pts, fill=(*arc_rgb, 245), width=5, joint="curve")

        # Racing glowing orbs along the route
        for k in range(5):
            u = ((t * 0.55) + k * 0.20) % 1.0
            if u <= prog:
                ox, oy, _ = qbez(u)
                gd.ellipse([ox - 10, oy - 10, ox + 10, oy + 10], fill=(*arc_rgb, 180))
                gd.ellipse([ox - 4, oy - 4, ox + 4, oy + 4], fill=(255, 255, 255, 255))

        # Rotating airplane chevron at leading tip if flight/route
        if prog > 0.04:
            lx, ly, lang = qbez(prog)
            sz = 18 if is_flight else 12
            tip = (lx + math.cos(lang) * sz, ly + math.sin(lang) * sz)
            left = (lx + math.cos(lang + 2.4) * sz * 0.9, ly + math.sin(lang + 2.4) * sz * 0.9)
            right = (lx + math.cos(lang - 2.4) * sz * 0.9, ly + math.sin(lang - 2.4) * sz * 0.9)
            gd.polygon([tip, left, (lx, ly), right], fill=(255, 255, 255, 255))

        # Pulsing radar rings at Node A & Node B
        for nx, ny, col, show_at in ((ax, ay, (45, 230, 255), 0.0), (bx, by, (255, 205, 55), 0.65)):
            if prog >= show_at:
                for ri in range(2):
                    rp = (t * 0.9 + ri * 0.5) % 1.0
                    rad = 10 + rp * 48
                    gd.ellipse([nx - rad, ny - rad, nx + rad, ny + rad], outline=(*col, int((1 - rp) * 190)), width=3)
                gd.ellipse([nx - 8, ny - 8, nx + 8, ny + 8], fill=(*col, 255))

        # Soft bloom composite
        bloom = glow_layer.filter(ImageFilter.GaussianBlur(7))
        im = Image.alpha_composite(im, bloom)
        im = Image.alpha_composite(im, glow_layer)
        d = ImageDraw.Draw(im)

        # City Labels
        lbl_a = name_a.upper()[:18]
        lbl_b = name_b.upper()[:18]
        d.text((max(24, min(W - 220, ax - 40)), min(H - 90, ay + 22)), lbl_a, font=f_city, fill=(115, 240, 255, 255), stroke_width=4, stroke_fill=(6, 10, 16, 255))
        if prog >= 0.45:
            d.text((max(24, min(W - 220, bx - 40)), min(H - 90, by + 22)), lbl_b, font=f_city, fill=(255, 222, 85, 255), stroke_width=4, stroke_fill=(6, 10, 16, 255))

        # Glassmorphism HUD Badge at lower-center
        if badge:
            hp = _ease_out((t - 0.25) / 0.55)
            cw = min(int(W * 0.80), 660)
            ch = 148 if H > W else 128
            cx0 = (W - cw) // 2
            cy0 = int(H * (0.72 if H > W else 0.76) + (1 - hp) * 35)
            d.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=22, fill=(10, 16, 28, 225), outline=(*arc_rgb, 210), width=3)
            disp = badge.upper()
            if num_m:
                try:
                    raw_n = num_m.group(1)
                    target_v = float(raw_n.replace(",", ""))
                    cur_v = target_v * _ease_out(t / max(0.8, dur * 0.6))
                    dec = len(raw_n.split(".")[1]) if "." in raw_n else 0
                    fmt_n = f"{cur_v:,.{dec}f}" if dec else f"{int(round(cur_v)):,}"
                    disp = disp[:num_m.start()] + fmt_n + disp[num_m.end():]
                except Exception:
                    pass
            tw = d.textlength(disp, font=f_hud)
            d.text(((W - tw) / 2, cy0 + 22), disp, font=f_hud, fill=(*arc_rgb, 255))
            sub_txt = f"{lbl_a}  →  {lbl_b}"
            sw = d.textlength(sub_txt, font=f_sub)
            d.text(((W - sw) / 2, cy0 + ch - 44), sub_txt, font=f_sub, fill=(215, 230, 245, 230))

        # Subtle slow cinema zoom push-in (1.0 -> 1.06)
        z = 1.0 + 0.06 * (t / dur)
        if z > 1.002:
            nw, nh = int(W * z), int(H * z)
            im_rgb = im.convert("RGB").resize((nw, nh), Image.BILINEAR)
            ox, oy = (nw - W) // 2, (nh - H) // 2
            im_rgb = im_rgb.crop((ox, oy, ox + W, oy + H))
        else:
            im_rgb = im.convert("RGB")
        proc.stdin.write(im_rgb.tobytes())

    proc.stdin.close()
    if proc.wait() != 0:
        return None
    log(f"   🛰️ route map ready: {name_a} -> {name_b}" + (f" ({badge})" if badge else ""), show=False)
    return out
