"""v4.29 VIRAL HOOK TITLE – video ke pehle ~2.6 sec ka animated hook title (Shorts 9:16 + Longs 16:9).

1) Agar Node.js 22+ aur HyperFrames install ho (aur Short ho) to HeyGen HyperFrames use hota hai.
2) Warna (jaise GitHub Actions Node v20 par) – 100% Python/Pillow + FFmpeg native transparent VP9 WebM
   hook title banta hai: category pill badge + kinetic slide-up bold headline + animated accent underline sweep!
Zero Node 22+ dependency, 100% free, har video me guaranteed chalta hai.
"""
import json, os, re, shutil, subprocess
from pathlib import Path
from common import log, TOOL, ASSETS

HF_DIR = TOOL / "hyperframes"
TPL = TOOL / "assets" / "hyperframes" / "hook"
STATE = {"ok": None, "why": ""}


def _npx():
    return "npx.cmd" if os.name == "nt" else "npx"


def available():
    """Return True if HeyGen HyperFrames (Node 22+) is ready."""
    if STATE["ok"] is not None:
        return STATE["ok"]
    STATE["ok"] = False
    node = shutil.which("node")
    if not node:
        STATE["why"] = "Node.js nahi mila (native Python hook use hoga)"
        return False
    try:
        v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        if int(re.sub(r"[^\d.]", "", v).split(".")[0]) < 22:
            STATE["why"] = f"Node {v} purana – native Python hook use hoga"
            return False
    except Exception as e:
        STATE["why"] = f"node check fail: {e}"
        return False
    if not (HF_DIR / "node_modules" / "hyperframes").exists():
        STATE["why"] = "hyperframes install nahi – native Python hook use hoga"
        return False
    if not (TPL / "index.html").exists():
        STATE["why"] = "hook template nahi mila – native Python hook use hoga"
        return False
    STATE["ok"] = True
    return True


def _hex_rgb(hx, default=(250, 204, 21)):
    try:
        h = str(hx or "").strip().lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        pass
    return default


def _load_font(size, prefer_hi=False):
    from PIL import ImageFont
    cands = []
    if prefer_hi:
        cands += [
            ASSETS / "fonts" / "Mukta-ExtraBold.ttf",
            ASSETS / "fonts" / "NotoSansDevanagari-Bold.ttf",
            Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"),
        ]
    cands += [
        ASSETS / "fonts" / "Poppins-ExtraBold.ttf",
        ASSETS / "fonts" / "BebasNeue-Regular.ttf",
        ASSETS / "fonts" / "Mukta-ExtraBold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for p in cands:
        try:
            if p.exists():
                return ImageFont.truetype(str(p), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap_lines(draw, text, font, max_w, max_lines=2):
    """v4.30: Strictly pixel-bounded word wrapping — NEVER overflows left/right edges!"""
    words = (text or "").split()
    if not words:
        return []
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), cand, font=font)
        if bbox[2] - bbox[0] <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    # Clamp every final line strictly within max_w (word-safe trim if still wider)
    out = []
    for idx, ln in enumerate(lines[:max_lines]):
        if draw.textbbox((0, 0), ln, font=font)[2] <= max_w:
            out.append(ln)
            continue
        wds = ln.split()
        while len(wds) > 1 and draw.textbbox((0, 0), " ".join(wds), font=font)[2] > max_w:
            wds.pop()
        fitted = " ".join(wds)
        while len(fitted) > 4 and draw.textbbox((0, 0), fitted, font=font)[2] > max_w:
            fitted = fitted[:-1]
        out.append(fitted.strip())
    return [x for x in out if x]


def render_hook_native(line1, line2, out, hl="", W=1080, H=1920, badge="", accent="#FACC15", fps=30, dur=2.55):
    """v4.29 Python/Pillow + FFmpeg 30fps transparent VP9 WebM viral hook title (9:16 Shorts + 16:9 Longs)."""
    from PIL import Image, ImageDraw, ImageFilter
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    is_short = H > W
    pill_txt = (badge or line1 or "VIRAL FACT").strip().upper()[:26]
    main_txt = (line2 or line1 or "").strip()
    if not main_txt:
        return None
    # If line2 == line1 and badge was empty, keep pill generic so text doesn't duplicate
    if not badge and main_txt.upper() == pill_txt:
        pill_txt = "FACT BRIEF"

    has_dev = bool(re.search(r"[\u0900-\u097F]", main_txt))
    acc_rgb = _hex_rgb(accent, (250, 204, 21))

    f_pill = _load_font(max(24, int(W * (0.028 if is_short else 0.017))), prefer_hi=False)
    tmp_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dtmp = ImageDraw.Draw(tmp_img)
    max_tw = int(W * (0.84 if is_short else 0.68))
    disp_txt = main_txt.upper() if not has_dev else main_txt
    # v4.30: Auto-shrink headline font until ALL words fit cleanly inside 2 lines & max_tw (zero horizontal cutoff!)
    base_sz = max(44, int(W * (0.058 if is_short else 0.036)))
    min_sz = max(32, int(W * (0.036 if is_short else 0.024)))
    f_main = _load_font(base_sz, prefer_hi=has_dev)
    wrapped = _wrap_lines(dtmp, disp_txt, f_main, max_tw, max_lines=2)
    for sz in range(base_sz, min_sz - 1, -4):
        f_try = _load_font(sz, prefer_hi=has_dev)
        w_try = _wrap_lines(dtmp, disp_txt, f_try, max_tw, max_lines=2)
        used_words = sum(len(x.split()) for x in w_try)
        max_lw = max((dtmp.textbbox((0, 0), x, font=f_try)[2] for x in w_try), default=0)
        f_main, wrapped = f_try, w_try
        if used_words >= len(disp_txt.split()) and max_lw <= max_tw:
            break
    if not wrapped:
        return None

    # Measure layout in upper safe zone (never blocks captions at bottom or center faces)
    base_y = int(H * (0.125 if is_short else 0.105))
    pb = dtmp.textbbox((0, 0), pill_txt, font=f_pill)
    pw = (pb[2] - pb[0]) + int(W * (0.055 if is_short else 0.032))
    ph = (pb[3] - pb[1]) + int(H * (0.016 if is_short else 0.022))

    line_sizes = []
    for ln in wrapped:
        lb = dtmp.textbbox((0, 0), ln, font=f_main)
        line_sizes.append((lb[2] - lb[0], lb[3] - lb[1]))
    line_gap = int((line_sizes[0][1] if line_sizes else 50) * 1.24)
    total_text_h = len(wrapped) * line_gap
    bar_w_full = min(max_tw, max((w for w, _ in line_sizes), default=300) + 40)

    # Pre-render static soft dark scrim behind the title block for high contrast on any footage
    scrim_box_w = min(int(W * 0.92), max(pw, bar_w_full) + int(W * 0.10))
    scrim_box_h = ph + total_text_h + int(H * (0.055 if is_short else 0.085))
    scrim_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(scrim_layer)
    sx0 = (W - scrim_box_w) // 2
    sy0 = max(12, base_y - int(H * 0.018))
    ds.rounded_rectangle((sx0, sy0, sx0 + scrim_box_w, sy0 + scrim_box_h), radius=28, fill=(8, 12, 20, 148))
    scrim_layer = scrim_layer.filter(ImageFilter.GaussianBlur(radius=14))

    total_frames = max(24, int(round(dur * fps)))
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-deadline", "realtime", "-cpu-used", "6", "-crf", "28", "-b:v", "0",
        str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    hl_low = (hl or "").strip().lower()

    def _ease_out(x):
        x = max(0.0, min(1.0, x))
        return 1.0 - (1.0 - x) ** 3

    try:
        for fi in range(total_frames):
            t = fi / float(fps)
            # Global alpha (fade in 0.0-0.18s, hold, fade out last 0.42s)
            a_in = _ease_out(t / 0.18)
            a_out = 1.0 - _ease_out((t - (dur - 0.42)) / 0.42) if t > (dur - 0.42) else 1.0
            ga = max(0.0, min(1.0, a_in * a_out))

            frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            if ga > 0.01:
                # Apply faded scrim
                sc_a = scrim_layer.copy()
                if ga < 0.99:
                    r_, g_, b_, al_ = sc_a.split()
                    al_ = al_.point(lambda v: int(v * ga))
                    sc_a = Image.merge("RGBA", (r_, g_, b_, al_))
                frame = Image.alpha_composite(frame, sc_a)

                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(ov)

                # 1. Category pill badge pop-in (0.00 - 0.28s)
                p_prog = _ease_out(t / 0.28)
                p_dy = int((1.0 - p_prog) * (-26))
                px0 = (W - pw) // 2
                py0 = base_y + p_dy
                d.rounded_rectangle((px0, py0, px0 + pw, py0 + ph), radius=ph // 2,
                                    fill=(acc_rgb[0], acc_rgb[1], acc_rgb[2], int(245 * ga)))
                ptx = px0 + (pw - (pb[2] - pb[0])) // 2 - pb[0]
                pty = py0 + (ph - (pb[3] - pb[1])) // 2 - pb[1]
                d.text((ptx, pty), pill_txt, font=f_pill, fill=(14, 18, 26, int(255 * ga)))

                # 2. Bold 2-line headline slide-up (0.10 - 0.44s)
                h_prog = _ease_out((t - 0.10) / 0.34)
                h_dy = int((1.0 - h_prog) * 34)
                h_alpha = int(255 * ga * h_prog)
                ty0 = base_y + ph + int(H * (0.018 if is_short else 0.024)) + h_dy
                if h_alpha > 4:
                    for idx, ln in enumerate(wrapped):
                        lw, _ = line_sizes[idx]
                        lx = (W - lw) // 2
                        ly = ty0 + idx * line_gap
                        # Crisp drop shadow + stroke for readability
                        d.text((lx + 4, ly + 5), ln, font=f_main, fill=(0, 0, 0, int(h_alpha * 0.85)))
                        col = (acc_rgb[0], acc_rgb[1], acc_rgb[2], h_alpha) if (idx == 1 or (hl_low and hl_low in ln.lower())) else (255, 255, 255, h_alpha)
                        d.text((lx, ly), ln, font=f_main, fill=col, stroke_width=3, stroke_fill=(0, 0, 0, int(h_alpha * 0.92)))

                # 3. Animated accent bar sweep underneath (0.34 - 0.76s)
                b_prog = _ease_out((t - 0.34) / 0.42)
                if b_prog > 0.02:
                    bw = int(bar_w_full * b_prog)
                    bx0 = (W - bw) // 2
                    by0 = base_y + ph + int(H * (0.018 if is_short else 0.024)) + total_text_h + 10
                    bh = 7 if is_short else 6
                    d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=4,
                                        fill=(acc_rgb[0], acc_rgb[1], acc_rgb[2], int(240 * ga)))

                frame = Image.alpha_composite(frame, ov)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        proc.wait(timeout=90)
        if proc.returncode == 0 and out.exists() and out.stat().st_size > 5000:
            log(f"   ✨ Viral Hook Title ban gaya ({W}x{H}, pill='{pill_txt}') ✓")
            return out
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        log(f"   (Native hook error: {str(e)[:140]})", show=False)
    return None


def render_hook(line1, line2, out, hl="", timeout=300, W=1080, H=1920, badge="", accent="#FACC15"):
    """Return out (transparent .webm) ya None.
    v4.29: HyperFrames available ho (Shorts + Node 22+) to wahi; warna guaranteed Python-native VP9 WebM!"""
    out = Path(out)
    tc = lambda t: " ".join(w if any(c.isupper() for c in w) else w[:1].upper() + w[1:] for w in (t or "").split())
    vars_ = {"line1": tc(line1)[:28], "line2": tc(line2)[:70], "hl": hl or ""}

    if H > W and available():
        stamp = out.with_suffix(".vars.json")
        try:
            if out.exists() and out.stat().st_size > 5000 and stamp.exists() and \
                    json.loads(stamp.read_text(encoding="utf-8")) == vars_:
                log("   ✨ HyperFrames hook: pichhla wahi title dobara use ✓", show=False)
                return out
        except Exception:
            pass
        n = 0
        while (out.parent / f"hf_hook_{n}").exists() and n < 50:
            n += 1
        proj = out.parent / f"hf_hook_{n}"
        try:
            for old_ in out.parent.glob("hf_hook*"):
                if old_.is_dir():
                    shutil.rmtree(old_, ignore_errors=True)
            shutil.copytree(TPL, proj, dirs_exist_ok=True)
            vf = proj / "vars.json"
            vf.write_text(json.dumps(vars_, ensure_ascii=False), encoding="utf-8")
            env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1", HYPERFRAMES_NO_AUTO_INSTALL="1")
            cmd = [_npx(), "--no-install", "hyperframes", "render", str(proj), "--format", "webm", "-o", str(out),
                   "--quality", "draft", "--fps", "30", "--workers", "1", "--variables-file", str(vf), "--quiet"]
            r = subprocess.run(cmd, cwd=str(HF_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=timeout, env=env, stdin=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0 and out.exists() and out.stat().st_size > 5000:
                log("   ✨ HyperFrames hook title ban gaya ✓")
                try:
                    stamp.write_text(json.dumps(vars_, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass
                return out
            log(f"   (HyperFrames hook fail, native fallback: {(r.stderr or r.stdout or '')[-120:]})", show=False)
        except Exception as e:
            log(f"   (HyperFrames hook error, native fallback: {str(e)[:120]})", show=False)

    return render_hook_native(line1, line2, out, hl=hl, W=W, H=H, badge=badge, accent=accent)
