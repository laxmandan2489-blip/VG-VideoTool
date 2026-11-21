"""v3.30 REMOTION MOTION-GRAPHICS BRIDGE (After Effects-grade React + CSS 3D + Motion Blur).

Optional upgrade: If Node.js + remotion_studio/node_modules/remotion are installed (via 1-click
INSTALL_REMOTION.bat), renders true 3D-camera, spring-physics, directional-motion-blur documentary
beats directly into MP4. If not installed, returns None silently so pure-Python doc_cards.py runs.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from common import TOOL, log

REMOTION_DIR = TOOL / "remotion_studio"
STATE = {"ok": None, "why": ""}


def _npx():
    return "npx.cmd" if os.name == "nt" else "npx"


def available():
    if STATE["ok"] is not None:
        return STATE["ok"]
    STATE["ok"] = False
    node = shutil.which("node")
    if not node:
        STATE["why"] = "Node.js nahi mila (INSTALL_REMOTION.bat chalao)"
        return False
    if not (REMOTION_DIR / "node_modules" / "remotion").exists():
        STATE["why"] = "remotion install nahi (INSTALL_REMOTION.bat chalao)"
        return False
    if not (REMOTION_DIR / "src" / "DocumentaryBeat.tsx").exists():
        STATE["why"] = "remotion_studio template nahi mila"
        return False
    STATE["ok"] = True
    return True


def render_beat(kind, props, dur, out_mp4, W=1080, H=1920, fps=30):
    """Render a Remotion DocumentaryBeat MP4. Returns out_mp4 path or None on fallback.

    kind: 'news_highlight' | 'stat_slam' | 'cutout_3d' | 'timeline_3d'
    """
    if not available():
        return None
    out_mp4 = Path(out_mp4).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    frames = max(30, int(round(dur * fps)))
    payload = dict(props or {}, kind=kind, durationInFrames=frames, width=W, height=H, fps=fps)
    props_file = out_mp4.with_suffix(".props.json")
    props_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    cmd = [
        _npx(), "remotion", "render", "src/index.ts", "DocumentaryBeat", str(out_mp4),
        "--props", str(props_file),
        "--frames", f"0-{frames - 1}",
        "--concurrency", "2",
        "--codec", "h264",
        "--log", "error",
    ]
    try:
        r = subprocess.run(
            cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True,
            timeout=180, stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode == 0 and out_mp4.exists() and out_mp4.stat().st_size > 8000:
            log(f"   ✨ Remotion 3D Beat ready: {kind} ✓", show=False)
            return str(out_mp4)
        log(f"   (Remotion skip {kind}: {r.stderr[-120:]})", show=False)
    except Exception as e:
        log(f"   (Remotion skip {kind}: {str(e)[:90]})", show=False)
    return None
