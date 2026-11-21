"""v2.17: Photo ki GEHRAAI (depth) – asli 3D camera move ke liye.

Pehli baar: free AI model Depth-Anything-V2 (small, ~100 MB) VideoTool\\ai_aankh\\depth me download hota hai.
Model na chale -> andaze wali depth (beech/neeche wali cheez paas, dhundhli cheez door) – phir bhi 3D jaisa lagta hai.
"""
import threading
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter
from common import TOOL, log

DIR = TOOL / "ai_aankh" / "depth"
URLS = ["https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model_quantized.onnx",
        "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"]
_s = {"sess": None, "tried": False}
_lock = threading.Lock()


def _session():
    with _lock:
        if _s["tried"]:
            return _s["sess"]
        _s["tried"] = True
        flag = DIR / "nahi_chala.txt"
        import time as _t
        if flag.exists() and _t.time() - flag.stat().st_mtime < 3 * 86400:
            return None                                   # 3 din baad phir try
        try:
            import onnxruntime as ort
        except Exception:
            try:
                import sys, subprocess
                subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "onnxruntime"], capture_output=True,
                               timeout=900, stdin=subprocess.DEVNULL)
                import onnxruntime as ort
            except Exception as e:
                log(f"   (3D depth: onnxruntime nahi: {e})", show=False); return None
        DIR.mkdir(parents=True, exist_ok=True)
        mp = DIR / "depth_anything_v2_small.onnx"
        if not mp.exists() or mp.stat().st_size < 1_000_000:
            import requests
            from common import UA
            log("   (pehli baar) 3D gehraai wali AI download ho rahi hai (~30-100 MB, ek hi baar)...")
            for u in URLS:
                try:
                    with requests.get(u, stream=True, timeout=60, headers={"User-Agent": UA}) as r:
                        if r.status_code != 200: continue
                        tmp = mp.with_suffix(".part")
                        with open(tmp, "wb") as f:
                            for ch in r.iter_content(1 << 20): f.write(ch)
                        if tmp.stat().st_size > 1_000_000:
                            tmp.replace(mp); break
                except Exception as e:
                    log(f"   depth model download: {e}", show=False)
        if not mp.exists():
            flag.write_text("download nahi hua", encoding="utf-8"); return None
        try:
            _s["sess"] = ort.InferenceSession(str(mp), providers=["CPUExecutionProvider"])
            log("   3D gehraai AI ready ✓")
        except Exception as e:
            flag.write_text(str(e)[:500], encoding="utf-8")
            log(f"   (3D depth model load nahi hua: {e})", show=False)
        return _s["sess"]


def _ai_depth(im):
    sess = _session()
    if sess is None:
        return None
    try:
        S = 518
        x = np.asarray(im.convert("RGB").resize((S, S), Image.BICUBIC)).astype(np.float32) / 255
        x = (x - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
        x = x.transpose(2, 0, 1)[None].astype(np.float32)
        name = sess.get_inputs()[0].name
        d = sess.run(None, {name: x})[0]
        d = np.squeeze(d).astype(np.float32)
        d = (d - d.min()) / (d.max() - d.min() + 1e-6)            # bada = paas
        return np.asarray(Image.fromarray((d * 255).astype("uint8")).resize(im.size, Image.BILINEAR)).astype(np.float32) / 255
    except Exception as e:
        log(f"   (3D depth run fail: {e})", show=False); return None


def _guess_depth(im):
    """AI ke bina andaza: saaf (in-focus) + rangeen + beech/neeche wala hissa paas."""
    sm = im.convert("RGB").resize((256, int(256 * im.height / im.width)))
    a = np.asarray(sm).astype(np.float32)
    g = a.mean(2)
    blur = np.asarray(Image.fromarray(g.astype("uint8")).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)
    sharp = np.abs(g - blur)
    sharp = np.asarray(Image.fromarray(np.clip(sharp * 6, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
    mx, mn = a.max(2), a.min(2); sat = (mx - mn) / (mx + 1e-6)
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    center = 1 - np.sqrt(((xx / w - 0.5) * 1.6) ** 2 + ((yy / h - 0.55) * 1.2) ** 2)
    low = yy / h
    d = 0.40 * sharp / (sharp.max() + 1e-6) + 0.25 * np.clip(center, 0, 1) + 0.20 * low + 0.15 * sat
    d = np.asarray(Image.fromarray((np.clip(d, 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(6)))
    d = d.astype(np.float32); d = (d - d.min()) / (d.max() - d.min() + 1e-6)
    return np.asarray(Image.fromarray((d * 255).astype("uint8")).resize(im.size, Image.BILINEAR)).astype(np.float32) / 255


def get_depth(im, use_ai=True):
    d = _ai_depth(im) if use_ai else None
    return (d, "AI") if d is not None else (_guess_depth(im), "andaza")


def layers(im, depth, n=5):
    """Photo ko n parton me kaato (door -> paas), mulayam kinare. Returns [(rgba_layer, nearness 0..1)]."""
    out = []
    edges = np.quantile(depth, np.linspace(0, 1, n + 1))
    rgb = im.convert("RGB")
    for k in range(1, n):                                  # k=0 (sabse door) = poori photo, neeche base
        m = (depth >= edges[k]).astype(np.float32)
        mk = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(max(2, im.width // 300)))
        lay = rgb.copy().convert("RGBA"); lay.putalpha(mk)
        out.append((lay, k / (n - 1)))
    return out
