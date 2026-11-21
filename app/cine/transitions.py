"""NAYE TRANSITIONS (pro editor jaisa) – FFmpeg xfade se ASLI do-shot transition.

Purana tareeka: har 2-3 sec pe light-leak / film-burn video upar chipka do (har baar wahi "layer" look).
Naya tareeka:
  * line ke andar  -> seedha CUT (reference reels me 80% cut hi hote hain)
  * baat badle     -> storyboard ka chuna transition: smooth push (whip), zoom-in, blur, circle reveal...
  * ek hi transition lagatar do baar nahi
  * light-leak sirf 1 baar (bade reveal pe) – style.txt: light_leak_max

join() shots ko jodta hai:  cut wale hisse  -> concat (copy, tez)
                            transition      -> xfade (ek hi encode)
Kuch bhi fail -> seedha cut se jod deta hai (video kabhi nahi rukegi).
"""
import re, subprocess
from pathlib import Path

DUR = {"smoothleft": 0.30, "smoothright": 0.30, "smoothup": 0.30, "slideleft": 0.28, "slideup": 0.28,
       "zoomin": 0.32, "hblur": 0.30, "circleopen": 0.45, "fadewhite": 0.30, "fadeblack": 0.40, "radial": 0.40,
       "pixelize": 0.35, "squeezeh": 0.30, "coverleft": 0.30, "dissolve": 0.35, "fade": 0.30}
NICE = {"smoothleft": "whip push", "smoothright": "whip push", "smoothup": "push up", "slideleft": "slide",
        "slideup": "slide up", "zoomin": "zoom-in", "hblur": "blur swipe", "circleopen": "circle reveal",
        "fadewhite": "flash reveal", "fadeblack": "dip", "radial": "clock wipe", "pixelize": "pixel"}
_OK = {}


def available():
    if "set" in _OK: return _OK["set"]
    names = set()
    try:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-h", "filter=xfade"], capture_output=True, text=True, timeout=20,
                           stdin=subprocess.DEVNULL)
        txt = r.stdout + r.stderr
        part = txt.split("transition", 1)[1] if "transition" in txt else ""
        names = set(re.findall(r"^\s+([a-z]+)\s+-?\d*\s", part, re.M)) | set(re.findall(r"^\s+([a-z]+)\s", part, re.M))
    except Exception:
        names = set()
    _OK["set"] = names & set(DUR) if names else set()
    return _OK["set"]


def dur_of(name):
    return DUR.get(name, 0.3)


def usable(name):
    return bool(name) and name in available()


def _probe_frames(p):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                            "stream=nb_read_packets", "-of", "csv=p=0", str(p)], capture_output=True, text=True, timeout=60)
        return int(r.stdout.strip().split(",")[0])
    except Exception:
        return 0


def _concat(files, durs, out, work, run, cut_tail=True):
    lst = Path(work) / f"cc_{Path(out).stem}.txt"
    rows = []
    for f, d in zip(files, durs):
        rows.append(f"file '{Path(f).resolve().as_posix()}'")
        if cut_tail and d: rows.append(f"outpoint {d:.4f}")
    lst.write_text("\n".join(rows) + "\n", encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    return out


def join(files, durs, xf, out, work, run, enc, fps=30):
    """files: shot mp4s, durs: har shot ki asli (timeline) lambai, xf: {shot_index: transition_name}
    (shot_index se pehle wale cut pe). Transition se pehle wale shot me +D extra tail render hona chahiye."""
    work = Path(work)
    xf = {k: v for k, v in (xf or {}).items() if 0 < k < len(files) and usable(v)}
    if not xf:
        return _concat(files, durs, out, work, run)
    # runs: transitions ke beech ke shots
    bounds = [0] + sorted(xf) + [len(files)]
    runs = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        rf = work / f"run_{a:03d}.mp4"
        ds = list(durs[a:b])
        if b in xf: ds[-1] = ds[-1] + dur_of(xf[b])          # aakhri shot ki tail transition ke liye
        _concat(files[a:b], ds, rf, work, run)
        runs.append((a, b, rf, sum(durs[a:b])))
    try:
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for _, _, rf, _ in runs: cmd += ["-i", str(rf)]
        fc = []
        for k in range(len(runs)):
            fc.append(f"[{k}:v]fps={fps},settb=AVTB,format=yuv420p,setsar=1[r{k}]")
        last = "r0"; T = runs[0][3]
        for k in range(1, len(runs)):
            name = xf[runs[k][0]]; D = dur_of(name)
            fc.append(f"[{last}][r{k}]xfade=transition={name}:duration={D:.3f}:offset={T:.3f}[x{k}]")
            last = f"x{k}"; T += runs[k][3]
        cmd += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-an", "-t", f"{sum(durs):.3f}"] + enc + [str(out)]
        run(cmd)
        if Path(out).exists() and Path(out).stat().st_size > 1000:
            return out
    except Exception as e:
        try:
            from common import log
            log(f"   (xfade transitions fail – seedhe cut: {str(e)[:120]})", show=False)
        except Exception:
            pass
    return _concat(files, durs, out, work, run)
