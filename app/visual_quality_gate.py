"""v4.02 Toggleable Visual Quality Gate (1-tap ON/OFF via Telegram /vfilter on | /vfilter off).

Reads `seekha/aapki_settings.json`. If `"vfilter_off"` is present, this gate is 100% bypassed
and the exact original v4.0 Visual Search Engine behavior runs untouched.
"""
import json
import subprocess
from pathlib import Path

from common import TOOL, log

SETTINGS_FILE = TOOL / "seekha" / "aapki_settings.json"


def is_enabled():
    """Returns True by default; returns False if user turned off via `/vfilter off`."""
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and "vfilter_off" in data:
                return False
            if isinstance(data, dict) and data.get("vfilter_off"):
                return False
    except Exception:
        pass
    return True


def _check_image(path):
    """Reject tiny/low-res, blank/solid-color, severely blurry, or extreme banner images."""
    try:
        from PIL import Image
        import numpy as np
        with Image.open(path) as im:
            w, h = im.size
            if w < 520 or h < 340:
                return False, f"low-res image ({w}x{h})"
            aspect = max(w / max(1, h), h / max(1, w))
            if aspect > 3.6:
                return False, f"extreme banner aspect ({w}x{h})"
            gray = np.asarray(im.convert("L").resize((256, 256)), dtype=np.float32)
            std = float(gray.std())
            if std < 8.5:
                return False, f"blank/solid frame (std={std:.1f})"
            # Fast 2D Laplacian variance (sharpness) — rejects very blurry/pixelated stills
            lap = (
                -4.0 * gray[1:-1, 1:-1]
                + gray[:-2, 1:-1] + gray[2:, 1:-1]
                + gray[1:-1, :-2] + gray[1:-1, 2:]
            )
            sharp = float(lap.var())
            if sharp < 18.0:
                return False, f"blurry image (sharp={sharp:.1f})"
        return True, "ok"
    except Exception:
        return True, "skip-err"


def _check_video(path):
    """Reject ultra-low-res or extreme aspect video clips via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
            capture_output=True, text=True, timeout=8, stdin=subprocess.DEVNULL,
        )
        txt = (r.stdout or "").strip().splitlines()
        if txt and "x" in txt[0]:
            w, h = [int(x) for x in txt[0].split("x")[:2]]
            if w < 480 or h < 340:
                return False, f"low-res video ({w}x{h})"
            aspect = max(w / max(1, h), h / max(1, w))
            if aspect > 3.6:
                return False, f"extreme video aspect ({w}x{h})"
    except Exception:
        pass
    return True, "ok"


def check(path, kind="image"):
    """Returns (ok: bool, reason: str). Always passes if `/vfilter off` is active."""
    if not is_enabled():
        return True, "disabled"
    p = Path(path) if path else None
    if not (p and p.exists()):
        return False, "missing"
    if kind == "video":
        return _check_video(p)
    return _check_image(p)
