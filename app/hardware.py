"""v3.1 HARDWARE DETECTION + RENDER PROFILE.

Aapke laptop ki asli jaankari (andaza nahi): CPU, cores, RAM, GPU, VRAM, CUDA, Blender, FFmpeg, disk, Python, packages.
Isse tool khud tay karta hai: kitne shots ek saath, Blender Eevee/Cycles, samples, resolution, FreeVideo chalega ya nahi.

Chalao:  python app/hardware.py      -> HARDWARE_REPORT.json + HARDWARE_COMPATIBILITY.md (VideoTool folder me)
"""
import json, os, platform, re, shutil, subprocess, sys, datetime
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent
_CACHE = {}


def _out(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (r.stdout or "") + (r.stderr or "")
    except Exception:
        return ""


def ram_gb():
    if "ram" in _CACHE:
        return _CACHE["ram"]
    v = None
    try:
        import psutil
        v = psutil.virtual_memory().total / 1024 ** 3
    except Exception:
        pass
    if v is None and os.name == "nt":
        try:
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS(); m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            v = m.ullTotalPhys / 1024 ** 3
        except Exception:
            pass
    if v is None and Path("/proc/meminfo").exists():
        m = re.search(r"MemTotal:\s+(\d+)", Path("/proc/meminfo").read_text())
        if m: v = int(m.group(1)) / 1024 ** 2
    _CACHE["ram"] = round(v, 1) if v else None
    return _CACHE["ram"]


def cpu_name():
    if os.name == "nt":
        o = _out(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"])
        if o.strip(): return o.strip().splitlines()[0]
    if Path("/proc/cpuinfo").exists():
        m = re.search(r"model name\s*:\s*(.+)", Path("/proc/cpuinfo").read_text())
        if m: return m.group(1).strip()
    return platform.processor() or "unknown"


def gpus():
    """[{name, vram_gb, vendor, cuda}]  – NVIDIA ki VRAM nvidia-smi se (sahi), baaki Windows se."""
    out = []
    smi = shutil.which("nvidia-smi") or (r"C:\Windows\System32\nvidia-smi.exe" if os.name == "nt" else None)
    if smi and Path(smi).exists():
        o = _out([smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
        for ln in o.strip().splitlines():
            parts = [x.strip() for x in ln.split(",")]
            if len(parts) >= 2 and parts[1].replace(".", "").isdigit():
                out.append({"name": parts[0], "vram_gb": round(float(parts[1]) / 1024, 1), "vendor": "NVIDIA",
                            "driver": parts[2] if len(parts) > 2 else "", "cuda": True})
    if os.name == "nt":
        o = _out(["powershell", "-NoProfile", "-Command",
                  "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + '|' + $_.AdapterRAM }"])
        for ln in o.strip().splitlines():
            if "|" not in ln: continue
            name, ram = ln.rsplit("|", 1)
            if any(g["name"] == name.strip() for g in out): continue
            try: vr = round(int(ram) / 1024 ** 3, 1)          # AdapterRAM 4 GB pe atak jaata hai – sirf andaza
            except Exception: vr = None
            vendor = "NVIDIA" if "nvidia" in name.lower() else "Intel" if "intel" in name.lower() else \
                "AMD" if ("amd" in name.lower() or "radeon" in name.lower()) else "other"
            out.append({"name": name.strip(), "vram_gb": vr, "vendor": vendor, "cuda": False,
                        "note": "VRAM Windows ke andaze se (shared memory ho sakti hai)"})
    return out


def blender_info():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cine.blender_engine import find_blender
        b = find_blender()
    except Exception:
        b = None
    if not b:
        return {"path": None, "version": None}
    o = _out([b, "-b", "--version"], timeout=60)
    m = re.search(r"Blender\s+(\d+\.\d+(?:\.\d+)?)", o)
    return {"path": b, "version": m.group(1) if m else None}


def ffmpeg_version():
    o = _out(["ffmpeg", "-version"])
    m = re.search(r"ffmpeg version (\S+)", o)
    return m.group(1) if m else None


def disk_free_gb(path=TOOL):
    try:
        return round(shutil.disk_usage(str(path)).free / 1024 ** 3, 1)
    except Exception:
        return None


def packages():
    names = ["numpy", "PIL", "requests", "edge_tts", "faster_whisper", "torch", "open_clip", "transformers",
             "onnxruntime", "psutil", "telegram", "yt_dlp", "cv2"]
    res = {}
    import importlib.util
    for n in names:
        res[n] = importlib.util.find_spec(n) is not None
    return res


def profile(rep):
    """Render settings jo is laptop pe bina atke chalein."""
    ram = rep.get("ram_gb") or 4
    vram = max([g.get("vram_gb") or 0 for g in rep.get("gpus", []) if g.get("cuda")] or [0])
    cores = rep.get("cpu_cores") or 2
    p = {
        "parallel_shots": 1 if ram < 7 else 2 if ram < 12 else 3,
        "visual_search_threads": 2 if ram < 7 else 4,
        "blender_engine": "EEVEE",
        "blender_samples": 16 if ram < 12 else 32,
        "blender_scale": 0.5 if ram < 10 else 0.75 if ram < 20 else 1.0,  # Blender render resolution, ffmpeg upscale
        "blender_particles": 150 if ram < 10 else 300 if ram < 20 else 800,
        "blender_parallel": 1,                                           # Blender hamesha ek-ek (RAM bachao)
        "cycles_ok": bool(vram >= 4) or ram >= 16,
        "whisper_model": "small" if ram >= 6 else "base",
        "clip_model_ok": ram >= 6,
        "freevideo_ok": False,
        "freevideo_reason": "",
    }
    reasons = []
    if vram < 8: reasons.append(f"NVIDIA CUDA VRAM {vram or 0} GB hai, FreeVideo ko kam se kam 8 GB chahiye")
    if ram < 16: reasons.append(f"RAM {ram} GB hai, FreeVideo ko kam se kam 16 GB chahiye")
    if (rep.get("disk_free_gb") or 0) < 60: reasons.append(f"disk me {rep.get('disk_free_gb')} GB khaali, models ke liye ~60 GB+ rakhein")
    p["freevideo_ok"] = not reasons
    p["freevideo_reason"] = "; ".join(reasons) if reasons else "chal sakta hai (pehle chhota test karein)"
    return p


def detect(write=True):
    rep = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()} ({platform.version()})",
        "machine": platform.machine(),
        "cpu": cpu_name(), "cpu_cores": os.cpu_count(),
        "ram_gb": ram_gb(), "gpus": gpus(),
        "python": sys.version.split()[0], "python_exe": sys.executable,
        "ffmpeg": ffmpeg_version(), "blender": blender_info(),
        "disk_free_gb": disk_free_gb(), "packages": packages(),
    }
    rep["cuda"] = any(g.get("cuda") for g in rep["gpus"])
    rep["profile"] = profile(rep)
    if write:
        (TOOL / "HARDWARE_REPORT.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        (TOOL / "HARDWARE_COMPATIBILITY.md").write_text(markdown(rep), encoding="utf-8")
    return rep


def load_profile():
    """Pichhli report (ya nayi detect) ka profile – make_video isse settings leta hai."""
    f = TOOL / "HARDWARE_REPORT.json"
    try:
        rep = json.loads(f.read_text(encoding="utf-8"))
        return rep.get("profile") or profile(rep)
    except Exception:
        try:
            return detect(write=True)["profile"]
        except Exception:
            return profile({"ram_gb": ram_gb(), "cpu_cores": os.cpu_count(), "gpus": []})


def markdown(rep):
    p = rep["profile"]
    g = "\n".join(f"| {x['name']} | {x.get('vram_gb')} GB | {'haan' if x.get('cuda') else 'nahi'} | {x.get('note','')} |"
                  for x in rep["gpus"]) or "| (koi GPU nahi mila) | - | - | |"
    pk = ", ".join(f"{k} {'✓' if v else '✗'}" for k, v in rep["packages"].items())
    return f"""# HARDWARE COMPATIBILITY (is computer pe detect kiya – {rep['generated']})

> Ye file `CHECK_SYSTEM.bat` / `python app/hardware.py` chalane pe AAPKE laptop pe dobara banti hai.
> Jo yahan likha hai wahi tool ki settings tay karta hai.

| Cheez | Value |
|---|---|
| OS | {rep['os']} |
| CPU | {rep['cpu']} ({rep['cpu_cores']} threads) |
| RAM | {rep['ram_gb']} GB |
| Disk khaali | {rep['disk_free_gb']} GB |
| Python | {rep['python']} |
| FFmpeg | {rep['ffmpeg'] or 'NAHI MILA ✗'} |
| Blender | {rep['blender'].get('version') or 'NAHI MILA'} {rep['blender'].get('path') or ''} |
| CUDA | {'haan' if rep['cuda'] else 'nahi'} |

## GPU
| Naam | VRAM | CUDA | Note |
|---|---|---|---|
{g}

## Packages
{pk}

## Tool ne kya chuna (render profile)
- Ek saath shots: **{p['parallel_shots']}**, visual search threads: **{p['visual_search_threads']}**
- Blender: **{p['blender_engine']}**, samples {p['blender_samples']}, resolution scale {p['blender_scale']}, particles {p['blender_particles']}, Blender ek-ek shot (sequential)
- Cycles (sirf chuninda shots): {'chal sakta hai' if p['cycles_ok'] else 'band (RAM/VRAM kam)'}
- Whisper model: **{p['whisper_model']}**
- FreeVideo (local AI video): **{'HAAN' if p['freevideo_ok'] else 'NAHI'}** – {p['freevideo_reason']}

## Agar FreeVideo nahi chalta
Tool crash nahi karega. Iski jagah ye chain chalegi (har line ke liye):
1. sahi stock footage (Pixabay/Wikimedia/NASA/Openverse, AI aankh se jaanch)
2. aapki apni footage / script ke link
3. Gemini AI photo + 2.5D depth parallax
4. Blender procedural 3D scene (space, DNA, molecule, underwater, tech, mystery, history, globe, infographic)
5. animated kinetic card (kabhi static photo nahi)

Remote GPU: agar kisi doosre PC / cloud GPU pe ComfyUI+FreeVideo chal raha ho, `api keys.txt` me
`COMFYUI_URL=http://IP:8188` likhein – tool wahan se clip banwa lega.
"""


if __name__ == "__main__":
    r = detect(True)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    print("\nHARDWARE_REPORT.json + HARDWARE_COMPATIBILITY.md bana diye:", TOOL)
