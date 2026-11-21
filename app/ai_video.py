"""v2.22: AI VIDEO – jis line ki sahi footage na mile, uski photo ko chalti video banao (image-to-video).

ENGINE (api keys.txt – PAID, aapki permission ke bina kabhi nahi chalta):
  higgsfield – Higgsfield ki OFFICIAL API (docs.higgsfield.ai)
               HIGGSFIELD = KEY_ID:KEY_SECRET      (console.higgsfield.ai -> API keys)
               model (style.txt): higgsfield_model = wan/v2.6/image-to-video
  muapi      – Open-Higgsfield-AI (GitHub) yahi API use karta hai (muapi.ai)
               MUAPI = ...                          model: muapi_model = wan2.2-image-to-video
CHALU KARNA (style.txt / "setting:"):  ai_video = haan      (default: nahi)
KHARCHA ROKNA:  ai_video_max = 2  (ek video me)   ai_video_din_max = 6  (ek din me)
Asli insaan ki photo ko kabhi video nahi banata (deepfake jaisa) – sirf cheezein / jagah / janwar / scene.
"""
import json, time, uuid, datetime, hashlib, threading
from pathlib import Path
from common import log, TOOL, yes, num

USAGE = TOOL / "seekha" / "ai_video_usage.json"
CACHE = TOOL / "temp" / "cache" / "ai_video"
STATE = {"used": 0, "why": ""}
_LOCK = threading.Lock()
HF = "https://api.higgsfield.ai"
MU = "https://api.muapi.ai/api/v1"


def _rq():
    import requests
    return requests


def engine(style, keys):
    if not yes(style.get("ai_video", "nahi")):
        return None
    want = (style.get("ai_video_engine") or "").lower()
    hf = keys.get("HIGGSFIELD") or (f"{keys['HIGGSFIELDID']}:{keys['HIGGSFIELDSECRET']}"
                                    if keys.get("HIGGSFIELDID") and keys.get("HIGGSFIELDSECRET") else None)
    mu = keys.get("MUAPI")
    if want in ("", "higgsfield") and hf and ":" in hf: return ("higgsfield", hf)
    if want in ("", "muapi") and mu: return ("muapi", mu)
    if hf and ":" in hf: return ("higgsfield", hf)
    return None


def _today():
    try:
        d = json.loads(USAGE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    t = datetime.date.today().isoformat()
    return d if d.get("date") == t else {"date": t, "n": 0}


def budget_ok(style):
    per_video = int(num(style, "ai_video_max", 0, 10)) if style.get("ai_video_max") not in (None, "") else 2
    per_day = int(num(style, "ai_video_din_max", 0, 50)) if style.get("ai_video_din_max") not in (None, "") else 6
    if STATE["used"] >= per_video:
        STATE["why"] = f"is video ki AI video limit ({per_video}) poori"; return False
    if _today()["n"] >= per_day:
        STATE["why"] = f"aaj ki AI video limit ({per_day}) poori"; return False
    return True


def _count_day():
    d = _today(); d["n"] += 1
    USAGE.parent.mkdir(parents=True, exist_ok=True)
    USAGE.write_text(json.dumps(d), encoding="utf-8")


def _to_jpg(img):
    """Kisi bhi photo ko 9:16 / 16:9 ke paas wali jpg (max 1440) – upload chhota."""
    from PIL import Image
    out = Path(str(img) + ".up.jpg")
    im = Image.open(img).convert("RGB")
    im.thumbnail((1440, 1440))
    im.save(out, "JPEG", quality=90)
    return out


# ------------------------------------------------------------------ Higgsfield official
def _hf_headers(cred, extra=None):
    h = {"Authorization": f"Key {cred}", "Content-Type": "application/json"}
    if extra: h.update(extra)
    return h


def hf_upload(cred, img):
    rq = _rq(); jp = _to_jpg(img)
    r = rq.post(f"{HF}/files/generate-upload-url", json={"content_type": "image/jpeg"}, headers=_hf_headers(cred), timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Higgsfield upload-url {r.status_code}: {r.text[:200]}")
    u = r.json()
    put = rq.put(u["upload_url"], data=jp.read_bytes(), headers=u.get("upload_headers") or {"Content-Type": "image/jpeg"},
                 timeout=120)                                    # presigned URL pe API key NAHI bhejni
    if put.status_code not in (200, 201, 204):
        raise RuntimeError(f"Higgsfield upload {put.status_code}")
    return u["public_url"]


def hf_generate(cred, model, body, poll_s=6, max_wait=420):
    rq = _rq()
    r = rq.post(f"{HF}/{model.strip('/')}", json=body, timeout=90,
                headers=_hf_headers(cred, {"Idempotency-Key": str(uuid.uuid4())}))
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"Higgsfield {r.status_code}: {r.text[:200]}")
    j = r.json(); st_url = j.get("status_url") or f"{HF}/requests/{j.get('request_id')}/status"
    t0 = time.time(); wait = poll_s
    while time.time() - t0 < max_wait:
        time.sleep(wait); wait = min(wait + 2, 15)
        s = rq.get(st_url, headers=_hf_headers(cred), timeout=60).json()
        st = s.get("status")
        if st == "completed":
            v = (s.get("video") or {}).get("url") or ((s.get("videos") or [{}])[0].get("url"))
            if not v: raise RuntimeError("Higgsfield: video URL nahi mila")
            return v
        if st in ("failed", "nsfw", "canceled"):
            raise RuntimeError(f"Higgsfield: {st} {str(s.get('error',''))[:150]}")
    raise RuntimeError("Higgsfield: 7 min me video nahi bani")


# ------------------------------------------------------------------ Muapi (Open-Higgsfield-AI ka backend)
def mu_upload(key, img):
    rq = _rq(); jp = _to_jpg(img)
    with open(jp, "rb") as f:
        r = rq.post(f"{MU}/upload_file", files={"file": (jp.name, f, "image/jpeg")}, headers={"x-api-key": key}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Muapi upload {r.status_code}: {r.text[:200]}")
    j = r.json()
    u = j.get("url") or j.get("file_url") or (j.get("data") or {}).get("url")
    if not u: raise RuntimeError(f"Muapi upload: url nahi mila {str(j)[:150]}")
    return u


def _first_url(j):
    for k in ("outputs", "output", "videos", "result"):
        v = j.get(k)
        if isinstance(v, list) and v:
            x = v[0]; return x if isinstance(x, str) else (x.get("url") if isinstance(x, dict) else None)
        if isinstance(v, str) and v.startswith("http"): return v
        if isinstance(v, dict) and v.get("url"): return v["url"]
    if isinstance(j.get("data"), dict): return _first_url(j["data"])
    return None


def mu_generate(key, model, body, poll_s=6, max_wait=420):
    rq = _rq()
    r = rq.post(f"{MU}/{model}", json=body, headers={"x-api-key": key, "Content-Type": "application/json"}, timeout=90)
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"Muapi {r.status_code}: {r.text[:200]}")
    j = r.json(); rid = j.get("request_id") or j.get("id") or (j.get("data") or {}).get("request_id")
    if not rid: raise RuntimeError(f"Muapi: request_id nahi mila {str(j)[:150]}")
    t0 = time.time(); wait = poll_s
    while time.time() - t0 < max_wait:
        time.sleep(wait); wait = min(wait + 2, 15)
        s = rq.get(f"{MU}/predictions/{rid}/result", headers={"x-api-key": key}, timeout=60).json()
        d = s.get("data") if isinstance(s.get("data"), dict) else s
        st = str(d.get("status", "")).lower()
        if st in ("completed", "succeeded", "success"):
            u = _first_url(d)
            if not u: raise RuntimeError("Muapi: video URL nahi mila")
            return u
        if st in ("failed", "error", "canceled", "cancelled"):
            raise RuntimeError(f"Muapi: {st} {str(d.get('error',''))[:150]}")
    raise RuntimeError("Muapi: 7 min me video nahi bani")


# ------------------------------------------------------------------ ek photo -> 5 sec video
def animate(img, prompt, style, keys, vertical=True, avoid=()):
    """Returns local mp4 path ya None. Har kaam log me; kharcha limit ke andar."""
    eng = engine(style, keys)
    if not eng:
        return None
    name, cred = eng
    h0 = hashlib.sha1((name + str(Path(img).stat().st_size) + prompt).encode("utf-8")).hexdigest()[:16]
    if (CACHE / f"{h0}.mp4").exists():
        return str(CACHE / f"{h0}.mp4")
    with _LOCK:                                    # slot pehle pakka karo (do line ek saath limit na tode)
        if not budget_ok(style):
            log(f"   AI video nahi: {STATE['why']}", show=False); return None
        STATE["used"] += 1
    h = hashlib.sha1((name + str(Path(img).stat().st_size) + prompt).encode("utf-8")).hexdigest()[:16]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{h}.mp4"
    if out.exists() and out.stat().st_size > 20000:
        return str(out)
    motion = (style.get("ai_video_motion") or "slow cinematic camera push-in, subtle parallax, natural motion, "
              "documentary look, no text, no watermark")
    full = f"{prompt}. {motion}"
    neg = ", ".join(list(avoid) + ["text", "watermark", "logo", "distorted faces", "extra limbs"])
    try:
        if name == "higgsfield":
            url = hf_upload(cred, img)
            body = {"prompt": full, "image_url": url, "duration": 5,
                    "resolution": style.get("higgsfield_res", "720p"), "negative_prompt": neg}
            vurl = hf_generate(cred, style.get("higgsfield_model", "wan/v2.6/image-to-video"), body)
        else:
            url = mu_upload(cred, img)
            body = {"prompt": full, "image_url": url, "duration": 5, "aspect_ratio": "9:16" if vertical else "16:9",
                    "resolution": style.get("muapi_res", "480p")}
            vurl = mu_generate(cred, style.get("muapi_model", "wan2.2-image-to-video"), body)
        with _LOCK: _count_day()                                  # paisa kata – aaj ki ginti
        r = _rq().get(vurl, timeout=300)
        r.raise_for_status()
        out.write_bytes(r.content)
        log(f"   🎥 AI video bani ({name}) ✓  [aaj: {_today()['n']}]")
        return str(out)
    except Exception as e:
        with _LOCK: STATE["used"] = max(0, STATE["used"] - 1)        # nahi bani – slot wapas
        log(f"   AI video ({name}) nahi bani: {str(e)[:180]}")
        return None
