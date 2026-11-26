"""Video building: shots, captions (ASS), overlays, audio mix, final mux."""
import random, re, shutil
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from common import log, run, run_progress, duration, num, yes, ASSETS, has_video_stream
from voice import load_wav, save_wav, SR

FPS = 30
COLORS = {"peela": (255, 221, 0), "hara": (60, 230, 90), "laal": (255, 60, 60),
          "neela": (60, 170, 255), "safed": (255, 255, 255), "orange": (255, 140, 42)}
FONT = ASSETS / "fonts" / "VTBaloo.ttf"


def size_for(style):
    """Output dimensions; VG_LOW_MEMORY=1 renders at half linear resolution."""
    dims = (1920, 1080) if style.get("format") == "lambi" else (1080, 1920)
    if yes(__import__("os").environ.get("VG_LOW_MEMORY", "nahin")):
        return (dims[0] // 2, dims[1] // 2)
    return dims


def enc_args(style, final=False):
    # v2.1 speed: final "achhi" = veryfast (pehle medium tha, 2-3 guna dheema, YouTube pe farak nahi dikhta)
    fast = style.get("quality") == "tez"
    if final:
        return ["-c:v", "libx264", "-threads", "0", "-preset", "ultrafast" if fast else "superfast", "-crf", "22" if fast else "19",
                "-pix_fmt", "yuv420p"]
    # beech ke chhote shots: sirf temporary, isliye sabse tez setting
    # v3.1: sab shots ka same fps + timebase -> concat (-c copy) me jhatka / atka frame nahi
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "17", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-video_track_timescale", "15360"]


# ------------------------------------------------------------------ text card
def text_card(text, path, W, H, idx=0):
    pal = [((25, 20, 60), (120, 20, 60)), ((10, 40, 70), (10, 110, 120)), ((60, 15, 15), (160, 60, 20)),
           ((15, 15, 15), (70, 70, 90))]
    a, b = pal[idx % len(pal)]
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    # soft glow circle
    glow = Image.new("L", (W, H), 0); g = ImageDraw.Draw(glow)
    r = int(min(W, H) * 0.45); g.ellipse((W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r), fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    im = Image.composite(Image.new("RGB", (W, H), (255, 170, 60)), im, glow)
    d = ImageDraw.Draw(im)
    # text: pick the most "punchy" part (number or first 3 words)
    m = re.search(r"[\d,.]+\s*\S*", text)
    big = m.group(0) if m else " ".join(text.split()[:3])
    if re.search(r"[\u0900-\u097f]", big):          # v3.1: card pe Hindi lipi nahi (captions Hinglish hain) – Hinglish
        try:
            from translit import word as _hw
            big = " ".join(_hw(w) for w in big.split()).upper()
        except Exception:
            big = ""
    size = int(W * 0.16) if len(big) < 10 else int(W * 0.11)
    f = ImageFont.truetype(str(FONT), size)
    words = big.split(); lines = []; cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) > W * 0.85 and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    lines.append(cur)
    y = H // 2 - len(lines) * size * 0.6
    for ln in lines:
        w = d.textlength(ln, font=f)
        d.text(((W - w) / 2, y), ln, font=f, fill=(255, 221, 0), stroke_width=int(size * 0.07), stroke_fill=(0, 0, 0))
        y += size * 1.15
    im.save(path, quality=92)
    return path


# ------------------------------------------------------------------ one shot
def _prep_image(path, W, H, S=1.12):  # v3.86: gentler zoom so portrait/archival edges never chop off
    """Cover-fit if the photo shape is close to the frame, else show it whole on a blurred copy.
    v3.13: zoom ke baad bhi poori photo dikhe – foreground poori chaudai ka (zoom 6% tak kinare nahi katte)."""
    im = Image.open(path).convert("RGB")
    tw, th = int(W * S), int(H * S)
    ar_img = im.width / im.height; ar_out = W / H
    r = max(tw / im.width, th / im.height)
    bg = im.resize((max(tw, int(im.width * r)), max(th, int(im.height * r))), Image.LANCZOS)
    l = (bg.width - tw) // 2; t = (bg.height - th) // 2
    bg = bg.crop((l, t, l + tw, t + th))
    if abs(ar_img - ar_out) / ar_out < 0.30:
        return bg
    bg = bg.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.55))
    f = min(tw * 0.92 / im.width, th * 0.7 / im.height)
    fg = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
    bg.paste(fg, ((tw - fg.width) // 2, (th - fg.height) // 2 - int(th * 0.06)))
    return bg


def _with_transition(cmd_in, vf, trans, W, H, frames, style, out):
    """Run a shot with a light-leak video screen-blended on its first part."""
    # v3.15 FIX (15 Nov: "transition lage par kuch dikhta hi nahi" – light leak 1-2 sec poora frame laal/peela kar deta
    # tha): transition sirf 0.55 sec, aakhri 0.25 sec me fade, aur 70% taakat – footage hamesha dikhe
    td = float(trans.get("dur") or 0.55)
    tf = (f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setpts=PTS-STARTPTS,"
          f"trim=duration={td:.2f},fade=t=out:st={max(0.1, td - 0.25):.2f}:d=0.25,"
          f"tpad=stop_mode=add:stop_duration=30:color=black,format=gbrp[t];"
          f"[0:v]{vf},format=gbrp[b];[b][t]blend=all_mode=screen:all_opacity=0.7:shortest=1,format=yuv420p[v]")
    cmd = ["ffmpeg", "-y", "-v", "error"] + cmd_in + ["-ss", f"{trans['ss']:.2f}", "-i", trans["file"],
           "-filter_complex", tf, "-map", "[v]", "-an", "-frames:v", str(frames)] + enc_args(style) + [out]
    run(cmd); return out


def _dims(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split(",")[:2]; return int(w), int(h)
    except Exception:
        return 0, 0


def _autocrop(src):
    """v3.2: video ke andar pehle se kaali / dhundhli patti (letterbox, shorts ke andar leti video) ho to kaat do.
    Return (crop_filter, w, h) ya ("", w, h)."""
    import subprocess, re as _re
    w, h = _dims(src)
    if not (w and h): return "", w, h
    try:
        d = duration(src) or 4
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-ss", f"{max(0.0, d * 0.4):.2f}", "-i", str(src), "-t", "1.2",
                            "-vf", "cropdetect=24:2:0", "-f", "null", "-"], capture_output=True, text=True, timeout=40,
                           stdin=subprocess.DEVNULL)
        m = _re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", r.stderr or "")
        if not m: return "", w, h
        cw, ch, cx, cy = map(int, m[-1])
        # v3.13 FIX ("chehra/baal pe zoom"): sirf ASLI letterbox/pillarbox (patti poori chaudai ya poori oonchai
        # ki) kaato – pehle dark background wali clip me cropdetect andar ka chhota hissa kaat deta tha -> zoom
        full_side = cw >= w * 0.97 or ch >= h * 0.97
        if full_side and cw * ch < w * h * 0.88 and cw >= w * 0.4 and ch >= h * 0.3:
            return f"crop={cw}:{ch}:{cx}:{cy},", cw, ch
    except Exception:
        pass
    return "", w, h


_SMART = {}


def smart_x(src, w, h, W, H):
    """v3.18 FIX ("frames kat rahi hain"): leti (16:9) clip ko khadi (9:16) karte waqt pehle hamesha BEECH se
    kaat-te the – cheez kinare pe ho to kat jaati thi. Ab 4 frame dekh ke jahan sabse zyada 'cheez' hai (kinare,
    rang, harkat) us taraf ki khidki chuni jaati hai. Return 0..1 (0 = baayan, 0.5 = beech, 1 = daayan)."""
    key = str(src)
    if key in _SMART: return _SMART[key]
    fx = 0.5
    try:
        import subprocess, numpy as np
        d = duration(src) or 4
        sh = 90; sw = max(16, int(round(w / h * sh)))
        frames = []
        for f in (0.15, 0.4, 0.65, 0.9):
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d * f:.2f}", "-i", str(src), "-frames:v", "1",
                                "-vf", f"scale={sw}:{sh},format=gray", "-f", "rawvideo", "-"],
                               capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            if r.stdout and len(r.stdout) >= sw * sh:
                frames.append(np.frombuffer(r.stdout[:sw * sh], np.uint8).reshape(sh, sw).astype(np.float32))
        if frames:
            col = np.zeros(sw, np.float32)
            for fr in frames:
                gx = np.abs(np.diff(fr, axis=1, prepend=fr[:, :1])); gy = np.abs(np.diff(fr, axis=0, prepend=fr[:1]))
                col += (gx + gy).mean(axis=0)
            for a, b in zip(frames, frames[1:]):
                col += 1.5 * np.abs(b - a).mean(axis=0)            # jo hilta hai wahi aksar asli cheez
            win = max(1, int(round(sw * (W / H) / (w / h))))
            if win < sw:
                cs = np.concatenate([[0], np.cumsum(col)])
                sums = cs[win:] - cs[:-win]
                xs = np.arange(len(sums)); mid = (len(sums) - 1) / 2
                prior = 1.0 - 0.25 * ((xs - mid) / max(1, mid)) ** 2   # barabar ho to beech hi
                best = int(np.argmax(sums * prior))
                if sums[best] > sums[int(round(mid))] * 1.12:          # saaf farq ho tabhi beech se hatao
                    fx = best / max(1, len(sums) - 1)
    except Exception as e:
        log(f"   (smart crop skip: {str(e)[:80]})", show=False)
    _SMART[key] = round(float(fx), 3)
    return _SMART[key]


def video_frame_vf(src, W, H, style):
    """v3.2: Clip ka aakar dekh ke layout (user: "kata hua" / "bade frame me chhoti video" dono galat):
       * pehle letterbox ki kaali patti kaato
       * khadi / lagbhag khadi video  -> poori screen
       * leti (16:9) video           -> poori chaudai, halka zoom (sirf ~18% side kate), beech me; peeche usi ka blur
       * chaukor-si video            -> 4:5 frame
    video_fit: auto (default) / 4:5 / poora / bhar."""
    pre, w, h = _autocrop(src)
    fit = style.get("video_fit", "auto")
    if fit in ("4:5",) and style.get("video_fit_purana") != "haan":
        fit = "auto"                                   # purani style.txt ka 4:5 bhi auto (user ko kata hua laga)
    ar = (w / h) if (w and h) else W / H
    same_shape = abs(ar - (W / H)) / (W / H) < 0.25
    # v3.5 FIX (brief 3C: "bade frame me chhoti video / blur card – kabhi nahi, hamesha full screen"):
    # pehle 'auto' me leti video blur background pe beech me chhoti patti banti thi (log: overlay 1080x1350).
    # Ab default = POORI SCREEN bharo. Sirf style.txt me  video_fit = poora  likhne pe purana blur-frame.
    # v3.21 SMART FRAME FIT: Stop brutal 3.16x center-crop on 16:9 videos (chops off rockets/trains/hands).
    # When smart_frame_fit = haan (default), wide landscape clips use clean 1.18x documentary framing over
    # a dark blurred backdrop so the full subject stays visible. Set smart_frame_fit = nahi for old hard crop.
    # v4.13 CINEMATIC FULL-SCREEN SHORTS: fill vertical 9:16 screen with smart_x subject tracking
    # (eliminates tiny 38% horizontal strip + 62% blur bars). Reversible via style.txt: shorts_full_frame = nahi
    if yes(style.get("shorts_full_frame", "haan")) and W < H and fit != "poora":
        fit = "bhar"
    elif yes(style.get("smart_frame_fit", "haan")) and W < H and ar >= 1.35 and fit != "bhar":
        fit = "auto"
    elif fit != "poora":
        fit = "bhar"
    if same_shape or fit == "bhar" or not (w and h) or W > H or ar < 0.8:
        fx_ = smart_x(src, w, h, W, H) if (w and h and ar > (W / H) * 1.25 and H > W) else 0.5
        return pre + (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                      f"crop={W}:{H}:x='(iw-ow)*{fx_:.3f}':y='(ih-oh)/2'")
    if fit == "poora":
        bw = W; bh = int(W / ar) // 2 * 2
    elif ar >= 1.25:                                   # leti video
        bw = W; bh = int(W / ar * 1.22) // 2 * 2       # 22% bada -> kam kaali jagah, sirf thode side kate
    else:
        bw = W; bh = int(W * 5 / 4) // 2 * 2
    bh = min(bh, H)
    y = max(0, int((H - bh) / 2 - H * 0.06))
    # v3.93 BLURRED-CINEMA FULL-SCREEN BACKDROP: fills 9:16 with soft darkened cinema blur (zero black bars!)
    if yes(style.get("blurred_backdrop", "haan")) and W < H and bh < H - 40:
        return (
            pre + f"split[vg_bg][vg_fg];"
            f"[vg_bg]scale={W}:{H}:force_original_aspect_ratio=increase:flags=fast_bilinear,"
            f"crop={W}:{H},gblur=sigma=24,eq=brightness=-0.12:saturation=1.12[vg_b];"
            f"[vg_fg]scale={bw}:{bh}:force_original_aspect_ratio=increase:flags=lanczos,crop={bw}:{bh}[vg_f];"
            f"[vg_b][vg_f]overlay=(W-w)/2:{y}:shortest=1"
        )
    return (pre + f"scale={bw}:{bh}:force_original_aspect_ratio=increase:flags=lanczos,crop={bw}:{bh},"
            f"pad={W}:{H}:(ow-iw)/2:{y}:color=0x0B0F17")


LOOKS = {   # v2.14: saari footage ek jaisa rang (alag jagah ki clips bhi ek film jaisi lagein)
    "film":    "eq=contrast=1.08:saturation=1.14:gamma=0.97,colorbalance=rs=0.03:gs=0.0:bs=-0.03:rh=0.03:bh=-0.04,"
               "vignette=angle=PI/5",
    "teal":    "eq=contrast=1.10:saturation=1.10,colorbalance=rs=-0.04:bs=0.05:rh=0.05:bh=-0.05,vignette=angle=PI/5",
    "doc":     "eq=contrast=1.07:saturation=0.92:brightness=-0.015,vignette=angle=PI/4.5",
    "natural": "eq=contrast=1.04:saturation=1.06",
}


LOOKS["archive"] = ("hue=s=0.12,eq=contrast=1.18:brightness=-0.02:gamma=0.95,noise=alls=10:allf=t,"
                     "vignette=angle=PI/4")                      # v3.1: itihaas – purani B&W film
LOOKS["warm"] = ("eq=contrast=1.06:saturation=1.16:gamma=0.98,colorbalance=rs=0.05:gs=0.01:bs=-0.05:rh=0.04:bh=-0.05,"
                  "vignette=angle=PI/5")                       # v3.16: tyohaar / sanskriti – sunehra garam rang
LOOKS["danger"] = ("eq=contrast=1.12:saturation=1.05,colorbalance=rs=0.18:gs=-0.06:bs=-0.08:rm=0.10:bm=-0.05,"
                    "vignette=angle=PI/3.5")                     # v3.1: khatra – laal tint


def grade_vf(style):
    lk = style.get("color_look", "film")
    return ("," + LOOKS[lk]) if lk in LOOKS else ""


def _photo_3d(item, dur, frames, W, H, style, out, first):
    """v3.10: photo POORI SCREEN pe 3D camera move (depth parallax / pan / pull) – hero engine se.
    Pehle yahan photo blur background ke beech CHHOTE CARD me aati thi (15 Nov Yash video, Review: 'chhota frame').
    style.txt  photo_card = haan  likho to purana card."""
    if not yes(style.get("photo_card", "nahi")) and W < H:
        try:
            import hero
            seed = abs(hash(str(item.get("path")))) % 97
            it = dict(item, show_name=False, entity="", motion=("depth_push", "pan", "pull_out")[seed % 3], seed=seed)
            if hero.render(it, dur, out, W, H, style, FPS):
                return out
        except Exception as e:
            log(f"   (full-screen 3D photo fail, card: {str(e)[:80]})", show=False)
    im = Image.open(item["path"]).convert("RGB")
    bgi = _prep_image(item["path"], W, H, S=1.0).filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.5))
    f = min(W * 0.90 / im.width, H * (0.62 if H > W else 0.80) / im.height)
    fg = im.resize((max(2, int(im.width * f)) // 2 * 2, max(2, int(im.height * f)) // 2 * 2), Image.LANCZOS)
    tb = Path(out).with_suffix(".bg.jpg"); tf = Path(out).with_suffix(".fg.png")
    bgi.save(tb, quality=92); fg.save(tf)
    # v3.1: pehle shot me punch ke baad background ruk jaata tha (atka lagta) – ab punch ke baad bhi dheere push
    zs = f"max(1.0,1.16-0.012*on)+0.05*on/{frames}" if first else "1+0.05*on/" + str(frames)
    zf = "max(1.0,1.22-0.016*on)+0.10*on/" + str(frames) if first else "1+0.12*on/" + str(frames)
    yoff = int(H * 0.05) if H > W else 0
    fc = (f"[0:v]zoompan=z='{zs}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[bg];"
          f"[1:v]format=rgba,zoompan=z='{zf}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:"
          f"s={fg.width}x{fg.height}:fps={FPS}[fg];"
          f"[bg][fg]overlay=(W-w)/2:(H-h)/2-{yoff},setsar=1{grade_vf(style)}[v]")
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", tb, "-loop", "1", "-i", tf, "-filter_complex", fc,
         "-map", "[v]", "-frames:v", str(frames), "-an"] + enc_args(style) + [out])
    return out


def _green_shot(item, dur, frames, W, H, style, out):
    """v2.17c PRO: green screen cheez ka hara hata ke (chroma key) topic wale background pe – poori cheez dikhe
    (chehra/sar na kate), neeche parchhai, background dheere chalta (3D jaisa). Hara na hate to None."""
    import motion
    src = item["path"]
    total = duration(src) or dur
    start = 0 if total <= dur + 0.5 else random.uniform(0, max(0, total - dur - 0.3))
    kc = motion.key_color(src)
    if kc == "0x00FF00":
        kc = "0x00D000"
    fw, fh = int(W * 0.94) // 2 * 2, int(H * (0.62 if H > W else 0.80)) // 2 * 2
    bg = item.get("bg")
    ins = []
    if bg and Path(bg).exists():
        ins += ["-stream_loop", "-1", "-i", str(bg)]
        bgf = (f"[0:v]scale={int(W*1.10)//2*2}:{int(H*1.10)//2*2}:force_original_aspect_ratio=increase,"
               f"crop={int(W*1.10)//2*2}:{int(H*1.10)//2*2},crop={W}:{H}:x='(iw-ow)*t/{max(dur,0.5):.2f}':y='(ih-oh)/2',"
               f"boxblur=3:1,eq=brightness=-0.06:saturation=1.05,fps={FPS},setsar=1[bg]")
    else:
        ins += ["-f", "lavfi", "-i", f"color=c=0x141a24:s={W}x{H}:r={FPS}"]
        bgf = f"[0:v]format=yuv420p,vignette=angle=PI/4,setsar=1[bg]"
    # v3.13 FIX (Bug C): green clip shot se chhoti ho to LOOP (pehle overlay shortest=1 -> shot chhota -> atakta)
    lpg = ["-stream_loop", "-1"] if total < start + dur + 0.25 else []
    ins += lpg + ["-ss", f"{start:.2f}", "-t", f"{dur + 0.2:.3f}", "-i", str(src)]
    yo = int(H * (0.60 if H > W else 0.55))
    def chain(despill):
        ds = ",despill=type=green:mix=0.6:expand=0.2" if despill else ""
        return (bgf + ";"
                f"[1:v]fps={FPS},scale={fw}:{fh}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"chromakey={kc}:0.14:0.07{ds},format=yuva420p,split[f1][f2];"
                f"[f2]format=rgba,colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,boxblur=18:2[sh];"
                f"[bg][sh]overlay=(W-w)/2+14:{yo}-h/2+26:shortest=1[b2];"
                f"[b2][f1]overlay=(W-w)/2:{yo}-h/2:shortest=1,setsar=1{grade_vf(style)}[v]")
    for ds in (True, False):
        try:
            run(["ffmpeg", "-y", "-v", "error"] + ins + ["-filter_complex", chain(ds), "-map", "[v]", "-an",
                 "-frames:v", str(frames)] + enc_args(style) + [out])
            break
        except Exception as e:
            if not ds:
                log(f"  green key fail ({str(e)[:120]})", show=False); return None
    # jaancho: hara sach me hata?
    try:
        import io as _io, subprocess as _sp
        from sources import green_frac
        r = _sp.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{dur/2:.2f}", "-i", str(out), "-frames:v", "1",
                     "-vf", "scale=160:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True, timeout=30)
        if r.stdout and green_frac(Image.open(_io.BytesIO(r.stdout))) > 0.05:
            log("  green screen saaf nahi hata – ye shot nahi lagega", show=False); return None
    except Exception:
        pass
    return out


SHOT_SS = {}


def render_shot(item, dur, out, style, idx, effect=None, trans=None):
    W, H = size_for(style)
    if item.get("look") in LOOKS:                       # v3.1: scene ka apna rang (archive / danger)
        style = dict(style, color_look=item["look"])
    # Optional Blender procedural 3D shot. Falls back safely to existing footage flow.
    if item.get("kind") == "blender3d":
        try:
            from cine.blender3d import render_scene
            result = render_scene(out, dur, (W, H), item.get("visual", "cinematic"),
                                 blend_file=item.get("blend_file"))
            if result:
                return result
        except Exception as e:
            log(f"  Blender 3D fallback: {str(e)[:100]}", show=False)
        return None
    if item.get("hero") and item["kind"] == "image":          # v3.1: asli insaan/brand/jagah – 3D motion + naam typography
        try:
            import hero
            r = hero.render(item, dur, out, W, H, style, FPS)
            if r and trans:
                mid = Path(out).with_suffix(".hero.mp4"); shutil.move(str(out), mid)
                try:
                    return _with_transition(["-i", str(mid)], "setsar=1", trans, W, H, max(2, int(round(dur * FPS))), style, out)
                except Exception:
                    shutil.move(str(mid), out); return out
            if r: return r
        except Exception as e:
            log(f"  hero shot fail, normal photo ({str(e)[:100]})", show=False)
    if item.get("green") and item["kind"] == "video":          # v2.17c
        frames_ = max(2, int(round(dur * FPS)))
        r = _green_shot(item, dur, frames_, W, H, style, out)
        if r: return r
        if item.get("bg"):                                    # hara nahi hata -> sirf background (topic wala)
            item = {"kind": "video", "path": item["bg"], "credit": item.get("credit", "")}
        else:
            return None
    frames = max(2, int(round(dur * FPS)))
    fcol = "0x%02X%02X%02X" % COLORS.get(style.get("flash_rang", "orange"), COLORS["orange"])
    post = ""
    if effect == "flash":
        post += f",fade=t=in:st=0:d=0.16:color={fcol}"
    if effect == "shake" or (effect == "punch" and item["kind"] == "video"):
        post += (f",crop={W-48}:{H-48}:x='24+22*sin(n*2.3)*lt(n,10)':y='24+22*cos(n*2.9)*lt(n,10)',"
                 f"scale={W}:{H},setsar=1")
    if item["kind"] == "video":
        src = item["path"]
        total = duration(src)
        start = 0 if total <= dur + 0.5 else random.uniform(0, max(0, total - dur - 0.3))
        if item.get("ss") is not None:                 # v2.8 chehra: awaaz ke saath bilkul sync
            start = max(0.0, float(item["ss"]))
            if total and start >= total - 0.2:          # v3.13: ss clip ke bahar -> loop ke hisaab se andar
                start = start % max(0.5, total)
        SHOT_SS[str(out)] = round(float(start), 3)       # v3.6: EDL ke liye – source ka kaunsa hissa
        vf = video_frame_vf(src, W, H, style)
        if yes(style.get("stabilize", "nahi")):                         # hilti footage sthir
            vf = "deshake," + vf
        if idx == 0 and yes(style.get("punch_shuru", "haan")):          # v3.20: smooth ease-out punch zoom
            vf += (f",scale=w='trunc(iw*(1+0.14*pow(max(0\\,1-t/1.8)\\,3))/2)*2':h=-2:eval=frame,"
                   f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2")
        if item.get("kb") and yes(style.get("slow_zoom", "haan")):     # v3.21: gentle 1.05x camera drift (no over-zoom)
            z = 1.05
            xs = f"(iw-ow)*t/{max(dur, 0.5):.2f}" if idx % 2 == 0 else f"(iw-ow)*(1-t/{max(dur, 0.5):.2f})"
            vf += f",scale={int(W*z)//2*2}:{int(H*z)//2*2},crop={W}:{H}:x='{xs}':y='(ih-oh)/2'"
        vf += f",fps={FPS},setsar=1{grade_vf(style)}{post}"
        # v3.1 FIX (atka frame): clip shot se chhoti ho to LOOP karo – pehle kam frames bante the aur video atak jaati
        # v3.13 (Bug C): 'ss' wali (map/chehra) clip bhi chhoti ho to loop – pehle sirf bina-ss wali loop hoti thi
        lp = ["-stream_loop", "-1"] if (total and total < start + dur + 0.15 and not item.get("face")) else []
        tt = [] if lp else ["-t", f"{dur:.3f}"]
        cmd = ["ffmpeg", "-y", "-v", "error"] + lp + ["-ss", f"{start:.2f}"] + tt + ["-i", src,
               "-vf", vf, "-an", "-frames:v", str(frames)] + enc_args(style) + [out]
        try:
            if trans:
                try:
                    return _with_transition(lp + ["-ss", f"{start:.2f}"] + tt + ["-i", str(src)], vf,
                                            trans, W, H, frames, style, out)
                except Exception as e:
                    log(f"  transition fail, bina transition ({e})", show=False)
            run(cmd); return out
        except Exception as e:
            log(f"  video clip kharab, photo/text use karunga ({e})", show=False)
            return None
    # v3.59 FIX: Polaroid at most ONCE (idx == 4) instead of wrapping every photo; all others render full-screen 9:16!
    if (yes(style.get("documentary_mode", "haan")) and W < H and idx == 4 and not item.get("hero")
            and not item.get("fullbleed")):
        try:
            from PIL import Image as _PIm
            with _PIm.open(item["path"]) as _im0:
                _pw0, _ph0 = _im0.size
            if _pw0 > _ph0 * 1.18:
                from cine import doc_cards as _dc, bible as _bib
                _pal = _bib.build([], [], style)["palette"]
                _ang = -2.8 if (idx % 2 == 0) else 2.5
                _cap = str(item.get("label") or item.get("entity") or "")
                _dc.render_polaroid_archival(item["path"], _cap, dur, out, W, H, style, _pal, angle=_ang, fps=FPS)
                return out
        except Exception as _pe:
            log(f"  polaroid archival fallback ({str(_pe)[:80]})", show=False)
    # v3.13: photo_poora me 'punch' wala photo bhi hero engine se (poori photo badi; pehle chhota card banta tha)
    if yes(style.get("photo_3d", "haan")) and (effect != "punch" or yes(style.get("photo_poora", "haan"))):
        try:
            if not trans:
                return _photo_3d(item, dur, frames, W, H, style, out, idx == 0)
            mid = Path(out).with_suffix(".3d.mp4")
            _photo_3d(item, dur, frames, W, H, style, mid, idx == 0)
            try:
                return _with_transition(["-i", str(mid)], "setsar=1", trans, W, H, frames, style, out)
            except Exception:
                shutil.copy(mid, out); return out
        except Exception as e:
            log(f"  3D photo nahi bana, normal zoom ({str(e)[:100]})", show=False)
    try:
        im = _prep_image(item["path"], W, H)
    except Exception:
        return None
    tmp = Path(out).with_suffix(".jpg"); im.save(tmp, quality=93)
    cx = "iw/2-(iw/zoom/2)"; cy = "ih/2-(ih/zoom/2)"
    # v3.13 FIX ("chehra bahut zoom / poori photo nahi"): photo pe zoom 16% -> 6%, punch 1.32 -> 1.15
    zz = 0.06 if yes(style.get("photo_poora", "haan")) else 0.16
    if effect == "punch":
        z = f"if(lt(on,6),1.15-0.022*on,1.02+0.04*(on-6)/{frames})"; x = cx; y = cy
    elif yes(style.get("zoom")):
        mode = idx % 3
        if mode == 0:   z = f"1+{zz}*on/{frames}"; x = cx; y = cy
        elif mode == 1: z = f"{1+zz}-{zz}*on/{frames}"; x = cx; y = cy
        else:           z = f"{1+zz*0.6:.3f}"; x = f"(iw-iw/zoom)*on/{frames}"; y = cy
    else:
        z = "1"; x = cx; y = cy
    if idx == 0 and yes(style.get("punch_shuru", "haan")) and effect != "punch":
        z = f"max(1.0,1.10-0.008*on)+({z})-1"
    vf = f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},setsar=1{grade_vf(style)}{post}"
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", tmp, "-vf", vf,
           "-frames:v", str(frames), "-an"] + enc_args(style) + [out]
    try:
        if trans:
            try:
                return _with_transition(["-loop", "1", "-i", str(tmp)], vf, trans, W, H, frames, style, out)
            except Exception as e:
                log(f"  transition fail, bina transition ({e})", show=False)
        run(cmd); return out
    except Exception as e:
        log(f"  photo render fail ({e})", show=False); return None


# ------------------------------------------------------------------ captions
def ass_color(rgb):
    r, g, b = rgb
    return f"&H00{b:02X}{g:02X}{r:02X}"


def ass_time(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(sents, path, style, total, events=(), hook=None, cards=(), endscreen=False, extra=()):
    W, H = size_for(style)
    size = int(num(style, "caption_size", 60, 200) * (W / 1080 if W < H else 0.8))
    hi = COLORS.get(style.get("caption_rang", "peela"), COLORS["peela"])
    pos = {"upar": 0.30, "beech": 0.76, "neeche": 0.79}.get(style.get("caption_jagah", "beech"), 0.76)  # v2.14 safe zone
    if W > H: pos = {"upar": 0.2, "beech": 0.7, "neeche": 0.82}.get(style.get("caption_jagah", "beech"), 0.7)
    n = int(num(style, "caption_shabd", 1, 4))
    sp1, sp2 = (0, 0) if style.get("caption_lipi", "hinglish") == "hindi" else (1, 2)   # Hindi: spacing 0
    # v3.1 VIRAL TYPOGRAPHY: Poppins ExtraBold (hinglish) / Mukta ExtraBold (Hindi – matra/sanyukt akshar sahi,
    # libass+HarfBuzz shaping), mota kaala outline + naram shadow, bolta shabd rang + halka pop
    cf = style.get("caption_style") or style.get("caption_font", "reference")
    hindi = style.get("caption_lipi", "hinglish") == "hindi"
    REF = cf == "reference"
    if REF:
        # v3.1 REFERENCE (Emergency reel jaisa): Title Case Hinglish, phrase dheere-dheere khulta hai (jo bola wahi
        # dikhe), Poppins SemiBold + zaroori shabd ExtraBold peela / khatre wala laal, patla outline + naram shadow
        capfont = "Mukta ExtraBold" if hindi else "Poppins SemiBold"
        size = int(num(style, "caption_ref_size", 40, 140) if style.get("caption_ref_size") else 82) * (W / 1080 if W < H else 0.9)
        size = int(size)
        n = max(n, int(num(style, "caption_ref_shabd", 2, 6)) if style.get("caption_ref_shabd") else 4)
        pos = (num(style, "caption_ref_jagah", 0.5, 0.9) if style.get("caption_ref_jagah") else 0.745) if W < H else 0.82
    elif cf == "viral":
        capfont = "Mukta ExtraBold" if hindi else "Poppins ExtraBold"
        size = int(size * (0.95 if hindi else 0.86))
    else:
        capfont = "VT Baloo"
    VIRAL = cf == "viral"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{capfont},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,{"&H78000000" if REF else "&H64000000"},0,0,0,0,100,100,{0 if REF else sp1},0,1,{(max(4, size//20) if REF else max(6,size//8))},{(3 if REF else max(4,size//14))},5,60,60,0,1
Style: Hook,VT Baloo,{int(max(size, 120)*(0.86 if W < H else 0.66))},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,{sp1},0,1,{max(6,size//12)},{max(4,size//16)},5,170,170,0,1
Style: Card,VT Baloo,{int(max(size, 120)*1.15)},&H0000DDFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,{sp2},0,1,{max(7,size//7)},{max(5,size//10)},5,80,80,0,1
Style: Big,VT Baloo,{int(size*1.45)},&H0000DDFF,&H0000DDFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,{max(6,size//8)},{max(6,size//9)},5,40,40,0,1
{fx_styles(W, H)}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    hc = ass_color(hi)
    if style.get("caption_lipi", "hinglish") != "hindi":
        from translit import word as hw
        for s_ in sents:
            for w in s_["words"]:
                w["show"] = hw(w["w"])
    sents = _merge_names(sents) if not hindi else sents     # v3.5: "Carry Minati" -> "CarryMinati"
    if REF and not hindi:                          # Title Case (reference jaisa), CAPS nahi
        for s_ in sents:
            for w in s_["words"]:
                t_ = w.get("show", w["w"])
                w["show"] = t_ if (t_ and any(c.isupper() for c in t_[1:])) else (t_[:1].upper() + t_[1:].lower() if t_ else t_)
    elif yes(style.get("caption_capital", "haan")):
        for s_ in sents:
            for w in s_["words"]:
                w["show"] = w.get("show", w["w"]).upper()
    kc = ass_color(COLORS.get(style.get("key_rang", "laal"), COLORS.get("laal", (255, 60, 40))))
    emph = yes(style.get("key_shabd", "haan"))
    cx = int(W * (0.47 if W < H else 0.5))          # Shorts: daayein taraf YouTube ke buttons – thoda baayein
    import re as _re

    def is_key(ww, s):
        if not emph: return False
        k = (s.get("key") or "").strip()
        w0 = ww["w"].strip("।,.!?\"'")
        if k and (w0 == k or (len(k) > 2 and k in w0) or (len(w0) > 2 and w0 in k.split())):
            return True
        if REF and DANGER.search(w0) and len(w0) > 2: return True
        return bool(_re.search(r"\d", w0))           # number hamesha khaas
    DANGER = _re.compile(r"(खतर|मौत|जहर|ज़हर|फेल|बर्बाद|बैन|गिरफ्तार|हमला|युद्ध|भ्रष्ट|झूठ|धोखा|नुकसान|गलत|मर|"
                         r"fail|ban|death|war|scam|corrupt)", _re.I)
    ycol = ass_color((255, 214, 10)); rcol = ass_color((255, 48, 48))
    if REF and yes(style.get("captions", "haan")):
        # v3.6 FIX (user: "ek line khatam, doosri aati hai to kharab lagta hai"): pehle har line ka caption apne end
        # ke +0.15s tak rehta tha aur agli line usse pehle shuru -> DO caption ek saath / beech me jhapak.
        # Ab poori video ki EK timeline: har tukda agle tukde ke shuru hote hi khatam, kabhi overlap nahi.
        for ev_ in cap_timeline(sents, n, total):
            s, g, wi, st, en, first = ev_
            parts = []
            for k, ww in enumerate(g[:wi + 1]):
                t = ww.get("show", ww["w"]).replace("{", "").replace("}", "")
                pop = "\\alpha&H60&\\t(0,90,\\alpha&H00&)" if k == wi else ""
                if is_key(ww, s):
                    col = rcol if DANGER.search(ww["w"]) else ycol
                    parts.append("{\\fnPoppins ExtraBold\\c" + col + pop + "}" + t + "{\\fn" + capfont + "\\c&H00FFFFFF&}")
                else:
                    parts.append(("{" + pop + "}" if pop else "") + t + ("{\\alpha&H00&}" if pop else ""))
            lines_ = " ".join(parts)
            entry = "\\fscx90\\fscy90\\t(0,90,\\fscx100\\fscy100)" if first else ""   # naya tukda: halka zoom-in
            txt = "{\\an5\\pos(" + f"{cx},{int(H*pos)}" + ")\\q0\\blur0.6" + entry + "}" + lines_
            ev.append(f"Dialogue: 0,{ass_time(st)},{ass_time(min(en, total))},Cap,,0,0,0,,{txt}")
    for s in (sents if (not REF and yes(style.get("captions", "haan"))) else []):     # v2.15: captions band -> baaki graphics phir bhi
        words = s["words"]
        groups = [words[i:i + n] for i in range(0, len(words), n)]
        for gi, g in enumerate(groups):
            gend = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else s["end"] + 0.1
            for wi, w in enumerate(g):
                st = w["start"]
                en = g[wi + 1]["start"] if wi + 1 < len(g) else gend
                if en - st < 0.04: continue
                parts = []
                for k, ww in enumerate(g):
                    t = ww.get("show", ww["w"]).replace("{", "").replace("}", "")
                    if is_key(ww, s):                     # v2.14: zaroori shabd – laal aur thoda bada
                        parts.append("{\\c" + kc + "\\fscx118\\fscy118}" + t + "{\\c&H00FFFFFF&\\fscx100\\fscy100}")
                    elif k == wi and VIRAL:              # v3.1: bolta shabd – rang + chhota pop (bounce nahi)
                        parts.append("{\\c" + hc + "\\fscx112\\fscy112\\t(0,110,\\fscx106\\fscy106)}" + t +
                                     "{\\c&H00FFFFFF&\\fscx100\\fscy100}")
                    else:
                        parts.append("{\\c" + hc + "}" + t + "{\\c&H00FFFFFF&}" if k == wi else t)
                pop = ""          # v2.2: bump/uchhalna band – saaf captions
                txt = "{\\an5\\pos(" + f"{cx},{int(H*pos)}" + ")}" + pop + " ".join(parts)
                ev.append(f"Dialogue: 0,{ass_time(st)},{ass_time(min(en, total))},Cap,,0,0,0,,{txt}")
    if hook and yes(style.get("hook_text", "haan")):
        # v2.2: shuru ke ~3 second topic ka bada text (upar), halke fade ke saath
        hk = hook
        if style.get("caption_lipi", "hinglish") != "hindi":
            from translit import word as hw2
            hk = [" ".join(hw2(x) for x in ln.split()) for ln in hk]
        if yes(style.get("caption_capital", "haan")):
            hk = [ln.upper() for ln in hk]
        hk = [ln.replace("{", "").replace("}", "") for ln in hk]
        txt = hk[0] + ("\\N{\\c" + hc + "}" + hk[1] if len(hk) > 1 else "")
        end = min(total, max(2.2, min(3.2, sents[0]["end"] if sents else 3.0)))
        ev.append(f"Dialogue: 2,{ass_time(0.05)},{ass_time(end)},Hook,,0,0,0,,"
                  "{\\an5\\pos(" + f"{W//2},{int(H*(0.17 if W < H else 0.14))}" + ")\\fad(180,250)}" + txt)
    if endscreen and total > 45:                     # v2.14 lambi video: aakhri 12 sec "agli video" box
        es = int(max(size, 110) * 0.55)
        t0 = max(0.0, total - 4.5)
        ev.append(f"Dialogue: 4,{ass_time(t0)},{ass_time(total)},Cap,,0,0,0,,"
                  "{\\an5\\pos(" + f"{int(W*0.78)},{int(H*0.22)}" + f")\\fs{es}\\bord8\\3c&H000000&\\fad(400,0)}}"
                  "{\\c&H0000DDFF&}▶ AGLI VIDEO{\\c&H00FFFFFF&}\\NDEKHNA MAT BHOOLNA")
    for (ct, ctext) in cards:                        # v2.11: lambi video – section ka naam bade akshar me
        ctext = ctext.replace("{", "").replace("}", "")
        if style.get("caption_lipi", "hinglish") != "hindi":
            from translit import word as cw
            ctext = " ".join(cw(x) for x in ctext.split())
        if yes(style.get("caption_capital", "haan")): ctext = ctext.upper()
        # v4.29: Clean documentary chapter bar (lower-upper third, bold accent + smooth scale-in)
        _ch_y = int(H * (0.46 if W < H else 0.78))
        ev.append(f"Dialogue: 3,{ass_time(ct + 0.12)},{ass_time(min(total, ct + 2.6))},Card,,0,0,0,,"
                  "{\\an5\\pos(" + f"{W//2},{_ch_y}" + ")\\fad(220,300)\\fscx88\\fscy88\\t(0,260,\\fscx100\\fscy100)}"
                  "{\\c&H0015CCFA&}▎ {\\c&H00FFFFFF&}" + ctext)
    if events and yes(style.get("bada_number", "nahi")):     # v2.17: beech ka bada "important" text band (sirf 1 caption)
        from motion import number_ass_events
        hwf = None
        if style.get("caption_lipi", "hinglish") != "hindi":
            from translit import word as hwf
        ev += number_ass_events(events, W, H, ass_time, hwf, yes(style.get("caption_capital", "haan")),
                                counter=yes(style.get("number_counter", "haan")))
    ev += list(extra)
    path.write_text(head + "\n".join(ev) + "\n", encoding="utf-8")
    return [g[0]["start"] for s in sents for g in (cap_groups(s["words"], n) if REF else
                                                  [s["words"][i:i + n] for i in range(0, len(s["words"]), n)]) if g]


def cap_timeline(sents, n, total, hold=0.35, min_ev=0.04):
    """v3.6: (sent, group, word_index, start, end, is_first_of_group) – poori video me overlap-free.
    * tukda agle tukde ke shuru tak (lambi chuppi ho to aakhri shabd + hold tak)
    * 0.04s se chhota event chhoda nahi jaata – pichhla event aage badh jaata hai (jhapak nahi)"""
    G = []
    for s in sents:
        for g in cap_groups(s.get("words") or [], n):
            if g: G.append((s, g))
    out = []
    last_end = 0.0
    for gi, (s, g) in enumerate(G):
        nxt = G[gi + 1][1][0]["start"] if gi + 1 < len(G) else None
        g_last = max(g[-1].get("end", g[-1]["start"]), g[-1]["start"] + 0.2)
        gend = min(nxt, g_last + hold) if nxt is not None else min(total, g_last + hold)
        if nxt is not None and nxt - g_last < 0.6: gend = nxt          # chhoti saans – seedha agla tukda
        evs = []
        for wi, w in enumerate(g):
            st = max(w["start"], last_end)
            en = g[wi + 1]["start"] if wi + 1 < len(g) else gend
            en = min(en, gend)
            if en - st < min_ev:
                if evs: evs[-1][1] = max(evs[-1][1], en)
                continue
            evs.append([st, en, wi])
        if not evs and gend - max(g[0]["start"], last_end) >= min_ev:   # poora tukda bahut tez – ek saath dikhao
            evs.append([max(g[0]["start"], last_end), gend, len(g) - 1])
        for k, (st, en, wi) in enumerate(evs):
            out.append((s, g, wi, st, en, k == 0))
        if evs: last_end = evs[-1][1]
    return out


def cap_groups(words, n):
    """v3.5: shabd ke tukde barabar (4+1 nahi, 3+2), aur comma/poorn-viram pe tod. Akela 1 shabd sirf tab jab
    poori line hi 1 shabd ho."""
    import math, re as _re
    if not words: return []
    # pehle viram (, । . ? !) pe phrase banao
    phr, cur = [], []
    for w in words:
        cur.append(w)
        if _re.search(r"[,।.?!]$", (w.get("w") or "").strip()) and len(cur) >= 2:
            phr.append(cur); cur = []
    if cur:
        if len(cur) == 1 and phr: phr[-1].append(cur[0])
        else: phr.append(cur)
    out = []
    for p in phr:
        k = max(1, math.ceil(len(p) / n))
        base, extra = divmod(len(p), k)
        i = 0
        for j in range(k):
            sz = base + (1 if j < extra else 0)
            out.append(p[i:i + sz]); i += sz
    return [g for g in out if g]


def _merge_names(sents):
    try:
        from translit import LABELS
    except Exception:
        return sents
    labs = {l.lower(): l for l in LABELS}
    if not labs: return sents
    out = []
    for s in sents:
        ws = s.get("words") or []; nw = []; i = 0
        while i < len(ws):
            if i + 1 < len(ws):
                a = ws[i].get("show", ws[i]["w"]).strip(); b = ws[i + 1].get("show", ws[i + 1]["w"]).strip()
                tail = _re_tail(b)
                b_clean = b[:len(b) - len(tail)]
                key_sp = (a + " " + b_clean).lower()
                key_nosp = (a + b_clean).lower()
                matched = labs.get(key_sp) or labs.get(key_nosp)
                if matched:
                    # v3.25 FIX: preserve space between distinct capitalized words (NASA Artemis, Hubble Space)
                    if " " not in matched and a and b_clean and a[0].isupper() and b_clean[0].isupper():
                        matched = f"{a} {b_clean}"
                    m = dict(ws[i]); m["show"] = matched + tail; m["w"] = ws[i]["w"] + " " + ws[i + 1]["w"]
                    m["end"] = ws[i + 1].get("end", m.get("end")); nw.append(m); i += 2; continue
            nw.append(ws[i]); i += 1
        out.append(dict(s, words=nw))
    return out


def _re_tail(t):
    import re as _re
    m = _re.search(r"[^\w]+$", t)
    return m.group(0) if m else ""


def fx_styles(W, H):
    try:
        import fx
        return fx.ass_styles(W, H).rstrip("\n")
    except Exception:
        return ""


# ------------------------------------------------------------------ overlays
def overlay_png(style, path, title_lines=None):
    W, H = size_for(style)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top_offset = 120 if W < H else 30
    if yes(style.get("title")) and title_lines:
        hb = int(H * 0.13) if W < H else int(H * 0.15)
        for y in range(hb):
            t = y / hb
            d.line([(0, y), (W, y)], fill=(int(110 + 40 * t), int(10 + 6 * t), int(10 + 6 * t), 255))
        d.rectangle((0, hb, W, hb + 5), fill=(255, 212, 0, 255))
        f1 = ImageFont.truetype(str(FONT), int(hb * 0.36))
        ys = [int(hb * 0.08), int(hb * 0.52)]
        for i, ln in enumerate(title_lines[:2]):
            col = (255, 212, 0) if i == 0 else (255, 255, 255)
            w = d.textlength(ln, font=f1)
            d.text(((W - w) / 2, ys[i]), ln, font=f1, fill=col, stroke_width=5, stroke_fill=(0, 0, 0))
        top_offset = hb + 25
    if yes(style.get("logo")):
        lp = ASSETS / "logo" / "logo.png"
        if lp.exists():
            lg = Image.open(lp).convert("RGBA")
            s = int(num(style, "logo_size", 40, 400))
            lg.thumbnail((s, s), Image.LANCZOS)
            pos = style.get("logo_jagah", "upar_left")
            m = 30
            if pos == "upar_right": xy = (W - lg.width - m - (90 if W < H else 0), top_offset)
            elif pos == "neeche_left": xy = (m, H - lg.height - (430 if W < H else 60))
            else: xy = (m, top_offset)
            im.alpha_composite(lg, xy)
    im.save(path)


# ------------------------------------------------------------------ audio mix
def movavg(x, k):
    """Fast centred moving average (cumsum), same length as x."""
    k = max(1, int(k))
    c = np.cumsum(np.concatenate([np.zeros(k // 2 + 1), x, np.zeros(k)]))
    out = (c[k:k + len(x)] - c[:len(x)]) / k
    return out.astype(np.float32)


SFX_LEN = {"whoosh": (0.15, 1.6), "flash": (0.1, 1.5), "intro": (0.4, 4.0), "ding": (0.2, 2.5),
           "boom": (0.4, 3.5), "pop": (0.03, 0.6), "riser": (0.8, 2.6), "wrong": (0.3, 1.5), "click": (0.03, 0.5),
           "glitch": (0.2, 1.4), "cash": (0.3, 1.2), "typing": (0.3, 1.5), "gears": (0.5, 2.0), "censor": (0.3, 1.0),
           "shimmer": (0.4, 1.6)}


TR_N = {"n": 0}
_CLEAN = {}


def sound_clean(path, x):
    """v2.18: awaaz me 'jar-jar' (kharkharahat / chatak) to nahi? True = saaf."""
    key = str(path)
    if key in _CLEAN: return _CLEAN[key]
    ok = True
    try:
        if len(x) < SR * 0.15 or np.max(np.abs(x)) < 0.02:
            ok = False
        else:
            hop = int(0.005 * SR); n = len(x) // hop
            env = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
            loc = np.convolve(env, np.ones(25) / 25, mode="same") + 1e-9
            spikes = int(((env / loc) > 2.6).sum())                         # chatak-chatak
            win = 1024; m = (len(x) - win) // 512
            if m > 4:
                idx = np.arange(win)[None, :] + 512 * np.arange(m)[:, None]
                sp = np.abs(np.fft.rfft(x[idx] * np.hanning(win), axis=1)) ** 2 + 1e-12
                flat = np.exp(np.mean(np.log(sp), axis=1)) / np.mean(sp, axis=1)
                hi = sp[:, int(sp.shape[1] * 0.35):].sum(1) / sp.sum(1)
                harsh = float(np.median(flat)) > 0.42 and float(np.median(hi)) > 0.30   # sirf shor (jar-jar)
            else:
                harsh = False
            ok = spikes <= max(6, len(x) / SR * 5) and not harsh
    except Exception:
        ok = True
    _CLEAN[key] = ok
    if not ok: log(f"   transition awaaz kharab (jar-jar) – whoosh lagaya: {Path(key).name}", show=False)
    return ok


def _clean(x, cat):
    """v2.17d: whoosh/shutter saaf – bahut neeche ki gungunahat aur upar ki 'jar-jar' chhanti kaat do."""
    if cat not in ("whoosh", "flash", "riser"): return x
    try:
        a = 0.97                                  # high-pass ~200 Hz
        hp = np.empty_like(x); prev_x = 0.0; prev_y = 0.0
        for i in range(len(x)):
            prev_y = a * (prev_y + x[i] - prev_x); prev_x = x[i]; hp[i] = prev_y
        k = 4                                     # low-pass (chhanti kam)
        lp = np.convolve(hp, np.ones(k) / k, mode="same").astype(np.float32)
        return lp / (np.max(np.abs(lp)) + 1e-9) * 0.9
    except Exception:
        return x


SFX_OPTS = {"reel": False}      # v3.1: style.txt  reel_sfx = haan  -> reels se kaate sound bhi chalenge


def _sfx_allowed(p):
    """v3.1 FIX: 'reel..' / 'auto_..' sound doosre logon ki reels se kaate gaye the – unme insaan ki awaaz /
    music ke tukde the (video ke beech 'kisi aur video jaisi' chhoti awaaz). Default: inhe mat lagao."""
    n = p.name.lower()
    if n.startswith(("reel", "auto_")) and not SFX_OPTS["reel"]:
        return False
    return True


BROKEN_SFX = set()


def sfx_broken(x):
    """v3.5 FIX ('bat-bat'): aapke mere_sounds ki files me sirf pehle ~5-10 ms me awaaz thi, baaki bilkul 0 (file
    kharab copy hui / OneDrive placeholder). Aisi 'ding' / 'whoosh' asal me ek chhota CLICK bajati thi = bat.
    Return: wajah (str) ya '' (theek)."""
    x = np.asarray(x, dtype=np.float32)
    if len(x) < int(0.02 * SR): return "bahut chhoti"
    a = np.abs(x); pk = float(a.max())
    if pk < 1e-3: return "bilkul chup (silent)"
    act = np.nonzero(a > pk * 0.01)[0]                 # -40 dB tak ki awaaz
    span = (act[-1] - act[0] + 1) / SR if len(act) else 0
    zero_frac = float((a < 1e-6).mean())
    if span < 0.03 and zero_frac > 0.6:
        return f"sirf {span*1000:.0f} ms awaaz, baaki {zero_frac*100:.0f}% bilkul khaali – Pixabay se dobara download karo"
    return ""


def _quarantine(p, why):
    """v3.16 (log 16 Nov: har video me wahi 10 kharab files dobara jaanchi + 10 warning): kharab file ko
    mere_sounds\\_kharab_files\\ me khiskao (delete NAHI) – agli video me jhanjhat nahi. Asli sound Pixabay /
    Mixkit se daalo (PADHO_SOUNDS_HINDI.txt)."""
    try:
        from common import TOOL
        root = TOOL / "mere_sounds"
        if root not in p.parents: return
        q = root / "_kharab_files"; q.mkdir(exist_ok=True)
        dst = q / f"{p.parent.name}__{p.name}"
        if not dst.exists():
            p.replace(dst)
            with open(q / "KYUN_YAHAN.txt", "a", encoding="utf-8") as f:
                f.write(f"{p.parent.name}\\{p.name}: {why}\n")
    except Exception:
        pass


USER_ONLY = {"whoosh"}            # v3.5: transition whoosh sirf mere_sounds\whoosh (aapki Pixabay files) se
LOUD_NORM = {"whoosh", "flash"}   # v3.5: in sounds ka level loudness se (peak se nahi)
SFX_REF = 0.18                    # voice ka RMS (mix_audio isi pe voice set karta hai)


def loud_level(x, target=SFX_REF):
    """v3.5 FIX (transition ki awaaz sunai nahi deti thi): whoosh files ka peak -2 dB par loudness (RMS) -29...-38 dB
    hota hai – peak se normalize karne pe ye awaaz ke neeche 20+ dB dab jaati thi. Ab sabse tez 120 ms hissa
    voice ke RMS ke barabar, phir peak 0.98 tak soft-limit (koi clipping nahi)."""
    x = np.asarray(x, dtype=np.float32)
    if len(x) < 64: return x
    w = max(32, int(0.12 * SR))
    st = np.sqrt(movavg(x ** 2, w) + 1e-12)
    loud = float(np.max(st))
    if loud < 1e-5: return x
    y = x * (target / loud)
    return limit(y, 0.98, attack_ms=1.0, release_ms=40)


def limit(x, ceiling=0.89, attack_ms=3.0, release_ms=80.0):
    """v3.5 FIX ('jhar-jhar' / 'bat-bat'): pehle mix pe tanh soft-clip tha – awaaz ki har peak pe distortion.
    Ab asli look-ahead limiter: gain dheere ghat-badhta hai, waveform ka aakar nahi bigadta."""
    x = np.asarray(x, dtype=np.float32)
    if len(x) == 0: return x
    a = np.abs(x)
    if float(a.max()) <= ceiling: return x
    la = max(1, int(attack_ms / 1000 * SR))
    # look-ahead peak: har sample pe agle `la` samples ka max
    from numpy.lib.stride_tricks import sliding_window_view
    pad = np.concatenate([a, np.zeros(la, np.float32)])
    pk = sliding_window_view(pad, la + 1).max(axis=1)[:len(a)]
    need = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9)).astype(np.float32)
    # release: gain dheere wapas 1 pe (one-pole), attack turant (look-ahead se pehle hi neeche)
    rel = float(np.exp(-1.0 / max(1.0, release_ms / 1000 * SR)))
    g = _release_smooth(need, rel)
    sm = max(1, la // 2)
    g = np.minimum(g, movavg(g, sm)) if sm > 1 else g
    y = x * g
    return np.clip(y, -ceiling, ceiling).astype(np.float32)          # bacha-khucha (bahut kam) – safety


def _release_smooth(need, rel):
    """g[i] = min(need[i], rel*g[i-1] + (1-rel)) – block-wise vectorized (laptop pe tez)."""
    out = np.empty_like(need); g = 1.0
    B = 2048
    for b0 in range(0, len(need), B):
        blk = need[b0:b0 + B]
        if blk.min() >= 0.9999 and g >= 0.9999:
            out[b0:b0 + B] = 1.0; g = 1.0; continue
        for i in range(len(blk)):
            g = rel * g + (1.0 - rel)
            if blk[i] < g: g = blk[i]
            out[b0 + i] = g
    return out


def audio_qa(x):
    """v3.5 AUDIO QA (local, sach): peak, clipping samples, click/chatak (achanak sample jump), loudness andaza."""
    x = np.asarray(x, dtype=np.float32)
    rep = {"peak_db": None, "clipped": 0, "clicks": 0, "rms_db": None}
    if len(x) == 0: return rep
    pk = float(np.max(np.abs(x))) + 1e-12
    rep["peak_db"] = round(float(20 * np.log10(pk)), 2)          # v3.10: float32 JSON me crash karta tha
    rep["clipped"] = int((np.abs(x) >= 0.999).sum())
    nz = x[np.abs(x) > 1e-3]
    rep["rms_db"] = round(float(20 * np.log10(np.sqrt(np.mean(nz ** 2)) + 1e-12)), 2) if len(nz) else None
    d2 = np.abs(np.diff(x, 2)) if len(x) > 3 else np.zeros(1)
    loc = movavg(d2, 441) + 1e-4
    rep["clicks"] = int(((d2 > 0.25) & (d2 > loc * 12)).sum())
    rep["note"] = "click detection simple hai (2nd-derivative spikes) – kaan se sunna ab bhi zaroori"
    return rep


def _load_sfx(p, cat, hi):
    lo_, hi_ = SFX_LEN.get(cat, (0.05, 5))
    try:
        x = load_wav(p)
    except Exception:
        return None
    if len(x) == 0: return None
    bad = sfx_broken(x)
    if bad:
        BROKEN_SFX.add(f"{cat}/{p.name}")
        log(f"   ⚠️ sound file kharab: {p.parent.name}\\{p.name} – {bad}", show=False)
        _quarantine(p, bad)
        return None
    if len(x) / SR > hi:              # long file: keep only the loudest part
        k = int(hi * SR); e = movavg(np.abs(x), int(0.05 * SR)); c = int(np.argmax(e))
        a = max(0, min(len(x) - k, c - k // 3)); x = x[a:a + k].copy()
        f = int(0.03 * SR); x[-f:] *= np.linspace(1, 0, f)
        fi = int(0.004 * SR); x[:fi] *= np.linspace(0, 1, fi)      # v3.5: shuru me bhi fade – 'bat' click nahi
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    if len(x) < SR * 3: x = _clean(x, cat)
    if cat in LOUD_NORM:
        q_ = audio_qa(x)
        if q_["clicks"] > 2 or q_["clipped"] > 20:   # v3.5: chatak / clipping wali file transition pe nahi
            log(f"   (sound {p.name}: chatak/clipping – chhodi)", show=False); return None
        x = loud_level(x)                          # v3.5: peak nahi, ASLI loudness se barabar (whoosh sunai de)
    env = movavg(np.abs(x), int(0.02 * SR)); peak = int(np.argmax(env)) / SR
    return (x, peak, abs(len(x) / SR - (lo_ + hi_) / 2))


def pick_sfx(cat):
    """One sound per category per video. User's mere_sounds/<cat> first, else built-in assets/sfx/<cat>.
    v3.5: agar aapke folder ki saari files kharab hain to agle folder (built-in) pe jao – chup nahi, click nahi."""
    from common import TOOL
    exts = (".wav", ".mp3", ".m4a", ".ogg", ".aac", ".flac")
    # v3.16: aapki files kharab/khaali hon to cinematic-skill (MIT, github.com/Moh4696/cinematic-skill) ka
    # trailer-style pack (assets\sfx_cinematic – noise + partials se bana, koi licence jhanjhat nahi)
    dirs = [TOOL / "mere_sounds" / cat, ASSETS / "sfx_cinematic" / cat, ASSETS / "sfx" / cat]
    if cat in USER_ONLY: dirs = dirs[:2]               # v3.5: whoosh – aapki files, warna cinematic pack (purana synth nahi)
    groups = [[p for p in d.iterdir() if p.suffix.lower() in exts and _sfx_allowed(p)] for d in dirs if d.exists()]
    if cat not in USER_ONLY and (ASSETS / "sfx" / f"{cat}.wav").exists():
        groups.append([ASSETS / "sfx" / f"{cat}.wav"])  # purana v1 built-in
    lo, hi = SFX_LEN.get(cat, (0.05, 5))
    good = []
    for files in groups:
        good = [g_ for g_ in (_load_sfx(p, cat, hi) for p in files) if g_ is not None]
        if good: break
    if not good:
        return None
    good.sort(key=lambda t: t[2])
    x, peak, _ = random.choice(good[: max(1, len(good) // 2 + 1)])
    return x, peak


def pick_sfx_pool(cat, limit=5):
    """v3.86: Return up to `limit` clean distinct sounds so transitions/whooshes rotate instead of repeating 1 file."""
    from common import TOOL
    exts = (".wav", ".mp3", ".m4a", ".ogg", ".aac", ".flac")
    dirs = [TOOL / "mere_sounds" / cat, ASSETS / "sfx_cinematic" / cat, ASSETS / "sfx" / cat]
    if cat in USER_ONLY: dirs = dirs[:2]
    groups = [[p for p in d.iterdir() if p.suffix.lower() in exts and _sfx_allowed(p)] for d in dirs if d.exists()]
    if cat not in USER_ONLY and (ASSETS / "sfx" / f"{cat}.wav").exists():
        groups.append([ASSETS / "sfx" / f"{cat}.wav"])
    lo, hi = SFX_LEN.get(cat, (0.05, 5))
    good = []
    for files in groups:
        good = [g_ for g_ in (_load_sfx(p, cat, hi) for p in files) if g_ is not None]
        if good: break
    if not good:
        return []
    good.sort(key=lambda t: t[2])
    pool = [(x, pk) for x, pk, _ in good[:max(1, min(limit, len(good)))]]
    random.shuffle(pool)
    return pool


_file_snd = {}


def file_sound(path, ss=0.0, maxlen=12.0):
    """Audio of a transition / subscribe video (or None)."""
    key = (str(path), round(ss, 2))
    if key not in _file_snd:
        try:
            x = load_wav(path)[int(ss * SR):int((ss + maxlen) * SR)]
            _file_snd[key] = x / (np.max(np.abs(x)) + 1e-9) * 0.9 if len(x) and np.max(np.abs(x)) > 0.01 else None
        except Exception:
            _file_snd[key] = None
    return _file_snd[key]


def pick_music(style):
    """v2.14: music pehle hi chuno (beat pe cut ke liye)."""
    mfiles = [p for p in (ASSETS.parent / "music").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
    return random.choice(mfiles) if mfiles else ASSETS / "music" / "default_bed.wav"


def music_beats(path, total):
    """Music ki thaap (beat/onset) ke time – simple spectral flux. Music chhota ho to repeat."""
    try:
        x = load_wav(path)
        if len(x) < SR: return []
        hop, win = 512, 1024
        nfr = (len(x) - win) // hop
        if nfr < 10: return []
        idx = np.arange(win)[None, :] + hop * np.arange(nfr)[:, None]
        spec = np.abs(np.fft.rfft(x[idx] * np.hanning(win), axis=1))
        flux = np.maximum(0, np.diff(np.log1p(spec), axis=0)).sum(axis=1)
        flux = (flux - flux.mean()) / (flux.std() + 1e-9)
        peaks = [i for i in range(1, len(flux) - 1) if flux[i] > 1.0 and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
        t = [(i + 1) * hop / SR for i in peaks]
        dur = len(x) / SR; out = []
        k = 0
        while k * dur < total + 1 and k < 50:
            out += [b + k * dur for b in t]; k += 1
        return sorted(out)
    except Exception:
        return []


MIX_QA = {}


def _fade_in(x, ms=4):
    x = np.array(x, dtype=np.float32, copy=True); k = min(len(x), int(SR * ms / 1000))
    if k > 1: x[:k] *= np.linspace(0, 1, k, dtype=np.float32)
    return x


def _loop_xfade(x, length, xf_s=0.08):
    """Music ko lambai tak repeat karo – har jod pe chhota crossfade (pehle seedha tile = click)."""
    x = np.asarray(x, dtype=np.float32)
    if len(x) >= length: return x[:length].copy()
    xf = min(int(xf_s * SR), len(x) // 4)
    if xf < 8: return np.tile(x, int(np.ceil(length / len(x))) + 1)[:length]
    out = np.zeros(length + len(x), np.float32); pos = 0
    up = np.linspace(0, 1, xf, dtype=np.float32)
    while pos < length:
        seg = x.copy()
        if pos > 0: seg[:xf] *= up
        seg[-xf:] *= up[::-1]
        out[pos:pos + len(seg)] += seg[:len(out) - pos]
        pos += len(x) - xf
    return out[:length]


def loudness_to(x, target=-14.0):
    """Integrated loudness (EBU R128) ffmpeg se naapo, phir seedha gain (koi dynamic pumping nahi)."""
    import subprocess, tempfile, os, re as _re
    try:
        fd, tmp = tempfile.mkstemp(suffix=".wav"); os.close(fd)
        save_wav(tmp, np.clip(x, -1, 1))
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", tmp, "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        os.remove(tmp)
        m = _re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr or "")
        if not m: return x
        cur = float(m[-1])
        if cur < -70: return x
        gain_db = max(-12.0, min(12.0, target - cur))
        return (x * float(10 ** (gain_db / 20))).astype(np.float32)
    except Exception as e:
        log(f"   (loudness naap nahi paya: {e})", show=False)
        return x


def mix_audio(voice_wav, sents, effects, cap_times, style, out_wav, total, extra=(), sections_t=()):
    v = load_wav(voice_wav)
    n = int((total + 0.5) * SR)
    v = np.pad(v, (0, max(0, n - len(v))))[:n]
    rms = np.sqrt(np.mean(v[np.abs(v) > 0.01] ** 2)) if np.any(np.abs(v) > 0.01) else 0.1
    v = v * (0.18 / (rms + 1e-9))
    mix = v.copy()
    SFX_OPTS["reel"] = yes(style.get("reel_sfx", "nahi"))
    # v3.1: voice envelope (sfx + music dono ke ducking ke liye) – smooth attack/release
    _e = np.sqrt(movavg(v ** 2, 1024))
    _sp = movavg((_e > 0.02).astype(np.float32), int(0.25 * SR))
    speaking = np.clip(_sp * 1.5, 0, 1)
    sfx_bus = np.zeros(n, dtype=np.float32)
    tr_bus = np.zeros(n, dtype=np.float32)            # v3.5: transition whoosh ka alag bus (kam dabe – sunai de)
    main_mix = mix
    TRQ = {"n": 0, "last": -99.0, "skip": 0}
    mix = sfx_bus                       # neeche ke saare put()/put_raw() ab sfx bus me jaate hain

    if yes(style.get("sfx")):
        g = num(style, "sfx_awaaz", 0, 100) / 100
        bank = {}

        _rot = {}
        def get(cat):
            # v3.86: rotate across distinct sounds for whoosh/boom/pop/click so same sound never repeats back-to-back
            if cat in ("whoosh", "boom", "pop", "click", "flash"):
                if cat not in bank:
                    bank[cat] = pick_sfx_pool(cat, limit=5)
                    _rot[cat] = 0
                pool = bank[cat]
                if not pool: return None
                snd = pool[_rot[cat] % len(pool)]
                _rot[cat] += 1
                return snd
            if cat not in bank:
                bank[cat] = pick_sfx(cat)
            return bank[cat]

        def put(cat, t_peak, gain):
            snd = get(cat)
            if snd is None: return
            x, peak = snd
            x = x * gain * g
            i = int((t_peak - peak) * SR)
            if i < 0: x = _fade_in(x[-i:]); i = 0        # v3.5: kata hua shuru = click – fade
            j = min(n, i + len(x))
            if j > i: mix[i:j] += x[: j - i]

        def put_tr(t_peak, db, cat="whoosh"):
            """v3.5: transition whoosh – aapki Pixabay file, loudness se level, alag bus (sirf halka duck)."""
            snd = get(cat)
            if snd is None: return False
            x, peak = snd
            x = x * float(10 ** (db / 20))
            i = int((t_peak - peak) * SR)
            if i < 0: x = _fade_in(x[-i:]); i = 0
            j = min(n, i + len(x))
            if j > i: tr_bus[i:j] += x[: j - i]
            return True
        def put_raw(x, t, gain):
            x = x * gain * g; i = int(t * SR)
            if i < 0: x = x[-i:]; i = 0
            j = min(n, i + len(x))
            if j > i: mix[i:j] += x[: j - i]

        tg_ = num(style, "transition_awaaz", 0, 200) / 100          # v2.14: alag-alag volume
        ig_ = num(style, "intro_awaaz", 0, 200) / 100
        # v3.86 FIX: Riser plays ONLY ONCE (at opening hook) — never repeats 2-3 times in one Short!
        _sfx_last = -99.0
        _cat_last = {}
        _cat_cnt = {}
        _CAT_CD = {"riser": 25.0, "boom": 8.0, "ding": 8.0, "whoosh": 2.5, "paper": 3.5, "click": 3.0, "pop": 3.0}
        _CAT_MAX = {"riser": 1, "ding": 2}
        if yes(style.get("intro_sound", "haan")):
            # v3.45 PRO OPENING HOOK RISER: smooth cinematic riser under opening hook swelling into hook peak hit!
            _hook_end = float(sents[0].get("end", 1.8)) if sents else 1.8
            _hook_peak = min(max(1.15, _hook_end - 0.10), 2.35)
            if get("riser"):
                put("riser", _hook_peak, 0.42 * ig_)          # gentle buildup under voice
                _cat_cnt["riser"] = 1; _cat_last["riser"] = _hook_peak
                if get("boom"):
                    put("boom", _hook_peak + 0.02, 0.45 * ig_) # subtle impact right at hook reveal
            elif get("intro"):
                put("intro", 0.05 + get("intro")[1], 0.55 * ig_)

        def _sfx_ok(cat_nm, t_at, force=False):
            nonlocal _sfx_last
            # v3.90 FIX: Riser plays ONLY ONCE (opening hook) — even explicit [riser] tags obey _CAT_MAX['riser']=1!
            if cat_nm == "riser" and _cat_cnt.get("riser", 0) >= _CAT_MAX.get("riser", 1):
                return False
            if force:
                _sfx_last = t_at; _cat_last[cat_nm] = t_at; _cat_cnt[cat_nm] = _cat_cnt.get(cat_nm, 0) + 1
                return True
            if abs(t_at - _sfx_last) < 3.5:
                return False
            if abs(t_at - TRQ["last"]) < 1.2:
                return False
            if cat_nm in _CAT_MAX and _cat_cnt.get(cat_nm, 0) >= _CAT_MAX[cat_nm]:
                return False
            if t_at - _cat_last.get(cat_nm, -99.0) < _CAT_CD.get(cat_nm, 2.2):
                return False
            _sfx_last = t_at; _cat_last[cat_nm] = t_at; _cat_cnt[cat_nm] = _cat_cnt.get(cat_nm, 0) + 1
            return True

        for ev in effects:
            t, eff = ev[0], ev[1]
            tr = ev[2] if len(ev) > 2 else None
            if eff == "mark":                                        # explicit script tag [boom]
                if _sfx_ok(str(tr), t, force=True):
                    put(tr, t, 0.95)
                continue
            if eff == "sfx" and tr:                                  # v3.42: motivated SFX with anti-collision guard
                if _sfx_ok(str(tr[0]), t):
                    put(tr[0], t, tr[1] * tg_)
                continue
            if eff == "transition" and tr and yes(style.get("transition_whoosh", "haan")):
                # v3.43: Prefer transition clip own clean embedded audio (from user videos), else synced whoosh fallback!
                new_l = tr.get("gain", 1.0) >= 1.0
                db = num(style, "transition_sound_db", -20, 8) if style.get("transition_sound_db") else -1.0
                used_own = False
                if yes(style.get("transition_file_awaaz", "haan")) and tr.get("file"):
                    x_own = file_sound(tr["file"], tr.get("ss", 0.0), 2.2)
                    if x_own is not None and sound_clean(tr["file"], x_own):
                        x_own = loud_level(x_own) * float(10 ** ((db if new_l else db - 3) / 20))
                        i_tr = int((t - 0.15) * SR)
                        if i_tr < 0: x_own = _fade_in(x_own[-i_tr:]); i_tr = 0
                        j_tr = min(n, i_tr + len(x_own))
                        if j_tr > i_tr: tr_bus[i_tr:j_tr] += x_own[: j_tr - i_tr]
                        TRQ["n"] += 1; TRQ["last"] = t; _sfx_last = max(_sfx_last, t)
                        used_own = True
                if not used_own and put_tr(t + 0.02, db if new_l else db - 3, cat="whoosh"):
                    TRQ["n"] += 1; TRQ["last"] = t; _sfx_last = max(_sfx_last, t)
                continue
            if eff == "transition" and style.get("transition_sound", "nahi") in ("nahi", "band", "no", "off"):
                continue                       # v3.1: default BAND – user ko transition ki awaaz "machine jaisi" lagi
            if eff == "transition" and tr:
                # v2.17: transition video ki apni awaaz (jar-jar) nahi – saaf halka whoosh, awaaz ke neeche
                gn = tr.get("gain", 1.0) * tg_
                # v2.18: transition ki APNI achhi awaaz (pehle jaisi "suuush/tunu") – sirf jab saaf ho
                if yes(style.get("transition_file_awaaz", "nahi")):   # v3.1: purani 'transition_apni_awaaz=haan' ab ignore (usi se ajeeb awaaz aati thi)   # v3.1: default BAND (light leak files me kisi aur video ki awaaz thi)
                    x = file_sound(tr["file"], tr["ss"], 2.0)
                    if x is not None and sound_clean(tr["file"], x):
                        put_raw(x * 0.9, t - 0.12, gn); continue
                mode = style.get("transition_sound", "whoosh")
                cat = "flash" if (mode == "shutter" and get("flash")) else "whoosh"   # "bhat" (shutter) sirf maangne pe
                TR_N["n"] += 1
                put(cat, t, num(style, "transition_sound_taakat", 0, 200) / 100 * gn if style.get("transition_sound_taakat")
                    else 1.0 * gn)
                continue
            if tr == "whoosh": put("whoosh", t, 0.9 * tg_)
            if eff == "flash": put("flash", t + 0.02, 0.9 * tg_)
            if eff == "shake": put("boom", t + 0.02, 0.6)
        for snd in extra:
            if snd[0] == "@file":
                if yes(style.get("subscribe_apni_awaaz", "nahi")):
                    x = file_sound(snd[3], 0, 12)
                    if x is not None: put_raw(x, snd[1], snd[2])
                else:                                   # v3.1: subscribe video ki apni (unknown) awaaz nahi – saaf pop + click
                    put("whoosh", snd[1] + 0.1, 0.35); put("click", snd[1] + 0.9, 0.5)
            else:
                put(snd[0], snd[1], snd[2])
        # v3.45 SCRIPT-AWARE SOUND DIRECTOR: zero random SFX — every sound matches exact line meaning & emotion!
        _RE_TWIST  = re.compile(r"(लेकिन|मगर|पर असली|असली सच|रहस्य|सीक्रेट|चौंक|कहानी यहीं|twist|secret|mystery|shocking|wait|but actually)", re.I)
        _RE_SHOCK  = re.compile(r"(खतरनाक|बैन|मौत|विनाश|तबाह|धोखा|स्कैम|हमला|युद्ध|घोटाला|हिला|डरावना|danger|banned|crash|scam|deadly|destroyed|warning)", re.I)
        _RE_PROOF  = re.compile(r"(रिपोर्ट|रिसर्च|स्टडी|अखबार|सबूत|कोर्ट|डेटा|सर्वे|इतिहास|फाइल|दस्तावेज़|report|study|proof|news|history|archive|record|data)", re.I)
        _RE_TECH   = re.compile(r"(ऐप|फोन|इंटरनेट|क्लिक|गूगल|यूट्यूब|कंप्यूटर|कोड|सिस्टम|स्क्रीन|app|phone|internet|click|google|youtube|ai\b|tech)", re.I)
        _RE_POINT  = re.compile(r"(पहला|पहली|दूसरा|दूसरी|तीसरा|तीसरी|नंबर\s*[0-9०-९]|फैक्ट|fact)", re.I)

        _mid_riser_used = 0
        _mid_boom_used = 0
        for idx_s, s in enumerate(sents):
            if idx_s == 0 or idx_s == len(sents) - 1:
                continue  # Hook handled by Opening Riser; Outro handled by Subscribe!
            t_s = float(s.get("start", 0.0))
            if t_s < 3.5 or t_s > max(4.0, total - 4.0):
                continue
            txt = str(s.get("script") or s.get("text") or "")
            # 1) Suspense / Twist -> gentle mid-video riser (max 1, >=14s after start)
            if _RE_TWIST.search(txt) and t_s >= 14.0 and _mid_riser_used < 1 and get("riser"):
                t_end_s = float(s.get("end", t_s + 2.0))
                if _sfx_ok("riser", t_end_s):
                    put("riser", t_end_s, 0.36); _mid_riser_used += 1
                    continue
            # 2) Shock / Danger / Big Reveal -> crisp boom/hit (max 2, >=8s cooldown)
            if _RE_SHOCK.search(txt) and _mid_boom_used < 2 and get("boom"):
                if _sfx_ok("boom", t_s + 0.06):
                    put("boom", t_s + 0.06, 0.44); _mid_boom_used += 1
                    continue
            # 3) Archival / Proof / Report -> tactile paper flip
            if _RE_PROOF.search(txt) and get("paper"):
                if _sfx_ok("paper", t_s + 0.05):
                    put("paper", t_s + 0.05, 0.40)
                    continue
            # 4) Tech / Digital / UI -> crisp click
            if _RE_TECH.search(txt) and get("click"):
                if _sfx_ok("click", t_s + 0.04):
                    put("click", t_s + 0.04, 0.38)
                    continue
            # 5) Numbered point or big stat -> subtle ding (max 2 total, >=8s cooldown)
            if _RE_POINT.search(txt) or re.search(r"[0-9०-९]{2,}|करोड़|लाख|मिलियन|बिलियन|%", txt):
                if _sfx_ok("ding", t_s + 0.04):
                    put("ding", t_s + 0.04, 0.36)
                    continue
        if yes(style.get("caption_pop_sound", "nahi")) and yes(style.get("captions")):
            for t in cap_times:
                put("pop", t, 0.12)

    # v3.1: SFX awaaz ke neeche dabe (bolte waqt -45%), clipping se pehle soft limit
    sfx_duck = 1.0 - num(style, "sfx_duck", 0, 90) / 100 * speaking if style.get("sfx_duck") else 1.0 - 0.45 * speaking
    tr_duck = 1.0 - (num(style, "transition_duck", 0, 90) if style.get("transition_duck") else 15.0) / 100 * speaking
    mix = main_mix + sfx_bus * sfx_duck + tr_bus * tr_duck
    if TRQ["n"] or TRQ["skip"]:
        log(f"   🔊 transition whoosh: {TRQ['n']} lagi (saaf, aapki whoosh files), {TRQ['skip']} paas-paas the – chhodi")
    elif yes(style.get("transition_whoosh", "haan")) and any(e_[1] == "transition" for e_ in effects):
        log("   🔊 transition whoosh nahi lagi – mere_sounds\\whoosh me saaf Pixabay whoosh file daalo")
    mv = num(style, "music_awaaz", 0, 60) / 100
    if mv > 0:
        mfiles = [p for p in (ASSETS.parent / "music").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
        mp = Path(style["_music"]) if style.get("_music") and Path(style["_music"]).exists() else \
            (random.choice(mfiles) if mfiles else ASSETS / "music" / "default_bed.wav")
        try:
            def track(path, length):
                x = load_wav(path)
                if len(x) == 0: return None
                x = _loop_xfade(x, length)                 # v3.5: music loop jod pe 'chatak' nahi (crossfade)
                return x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.18
            m = None
            cuts = sorted({0.0} | {float(t) for t in sections_t if 0 < t < total - 2})
            if len(cuts) > 1 and len(mfiles) > 1:        # v2.11 lambi video: har section me alag music
                order = random.sample(mfiles, len(mfiles))
                m = np.zeros(n, dtype=np.float32); xf = int(1.5 * SR)
                for k, a in enumerate(cuts):
                    i0 = max(0, int(a * SR) - (xf if k else 0))
                    i1 = int(cuts[k + 1] * SR) + xf if k + 1 < len(cuts) else n
                    i1 = min(n, i1)
                    seg = track(order[k % len(order)], i1 - i0)
                    if seg is None: continue
                    env = np.ones(len(seg), dtype=np.float32)
                    if k: env[:xf] = np.linspace(0, 1, min(xf, len(seg)))
                    if k + 1 < len(cuts): env[-xf:] = np.linspace(1, 0, min(xf, len(seg)))
                    m[i0:i1] += seg * env
                log(f"   music: {len(cuts)} sections, {min(len(cuts), len(mfiles))} alag tracks", show=False)
            if m is None:
                m = track(mp, n)
            if m is not None and len(m) > 0:
                # ducking envelope from voice energy (v3.1: shared smooth envelope)
                gain = mv * (1.0 - 0.55 * speaking) * 1.6
                # v3.47 PRO BGM SILENCE DROP: 0.9s dramatic music dip right before big twist/reveal lines (max 2)
                if yes(style.get("pro_editing", "haan")) and sents:
                    _RE_DROP = re.compile(r"(लेकिन|मगर|पर असली|असली सच|रहस्य|सीक्रेट|चौंक|कहानी यहीं|twist|secret|mystery|shocking)", re.I)
                    _last_drop = -99.0; _drops = 0
                    for _si, _ss in enumerate(sents):
                        if _si == 0 or _si == len(sents) - 1 or _drops >= 2: continue
                        _ts = float(_ss.get("start", 0.0))
                        if _ts < 6.0 or _ts > max(7.0, total - 5.0) or (_ts - _last_drop) < 15.0: continue
                        _stxt = str(_ss.get("script") or _ss.get("text") or "")
                        if _RE_DROP.search(_stxt):
                            _d0 = max(0, int((_ts - 0.15) * SR))
                            _d1 = min(n, int((_ts + 0.80) * SR))
                            _rmp = max(1, int(0.12 * SR))
                            if _d1 - _d0 > 2 * _rmp:
                                gain[_d0:_d0 + _rmp] *= np.linspace(1.0, 0.06, _rmp)
                                gain[_d0 + _rmp:_d1 - _rmp] *= 0.06
                                gain[_d1 - _rmp:_d1] *= np.linspace(0.06, 1.0, _rmp)
                                _last_drop = _ts; _drops += 1
                fade = int(1.0 * SR)
                gain[-fade:] *= np.linspace(1, 0, fade)
                mix += m * gain
        except Exception as e:
            log(f"  music load nahi hua ({e})", show=False)

    # v3.5 FIX: pehle tanh soft-clip (0.8 se upar har peak bigadti thi = jhar-jhar). Ab:
    #   1) poore mix ko loudness target pe (-14 LUFS andaza, ffmpeg ebur128 se naapa)  2) asli limiter -1 dBFS
    mix = np.nan_to_num(mix.astype(np.float32))
    mix = loudness_to(mix, float(style.get("video_loudness", "-14") or -14))
    mix = limit(mix, 0.89)
    qa = audio_qa(mix)
    MIX_QA.clear(); MIX_QA.update(qa, transitions=TRQ["n"])
    log(f"   🔊 audio QA: peak {qa['peak_db']} dB, clipping {qa['clipped']}, chatak {qa['clicks']}", show=False)
    # v3.20 STEREO: centered crisp voice + subtle stereo width on ambient/music bus
    haas = int(0.011 * SR)
    ambient = np.nan_to_num((sfx_bus * sfx_duck + tr_bus * tr_duck).astype(np.float32))
    amb_r = np.concatenate([np.zeros(haas, dtype=np.float32), ambient[:-haas]]) if len(ambient) > haas else ambient
    left = limit(mix, 0.89)
    right = limit(mix + (amb_r - ambient) * 0.35, 0.89)
    stereo = np.stack([left, right], axis=1).astype(np.float32)
    save_wav(out_wav, stereo)


# ------------------------------------------------------------------ final
LAST_FINAL = {}


def final_mux(joined, overlay, ass, audio, out, style, total, work, events=()):
    try:
        return _final_mux(joined, overlay, ass, audio, out, style, total, work, events)
    except Exception as e:
        log(f"   Final me dikkat aayi ({str(e)[:80]}) – bina dust layer dobara bana raha hoon...")
    simple = dict(style); simple["layer"] = "nahi"
    try:
        return _final_mux(joined, overlay, ass, audio, out, simple, total, work, events)
    except Exception as e:
        log(f"   Phir dikkat ({str(e)[:80]}) – simple tareeke se (bina arrow/subscribe) bana raha hoon...")
    keep = [e for e in events if e["kind"] == "number"]      # number text captions me hai, safe
    return _final_mux(joined, overlay, ass, audio, out, simple, total, work, keep)


def _final_mux(joined, overlay, ass, audio, out, style, total, work, events=()):
    W, H = size_for(style)
    if (work / "fonts").exists():
        from common import copy_font
        copy_font(FONT, work / "fonts" / FONT.name)
    import motion
    m_in, m_chain, _ = motion.build(events, style, W, H, FPS, total, work, 4)
    mc, mlast = m_chain("0:v")
    chain = (mc + ";" if mc else "") + f"[{mlast}][1:v]overlay=0:0[v1]"
    last = "v1"
    if yes(style.get("progress_bar")) and W < H:
        chain += (f";[3:v]format=rgba[pb];[{last}][pb]overlay=x='-w+W*t/{total:.3f}':y=0:eval=frame:shortest=1[v2]")
        last = "v2"
    extra_in = []
    if W < H and yes(style.get("loop_ending", "nahi")) and total > 4:
        # v2.14: Short ka aakhri pal pehle frame me ghul jaaye -> video loop jaisi, log dobara dekhte hain
        try:
            fp = work / "loop_first.png"
            run(["ffmpeg", "-y", "-v", "error", "-ss", "0.05", "-i", joined.name, "-frames:v", "1", fp.name], cwd=work)
            li = 4 + m_in.count("-i")
            extra_in = ["-loop", "1", "-framerate", str(FPS), "-t", f"{total+1:.2f}", "-i", fp.name]
            chain += (f";[{li}:v]format=rgba,fade=t=in:st={max(0, total-0.5):.2f}:d=0.45:alpha=1[lp];"
                      f"[{last}][lp]overlay=0:0[vl]")
            last = "vl"
        except Exception as e:
            log(f"   (loop ending skip: {e})", show=False)
    hk = Path(work) / "hook_hf.webm"                  # v3.6: HyperFrames hook title (transparent) – shuru me
    if hk.exists() and hk.stat().st_size > 5000:       # v4.29: Shorts (9:16) + Longs (16:9) dono me hook title
        hi_ = 4 + m_in.count("-i") + extra_in.count("-i")
        extra_in = extra_in + ["-c:v", "libvpx-vp9", "-i", hk.name]
        chain += (f";[{hi_}:v]format=yuva420p,setpts=PTS+0.10/TB[hkv];"
                  f"[{last}][hkv]overlay=0:0:eof_action=pass:format=auto[vhk]")
        last = "vhk"
    # v3.37 EMOTION / MEME GREEN-SCREEN OVERLAYS (placed cleanly below captions)
    try:
        import emotion_fx as _efx
        _em_idx = 4 + m_in.count("-i") + extra_in.count("-i")
        _em_in, _em_ch, _em_last = _efx.build_ffmpeg_chain(work, last, _em_idx, W, H, FPS)
        if _em_in:
            extra_in = extra_in + _em_in
            chain += _em_ch
            last = _em_last
    except Exception:
        pass
    if yes(style.get("pro_editing", "haan")) and (W > H or total >= 95.0):
        # v3.47 PRO LONG-VIDEO PROGRESS BAR: subtle 4px top amber bar (zero screen clutter)
        _tot_s = max(1.0, float(total))
        chain += f";[{last}]drawbox=x=0:y=0:w='iw*t/{_tot_s:.2f}':h=4:color=0xF5B041@0.85:t=fill[vpb]"
        last = "vpb"
    chain += f";[{last}]ass={ass.name}:fontsdir=fonts[v3]"; last = "v3"     # v2.15: hamesha (captions band ho to bhi graphics)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", joined.name, "-i", overlay.name, "-i", audio.name,
           "-f", "lavfi", "-i", f"color=c=0xFFD400:s={W}x10:r={FPS}:d={total+1:.2f}"] + m_in + extra_in + [
           "-filter_complex", chain, "-map", f"[{last}]", "-map", "2:a", "-af", "aresample=48000", "-ar", "48000", "-ac", "2", "-t", f"{total:.3f}",
           "-r", str(FPS)] + enc_args(style, final=True) + ["-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(Path(out).resolve())]
    LAST_FINAL.update(cmd=[str(x) for x in cmd], cwd=str(work), total=total)   # v3.16: Edit Kit (visual badlo)
    run_progress(cmd, total, cwd=work, label="Final video", stall=150)
