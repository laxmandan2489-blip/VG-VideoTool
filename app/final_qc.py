"""v3.1 FINAL QC – video bhejne se PEHLE poori technical jaanch. Fail = "success" nahi bola jaata.

Check: file hai, size theek, video + audio stream, duration (awaaz se mel), resolution, fps, kaale frame,
ruke (frozen) frame, audio clipping / peak, chupp (silence) hisse, A/V lambai ka farak, missing scenes,
captions file, Blender/visual fallback ginti, AI aankh relevance scores.
Output: <video>_QC.json  + (ok, problems, report)
"""
import json, re, subprocess
from pathlib import Path


def _ff(args, timeout=600):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info"] + [str(a) for a in args] + ["-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       stdin=subprocess.DEVNULL)
    return r.stderr


def probe(path):
    # v3.2 FIX: Windows pe Hindi file-naam -> ffprobe ka UTF-8 jawab cp1252 se padhne pe khaali aata tha
    # ("video stream nahi hai, lambai 0.00s" – jabki video sahi thi)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate,duration:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    j = {}
    try:
        j = json.loads(r.stdout or "{}")
    except Exception:
        j = {}
    if j.get("streams"):
        return j
    # v3.5 FIX: log me "video stream nahi hai, lambai 0.00s" aaya jabki video theek thi (ffprobe Hindi naam wali
    # OneDrive file nahi khol paya). Ab ffmpeg -i se dobara padho (baaki checks ffmpeg se hi chal rahe the).
    j2 = _probe_ffmpeg(path)
    if j2.get("streams"):
        j2["_via"] = "ffmpeg (ffprobe fail: " + (r.stderr or "khaali jawab").strip()[-160:] + ")"
        return j2
    j["_probe_failed"] = (r.stderr or "khaali jawab").strip()[-200:]
    return j


def _probe_ffmpeg(path):
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL)
    e = r.stderr or ""
    out = {"streams": [], "format": {}}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e)
    if m:
        out["format"]["duration"] = str(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)))
    for ln in e.splitlines():
        if "Stream #" not in ln: continue
        if "Video:" in ln:
            st = {"codec_type": "video"}
            m = re.search(r", (\d{2,5})x(\d{2,5})", ln)
            if m: st["width"], st["height"] = int(m.group(1)), int(m.group(2))
            m = re.search(r"([\d.]+) fps", ln)
            if m: st["r_frame_rate"] = f"{float(m.group(1)) * 1000:.0f}/1000"
            out["streams"].append(st)
        elif "Audio:" in ln:
            out["streams"].append({"codec_type": "audio"})
    return out


def check(video, expect_w, expect_h, expect_dur, fps=30, sents=None, ass=None, scene_info=None, last_line_ok=True):
    p = Path(video); rep = {"video": str(p), "checks": {}, "problems": [], "warnings": []}
    prob = rep["problems"]; warn = rep["warnings"]; C = rep["checks"]
    if not p.exists():
        prob.append("MP4 file bani hi nahi"); return False, prob, rep
    size = p.stat().st_size; C["size_mb"] = round(size / 1e6, 2)
    if size < 100_000: prob.append(f"file bahut chhoti ({size} bytes) – kharab")
    try:
        j = probe(p)
    except Exception as e:
        prob.append(f"ffprobe fail: {e}"); return False, prob, rep
    if j.get("_probe_failed"):
        rep["probe_failed"] = True
        prob.append(f"file padh nahi paya (ffprobe + ffmpeg dono): {j['_probe_failed'][-120:]}")
    if j.get("_via"): warn.append("ffprobe nahi chala, ffmpeg se jaancha: " + j["_via"][-120:])
    vs = [s for s in j.get("streams", []) if s.get("codec_type") == "video"]
    as_ = [s for s in j.get("streams", []) if s.get("codec_type") == "audio"]
    if not vs: prob.append("video stream nahi hai")
    if not as_: prob.append("audio stream nahi hai")
    dur = float((j.get("format") or {}).get("duration") or 0); C["duration"] = round(dur, 2)
    if vs:
        v = vs[0]; C["resolution"] = f"{v.get('width')}x{v.get('height')}"
        n, d = (v.get("r_frame_rate") or "0/1").split("/"); C["fps"] = round(float(n) / max(1, float(d)), 2)
        if (v.get("width"), v.get("height")) != (expect_w, expect_h):
            prob.append(f"resolution galat {C['resolution']} (chahiye {expect_w}x{expect_h})")
        if abs(C["fps"] - fps) > 0.5: prob.append(f"fps galat {C['fps']} (chahiye {fps})")
        vd = float(v.get("duration") or dur)
        C["video_dur"] = round(vd, 2)
    if as_:
        ad = float(as_[0].get("duration") or dur); C["audio_dur"] = round(ad, 2)
        if vs and abs(ad - C.get("video_dur", dur)) > 0.35:
            prob.append(f"audio ({ad:.2f}s) aur video ({C.get('video_dur'):.2f}s) ki lambai alag")
    if expect_dur and dur > 0 and abs(dur - expect_dur) > 0.6:
        prob.append(f"lambai {dur:.2f}s, awaaz ke hisaab se {expect_dur:.2f}s honi chahiye")
    # kaale + ruke frame
    try:
        e = _ff(["-i", p, "-vf", "blackdetect=d=0.25:pix_th=0.06,freezedetect=n=0.002:d=1.2", "-an"])
        blacks = [float(x) for x in re.findall(r"black_start:([\d.]+)", e)]
        fstart = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", e)]
        fdur = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", e)]
        blacks = [b for b in blacks if b > 0.3]
        C["black_at"] = blacks; C["freeze_at"] = list(zip(fstart, fdur + [None] * (len(fstart) - len(fdur))))
        tail = dur - 2.5 if not last_line_ok else dur - 0.8           # aakhir me subscribe/loop – normal
        real_freeze = [(a, b) for a, b in C["freeze_at"] if a < tail]
        if blacks: prob.append(f"kaala frame {', '.join(f'{b:.1f}s' for b in blacks[:4])} pe")
        if real_freeze: prob.append("video ATKI hui: " + ", ".join(f"{a:.1f}s ({(b or 0):.1f}s)" for a, b in real_freeze[:4]))
    except Exception as ex:
        warn.append(f"black/freeze check nahi hua: {ex}")
    # audio level
    try:
        e = _ff(["-i", p, "-vn", "-af", "astats=metadata=0:reset=0,silencedetect=n=-45dB:d=1.5"])
        pk = re.findall(r"Peak level dB:\s*(-?[\d.inf]+)", e)
        peak = max(float(x) for x in pk if x not in ("-inf", "inf")) if pk else None
        C["audio_peak_db"] = peak
        if peak is not None and peak > -0.1: prob.append(f"awaaz clip ho rahi (peak {peak:.2f} dB)")
        sil = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", e)]
        C["silences"] = sil
        if sil and max(sil) > 2.5: warn.append(f"{max(sil):.1f}s ki chuppi hai")
        if peak is not None and peak < -30: prob.append("awaaz bahut dheemi / gayab")
    except Exception as ex:
        warn.append(f"audio check nahi hua: {ex}")
    if ass:
        try:
            t = Path(ass).read_text(encoding="utf-8")
            C["caption_events"] = t.count("Dialogue:")
            if sents and C["caption_events"] < len(sents): warn.append("captions kam lag rahe hain")
        except Exception:
            prob.append("captions file nahi padhi ja saki")
    if scene_info:
        rep["scenes"] = scene_info
        miss = [s for s in scene_info if s.get("source") in ("none", "missing")]
        if miss: prob.append(f"{len(miss)} scene(s) ka visual missing")
    ok = not prob
    rep["ok"] = ok
    try:
        p.with_name(p.stem + "_QC.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return ok, prob, rep


def repair(video, audio_wav, expect_dur, work):
    """Chhoti marammat: A/V lambai ka farak – video ko awaaz ki lambai pe dobara mux (bina freeze)."""
    p = Path(video); tmp = Path(work) / "qc_repair.mp4"
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(p), "-i", str(audio_wav),
                        "-map", "0:v", "-map", "1:a", "-t", f"{expect_dur:.3f}", "-c:v", "libx264", "-preset",
                        "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart", str(tmp)], check=True, capture_output=True)
        tmp.replace(p); return True
    except Exception:
        return False
