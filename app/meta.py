"""v2.6: Title, description, hashtags, thumbnail aur Upload Kit (YouTube Studio khol deta hai)."""
import re, shutil, subprocess, webbrowser
from pathlib import Path
import numpy as np
from common import log, run, yes, duration
from ai import ask_json

BIG_TOPIC_WORDS = 4


def make_meta(key, lines, data=None, style=None, credits=()):
    style = style or {}
    m = {}
    if data:
        m = {k: data.get(k) for k in ("yt_title", "yt_description", "hashtags", "thumb_text")}
    if key and not all(m.get(k) for k in ("yt_title", "yt_description", "thumb_text")):
        res = ask_json(key, [
            "You are India's #1 YouTube SEO & High-CTR packaging expert for 'The Viral Gyaan'. "
            "From this Hindi script craft 2026 YouTube SEO-optimized, curiosity-driven upload metadata (100% factual, no fake claims):\n"
            "- yt_title: 45-62 chars in crisp Devanagari Hindi with the main searchable keyword + a shock number or curiosity gap (so it never cuts off on mobile).\n"
            "- thumb_text: ONLY 2-4 bold Hindi punch words that COMPLEMENT (never repeat) yt_title.\n"
            "- yt_description: 4 lines; first 2 lines naturally include primary Hindi + Hinglish search keywords.\n"
            "Return ONLY JSON: {\"yt_title\": \"45-62 char SEO Hindi title\", "
            "\"yt_description\": \"4 SEO-rich Hindi/Hinglish lines\", "
            "\"hashtags\": [\"#...\" x8], "
            "\"thumb_text\": \"2-4 bold Hindi punch words\", "
            "\"story_hook\": \"Short 6-10 word Hindi curiosity question ending with ?\", "
            "\"ig_caption\": \"2 punchy Hindi lines for IG/FB Reels with curiosity CTA\"}\n\n"
            + "\n".join(lines)], temperature=0.7, timeout=60)
        if isinstance(res, dict):
            for k, v in res.items():
                if not m.get(k): m[k] = v
    first = re.sub(r"[।,!?\"']", "", lines[0]).strip() if lines else "Fact"
    m.setdefault("yt_title", None); m["yt_title"] = (m["yt_title"] or first)[:95]
    m["yt_description"] = m.get("yt_description") or first
    tags = m.get("hashtags") or []
    if isinstance(tags, str): tags = tags.split()
    fixed = [t for t in re.split(r"[\s,]+", style.get("hashtags", "") or "") if t]
    allt = []
    for t in fixed + list(tags) + ["#shorts"]:
        t = "#" + t.lstrip("#").replace(" ", "")
        if len(t) > 1 and t.lower() not in [x.lower() for x in allt]: allt.append(t)
    m["hashtags"] = allt[:12]
    tt = m.get("thumb_text") or " ".join(first.split()[:BIG_TOPIC_WORDS])
    m["thumb_text"] = str(tt).strip()
    sh = str(m.get("story_hook") or "").strip()
    if not sh:
        sh = f"क्या आप जानते हैं? {first[:48]}?"
    m["story_hook"] = sh[:90]
    igc = str(m.get("ig_caption") or "").strip() or m["yt_description"]
    ig_tags = " ".join(m["hashtags"][:10])
    m["ig_caption"] = (igc.strip() + ("\n\n" + ig_tags if ig_tags and "#" not in igc else "")).strip()
    return m


# ------------------------------------------------------------------ thumbnail
def _best_time(video, total, work):
    """Sabse saaf + rangeen frame dhoondho (shuru ke 0.5s aur aakhri 4s chhod ke)."""
    best, bt = -1, total * 0.3
    for i in range(12):
        t = 0.6 + (total - 4.6) * i / 11 if total > 6 else total * (i + 1) / 13
        f = work / f"tf_{i}.jpg"
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                 "-vf", "scale=270:-2", f])
            from PIL import Image
            a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
            g = a.mean(2); sharp = np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean()
            rg = a[..., 0] - a[..., 1]; yb = (a[..., 0] + a[..., 1]) / 2 - a[..., 2]
            color = np.sqrt(rg.std() ** 2 + yb.std() ** 2)
            bright = g.mean()
            score = sharp * 2 + color * 0.5 - abs(bright - 115) * 0.3
            if score > best: best, bt = score, t
        except Exception:
            continue
    return bt


def _thumb_ass(path, W, H, text, font_size, y):
    words = text.split()
    if len(words) > 2:
        cut = (len(words) + 1) // 2
        text = " ".join(words[:cut]) + "\\N{\\c&H0000DDFF&}" + " ".join(words[cut:])
    path.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,VT Baloo,{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,1,{max(8, font_size // 9)},{max(6, font_size // 14)},5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,T,,0,0,0,,{{\\an5\\pos({W // 2},{y})}}{text}
""", encoding="utf-8")


def _score(img):
    a = np.asarray(img.convert("RGB").resize((270, 270))).astype(np.float32)
    g = a.mean(2); sharp = np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean()
    rg = a[..., 0] - a[..., 1]; yb = (a[..., 0] + a[..., 1]) / 2 - a[..., 2]
    color = np.sqrt(rg.std() ** 2 + yb.std() ** 2)
    return sharp * 2 + color * 0.6 - abs(g.mean() - 120) * 0.25


def _candidates(srcs, work, video):
    """v2.15: Asli footage ke saaf frames – SHURU ki lines (hook) wali footage pehle, kyunki thumbnail usi ki baat karta hai."""
    from PIL import Image
    out = []
    for k, (p, kind) in enumerate(srcs[:10]):
        try:
            if kind == "image":
                out.append((Image.open(p).convert("RGB"), k)); continue
            d = duration(p) or 3
            for j, f in enumerate((0.2, 0.5, 0.8)):
                fp = work / f"tc_{k}_{j}.jpg"
                run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d*f:.2f}", "-i", p, "-frames:v", "1", "-q:v", "2", fp])
                out.append((Image.open(fp).convert("RGB"), k))
        except Exception:
            continue
    if not out and video:                               # backup: bani hui video se
        total = duration(video)
        for i in range(8):
            fp = work / f"tc_v{i}.jpg"
            try:
                run(["ffmpeg", "-y", "-v", "error", "-ss", f"{0.6 + (total - 4) * i / 7:.2f}", "-i", video,
                     "-frames:v", "1", "-q:v", "2", fp])
                out.append((Image.open(fp).convert("RGB"), 5))
            except Exception:
                pass
    return [(im, k) for im, k in out if min(im.size) >= 200]


def _gemini_pick(key, ims, text, topic=""):
    """Returns (best_index, subject_box (x0,y0,x1,y1) 0..1 ya None)."""
    if not key or len(ims) < 1:
        return 0, None
    try:
        import io
        from ai import ask_json
        parts = [f"You are a top YouTube thumbnail designer. Video topic: {topic or text}. Thumbnail text: {text}.\n"
                 "Pick the ONE frame that best shows WHAT THE VIDEO IS ABOUT, so a viewer instantly understands the "
                 "topic: the actual subject clearly visible, big, sharp, dramatic, emotional or curious. "
                 "STRICTLY REJECT frames that are blurry, pitch-dark silhouettes/hoodies, generic filler (random sky/landscape/crowds), or text/logos. The chosen frame MUST visibly show the exact concrete subject/object/person named in the Video topic so the thumbnail background matches the title 100%.\n"
                 "Prefer a frame where the main person's FACE is clearly visible (not cut off).\n"
                 "Also give the bounding box of the main subject in that frame (0-1000). If the subject is a person, "
                 "the box must tightly cover the person's FACE / HEAD only (not the body or clothes).\n"
                 'Return ONLY JSON {"best": number, "box": [x0, y0, x1, y1]}']
        for i, im in enumerate(ims):
            b = io.BytesIO(); x = im.copy(); x.thumbnail((384, 384)); x.save(b, "JPEG", quality=78)
            parts += [f"Frame {i}:", {"jpg": b.getvalue()}]
        r = ask_json(key, parts, temperature=0.1, timeout=60, budget=120) or {}
        n = int(r.get("best", 0))
        n = n if 0 <= n < len(ims) else 0
        box = None
        try:
            bx = [float(v) / 1000 for v in r.get("box")]
            if len(bx) == 4 and bx[2] - bx[0] > 0.05 and bx[3] - bx[1] > 0.05: box = tuple(bx)
        except Exception:
            pass
        return n, box
    except Exception:
        return 0, None


def _compose(im, tw, th, side, focus=None):
    """Pro look: subject pe centre crop + tez rang + kinare andhere + text ki taraf dark gradient."""
    from PIL import Image, ImageEnhance
    r = max(tw / im.width, th / im.height) * 1.08
    x = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    if focus:
        fx_, fy_ = focus
        l = int(min(max(0, fx_ * x.width - tw * (0.62 if side == "left" else 0.5)), x.width - tw))
        t = int(min(max(0, fy_ * x.height - th * (0.58 if side != "left" else 0.5)), x.height - th))
    else:
        l = (x.width - tw) // 2; t = int((x.height - th) * 0.28)
        if side == "left": l = int((x.width - tw) * 0.65); t = int((x.height - th) * 0.12)   # v3.4: sir na kate
    x = x.crop((l, t, l + tw, t + th))
    # v4.10 Cinematic Grade: punchy film contrast, rich color pop & crisp hero detail
    x = ImageEnhance.Contrast(x).enhance(1.32)
    x = ImageEnhance.Color(x).enhance(1.42)
    x = ImageEnhance.Sharpness(x).enhance(1.95)
    yy, xx = np.mgrid[0:th, 0:tw].astype(np.float32)
    v = 1 - 0.55 * (((xx / tw - 0.5) ** 2 + (yy / th - 0.5) ** 2) * 2.2)      # vignette
    if side == "left":
        v *= np.clip(0.30 + 1.1 * (xx / tw), 0.30, 1.0)
    else:
        v *= np.clip(0.30 + 1.6 * (yy / th), 0.30, 1.0)
    a = np.asarray(x).astype(np.float32) * np.clip(v, 0.22, 1.0)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8")), (l / x.width if x.width else 0, t, r)


def _gola(img, box_px):
    """Subject ke chaaron taraf laal dashed gola + arrow (reference jaisa)."""
    from PIL import ImageDraw
    import math
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box_px
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = max(40, min(max(x1 - x0, y1 - y0) * 0.62, min(img.size) * 0.36))
    w = max(8, int(R * 0.07))
    for k in range(16):
        a0 = 360 * k / 16
        d.arc((cx - R, cy - R, cx + R, cy + R), a0, a0 + 13, fill=(0, 0, 0), width=w + 6)
    for k in range(16):
        a0 = 360 * k / 16
        d.arc((cx - R, cy - R, cx + R, cy + R), a0, a0 + 13, fill=(232, 28, 36), width=w)
    side = -1 if cx > img.width * 0.4 else 1
    tip = (cx + side * R * 0.80, cy + R * 0.62)
    L = R * 1.0; ang = math.atan2(R * 0.62, side * R * 0.80)
    ux, uy = math.cos(ang), math.sin(ang)
    tail = (tip[0] + ux * L, tip[1] + uy * L)
    hw, hl, sw = R * 0.22, R * 0.34, max(6, R * 0.075)
    px, py = -uy, ux
    base = (tip[0] + ux * hl, tip[1] + uy * hl)
    pts = [tip, (base[0] + px * hw, base[1] + py * hw), (base[0] + px * sw, base[1] + py * sw),
           (tail[0] + px * sw, tail[1] + py * sw), (tail[0] - px * sw, tail[1] - py * sw),
           (base[0] - px * sw, base[1] - py * sw), (base[0] - px * hw, base[1] - py * hw)]
    d.polygon(pts, fill=(232, 28, 36), outline=(0, 0, 0), width=4)
    return img


def _thumb_text_ass(path, W, H, text, side):
    words = text.split()
    cut = (len(words) + 1) // 2 if len(words) > 2 else (1 if len(words) == 2 else len(words))
    l1, l2 = " ".join(words[:cut]), " ".join(words[cut:])
    if not l2: l1, l2 = "", l1                         # ek hi hissa -> laal dabbe me
    mx = max(len(l1), len(l2))
    if side == "left":
        fs = 150 if mx <= 9 else (125 if mx <= 13 else 100)
        p1 = f"\\an4\\pos(60,{int(H * 0.40)})"; p2 = f"\\an4\\pos(78,{int(H * 0.40 + fs * 1.25)})"
    else:
        fs = 235 if mx <= 8 else (200 if mx <= 12 else (165 if mx <= 16 else 135))
        p1 = f"\\an8\\pos({W // 2},{int(H * 0.075)})"; p2 = f"\\an8\\pos({W // 2},{int(H * 0.075 + (fs * 1.18 if l1 else 0))})"
    ev = []
    if l1:
        ev.append(f"Dialogue: 1,0:00:00.00,0:00:10.00,T,,0,0,0,,{{{p1}}}{l1}")
    ev.append(f"Dialogue: 2,0:00:00.00,0:00:10.00,R,,0,0,0,,{{{p2}}}{l2}")
    path.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: T,VT Baloo,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,{max(10, fs // 9)},{max(7, fs // 12)},5,50,50,0,1
Style: R,VT Baloo,{int(fs * 0.92)},&H00FFFFFF,&H00FFFFFF,&H002420E8,&H96000000,1,0,0,0,100,100,0,0,3,{max(12, fs // 7)},{max(6, fs // 14)},5,50,50,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n", encoding="utf-8")


def make_thumbs(video, text, out_base, work, W=1080, H=1920, srcs=(), key=None, topic="", style=None):
    """v2.15 PRO thumbnail: hook wali footage ka sabse saaf frame jo TOPIC dikhaye (AI aankh + Gemini chunte hain),
    subject pe crop, laal gola + arrow, bada text (2nd line laal dabbe me), logo. Chaaho to Gemini AI photo wala bhi."""
    from PIL import Image
    style = style or {}
    ims = _candidates(list(srcs), work, video)
    if not ims:
        return []
    q = [_score(im) for im, _ in ims]
    qn = (np.array(q) - np.mean(q)) / (np.std(q) + 1e-6)
    sc = list(qn * 0.6 - np.array([k for _, k in ims]) * 0.12)       # shuru ki lines thodi aage
    try:
        import aankh
        if topic and yes(style.get("ai_aankh", "haan")) and aankh.STATE["ok"]:
            for i, (im, _) in enumerate(ims):
                m = aankh.match(im, topic)
                if m is not None: sc[i] += (m - 0.22) * 40           # topic se match = sabse zaroori
    except Exception:
        pass
    order = sorted(range(len(ims)), key=lambda i: sc[i], reverse=True)[:6]
    top = [ims[i][0] for i in order]
    bi, box = _gemini_pick(key, top, text, topic)
    best = top[bi]
    variants = [("", best, box)]
    if key and yes(style.get("thumb_ai", "haan")):
        try:
            import io, ai
            b = io.BytesIO(); r_ = best.copy(); r_.thumbnail((768, 768)); r_.save(b, "JPEG", quality=85)
            raw = ai.make_image(key, (
                f"Create a dramatic, photorealistic YouTube thumbnail image for a Hindi fact video about: {topic or text}. "
                "Use the reference photo as the subject and keep it accurate and realistic. One big clear subject, "
                "cinematic lighting, high contrast, rich colours, shallow depth of field, leave empty dark space at the top. "
                "Absolutely NO text, letters, numbers, logos or watermarks."), "9:16", b.getvalue())
            if raw:
                aim = Image.open(io.BytesIO(raw)).convert("RGB")
                if min(aim.size) >= 300:
                    variants.append(("_ai", aim, None))
                    log("   Gemini ne AI thumbnail bhi banaya ✓")
        except Exception as e:
            log(f"   (AI thumbnail skip: {str(e)[:80]})", show=False)
    logo = None
    try:
        from common import ASSETS
        lp = ASSETS / "logo" / "logo.png"
        if lp.exists(): logo = Image.open(lp).convert("RGBA")
    except Exception:
        pass
    done = []
    for tag, src, bx in variants:
        for kind, (tw, th), side in (("short", (W, H), "top"), ("16x9", (1280, 720), "left")):
            try:
                focus = ((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2) if bx else None
                base, _ = _compose(src, tw, th, side, focus)
                if bx and yes(style.get("thumb_gola", "haan")):
                    r = max(tw / src.width, th / src.height) * 1.08
                    sw, sh = src.width * r, src.height * r
                    fx_, fy_ = focus
                    l = min(max(0, fx_ * sw - tw * (0.62 if side == "left" else 0.5)), sw - tw)
                    t = min(max(0, fy_ * sh - th * (0.58 if side != "left" else 0.5)), sh - th)
                    bp_ = (bx[0] * sw - l, bx[1] * sh - t, bx[2] * sw - l, bx[3] * sh - t)
                    if bp_[2] > 0 and bp_[3] > th * 0.25 and bp_[0] < tw and bp_[1] < th:
                        _gola(base, bp_)
                if logo is not None:
                    s_ = int(min(tw, th) * 0.13); lg = logo.copy(); lg.thumbnail((s_, s_))
                    base.paste(lg, (tw - lg.width - int(tw * 0.03), th - lg.height - int(th * 0.03)), lg)
                bp = work / f"thumb_base_{kind}{tag}.png"; base.save(bp)
                ass = work / f"thumb_{kind}{tag}.ass"; _thumb_text_ass(ass, tw, th, text, side)
                out = Path(f"{out_base}_thumbnail{tag}_{kind}.jpg")
                run(["ffmpeg", "-y", "-v", "error", "-i", bp.name, "-vf", f"ass={ass.name}:fontsdir=fonts", "-q:v", "2",
                     str(out.resolve())], cwd=work)
                done.append(out)
            except Exception as e:
                log(f"   thumbnail ({kind}{tag}) nahi bana: {e}", show=False)
    return done


# ------------------------------------------------------------------ upload kit
def upload_kit(video, meta, credits, style, work, ai_voice=True, frame_src=None, chapters=(), srcs=(), key=None, topic=""):
    video = Path(video)
    base = video.with_suffix("")
    src = frame_src if frame_src and Path(frame_src).exists() else video
    thumbs = make_thumbs(src, meta["thumb_text"], base, work, srcs=srcs, key=key, topic=topic, style=style)
    desc = [meta["yt_description"].strip(), ""]
    ch_ok = [c for c in chapters]
    if len(ch_ok) >= 3:                                 # YouTube: kam se kam 3 chapters, pehla 0:00
        desc.append("⏱️ Chapters")
        for t, nm in ch_ok:
            desc.append(f"{int(t // 60)}:{int(t % 60):02d} {nm}")
        desc.append("")
    ch = (style.get("channel_naam") or "").strip()
    if ch: desc += [f"Aise hi aur facts ke liye {ch} ko subscribe karo!", ""]
    if credits:
        desc += ["Visuals: " + ", ".join(sorted({c.split(' – ')[0] for c in credits})), ""]
    desc.append(" ".join(meta["hashtags"]))
    kit = [
        "======== YOUTUBE UPLOAD KIT ========",
        "", "1) TITLE (copy karo):", meta["yt_title"],
        "", "2) DESCRIPTION (copy karo):", "\n".join(desc),
        "", "3) TAGS:", ", ".join(t.lstrip("#") for t in meta["hashtags"]),
        "", "4) THUMBNAIL:", *[f"   {p.name}" for p in thumbs],
        "   (Shorts me thumbnail phone app se video ka frame chun ke lagta hai; 16x9 wala normal video ke liye)",
    ]
    if ai_voice:
        kit += ["", "5) YouTube 'Altered or synthetic content' poochhe to: HAAN (AI awaaz hai)."]
    kit += ["", "Poori credits list:"] + [f"- {c}" for c in credits]
    kp = Path(f"{base}_UPLOAD.txt")
    kp.write_text("\n".join(kit), encoding="utf-8")
    log(f"   Upload Kit ready ✓  ({kp.name})")
    if yes(style.get("youtube_kholo", "haan")):
        try:
            webbrowser.open("https://www.youtube.com/upload")
        except Exception:
            pass
    return kp


# ------------------------------------------------------------------ Google Drive
def find_drive(style):
    """Google Drive for Desktop ka 'My Drive' folder dhoondho (G:\\My Drive waghera)."""
    import os, string
    want = (style.get("drive_folder") or "auto").strip()
    if want.lower() in ("nahi", "no", "band"):
        return None
    if want.lower() != "auto":
        p = Path(want)
        return p if p.exists() else None
    names = ("My Drive", "मेरी ड्राइव", "Meri Drive", "Mi unidad")
    for letter in string.ascii_uppercase[3:]:
        for n in names:
            p = Path(f"{letter}:/") / n
            try:
                if p.exists(): return p
            except Exception:
                pass
    home = Path.home()
    for p in (home / "Google Drive" / "My Drive", home / "Google Drive", home / "My Drive"):
        if p.exists(): return p
    return None


def to_drive(video, style):
    """Video + thumbnail + upload text ko Drive me: VG Videos/<aaj ki tarikh>/ (phone pe mil jaayega)."""
    import datetime
    root = find_drive(style)
    if not root:
        log("   (Google Drive nahi mila – video sirf output folder me hai)", show=False)
        return None
    video = Path(video); base = str(video.with_suffix(""))
    day = root / (style.get("drive_naam") or "VG Videos") / datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        day.mkdir(parents=True, exist_ok=True)
        for f in [video] + [Path(base + x) for x in ("_UPLOAD.txt", "_thumbnail_short.jpg", "_thumbnail_16x9.jpg")]:
            if f.exists(): shutil.copy2(f, day / f.name)
        log(f"   Google Drive me bhej diya ✓  ({day})")
        return day
    except Exception as e:
        log(f"   Drive me copy nahi hua: {e}")
        return None


# ------------------------------------------------------------------ v3.93 Reel Covers (3 Styles) & IG Stories (4 Styles)
def _load_social_font(name, size):
    from PIL import ImageFont
    from common import ASSETS
    cands = [
        ASSETS / "fonts" / name,
        Path("/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"),
        ASSETS / "fonts" / "Mukta-ExtraBold.ttf",
        ASSETS / "fonts" / "VTBaloo.ttf",
        ASSETS / "fonts" / "Poppins-ExtraBold.ttf",
    ]
    for p in cands:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap_hi_lines(text, font, max_w, max_lines=3):
    from PIL import Image, ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    words = str(text or "").strip().split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if d.textlength(test, font=font) <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
            if len(lines) >= max_lines - 1:
                break
    if cur:
        rem = words[sum(len(l.split()) for l in lines):]
        lines.append(" ".join(rem)[:42])
    return lines[:max_lines]


def _pick_hero_image(video, srcs, work):
    from PIL import Image
    ims = _candidates(list(srcs or ()), work, video)
    if not ims:
        return Image.new("RGB", (1080, 1920), (14, 18, 28))
    best_im = max(ims, key=lambda pair: _score(pair[0]) - pair[1] * 1.5)[0]
    return best_im.convert("RGB")


def make_reel_cover_and_story(video, meta, out_base, work, srcs=(), category=""):
    """v3.98 (Option A): Purane clean thumbnail style (smart _compose frame-fit + crisp FFmpeg libass Hindi shaping)
    for BOTH 1080x1920 Reel Cover Photo and IG Story — zero broken PIL Devanagari, zero cartoon/cropped boxes!"""
    from PIL import Image
    video = Path(video)
    base = Path(out_base)
    work = Path(work)
    hero_im = _pick_hero_image(video, srcs, work)
    W, H = 1080, 1920

    logo = None
    try:
        from common import ASSETS
        lp = ASSETS / "logo" / "logo.png"
        if lp.exists():
            logo = Image.open(lp).convert("RGBA")
    except Exception:
        pass

    def _render_clean_card(text_str, out_path, tag_name, cta_line=""):
        comp, _ = _compose(hero_im, W, H, "top", focus=None)
        if logo is not None:
            s_ = int(min(W, H) * 0.12)
            lg = logo.copy()
            lg.thumbnail((s_, s_))
            comp.paste(lg, (W - lg.width - int(W * 0.03), H - lg.height - int(H * 0.03)), lg)
        bp = work / f"social_base_{tag_name}.png"
        comp.save(bp)
        ass = work / f"social_{tag_name}.ass"
        _thumb_text_ass(ass, W, H, text_str, "top")
        if cta_line:
            try:
                _a = ass.read_text(encoding="utf-8")
                _a += f"Dialogue: 2,0:00:00.00,0:00:05.00,Sub,,0,0,0,,{{\an2\pos({W//2},{H-140})\fs38\b1\c&H00D4FF&\bord4\shad2}}{cta_line}\n"
                ass.write_text(_a, encoding="utf-8")
            except Exception:
                pass
        try:
            run(["ffmpeg", "-y", "-v", "error", "-i", bp.name, "-vf", f"ass={ass.name}:fontsdir=fonts",
                 "-q:v", "2", str(out_path.resolve())], cwd=work)
            if out_path.exists() and out_path.stat().st_size > 5000:
                return out_path
        except Exception as _e:
            log(f"   ({tag_name} ass render fallback: {_e})", show=False)
        comp.convert("RGB").save(out_path, "JPEG", quality=93)
        return out_path

    cover_txt = (meta.get("thumb_text") or meta.get("yt_title") or "असली सच").strip()
    story_txt = (meta.get("story_hook") or meta.get("yt_title") or cover_txt).strip()
    cover_path = _render_clean_card(cover_txt, Path(f"{base}_reel_cover.jpg"), "cover")
    story_path = _render_clean_card(story_txt, Path(f"{base}_ig_story.jpg"), "story", cta_line="NEW REEL LIVE  •  WATCH NOW")
    return cover_path, story_path
