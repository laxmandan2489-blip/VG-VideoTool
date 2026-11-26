"""v3.22 FREE CLOUD AI VISUAL GENERATOR + COMFYUI / MESHY BRIDGE (Zero GPU load on 8GB RAM laptop).

When stock footage fails or a script demands a specific visual that doesn't exist in Pixabay/YouTube:
  1. ComfyUI Bridge (optional: set COMFYUI_URL in .env to a Free Google Colab GPU or local ComfyUI)
  2. Pollinations.ai Flux (100% FREE, zero API key, 1080x1920 photorealistic documentary visuals)
  3. Hugging Face Free Inference API (optional: set HF_TOKEN in .env for FLUX.1-schnell)
  4. Meshy AI 3D Preview Bridge (optional: set MESHY_API_KEY in .env)

All generated visuals are cached by prompt hash and returned as clean 9:16 images ready for
2.5D parallax animation in render.py / doc_cards.py. Never crashes or blocks the pipeline.
"""
import hashlib
import json
import os
import time
import urllib.parse
from pathlib import Path

from common import log


def _doc_prompt(scene_desc, topic="", W=1080, H=1920):
    """Wrap raw scene description into a consistent documentary cinematography prompt (16:9 or 9:16)."""
    clean = str(scene_desc or "").strip()
    if not clean:
        return ""
    orient = "widescreen 16:9 cinematic composition" if W > H else "vertical 9:16 composition"
    return (
        f"Cinematic documentary photograph of {clean}. "
        f"{('Context: ' + topic + '. ') if topic else ''}"
        "Ultra realistic, dramatic moody lighting, shallow depth of field, MagnatesMedia and Fern documentary aesthetic, "
        f"sharp high detail, {orient}, "
        "NO text, NO watermark, NO captions, NO logos, NO cartoon, NO anime."
    )


def _try_comfyui(prompt, out_path, comfy_url, W=768, H=1344, timeout=120):
    """Send a lightweight txt2img workflow to a remote (Google Colab GPU) or local ComfyUI server."""
    import requests
    base = comfy_url.rstrip("/")
    # Check server health quickly (2s) so we never hang if ComfyUI isn't running
    r = requests.get(f"{base}/system_stats", timeout=3)
    r.raise_for_status()

    # Minimal SDXL/Flux-compatible ComfyUI API workflow (uses server's first available checkpoint)
    obj = requests.get(f"{base}/object_info/CheckpointLoaderSimple", timeout=5).json()
    ckpts = obj.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
    if not ckpts:
        return None
    wf = {
        "3": {"class_type": "KSampler", "inputs": {
            "seed": int(time.time()) % 9999999, "steps": 18, "cfg": 6.5,
            "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
            "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0],
        }},
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpts[0]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {
            "text": "text, watermark, subtitle, logo, cartoon, anime, blurry, deformed", "clip": ["4", 1],
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "VG_v322", "images": ["8", 0]}},
    }
    resp = requests.post(f"{base}/prompt", json={"prompt": wf}, timeout=15).json()
    pid = resp.get("prompt_id")
    if not pid:
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2.0)
        hist = requests.get(f"{base}/history/{pid}", timeout=10).json()
        if pid in hist:
            outs = hist[pid].get("outputs", {}).get("9", {}).get("images", [])
            if outs:
                fn = outs[0]["filename"]
                sf = outs[0].get("subfolder", "")
                img_r = requests.get(f"{base}/view", params={"filename": fn, "subfolder": sf, "type": "output"}, timeout=20)
                if img_r.status_code == 200 and len(img_r.content) > 5000:
                    Path(out_path).write_bytes(img_r.content)
                    return str(out_path)
            break
    return None


def _try_pollinations(prompt, out_path, W=1080, H=1920, timeout=45):
    """100% free cloud Flux image generation (zero API key, zero GPU load)."""
    import requests
    seed = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8], 16) % 999999
    q = urllib.parse.quote(prompt, safe="")
    url = f"https://image.pollinations.ai/prompt/{q}?width={W}&height={H}&seed={seed}&nologo=true&model=flux"
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "VG-VideoTool/3.22"})
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/") and len(r.content) > 8000:
        Path(out_path).write_bytes(r.content)
        # v4.16: auto-trim bottom 7% & right 3% so pollinations.ai corner watermark never shows on screen
        try:
            from PIL import Image
            with Image.open(out_path) as _im:
                _im = _im.convert("RGB")
                _iw, _ih = _im.size
                _im = _im.crop((0, 0, int(_iw * 0.97), int(_ih * 0.93))).resize((W, H), Image.LANCZOS)
                _im.save(out_path, quality=93)
        except Exception:
            pass
        return str(out_path)
    return None


def _try_huggingface(prompt, out_path, hf_token, timeout=60):
    """Optional Hugging Face free Inference API (FLUX.1-schnell)."""
    import requests
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
        json={"inputs": prompt},
        timeout=timeout,
    )
    if r.status_code == 200 and len(r.content) > 8000:
        Path(out_path).write_bytes(r.content)
        return str(out_path)
    return None


def generate_scene_image(scene_desc, out_dir, topic="", W=1080, H=1920, keys=None):
    """Generate a photorealistic documentary visual for any script demand (zero GPU hang).

    Returns local image path or None if offline/unavailable.
    """
    keys = keys or {}
    prompt = _doc_prompt(scene_desc, topic, W, H)
    if not prompt:
        return None

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(f"{prompt}|{W}x{H}".encode("utf-8")).hexdigest()[:12]
    out_path = out_dir / f"ai_doc_{h}.jpg"
    if out_path.exists() and out_path.stat().st_size > 8000:
        return str(out_path)

    # 1. Optional ComfyUI (Google Colab GPU or local)
    comfy_url = keys.get("COMFYUI_URL") or os.environ.get("COMFYUI_URL", "").strip()
    if comfy_url:
        try:
            res = _try_comfyui(prompt, out_path, comfy_url)
            if res:
                log(f"   🎨 ComfyUI visual generated ✓ ({out_path.name})", show=False)
                return res
        except Exception as e:
            log(f"   (ComfyUI skip: {str(e)[:80]})", show=False)

    # 2. Free Cloud Pollinations Flux (zero key, zero GPU)
    try:
        res = _try_pollinations(prompt, out_path, W=W, H=H)
        if res:
            log(f"   🎨 Cloud Flux visual generated ✓ ({out_path.name})", show=False)
            return res
    except Exception as e:
        log(f"   (Cloud Flux skip: {str(e)[:80]})", show=False)

    # 3. Optional Hugging Face Free Inference
    hf_tok = keys.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "").strip()
    if hf_tok:
        try:
            res = _try_huggingface(prompt, out_path, hf_tok)
            if res:
                log(f"   🎨 HF Flux visual generated ✓ ({out_path.name})", show=False)
                return res
        except Exception as e:
            log(f"   (HF Flux skip: {str(e)[:80]})", show=False)

    return None
