"""v3.80 AI VISION JUDGE – Top 3 candidate thumbnails ko asli vision model se jaanchta hai (CLIP ki kami poori).

Kaise kaam karta hai:
  1. Groq FREE key se /openai/v1/models list runtime par padhkar chalu vision model (jaise llama-4-scout /
     llama-4-maverick) khud dhoondhta hai – koi hardcoded/invented model naam nahi.
  2. Groq vision na mile ya 429/404 aaye to Gemini vision backup (max 4 calls/video – free quota safe).
  3. Har line/beat ke top 3 candidates ek hi call me bhejta hai -> jo sach me line dikhaye wahi upar, jo
     galat/unrelated ho wo reject. Kuch bhi fail ho to silently None -> CLIP ranking waise hi chalti hai.
  style.txt toggle: vision_judge = haan (default) | nahi
"""
import base64
import io
import json
import re
import threading
import requests

from common import log

STATE = {"groq_models": None, "calls": 0, "gem_calls": 0, "max_calls": 18, "max_gem": 4, "judged": 0, "rejected": 0}
_LOCK = threading.Lock()


def reset():
    with _LOCK:
        STATE.update(calls=0, gem_calls=0, judged=0, rejected=0)


def enabled(style=None):
    v = str((style or {}).get("vision_judge", "haan")).strip().lower()
    return v not in ("nahi", "no", "false", "0", "off")


def discover_groq_vision_models(groq_key, timeout=15):
    """Discover currently active vision-capable models from Groq /models API at runtime."""
    if not groq_key:
        return []
    with _LOCK:
        if STATE["groq_models"] is not None:
            return list(STATE["groq_models"])
    found = []
    try:
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_key}"},
            timeout=timeout,
        )
        if r.ok:
            data = (r.json() or {}).get("data") or []
            for m in data:
                mid = str(m.get("id") or "").strip()
                lo = mid.lower()
                if not mid or any(bad in lo for bad in ("guard", "whisper", "tts", "playai", "embed", "distil")):
                    continue
                if any(good in lo for good in ("llama-4", "vision", "llava")):
                    found.append(mid)
            # Prefer llama-4-scout / llama-4-maverick first
            found.sort(key=lambda x: (0 if "scout" in x.lower() else 1 if "maverick" in x.lower() else 2, x))
    except Exception as e:
        log(f"   (vision_judge groq models skip: {str(e)[:80]})", show=False)
    with _LOCK:
        STATE["groq_models"] = found
    return list(found)


def _to_b64_jpg(img_bytes):
    """Shrink thumbnail to max 384px JPEG so vision call is tiny and fast."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        im.thumbnail((384, 384))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=78)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return base64.b64encode(img_bytes).decode("ascii")


def _parse_json_obj(text):
    if not text:
        return None
    m = re.search(r"\{[\s\S]*\}", str(text))
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _ask_groq_vision(groq_key, prompt, b64_list, timeout=25):
    models = discover_groq_vision_models(groq_key)
    for model in models[:2]:
        content = [{"type": "text", "text": prompt}]
        for k, b64 in enumerate(b64_list, 1):
            content.append({"type": "text", "text": f"Candidate {k}:"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": content}],
                      "temperature": 0.0, "max_tokens": 160},
                timeout=timeout,
            )
            if r.status_code in (404, 429):
                continue
            if r.ok:
                txt = ((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
                obj = _parse_json_obj(txt)
                if isinstance(obj, dict):
                    return obj
        except Exception:
            continue
    return None


def _ask_gemini_vision(gem_key, prompt, raw_imgs, timeout=30):
    if not gem_key:
        return None
    with _LOCK:
        if STATE["gem_calls"] >= STATE["max_gem"]:
            return None
        STATE["gem_calls"] += 1
    try:
        import ai
        from PIL import Image
        parts = [prompt]
        for k, raw in enumerate(raw_imgs, 1):
            parts.append(f"Candidate {k}:")
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            im.thumbnail((384, 384))
            parts.append(im)
        res = ai.ask_json(gem_key, parts, temperature=0.0, timeout=timeout, budget=60)
        return res if isinstance(res, dict) else None
    except Exception:
        return None


def judge(cands, thumb_fn, line_hi, must_show, avoid=(), emotion="neutral", keys=None, style=None):
    """Re-rank & filter top 3 candidates using a free vision model.
    Returns reordered list of candidates (or original `cands` unchanged on skip/error)."""
    if not enabled(style) or not cands or len(cands) < 1:
        return cands
    keys = keys or {}
    gkey = keys.get("GROQ") or ""
    gem = keys.get("GEMINI") or ""
    if not (gkey or gem):
        return cands
    with _LOCK:
        if STATE["calls"] >= STATE["max_calls"]:
            return cands
        STATE["calls"] += 1

    top = list(cands[:3])
    raws, idx_map = [], []
    for idx, c in enumerate(top):
        th = c.get("thumb") or c.get("url") if c.get("kind") == "image" else c.get("thumb")
        raw = thumb_fn(th) if th else None
        if raw and len(raw) > 200:
            raws.append(raw)
            idx_map.append(idx)
    if not raws:
        return cands

    prompt = (
        f"You are a strict documentary video editor judging {len(raws)} candidate visuals for a Hindi script line.\n"
        f"Line: {str(line_hi)[:140]}\n"
        f"MUST SHOW: {str(must_show)[:120]}\n"
        f"Emotion/Tone: {emotion}\n"
        + (f"MUST NOT SHOW (reject if dominant): {', '.join(list(avoid)[:4])}\n" if avoid else "")
        + "Rank ONLY candidates (1-based) that genuinely match MUST SHOW. Put unrelated/wrong-subject candidates in 'reject'.\n"
        + 'Return ONLY JSON: {"best": [1], "reject": [2]}'
    )
    res = None
    if gkey:
        res = _ask_groq_vision(gkey, prompt, [_to_b64_jpg(r) for r in raws])
    if res is None and gem:
        res = _ask_gemini_vision(gem, prompt, raws)
    if not isinstance(res, dict):
        return cands

    best_1 = [int(x) for x in (res.get("best") or []) if isinstance(x, (int, float)) or str(x).isdigit()]
    rej_1 = {int(x) for x in (res.get("reject") or []) if isinstance(x, (int, float)) or str(x).isdigit()}

    picked_idx = []
    for one_based in best_1:
        if 1 <= one_based <= len(idx_map):
            ci = idx_map[one_based - 1]
            if ci not in picked_idx:
                picked_idx.append(ci)
    rej_ci = {idx_map[r - 1] for r in rej_1 if 1 <= r <= len(idx_map) and idx_map[r - 1] not in picked_idx}

    out = [top[ci] for ci in picked_idx]
    for ci, c in enumerate(top):
        if ci not in picked_idx and ci not in rej_ci:
            out.append(c)
    out.extend(cands[3:])
    with _LOCK:
        STATE["judged"] += 1
        STATE["rejected"] += len(rej_ci)
    # Never wipe all candidates if everything was rejected and nothing else remains
    return out if out else cands
