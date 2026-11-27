import re
"""v4.31 100% FREE ULTRA-REALISTIC CLOUD AI VISUAL GENERATOR (Zero GPU, Zero Card).

Engine Priority (all 100% FREE, zero international card):
  1. Cloudflare Workers AI (@cf/black-forest-labs/flux-1-schnell — 10,000 Neurons/day FREE, no card!)
     - Direct API using CF_API_TOKEN + CF_ACCOUNT_ID (or Worker proxy /ai-image using TG_TOKEN + env.AI binding)
  2. ComfyUI Bridge (optional: COMFYUI_URL)
  3. Pollinations.ai (gen.pollinations.ai with free POLLINATIONS_API_KEY + legacy image.pollinations.ai fallback)
  4. Hugging Face Free Inference API (optional: HF_TOKEN for FLUX.1-schnell)

All generated visuals are cached by prompt hash and returned as crisp 9:16 or 16:9 35mm documentary photographs.
"""
import base64
import hashlib
import io
import json
import os
import time
import urllib.parse
from pathlib import Path

from common import log

_DEFAULT_CF_ACCOUNT_ID = "79108b20de09ead3bfff43e738f1b8b9"
_WARNED_ONCE = False


def _sanitize_scene_for_ai(scene_desc, topic=""):
    """v4.34: Strip text/chart/number/meta triggers so FLUX NEVER draws garbled English, Chinese signs, or fake 'ubscribe'."""
    s = str(scene_desc or "").strip()
    # Remove internal beat/shot markers, subscribe/comment/UI triggers, and raw percentages/numbers
    s = re.sub(r"\b(?:beat|shot)\s*\d+\b", "", s, flags=re.I)
    s = re.sub(r"\b(?:subscribe|comment|follow|like|share|bell icon|pie chart|bar chart|graph|infographic|text overlay|headline|signboard|banner|billboard|calculator screen|phone screen|smartphone screen|logo|watermark)\b", "", s, flags=re.I)
    s = re.sub(r"\b\d+(?:\.\d+)?\s*(?:%|(?:percent|crore|lakh|million|billion)\b)", "", s, flags=re.I)
    s = re.sub(r"[₹$€]\s*[\d,.]+", "", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-—|")
    if len(s) < 6 and topic:
        s = f"authentic real-world documentary scene about {topic}"
    return s


def _doc_prompt(scene_desc, topic="", W=1080, H=1920):
    """v4.34: Cohesive 35mm documentary photojournalism prompt — authentic Indian look when Indian topic, ZERO text/charts/Chinese."""
    clean = _sanitize_scene_for_ai(scene_desc, topic)
    if not clean:
        return ""
    orient = "widescreen 16:9 horizontal framing" if W > H else "vertical 9:16 portrait framing"
    combined = f"{clean} {topic}".lower()
    is_indian = bool(re.search(
        r"(india|indian|bharat|hindi|delhi|mumbai|kashmir|tata|mahindra|railway|rupee|gst|isro|rbi|kirana|modi|bengaluru|chennai|kolkata|pune|jaipur|truck)",
        combined, re.I
    ))
    locale_lock = (
        "Authentic real Indian environment, natural Indian people and real Indian daylight textures, "
        if is_indian else ""
    )
    return (
        f"Pure candid 35mm documentary photograph of {clean}. {locale_lock}"
        "Shot on Kodak Portra 400 film with 50mm lens, warm natural ambient daylight, genuine real-life textures, "
        f"cinematic photojournalism still, sharp focus, subtle organic film grain, {orient}. "
        "STRICTLY PURE PHOTOGRAPH: ZERO text, ZERO letters, ZERO numbers, ZERO Chinese or foreign characters, "
        "ZERO signs, ZERO screens, ZERO charts, ZERO logos, ZERO plastic skin, ZERO glossy CGI, ZERO cartoon."
    )


def _save_resized(img_bytes, out_path, W, H, trim_watermark=False):
    from PIL import Image
    with Image.open(io.BytesIO(img_bytes)) as im:
        im = im.convert("RGB")
        iw, ih = im.size
        if iw < 128 or ih < 128:
            return None
        if trim_watermark and iw >= 300 and ih >= 300:
            im = im.crop((0, 0, int(iw * 0.97), int(ih * 0.93)))
            iw, ih = im.size
        # Center-crop to target aspect ratio (9:16 or 16:9) without stretching
        target_ar = W / float(H)
        cur_ar = iw / float(ih)
        if cur_ar > target_ar * 1.02:
            nw = int(ih * target_ar)
            x0 = (iw - nw) // 2
            im = im.crop((x0, 0, x0 + nw, ih))
        elif cur_ar < target_ar * 0.98:
            nh = int(iw / target_ar)
            y0 = (ih - nh) // 2
            im = im.crop((0, y0, iw, y0 + nh))
        im = im.resize((W, H), Image.LANCZOS)
        im.save(out_path, format="JPEG", quality=93)
    return str(out_path)


def _try_cloudflare_direct(prompt, out_path, cf_token, cf_account, W=1080, H=1920, timeout=45):
    """v4.32: 100% FREE Cloudflare Workers AI — FLUX.1-schnell (exact valid schema: prompt + steps ONLY) + SDXL-Lightning fallback."""
    import requests
    acc = (cf_account or _DEFAULT_CF_ACCOUNT_ID).strip()
    hdrs = {"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"}
    # Model 1: FLUX.1-schnell (ONLY accepts prompt + steps 4..8; passing width/height causes HTTP 400!)
    # Model 2: SDXL-Lightning (instant FREE backup on the same token if FLUX filters or hiccups)
    models = [
        ("@cf/black-forest-labs/flux-1-schnell", {"prompt": prompt[:1800], "steps": 6}),
        ("@cf/bytedance/stable-diffusion-xl-lightning", {"prompt": prompt[:1000]}),
    ]
    last_err = ""
    for mdl, payload in models:
        try:
            url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{mdl}"
            r = requests.post(url, headers=hdrs, json=payload, timeout=timeout)
            if r.status_code != 200:
                last_err = f"{mdl} HTTP {r.status_code}: {r.text[:110]}"
                continue
            ct = r.headers.get("content-type", "").lower()
            if ct.startswith("image/") and len(r.content) > 8000:
                return _save_resized(r.content, out_path, W, H)
            data = r.json()
            b64 = (data.get("result") or {}).get("image") or data.get("image")
            if b64:
                raw = base64.b64decode(b64)
                if len(raw) > 8000:
                    return _save_resized(raw, out_path, W, H)
            last_err = f"{mdl} empty image"
        except Exception as e:
            last_err = f"{mdl}: {str(e)[:90]}"
    raise RuntimeError(f"CF Direct failed ({last_err})")


def _try_cloudflare_worker_proxy(prompt, out_path, worker_url, tg_token, W=1080, H=1920, timeout=45):
    """Call user's own vg-bots Cloudflare Worker /ai-image route (uses free Workers AI binding, zero extra secrets!)."""
    import requests
    gw, gh = (1024, 576) if W > H else (768, 1344)
    r = requests.post(
        worker_url.rstrip("/") + "/ai-image",
        headers={"X-VG-Auth": tg_token, "Content-Type": "application/json"},
        json={"prompt": prompt[:1800], "steps": 6},
        timeout=timeout,
    )
    if r.status_code != 200:
        raise RuntimeError(f"CF Worker /ai-image HTTP {r.status_code}: {r.text[:100]}")
    if r.headers.get("content-type", "").lower().startswith("image/") and len(r.content) > 8000:
        return _save_resized(r.content, out_path, W, H)
    data = r.json()
    b64 = data.get("image")
    if b64:
        raw = base64.b64decode(b64)
        if len(raw) > 8000:
            return _save_resized(raw, out_path, W, H)
    return None


def _try_comfyui(prompt, out_path, comfy_url, W=768, H=1344, timeout=120):
    import requests
    base = comfy_url.rstrip("/")
    r = requests.get(f"{base}/system_stats", timeout=3)
    r.raise_for_status()
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
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "VG_v431", "images": ["8", 0]}},
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
                    return _save_resized(img_r.content, out_path, W, H)
            break
    return None


def _try_pollinations(prompt, out_path, W=1080, H=1920, api_key="", timeout=45):
    """Pollinations gen.pollinations.ai (with free key) + legacy image.pollinations.ai fallback."""
    import requests
    base_seed = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8], 16) % 999999
    q = urllib.parse.quote(prompt, safe="")
    hdrs = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"}
    urls = []
    if api_key:
        h_auth = dict(hdrs, Authorization=f"Bearer {api_key}")
        urls.append((f"https://gen.pollinations.ai/image/{q}?width={W}&height={H}&seed={base_seed}&model=flux&nologo=true", h_auth, False))
        urls.append((f"https://gen.pollinations.ai/image/{q}?width={W}&height={H}&seed={(base_seed+137)%999999}&model=zimage&nologo=true", h_auth, False))
    urls.append((f"https://image.pollinations.ai/prompt/{q}?width={W}&height={H}&seed={base_seed}&nologo=true&enhance=false&model=flux", hdrs, True))
    urls.append((f"https://image.pollinations.ai/prompt/{q}?width={W}&height={H}&seed={(base_seed+421)%999999}&nologo=true&enhance=false&model=turbo", hdrs, True))

    last_err = ""
    for url, h_use, do_trim in urls:
        try:
            r = requests.get(url, timeout=timeout, headers=h_use)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/") and len(r.content) > 12000:
                return _save_resized(r.content, out_path, W, H, trim_watermark=do_trim)
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)[:80]
            continue
    if last_err:
        raise RuntimeError(f"Pollinations failed ({last_err})")
    return None


def _try_huggingface(prompt, out_path, hf_token, W=1080, H=1920, timeout=60):
    import requests
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
        json={"inputs": prompt},
        timeout=timeout,
    )
    if r.status_code == 200 and len(r.content) > 8000:
        return _save_resized(r.content, out_path, W, H)
    raise RuntimeError(f"HF HTTP {r.status_code}")


def generate_scene_image(scene_desc, out_dir, topic="", W=1080, H=1920, keys=None, variation=0):
    """Generate a 100% realistic 35mm documentary AI photograph (zero GPU, zero card)."""
    global _WARNED_ONCE
    keys = keys or {}
    prompt = _doc_prompt(scene_desc, topic, W, H)
    if not prompt:
        return None

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _var_tag = ("wide establishing documentary frame", "medium candid action frame", "close-up natural detail frame", "over-the-shoulder real-life perspective")[int(variation or 0) % 4]
    if variation:
        prompt = f"{_var_tag}, {prompt}"
    h = hashlib.sha1(f"{prompt}|{W}x{H}|v{int(variation or 0)}".encode("utf-8")).hexdigest()[:12]
    out_path = out_dir / f"ai_doc_{h}.jpg"
    if out_path.exists() and out_path.stat().st_size > 8000:
        return str(out_path)

    errors = []

    # 1. PRIMARY (v4.31): Cloudflare Workers AI FLUX.1-schnell Direct (10,000 Neurons/day FREE, zero card!)
    cf_tok = (keys.get("CF_API_TOKEN") or keys.get("CLOUDFLARE_API_TOKEN")
              or os.environ.get("CF_API_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    cf_acc = (keys.get("CF_ACCOUNT_ID") or keys.get("CLOUDFLARE_ACCOUNT_ID")
              or os.environ.get("CF_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID") or _DEFAULT_CF_ACCOUNT_ID).strip()
    if cf_tok:
        try:
            res = _try_cloudflare_direct(prompt, out_path, cf_tok, cf_acc, W=W, H=H)
            if res:
                log(f"   🎨 Cloudflare FLUX 35mm visual ready ✓ ({out_path.name})", show=False)
                return res
        except Exception as e:
            errors.append(f"CF-Direct: {str(e)[:90]}")

    # 1b. Cloudflare Worker /ai-image Proxy (if VG_WORKER_URL + TG_TOKEN available)
    w_url = (keys.get("VG_WORKER_URL") or os.environ.get("VG_WORKER_URL") or "").strip()
    tg_tok = (keys.get("TG_TOKEN") or os.environ.get("TG_TOKEN") or "").strip()
    if w_url and tg_tok:
        try:
            res = _try_cloudflare_worker_proxy(prompt, out_path, w_url, tg_tok, W=W, H=H)
            if res:
                log(f"   🎨 Cloudflare Worker AI FLUX ready ✓ ({out_path.name})", show=False)
                return res
        except Exception as e:
            errors.append(f"CF-Worker: {str(e)[:90]}")

    # 2. Optional ComfyUI
    comfy_url = (keys.get("COMFYUI_URL") or os.environ.get("COMFYUI_URL") or "").strip()
    if comfy_url:
        try:
            res = _try_comfyui(prompt, out_path, comfy_url)
            if res:
                return res
        except Exception as e:
            errors.append(f"ComfyUI: {str(e)[:70]}")

    # 3. Pollinations (gen.pollinations.ai if free key present + legacy fallback)
    pol_key = (keys.get("POLLINATIONS_API_KEY") or os.environ.get("POLLINATIONS_API_KEY") or "").strip()
    try:
        res = _try_pollinations(prompt, out_path, W=W, H=H, api_key=pol_key)
        if res:
            log(f"   🎨 Pollinations 35mm visual ready ✓ ({out_path.name})", show=False)
            return res
    except Exception as e:
        errors.append(f"Pollinations: {str(e)[:90]}")

    # 4. Optional Hugging Face Free Inference
    hf_tok = (keys.get("HF_TOKEN") or os.environ.get("HF_TOKEN") or "").strip()
    if hf_tok:
        try:
            res = _try_huggingface(prompt, out_path, hf_tok, W=W, H=H)
            if res:
                return res
        except Exception as e:
            errors.append(f"HF: {str(e)[:70]}")

    # Loud diagnostic log ONCE so user immediately knows why AI fell back to Stock
    if not _WARNED_ONCE:
        _WARNED_ONCE = True
        msg = " | ".join(errors) if errors else "no AI image key configured"
        log(f"   ⚠️ AI Visual Engine skip ({msg}) — CF_API_TOKEN in make_video.yml ya Worker AI binding check karein!")
    return None
