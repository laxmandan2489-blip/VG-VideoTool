"""v2.19: Gemini ka BACKUP dimaag – Groq / OpenRouter ke FREE vision models (photo dekh ke jawab).

api keys.txt me (jo ho):
  GROQ = gsk_...          (console.groq.com -> API Keys, free)
  OPENROUTER = sk-or-...  (openrouter.ai -> Keys, free models)
Model naam badalte rehte hain – isliye har baar list se khud 'photo dekhne wala' free model chunta hai.
"""
import re, json, base64, time
from common import log

_MODELS = {}
_DEAD = set()
PROVIDERS = {
    "GROQ": {"base": "https://api.groq.com/openai/v1", "max_img": 5},
    "OPENROUTER": {"base": "https://openrouter.ai/api/v1", "max_img": 8},
}
GROQ_LIKE = ("llama-4", "scout", "maverick", "vision", "-vl", "vl-", "gemma-3", "llava", "pixtral", "qwen2.5-vl", "qwen3-vl")


def _session():
    import requests
    return requests


def models(prov, key, style=None):
    """photo samajhne wale model, best pehle."""
    if prov in _MODELS: return [m for m in _MODELS[prov] if m not in _DEAD]
    rq = _session(); out = []
    try:
        r = rq.get(PROVIDERS[prov]["base"] + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
        data = r.json().get("data", [])
        for m in data:
            mid = m.get("id", "")
            if prov == "OPENROUTER":
                mods = ((m.get("architecture") or {}).get("input_modalities") or [])
                pr = m.get("pricing") or {}
                free = mid.endswith(":free") or (str(pr.get("prompt", "1")) in ("0", "0.0") and str(pr.get("completion", "1")) in ("0", "0.0"))
                if "image" in mods and free: out.append(mid)
            else:
                if any(k in mid.lower() for k in GROQ_LIKE) and m.get("active", True): out.append(mid)
    except Exception as e:
        log(f"   ({prov} models list nahi mili: {e})", show=False)

    def rank(n):
        n = n.lower()
        sc = 0
        for i, k in enumerate(("maverick", "qwen3-vl", "qwen2.5-vl-72", "gemini", "scout", "llama-4", "gemma-3-27", "pixtral", "vision")):
            if k in n: sc = 20 - i; break
        return -sc
    out.sort(key=rank)
    _MODELS[prov] = out
    return out


def ask_vision(keys, prompt, images, temperature=0.1, timeout=120):
    """images = list of jpg bytes. Returns (text, 'Groq'/'OpenRouter') ya (None, None)."""
    rq = _session()
    for prov in ("GROQ", "OPENROUTER"):
        key = keys.get(prov)
        if not key: continue
        for mid in models(prov, key)[:3]:
            content = [{"type": "text", "text": prompt}] + [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(b).decode()}}
                for b in images[:PROVIDERS[prov]["max_img"]]]
            body = {"model": mid, "temperature": temperature, "max_tokens": 900,
                    "messages": [{"role": "user", "content": content}]}
            for attempt in range(2):
                try:
                    r = rq.post(PROVIDERS[prov]["base"] + "/chat/completions", json=body, timeout=timeout,
                                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                         "X-Title": "VG Video Tool"})
                    if r.status_code == 429:
                        time.sleep(8 + attempt * 10); continue
                    if r.status_code in (400, 404, 422):
                        _DEAD.add(mid); break
                    if r.status_code in (401, 403):
                        log(f"   {prov} key galat / band ({r.status_code})", show=False); _DEAD.update(models(prov, key)); break
                    r.raise_for_status()
                    txt = r.json()["choices"][0]["message"]["content"]
                    if txt: return txt, ("Groq" if prov == "GROQ" else "OpenRouter") + f" ({mid.split('/')[-1][:30]})"
                except Exception as e:
                    log(f"   ({prov} {mid}: {str(e)[:120]})", show=False)
                    time.sleep(3)
    return None, None


def parse_json(txt):
    if not txt: return None
    t = re.sub(r"```(?:json)?", "", txt)
    m = re.search(r"\{.*\}", t, re.S)
    if not m: return None
    try:
        return json.loads(m.group(0))
    except Exception:
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(0)))
        except Exception:
            return None


def available(keys):
    return bool(keys.get("GROQ") or keys.get("OPENROUTER"))



# ------------------------------------------------------------------ v3.12: TEXT backup (Gemini limit khatam ho to)
_TMODELS = {}
TEXT_PREF = ("qwen3.8-27b", "qwen3.6-27b", "gpt-oss-120b", "gpt-oss-20b", "deepseek-v3", "deepseek-chat",
             "qwen3-235b", "qwen-2.5-72b", "llama-4-maverick", "gemma-3-27b", "mistral-small")


def text_models(prov, key):
    if prov in _TMODELS: return [m for m in _TMODELS[prov] if m not in _DEAD]
    out = []
    try:
        r = _session().get(PROVIDERS[prov]["base"] + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
        for m in r.json().get("data", []):
            mid = m.get("id", "")
            if prov == "OPENROUTER":
                pr = m.get("pricing") or {}
                free = mid.endswith(":free") or (str(pr.get("prompt", "1")) in ("0", "0.0")
                                                  and str(pr.get("completion", "1")) in ("0", "0.0"))
                if not free: continue
            if any(x in mid.lower() for x in ("whisper", "tts", "guard", "embed", "playai", "distil")): continue
            out.append(mid)
    except Exception as e:
        log(f"   ({prov} text models nahi mile: {e})", show=False)
    def rank(n):
        n = n.lower()
        for i, k in enumerate(TEXT_PREF):
            if k in n: return i
        return 99
    out.sort(key=rank)
    _TMODELS[prov] = out[:6]
    return _TMODELS[prov]


def ask_text(keys, prompt, json_mode=False, temperature=0.4, timeout=60):
    """Gemini na mile to Groq / OpenRouter (free) se jawab. Returns (text, naam) ya (None, None)."""
    rq = _session()
    for prov in ("GROQ", "OPENROUTER"):
        key = (keys or {}).get(prov)
        if not key: continue
        for mid in text_models(prov, key)[:4]:
            body = {"model": mid, "temperature": temperature, "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt + ("\n\nReply with valid JSON only." if json_mode else "")}]}
            if prov == "GROQ":
                ml = mid.lower()
                if "qwen3" in ml:
                    body["reasoning_effort"] = "none"
                elif "gpt-oss" in ml:
                    body["reasoning_effort"] = "low"
            try:
                r = rq.post(PROVIDERS[prov]["base"] + "/chat/completions", json=body, timeout=timeout,
                            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "VG Video Tool"})
                if r.status_code == 400 and "reasoning_effort" in body:
                    body.pop("reasoning_effort", None)
                    r = rq.post(PROVIDERS[prov]["base"] + "/chat/completions", json=body, timeout=timeout,
                                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "VG Video Tool"})
                if r.status_code in (400, 404, 422): _DEAD.add(mid); continue
                if r.status_code in (401, 403):
                    log(f"   {prov} key galat / band ({r.status_code})", show=False); break
                if r.status_code == 429: continue
                r.raise_for_status()
                txt = (r.json()["choices"][0]["message"].get("content") or "").strip()
                if not txt:
                    continue
                if txt and txt.strip():
                    return txt, f"{'Groq' if prov == 'GROQ' else 'OpenRouter'} ({mid.split('/')[-1][:30]})"
            except Exception as e:
                log(f"   ({prov} {mid}: {str(e)[:120]})", show=False)
    return None, None


def available(keys):
    return bool((keys or {}).get("GROQ") or (keys or {}).get("OPENROUTER"))
