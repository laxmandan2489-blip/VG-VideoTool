"""v2.19: AWAAZ KI LINE – Gemini na mile to doosri achhi awaaz (Microsoft se pehle).

Line (style.txt: awaaz_line = sarvam, google, kokoro):
  sarvam  – Sarvam Bulbul (Indian company, bahut natural Hindi). api keys.txt me  SARVAM = ...  (free credit milta hai)
  google  – Google Cloud TTS Chirp3-HD (billing wali key). api keys.txt me  GOOGLE_TTS = ...
  kokoro  – laptop pe FREE, koi limit nahi (pehli baar ~400 MB download)
Har line alag banti hai -> shabdon ka time pakka, koi line chhootti / repeat nahi hoti.
Returns (wav, sents, naam) ya None.
"""
import os, sys, re, json, base64, subprocess
import numpy as np
from pathlib import Path
from common import log, num, TOOL

KDIR = TOOL / "ai_aankh" / "kokoro"
KFILES = {"kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
          "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"}
NAMES = {"sarvam": "Sarvam (Bulbul)", "google": "Google Chirp", "kokoro": "Kokoro (free)"}
LAST = {"used": "", "why": []}
_K = {"obj": None}


def _clean(t):
    t = re.sub(r"\[[^\]]*\]|\|\|.*", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _to_wav(raw, path):
    """koi bhi audio bytes -> 44.1k mono wav (voice.SR)"""
    import voice
    tmp = Path(str(path) + ".in")
    tmp.write_bytes(raw)
    x = voice.load_wav(tmp)
    try: tmp.unlink()
    except Exception: pass
    return x


# ------------------------------------------------------------------ engines (ek line -> numpy 44.1k)
def sarvam_line(text, key, style, path):
    import requests
    body = {"text": text, "language_code": "hi-IN", "model": style.get("sarvam_model", "bulbul:v3"),
            "speaker": style.get("sarvam_awaaz", "aditya").lower(), "speech_sample_rate": 24000,
            "pace": float(num(style, "sarvam_speed", 0.6, 1.6)) if style.get("sarvam_speed") else 1.05}
    r = requests.post("https://api.sarvam.ai/text-to-speech", json=body, timeout=90,
                      headers={"api-subscription-key": key, "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"Sarvam {r.status_code}: {r.text[:160]}")
    aud = r.json().get("audios") or []
    if not aud:
        raise RuntimeError("Sarvam ne awaaz nahi di")
    return _to_wav(base64.b64decode("".join(aud)), path)


def google_line(text, key, style, path):
    import requests
    name = style.get("google_awaaz", "hi-IN-Chirp3-HD-Charon")
    body = {"input": {"text": text}, "voice": {"languageCode": "hi-IN", "name": name},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 24000}}
    r = requests.post("https://texttospeech.googleapis.com/v1/text:synthesize", params={"key": key}, json=body, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"Google TTS {r.status_code}: {r.text[:160]}")
    return _to_wav(base64.b64decode(r.json()["audioContent"]), path)


def kokoro_ready(install=True):
    """Kokoro install + model download (ek hi baar). True/False."""
    try:
        import kokoro_onnx  # noqa
    except Exception:
        if not install: return False
        log("   (pehli baar) Kokoro install ho raha hai...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "kokoro-onnx", "soundfile"],
                           capture_output=True, text=True, timeout=1500, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            log("   Kokoro install nahi hua: " + r.stderr[-200:], show=False); return False
    KDIR.mkdir(parents=True, exist_ok=True)
    for name, url in KFILES.items():
        fp = KDIR / name
        if fp.exists() and fp.stat().st_size > 1_000_000: continue
        if not install: return False
        try:
            import requests
            log(f"   (pehli baar) Kokoro model download: {name} ...")
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = fp.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for ch in r.iter_content(1 << 20): f.write(ch)
                tmp.replace(fp)
        except Exception as e:
            log(f"   Kokoro model download nahi hua: {e}", show=False); return False
    return True


def kokoro_line(text, style, path):
    if _K["obj"] is None:
        from kokoro_onnx import Kokoro
        _K["obj"] = Kokoro(str(KDIR / "kokoro-v1.0.onnx"), str(KDIR / "voices-v1.0.bin"))
    sp = float(num(style, "kokoro_speed", 0.7, 1.5)) if style.get("kokoro_speed") else 1.05
    samples, sr = _K["obj"].create(text, voice=style.get("kokoro_awaaz", "hm_omega"), speed=sp, lang="hi")
    import voice
    x = np.asarray(samples, dtype=np.float32)
    n = int(len(x) * voice.SR / sr)                       # 24k -> 44.1k
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


# ------------------------------------------------------------------ poori script
def make(engine, lines, style, work, keys):
    import voice
    if engine == "sarvam":
        key = keys.get("SARVAM")
        if not key: return None
        fn = lambda t, p: sarvam_line(t, key, style, p)
    elif engine == "google":
        key = keys.get("GOOGLETTS") or keys.get("GOOGLE_TTS")
        if not key: return None
        fn = lambda t, p: google_line(t, key, style, p)
    elif engine == "kokoro":
        if not kokoro_ready(): return None
        fn = lambda t, p: kokoro_line(t, style, p)
    else:
        return None
    gap = float(num(style, "line_gap", 0.05, 0.8)) if style.get("line_gap") else 0.16
    full, sents, t = [], [], 0.0
    sub = Path(work) / f"bk_{engine}"; sub.mkdir(parents=True, exist_ok=True)
    for i, line in enumerate(lines):
        text = _clean(line)
        if not text: continue
        x = None
        for attempt in range(2):
            try:
                x = fn(text, sub / f"l{i:02d}"); break
            except Exception as e:
                log(f"   {NAMES[engine]} line {i+1}: {str(e)[:120]}", show=False)
                if "401" in str(e) or "403" in str(e) or "quota" in str(e).lower() or "429" in str(e):
                    return None                                     # key/limit ki dikkat – agla engine
        if x is None or len(x) < voice.SR * 0.3:
            return None                                             # ek bhi line nahi bani -> poori awaaz badlo (mix nahi)
        thr = 0.012; idx = np.where(np.abs(x) > thr)[0]
        if len(idx): x = x[max(0, idx[0] - int(0.03 * voice.SR)): idx[-1] + int(0.08 * voice.SR)]
        d = len(x) / voice.SR
        sents.append({"text": line, "script": line, "start": t, "end": t + d, "words": voice.spread_words(line, t, t + d)})
        full += [x, np.zeros(int(gap * voice.SR), np.float32)]
        t += d + gap
        log(f"   {NAMES[engine]}: line {len(sents)}/{len(lines)} ✓", show=False)
    if not sents: return None
    wav = Path(work) / "voice.wav"
    a = np.concatenate(full)
    a = a / max(1e-6, float(np.abs(a).max())) * 0.89
    voice.save_wav(wav, a)
    if engine == "kokoro": voice.warm_voice(wav, style)
    return wav, sents


def order(style, keys):
    raw = style.get("awaaz_line", "sarvam, google, kokoro")
    out = []
    for e in re.split(r"[,\s>]+", raw.lower()):
        e = e.strip()
        if e in NAMES and e not in out: out.append(e)
    return out


def backup_voice(lines, style, work, keys, only=None):
    LAST["used"] = ""; LAST["why"] = []
    for e in ([only] if only else order(style, keys)):
        if e == "sarvam" and not keys.get("SARVAM"): LAST["why"].append("Sarvam key nahi"); continue
        if e == "google" and not (keys.get("GOOGLETTS") or keys.get("GOOGLE_TTS")): LAST["why"].append("Google TTS key nahi"); continue
        log(f"   🎙️ {NAMES[e]} awaaz bana raha hoon...")
        try:
            r = make(e, lines, style, work, keys)
        except Exception as ex:
            log(f"   {NAMES[e]} nahi chali: {str(ex)[:150]}"); r = None
        if r:
            LAST["used"] = e
            log(f"   ✓ {NAMES[e]} ki awaaz bani")
            return r[0], r[1], NAMES[e]
        LAST["why"].append(f"{NAMES[e]} nahi chali")
    return None
