"""v3.1 BLENDER CINEMATIC ENGINE (wrapper) – script ki line -> asli procedural 3D shot.

* Blender 5.x / 4.x khud dhoondhta hai (Program Files ke saare version, Steam, portable, BLENDER_PATH).
* Hardware profile se Eevee/Cycles, samples, resolution scale, particles.
* Hamesha EK shot ek baar (8 GB RAM pe Windows na atke), timeout, progress, cache, temp safai.
* Output: bilkul `frames` frames @30fps, WxH, yuv420p (concat me jhatka nahi). Fail -> None (crash nahi).
"""
from __future__ import annotations
import glob, hashlib, json, os, re, shutil, subprocess, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "blender_templates.py"
_LOCK = threading.Lock()            # Blender ek waqt me ek hi (RAM)
STATE = {"timeouts": 0}             # timeout hua to is video me aur Blender nahi (time bachao)
TOOL = HERE.parent.parent
CACHE = TOOL / "temp" / "blender_cache"


def _ver_key(p):
    m = re.search(r"(\d+)\.(\d+)", str(p))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def find_blender():
    c = [os.environ.get("BLENDER_PATH"), shutil.which("blender")]
    if os.name == "nt":
        pats = [r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
                r"C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender*\blender.exe"),
                r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
                os.path.expanduser(r"~\Desktop\blender*\blender.exe"),
                os.path.expanduser(r"~\Downloads\blender*\blender.exe"),
                str(TOOL / "tools" / "blender*" / "blender.exe")]
        found = []
        for p in pats:
            found += glob.glob(p)
        c += sorted(found, key=_ver_key, reverse=True)       # sabse naya version pehle (5.3 > 4.5)
    else:
        c += sorted(glob.glob("/opt/blender*/blender") + glob.glob(str(TOOL / "tools" / "blender*" / "blender")),
                    key=_ver_key, reverse=True)
    for p in c:
        if p and Path(p).is_file():
            return str(Path(p))
    return None


def _profile():
    try:
        import hardware
        return hardware.load_profile()
    except Exception:
        return {"blender_engine": "EEVEE", "blender_samples": 16, "blender_scale": 0.5, "blender_particles": 150}


def render(out, frames, W, H, template, camera=None, palette=None, text="", seed=7, quality="normal",
           log=None, timeout=None, enc=None, image_path=None):
    """Return out path ya None. quality: preview / normal / hero (hero = Cycles agar profile allow kare)."""
    log = log or (lambda *a, **k: None)
    # v3.23 RELEVANCE GATE: Block generic ugly templates (abstract/mystery/history/energy/infographic)
    # so Cloud Flux 2.5D Parallax & Documentary Cards handle those scenes photorealistically!
    ALLOWED_3D = {"space", "planet", "globe", "solar_system", "dna", "molecule", "cell", "technology", "doc_stage"}
    if template not in ALLOWED_3D:
        log(f"   (Blender skip '{template}' -> Cloud AI / Documentary card behtar hai)", show=False)
        return None
    blender = find_blender()
    use_bpy = False
    if not blender:
        use_bpy = bool(os.environ.get("VG_BPY_PYTHON"))          # advanced/test: Python jisme bpy module ho
        if not use_bpy:
            return None
    prof = dict(_profile())
    if os.environ.get("VG_BLENDER_ENGINE"): prof["blender_engine"] = os.environ["VG_BLENDER_ENGINE"].upper()
    if os.environ.get("VG_BLENDER_SCALE"): prof["blender_scale"] = float(os.environ["VG_BLENDER_SCALE"])
    if os.environ.get("VG_BLENDER_SAMPLES"): prof["blender_samples"] = int(os.environ["VG_BLENDER_SAMPLES"])
    # v3.23 CINEMATIC SHARPNESS: 0.75 scale (810x1440) + 24 EEVEE samples instead of blurry 0.50
    sc = min(0.55, float(prof.get("blender_scale", 0.55)))
    if quality == "preview": sc = min(sc, 0.45)
    rw, rh = max(64, int(W * sc) // 2 * 2), max(64, int(H * sc) // 2 * 2)
    engine = "CYCLES" if (quality == "hero" and prof.get("cycles_ok")) else prof.get("blender_engine", "EEVEE")
    job = {"frames": int(frames), "fps": 30, "width": rw, "height": rh, "template": template, "camera": camera,
           "palette": palette or {}, "engine": engine, "samples": min(14, int(prof.get("blender_samples", 14))),
           "particles": int(prof.get("blender_particles", 150)) if quality != "preview" else 60,
           "seed": int(seed), "text": text or "", "motion_blur": sc >= 0.75, "image_path": str(image_path or "")}
    rt = hashlib.md5(RUNTIME.read_bytes()).hexdigest()[:8]          # template code badle to cache bhi naya
    hid = hashlib.md5((json.dumps(job, sort_keys=True) + rt).encode()).hexdigest()[:14]
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{template}_{hid}.mp4"
    out = Path(out)
    if cached.exists() and cached.stat().st_size > 5000:
        shutil.copy(cached, out); log(f"   🧊 Blender cache se: {template}", show=False)
        return _finish(out, frames, W, H, enc)
    tmpd = CACHE / f"job_{hid}"
    shutil.rmtree(tmpd, ignore_errors=True); tmpd.mkdir(parents=True)
    job["out_dir"] = str(tmpd)
    jf = tmpd / "job.json"; jf.write_text(json.dumps(job), encoding="utf-8")
    timeout = timeout or int(os.environ.get("VG_BLENDER_TIMEOUT") or 140)
    t0 = time.time()
    with _LOCK:
        try:
            if blender:
                cmd = [blender, "-b", "--factory-startup", "--python", str(RUNTIME), "--", str(jf)]
            else:
                cmd = [os.environ.get("VG_BPY_PYTHON") or "python", str(RUNTIME), "--", str(jf)]   # bpy module (test/advanced)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            last = 0; tail = []
            for line in p.stdout:
                tail = (tail + [line.rstrip()])[-25:]
                if time.time() - t0 > timeout:
                    p.kill(); STATE["timeouts"] += 1
                    log(f"   Blender timeout ({timeout}s) – {template} chhoda (laptop dheema – baaki lines pe 3D band)")
                    return None
                if "Saved:" in line or "Fra:" in line:
                    n = len(list(tmpd.glob("f_*.jpg")))
                    if n - last >= max(10, frames // 4):
                        last = n; log(f"   🧊 Blender {template}: {n}/{frames} frames", show=False)
            p.wait(timeout=30)
            got = sorted(tmpd.glob("f_*.jpg"))
            if p.returncode != 0 or len(got) < max(2, frames - 2):
                log(f"   Blender {template} fail (rc={p.returncode}, {len(got)}/{frames} frames): "
                    + " | ".join(tail[-4:])[-300:], show=False)
                return None
        except Exception as e:
            log(f"   Blender error: {e}", show=False); return None
    try:
        enc = enc or ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                      "-r", "30", "-video_track_timescale", "15360"]
        first = int(re.search(r"(\d+)", got[0].stem).group(1))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "30", "-start_number", str(first),
                        "-i", str(tmpd / "f_%04d.jpg"),
                        "-vf", f"scale={W}:{H}:flags=lanczos,setsar=1,format=yuv420p", "-frames:v", str(frames),
                        "-an"] + enc + [str(out)], check=True, capture_output=True, stdin=subprocess.DEVNULL)
        shutil.copy(out, cached)
    except Exception as e:
        log(f"   Blender frames -> mp4 fail: {e}", show=False); return None
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)                       # temp frames safai
    log(f"   🧊 Blender 3D: {template} ({engine}, {rw}x{rh}, {time.time()-t0:.0f}s)", show=False)
    return _finish(out, frames, W, H, enc)


def _finish(out, frames, W, H, enc):
    try:
        import shotfix
        ok, _ = shotfix.ensure(out, frames, W, H, enc or ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "17",
                                                          "-pix_fmt", "yuv420p", "-r", "30", "-video_track_timescale", "15360"])
        return str(out) if ok else None
    except Exception:
        return str(out) if Path(out).exists() else None


def clean_cache(max_mb=1500):
    """Purani Blender clips hatao jab cache bada ho jaaye."""
    if not CACHE.exists(): return
    fs = sorted(CACHE.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    tot = sum(p.stat().st_size for p in fs) / 1e6
    while fs and tot > max_mb:
        p = fs.pop(0); tot -= p.stat().st_size / 1e6; p.unlink(missing_ok=True)
