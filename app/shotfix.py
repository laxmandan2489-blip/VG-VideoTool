"""v3.1 SHOT GUARD – har bane hue shot ki jaanch + marammat (video "atakne" wali galti ki jad).

Pehle kya hota tha:
  * stock clip shot se chhoti ho -> ffmpeg kam frames banata -> joined.mp4 awaaz se chhota -> aakhri frame ATAK jaata
    (aur beech ke shots apni line se pehle khisak jaate).
  * Blender 24 fps / recipe / alag size ka shot `concat -c copy` me milta -> jhatka / atka frame.
  * recipe ke frames video khatam hone pe aakhri frame dohraate the -> freeze.

Ab: har shot ka frame count, size, fps check. Kam ho to shot ko LOOP karke poora (freeze nahi),
size/fps galat ho to normalize. Sab kuch log hota hai, chupchaap kuch nahi chhoda jaata.
"""
import json, subprocess
from pathlib import Path

FPS = 30


def probe(path):
    """{'w','h','fps','frames','dur','pix'} ya None."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                            "-show_entries", "stream=width,height,r_frame_rate,nb_read_packets,pix_fmt:format=duration",
                            "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        j = json.loads(r.stdout or "{}")
        st = (j.get("streams") or [{}])[0]
        if not st:
            return None
        num, den = (st.get("r_frame_rate") or "0/1").split("/")
        return {"w": int(st.get("width") or 0), "h": int(st.get("height") or 0),
                "fps": float(num) / max(1.0, float(den)), "frames": int(st.get("nb_read_packets") or 0),
                "dur": float((j.get("format") or {}).get("duration") or 0), "pix": st.get("pix_fmt")}
    except Exception:
        return None


def _run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-400:])


def ensure(path, frames, W, H, enc, log=None):
    """Shot ko bilkul `frames` frames, WxH, 30 fps, yuv420p banao. Return (ok, note)."""
    p = Path(path)
    info = probe(p)
    if not info or info["frames"] < 1:
        return False, "shot khaali / kharab"
    good_geom = info["w"] == W and info["h"] == H and abs(info["fps"] - FPS) < 0.01 and info["pix"] == "yuv420p"
    if good_geom and abs(info["frames"] - frames) <= 1:
        return True, "ok"
    tmp = p.with_name(p.stem + "_fix.mp4")
    vf = (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,format=yuv420p")
    # chhota shot -> LOOP (freeze nahi). stream_loop input pe lagta hai.
    loop = ["-stream_loop", "-1"] if info["frames"] < frames - 1 else []
    _run(["ffmpeg", "-y", "-v", "error"] + loop + ["-i", p, "-vf", vf, "-an", "-frames:v", str(frames)] + enc + [tmp])
    tmp.replace(p)
    note = []
    if info["frames"] < frames - 1:
        note.append(f"chhota tha ({info['frames']}/{frames} frames) – loop karke poora kiya")
    elif info["frames"] > frames + 1:
        note.append(f"lamba tha ({info['frames']}/{frames}) – kaata")
    if not good_geom:
        note.append(f"size/fps theek kiya ({info['w']}x{info['h']}@{info['fps']:.2f})")
    if log:
        log(f"   🛠 shot guard {p.name}: " + "; ".join(note), show=False)
    return True, "; ".join(note)


def frozen_ratio(path, noise=0.002, min_d=0.8):
    """Shot ka kitna hissa bilkul ruka hua hai (0..1)."""
    import re
    info = probe(path)
    if not info or info["dur"] <= 0:
        return 0.0
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(path), "-vf",
                        f"freezedetect=n={noise}:d={min_d}", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    durs = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", r.stderr)]
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", r.stderr)]
    if len(starts) > len(durs):                      # aakhir tak ruka hua
        durs.append(info["dur"] - starts[-1])
    return min(1.0, sum(durs) / info["dur"])
