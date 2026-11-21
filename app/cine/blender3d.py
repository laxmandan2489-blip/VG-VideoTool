"""Optional Blender 3D shot renderer for The Viral Gyaan VideoTool.

This is a procedural starter renderer (not a substitute for licensed rigged character
assets). It creates cinematic abstract/hero props and supports an externally supplied
.blend scene. Blender is optional; callers should gracefully fall back to stock footage.
"""
from __future__ import annotations
import os, shutil, subprocess, tempfile
from pathlib import Path

def find_blender():
    candidates = [os.environ.get("BLENDER_PATH"), shutil.which("blender")]
    candidates += [
        r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    ]
    for p in candidates:
        if p and Path(p).is_file(): return str(Path(p))
    return None

def visual_type(text):
    """Grounded universal visual taxonomy for Hindi/English narration."""
    t=(text or "").lower()
    # v3.23 STRICT RELEVANCE GATE: Procedural 3D ONLY for genuine space/science/tech subjects.
    # Humans, animals, cities, forts, vehicles, weapons are handled by real footage or Cloud Flux 2.5D Parallax!
    rules=[
      ("blackhole",("ब्लैक होल","black hole","blackhole","event horizon")),
      ("galaxy",("आकाशगंगा","गैलेक्सी","galaxy","milky way","नेबुला","nebula")),
      ("moon",("चंद्रमा","चाँद","moon","lunar")),
      ("rocket",("रॉकेट","rocket","spacecraft","अंतरिक्ष यान","गगनयान","gaganyaan")),
      ("atom",("परमाणु","atom","nucleus","न्यूक्लियस","dna","डीएनए","molecule","अणु")),
      ("planet",("ग्रह","पृथ्वी","मंगल","planet","earth","mars","अंतरिक्ष","space","orbit","कक्षा")),
    ]
    for kind,words in rules:
        if any(w in t for w in words): return kind
    return "cinematic"

def render_scene(output, duration=4, resolution=(1280,720), kind="cinematic", blender=None, blend_file=None):
    """Render a scene to MP4 via Blender background mode. Returns output path or None."""
    blender = blender or find_blender()
    if not blender: return None
    output = str(Path(output).resolve()); Path(output).parent.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).with_name("_blender_scene_runtime.py")
    if blend_file and Path(blend_file).is_file():
        cmd=[blender,"-b",str(blend_file),"--python",str(script),"--",output,str(duration),str(resolution[0]),str(resolution[1]),kind]
    else:
        cmd=[blender,"-b","--python",str(script),"--",output,str(duration),str(resolution[0]),str(resolution[1]),kind]
    try:
        subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=max(180,int(duration)*90))
        return output if Path(output).is_file() and Path(output).stat().st_size>1000 else None
    except Exception:
        return None


def plan_3d_shots(script, max_shots=8):
    """Create conservative 3D shot suggestions from narration sentences.
    The caller may use these only when 3D mode is enabled; ordinary footage remains default.
    """
    import re
    lines=[x.strip() for x in re.split(r"[।.!?\n]+", script or "") if x.strip()]
    out=[]
    for i,line in enumerate(lines[:max_shots]):
        kind=visual_type(line)
        # Only explicit visual subjects receive procedural shots; avoid forcing abstract narration.
        if kind != "cinematic":
            out.append({"kind":"blender3d","visual":kind,"text":line,"index":i})
    return out
