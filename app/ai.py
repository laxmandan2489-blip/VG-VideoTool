"""Gemini helper (free key): text / JSON / photo dekhna. Sab jagah yahi use hota hai."""
import json, re, time, base64
import requests
from common import log

# v2.10: Google model naam badalta rehta hai -> list API se khud pata karo kaunse chal rahe hain
FALLBACK = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.8-flash-lite", "gemini-flash-lite-latest"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
_models = {}
_dead = set()


# v3.16 (log 16 Nov: har video me 6-8 model dobara "aaj ki limit khatam" – har baar 1-2 sec + backup late):
# jis model ki AAJ ki limit khatam ho chuki, wo baat file me yaad rehti hai (Google ki limit Pacific raat 12 baje
# reset hoti hai = India me ~1:30 PM). Agli video us model ko poochhti hi nahi.
def _pt_day():
    import datetime as _dt
    return (_dt.datetime.utcnow() - _dt.timedelta(hours=8)).strftime("%Y-%m-%d")


def _qfile():
    try:
        from common import TOOL
        return TOOL / "temp" / "gemini_quota_today.json"
    except Exception:
        return None


def _quota_load():
    f = _qfile()
    try:
        if f and f.exists():
            j = json.loads(f.read_text(encoding="utf-8"))
            if j.get("day") == _pt_day():
                _dead.update(j.get("dead") or [])
    except Exception:
        pass


def _quota_mark(model):
    f = _qfile()
    if not f: return
    try:
        j = {}
        if f.exists():
            j = json.loads(f.read_text(encoding="utf-8"))
        if j.get("day") != _pt_day(): j = {"day": _pt_day(), "dead": []}
        if model not in j["dead"]: j["dead"].append(model)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(j), encoding="utf-8")
    except Exception:
        pass


_quota_load()


def _ver(name):
    import re as _re
    m = _re.search(r"(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def models(key, kind="text"):
    """Chalu models ki list (sabse naya pehle). kind = text / tts."""
    if kind in _models:
        return [m for m in _models[kind] if m not in _dead]
    found = []
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key, "pageSize": 200},
                         headers={"x-goog-api-key": key}, timeout=30)
        for m in r.json().get("models", []):
            n = m.get("name", "").split("/")[-1]
            if "generateContent" not in (m.get("supportedGenerationMethods") or []): continue
            if kind == "tts":
                if "tts" in n: found.append(n)
            else:
                if "flash" not in n or any(x in n for x in ("tts", "image", "live", "audio", "embedding", "thinking")):
                    continue
                found.append(n)
    except Exception as e:
        log(f"  gemini model list nahi mili: {e}", show=False)
    if kind == "text":
        # naya pehle; 'lite' aur 'preview/exp' peeche (backup)
        found.sort(key=lambda n: (("lite" in n), ("preview" in n or "exp" in n), -_ver(n)))
        found += [m for m in FALLBACK if m not in found]
    else:
        found.sort(key=lambda n: ("pro" in n, -_ver(n)))
    _models[kind] = found
    log(f"  gemini models ({kind}): {', '.join(found[:5])}", show=False)
    return [m for m in found if m not in _dead]


def _post(key, model, body, timeout=90):
    return requests.post(URL.format(m=model), headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                         params={"key": key}, json=body, timeout=timeout)


BUSY = {"flag": False}
MAX_TRY = {"n": 3}
QUOTA = {"out": False}         # v2.17c: aaj ki free limit khatam – baaki kaam bina Gemini, jaldi             # v2.15b: Gemini ko ek kaam ke liye max kitni baar poochhe (style: gemini_try)
DOWN = {"until": 0.0}          # v2.14: Gemini band mila -> 10 min tak chhote kaam jaldi aage badhein


BACKUP = {"keys": {}, "used": None, "n": 0}
TIMEOUTS = {"n": 0, "t": 0.0}      # v3.15: Gemini timeout circuit-breaker   # v3.12: make_video read_keys() yahan daalta hai (GROQ / OPENROUTER)


def ask(key, parts, json_mode=False, search=False, temperature=0.7, timeout=120, tries=3, budget=300):
    """v3.12: pehle Gemini; limit khatam / busy / timeout -> Groq ya OpenRouter (free) backup."""
    r = _ask_gemini(key, parts, json_mode, search, temperature, timeout, tries, budget)
    if r: return r
    bk = BACKUP["keys"]
    if not (bk.get("GROQ") or bk.get("OPENROUTER")):
        return None
    try:
        import free_ai
        texts = [p for p in parts if isinstance(p, str)]
        imgs = [p["jpg"] for p in parts if isinstance(p, dict) and "jpg" in p]
        if any(isinstance(p, dict) and ("wav" in p or "mp4" in p) for p in parts):
            return None                              # awaaz / poori video sirf Gemini samajhta hai
        prompt = "\n".join(texts)
        if imgs:
            txt, who = free_ai.ask_vision(bk, prompt + ("\nReply with JSON only." if json_mode else ""), imgs)
        else:
            txt, who = free_ai.ask_text(bk, prompt, json_mode=json_mode, temperature=min(temperature, 0.7))
        if txt:
            BACKUP["n"] += 1
            if BACKUP["used"] != who:
                BACKUP["used"] = who; log(f"   🔁 Gemini nahi mila – backup AI se kaam: {who}")
            return txt
    except Exception as e:
        log(f"   (backup AI fail: {str(e)[:120]})", show=False)
    return None


def _ask_gemini(key, parts, json_mode=False, search=False, temperature=0.7, timeout=120, tries=3, budget=300):
    """v2.11: parts: list of str or {"jpg": bytes}. Returns text or None.
    Busy (503/429) ho to RUKTA NAHI – turant agla model. Saare busy -> thoda ruk ke agla round.
    `budget` second tak koshish (quality ke liye sabr, lekin ghante bhar nahi)."""
    if not key or QUOTA["out"]:
        return None
    import re as _re
    pp = []
    for p in parts:
        if isinstance(p, dict) and "jpg" in p:
            pp.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(p["jpg"]).decode()}})
        elif isinstance(p, dict) and "wav" in p:                       # v2.16: Gemini awaaz sune
            pp.append({"inline_data": {"mime_type": "audio/wav", "data": base64.b64encode(p["wav"]).decode()}})
        elif isinstance(p, dict) and "mp4" in p:                       # v2.16: Gemini poori video dekhe
            pp.append({"inline_data": {"mime_type": "video/mp4", "data": base64.b64encode(p["mp4"]).decode()}})
        else:
            pp.append({"text": str(p)})
    cfg = {"temperature": temperature}
    if json_mode and not search:
        cfg["responseMimeType"] = "application/json"
    body = {"contents": [{"parts": pp}], "generationConfig": cfg}
    if search:
        body["tools"] = [{"google_search": {}}]
    if time.time() < DOWN["until"]:
        budget = min(budget, 25)                      # abhi-abhi band mila tha – lamba intezaar mat karo
    # v3.15 (log 15 Nov: Gemini ke 10+ timeout, har ek 25-180 sec -> video 58 min): 10 min me 3 timeout ->
    # agle 10 min Gemini ko poochho hi mat (seedha backup AI / offline) – video atke nahi
    if TIMEOUTS["n"] >= 3 and time.time() - TIMEOUTS["t"] < 600:
        return None
    deadline = time.time() + budget
    rnd = 0; calls = 0
    while time.time() < deadline and calls < MAX_TRY["n"]:          # v2.15b: sirf 2-3 koshish, phir aage
        rnd += 1
        busy_round = True
        for model in models(key)[:3]:
            left = deadline - time.time()
            if left < 10 or calls >= MAX_TRY["n"]: break
            calls += 1
            try:
                r = _post(key, model, body, min(timeout, max(20, left)))
            except Exception as e:
                log(f"  gemini {model} error: {str(e)[:120]}", show=False)
                if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                    if time.time() - TIMEOUTS["t"] > 600: TIMEOUTS["n"] = 0
                    TIMEOUTS["n"] += 1; TIMEOUTS["t"] = time.time()
                    if TIMEOUTS["n"] == 3:
                        log("   ⚠️ Gemini baar-baar timeout – agle 10 min backup AI / offline se kaam (video nahi rukegi)")
                    # v3.5 FIX ("footage 9/10 pe atki"): ek timeout = 2 min. Ab agle 5 min chhote intezaar (25 sec)
                    DOWN["until"] = time.time() + 300
                    deadline = min(deadline, time.time() + 25)
                continue      # timeout -> agla model
            if r.status_code in (429, 500, 503):
                if r.status_code == 429 and re.search(r"quota|RESOURCE_EXHAUSTED|PerDay", r.text or "", re.I) and \
                        re.search(r"per ?day|PerDay|daily", r.text or "", re.I):
                    _dead.add(model); _quota_mark(model)      # v2.17c / v3.16: aaj ki limit – yaad bhi rakho
                    log(f"  gemini {model}: aaj ki limit khatam (quota)", show=False)
                    if not [m for m in models(key)[:3] if m not in _dead]:
                        QUOTA["out"] = True; break
                    continue
                log(f"  gemini {model}: {r.status_code} busy", show=False); continue
            busy_round = False
            if r.status_code == 404:
                _dead.add(model); calls -= 1                  # purana model naam – ginti me nahi
                hint = _re.search(r"use models/([\w.\-]+)", r.text)
                if hint and hint.group(1) not in _models.get("text", []):
                    _models.setdefault("text", []).insert(0, hint.group(1))
                continue
            if r.status_code != 200:
                log(f"  gemini {model}: {r.status_code} {r.text[:300]}", show=False); continue
            try:
                c = r.json().get("candidates") or []
                txt = "".join(x.get("text", "") for x in c[0].get("content", {}).get("parts", [])) if c else ""
            except Exception:
                txt = ""
            if txt.strip():
                BUSY["flag"] = False; DOWN["until"] = 0.0; TIMEOUTS["n"] = 0
                return txt
            log(f"  gemini {model}: khaali jawab", show=False)
        if not busy_round:
            break                                     # busy nahi tha, asli galti – dobara se fayda nahi
        if calls >= MAX_TRY["n"]: break
        wait = min(8, max(0, deadline - time.time() - 10))
        if wait <= 0: break
        log(f"   ⏳ Gemini busy hai, {int(wait)} sec me dobara try (round {rnd})")
        time.sleep(wait)
    BUSY["flag"] = True
    if budget >= 60:
        DOWN["until"] = time.time() + 600
    return None


def parse_json(txt):
    """Gemini ke jawab se JSON nikaalo (```json fences / extra text ho tab bhi)."""
    if not txt:
        return None
    t = re.sub(r"```(?:json)?", "", txt).strip()
    for a, b in (("{", "}"), ("[", "]")):
        i, j = t.find(a), t.rfind(b)
        if i != -1 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                continue
    return None


def ask_json(key, parts, search=False, temperature=0.7, timeout=90, budget=300):
    return parse_json(ask(key, parts, json_mode=True, search=search, temperature=temperature, timeout=timeout,
                          budget=budget))


def image_models(key):
    """v2.15: Gemini ki photo banane wali models (jaise ...flash-image). Free key pe kabhi-kabhi band hoti hain."""
    if "image" in _models:
        return [m for m in _models["image"] if m not in _dead]
    found = []
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": key, "pageSize": 200},
                         headers={"x-goog-api-key": key}, timeout=30)
        for m in r.json().get("models", []):
            n = m.get("name", "").split("/")[-1]
            if "generateContent" in (m.get("supportedGenerationMethods") or []) and "image" in n and "imagen" not in n:
                found.append(n)
    except Exception:
        pass
    found.sort(key=lambda n: (("preview" in n or "exp" in n), -_ver(n)))
    for m in ("gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"):
        if m not in found: found.append(m)
    _models["image"] = found
    return found


def make_image(key, prompt, aspect="9:16", ref_jpg=None, timeout=120):
    """Gemini se photo banao -> jpg/png bytes ya None. ref_jpg = asli footage ka frame (usi jaisa banaye)."""
    if not key:
        return None
    parts = [{"text": prompt}]
    if ref_jpg:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(ref_jpg).decode()}})
    for model in image_models(key)[:3]:
        for cfg in ({"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}},
                    {"responseModalities": ["TEXT", "IMAGE"]}):
            try:
                r = _post(key, model, {"contents": [{"parts": parts}], "generationConfig": cfg}, timeout)
            except Exception as e:
                log(f"  gemini image {model}: {str(e)[:100]}", show=False); break
            if r.status_code == 400:
                continue                                  # ye config nahi chalti – doosri try
            if r.status_code != 200:
                log(f"  gemini image {model}: {r.status_code} {r.text[:160]}", show=False); break
            try:
                for c in r.json().get("candidates") or []:
                    for p in c.get("content", {}).get("parts", []):
                        d = p.get("inlineData") or p.get("inline_data")
                        if d and d.get("data"):
                            return base64.b64decode(d["data"])
            except Exception:
                pass
            break
    return None
