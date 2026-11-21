"""v2.16: Reel / video se SOUND EFFECTS nikaalo (whoosh, boom, ding, pop, riser...) aur mere_sounds me rakho.

Kaise:
 1. (agar ho sake) AI se bolne wali awaaz alag (Demucs) – warna Whisper ka VAD se jahan koi bol raha hai wo hissa chhodo
 2. Tez, chhote "dhamake" (onset) dhoondho, har ek ka tukda kaato
 3. Pehchaano kis type ka hai – Gemini sunta hai (ya free andaza: lambai, bass, tone se)
 4. Ek jaise tukde ek hi baar, ghatiya (bolna/music) hata do
 5. VideoTool\\mere_sounds\\<type>\\auto_....wav  me save -> agli videos me apne-aap lagenge
"""
import io, sys, json, wave, datetime, subprocess
import numpy as np
from pathlib import Path
from common import TOOL, log, yes

SR = 44100
CATS = ["whoosh", "boom", "ding", "pop", "click", "riser", "glitch", "cash", "typing", "wrong", "flash"]
MEM = TOOL / "seekha"


def _load(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[-300:])
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def _save(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def _wav_bytes(x, sr=16000):
    from_sr = SR
    if sr != from_sr:
        n = int(len(x) * sr / from_sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return b.getvalue()


# ------------------------------------------------------------------ awaaz alag karna
def separate(path, work):
    """Demucs (AI) se bolne wali awaaz + music ka bass hatao -> sirf 'drums + other' (yahin effects hote hain).
    numpy array (44.1k mono) ya None."""
    flag = MEM / "demucs_nahi_chala.txt"
    if flag.exists():
        return None                                      # pehle fail hua tha – baar-baar install mat karo
    def _fail(msg):
        MEM.mkdir(parents=True, exist_ok=True); flag.write_text(str(msg)[-1500:], encoding="utf-8")
        log(f"   awaaz alag karne wali AI nahi chali – bina iske karta hoon ({str(msg)[-150:]})", show=False)
        return None
    try:
        import demucs.pretrained  # noqa
    except Exception:
        log("   (pehli baar) awaaz alag karne wali AI (Demucs) install ho rahi hai – ~600 MB, 5-10 min, ek hi baar...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "demucs", "torch<2.9", "torchaudio<2.9"],
                           capture_output=True, text=True, timeout=3000, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            return _fail(r.stderr)
    try:
        import torch
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        log("   bolne wali awaaz alag kar raha hoon (Demucs, 1-4 min)...")
        m = get_model("htdemucs"); m.eval()
        x = _load(path, m.samplerate)
        x = x[: int(m.samplerate * 180)]                 # 3 min tak
        wav = torch.from_numpy(np.stack([x, x])).float()
        ref = wav.mean(0); mu, sd = ref.mean(), ref.std() + 1e-8
        with torch.no_grad():
            out = apply_model(m, ((wav - mu) / sd)[None], device="cpu", split=True, overlap=0.25, progress=False)[0]
        out = out * sd + mu
        keep = [k for k, n in enumerate(m.sources) if n in ("drums", "other")]
        y = out[keep].sum(0).mean(0).numpy().astype(np.float32)
        if m.samplerate != SR:
            y = np.interp(np.linspace(0, len(y) - 1, int(len(y) * SR / m.samplerate)), np.arange(len(y)), y).astype(np.float32)
        return y
    except Exception as e:
        return _fail(e)


def speech_mask(x):
    """True = yahan koi bol raha hai (Whisper ka VAD). None agar VAD nahi chala."""
    try:
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        x16 = np.interp(np.linspace(0, len(x) - 1, int(len(x) * 16000 / SR)), np.arange(len(x)), x).astype(np.float32)
        ts = get_speech_timestamps(x16, VadOptions(min_silence_duration_ms=150, speech_pad_ms=60))
        m = np.zeros(len(x), dtype=bool)
        for t in ts:
            a = int(t["start"] * SR / 16000); b = int(t["end"] * SR / 16000); m[a:b] = True
        return m
    except Exception as e:
        log(f"   (VAD nahi chala: {e})", show=False); return None


# ------------------------------------------------------------------ dhamake dhoondhna
def _env(x, hop):
    n = len(x) // hop
    return np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)


def onsets(x, hop=256):
    """Awaaz achaanak tez hui (8 dB+) aur shor se kaafi upar -> wahan ek effect shuru hua."""
    env = _env(x, hop)
    n = len(env)
    if n < 20: return [], env
    db = 20 * np.log10(env + 1e-9)
    floor = np.percentile(db, 30)
    back = int(0.25 * SR / hop)
    out = []; last = -99
    for i in range(back, n - 2):
        if i - last < int(0.2 * SR / hop): continue
        prev = db[i - back:i].min()
        if db[i] - prev > 8 and db[i] > floor + 12 and db[i] >= db[i - 1]:
            # chadhaav ka sabse tez point tak le jao
            k = i
            while k + 1 < n and db[k + 1] > db[k] and k - i < int(0.08 * SR / hop): k += 1
            start = i
            while start > 0 and db[start - 1] > prev + 3 and i - start < back: start -= 1
            out.append(start * hop); last = k
    return out, env


def cut(x, s0, env, hop=256, maxlen=2.5):
    a = max(0, s0 - int(0.03 * SR))
    i0 = s0 // hop
    seg = env[i0:i0 + int(maxlen * SR / hop)]
    if len(seg) < 3: return None
    pk = int(np.argmax(seg[:int(0.4 * SR / hop)] if len(seg) > int(0.4 * SR / hop) else seg)); peak = seg[pk]
    end = len(seg)
    quiet = 0
    for k in range(pk, len(seg)):
        quiet = quiet + 1 if seg[k] < peak * 0.08 else 0
        if quiet * hop >= 0.05 * SR:
            end = k; break
    b = min(len(x), (i0 + end) * hop + int(0.03 * SR))
    if b - a < 0.06 * SR: return None
    y = x[a:b].copy()
    f = min(len(y) // 4, int(0.03 * SR)); y[-f:] *= np.linspace(1, 0, f)
    y[:64] *= np.linspace(0, 1, 64)
    return a, y


def riser_before(x, s0, env, hop=256):
    """Dhamake se pehle 0.8-2.5 sec tak awaaz lagaataar badhti rahi? -> riser."""
    i0 = s0 // hop
    for L in (2.0, 1.4, 0.9):
        k = int(L * SR / hop)
        if i0 - k < 0: continue
        seg = env[i0 - k:i0]
        q = [seg[j * k // 4:(j + 1) * k // 4].mean() for j in range(4)]
        if all(q[j + 1] > q[j] * 1.25 for j in range(3)) and q[3] > q[0] * 3:
            a = s0 - int(L * SR)
            y = x[a:s0 + int(0.05 * SR)].copy()
            y[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
            return a, y
    return None


def features(y):
    spec = np.abs(np.fft.rfft(y[:min(len(y), SR)] * np.hanning(min(len(y), SR)))) ** 2 + 1e-12   # power
    fr = np.fft.rfftfreq(min(len(y), SR), 1 / SR)
    cen = float((spec * fr).sum() / spec.sum())
    low = float(spec[fr < 200].sum() / spec.sum())
    flat = float(np.exp(np.mean(np.log(spec))) / np.mean(spec))
    bands = np.array([spec[(fr >= lo) & (fr < lo * 1.6)].sum() for lo in np.geomspace(40, 15000, 24)])
    vec = 10 * np.log10(bands / (bands.max() + 1e-12) + 1e-6) + 60; vec = np.clip(vec, 0, None)
    vec = vec / (np.linalg.norm(vec) + 1e-9)
    q = np.array_split(np.abs(y), 3); qm = [float(np.sqrt(np.mean(z ** 2)) + 1e-9) for z in q]
    return {"dur": len(y) / SR, "cen": cen, "low": low, "flat": flat, "vec": vec, "rise": qm[2] / qm[0]}


def guess(f, is_riser=False):
    if is_riser or (f["dur"] > 0.8 and f.get("rise", 1) > 3): return "riser"
    if f["dur"] < 0.16: return "click" if f["cen"] > 3000 else "pop"
    if f["low"] > 0.40 and f["dur"] > 0.25: return "boom"
    if f["flat"] < 0.02 and f["cen"] > 700: return "ding"
    if f["flat"] > 0.10 and f["dur"] < 1.8: return "whoosh"
    if f["cen"] > 2500: return "glitch"
    return "whoosh"


def gemini_label(key, clips):
    if not key or not clips: return None
    try:
        from ai import ask_json
        parts = ["You are a sound designer. Each numbered clip was cut from a short video. Label each one with ONE type: "
                 + ", ".join(CATS) + ", or 'bekaar' if it is mostly speech, a song/music, noise or a bad cut. "
                 "whoosh=swish/swoosh transition, boom=deep hit/impact, ding=bell/notification, pop=bubble pop, "
                 "click=mouse/camera click, riser=rising tension build, glitch=digital glitch, cash=cash register/coins, "
                 "typing=keyboard, wrong=error buzzer, flash=camera flash/shutter.\n"
                 'Return ONLY JSON: {"clips": [{"clip": number, "type": "..."}]}']
        for i, y in enumerate(clips):
            parts += [f"Clip {i}:", {"wav": _wav_bytes(y[:int(2.5 * SR)])}]
        r = ask_json(key, parts, temperature=0.0, timeout=90, budget=120) or {}
        out = {}
        for c in r.get("clips") or []:
            try:
                i = int(c["clip"]); t = str(c["type"]).lower().strip()
                if 0 <= i < len(clips) and (t in CATS or t == "bekaar"): out[i] = t
            except Exception:
                continue
        return out or None
    except Exception as e:
        log(f"   (Gemini sound label skip: {e})", show=False); return None


def extract(video, key, work, style=None, maxn=15):
    """Returns list [{n, type, file, dur}] (saved files)."""
    style = style or {}
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    x = _load(video)
    if len(x) < SR:
        return []
    src = x; mask = None
    if yes(style.get("sfx_alag_ai", "haan")):
        nv = separate(video, work)
        if nv is not None and len(nv) > SR:
            src = nv; log("   bolne wali awaaz alag ho gayi ✓")
    if src is x:
        mask = speech_mask(x)
        if mask is not None and mask.mean() > 0.85:
            log("   ⚠️ Is reel me lagaataar koi bol raha hai aur awaaz alag karne wali AI nahi chali – "
                "sirf saaf (chup wale) hisson se sound nikaal raha hoon, kam milenge.")
    ons, env = onsets(src)
    log(f"   {len(ons)} dhamake mile, chhaant raha hoon...")
    cands = []
    for s0 in ons:
        r = riser_before(src, s0, env)
        if r and not (mask is not None and mask[r[0]:s0].mean() > 0.3):
            cands.append((r[0], r[1], True))
        c = cut(src, s0, env)
        if not c: continue
        a, y = c
        if mask is not None and mask[a:a + len(y)].mean() > 0.25:
            continue                                    # koi bol raha tha – tukda ganda hoga
        cands.append((a, y, False))
    # sabse tez pehle, ek jaise hatao
    cands.sort(key=lambda c: -float(np.abs(c[1]).max()))
    keep = []; vecs = []
    for a, y, rs in cands:
        if np.abs(y).max() < 0.03: continue
        if any(min(a + len(y), a2 + len(y2)) - max(a, a2) > 0.5 * min(len(y), len(y2)) for a2, y2, _, _ in keep):
            continue                                    # ek hi jagah ke do tukde – ek kaafi
        f = features(y)
        if any(float(f["vec"] @ v) > 0.995 and abs(f["dur"] - d) < 0.3 * max(f["dur"], d) for v, d in vecs): continue
        vecs.append((f["vec"], f["dur"])); keep.append((a, y, rs, f))
        if len(keep) >= maxn + 6: break
    if not keep:
        return []
    labels = gemini_label(key, [k[1] for k in keep])
    stamp = datetime.datetime.now().strftime("%y%m%d_%H%M")
    out = []
    for i, (a, y, rs, f) in enumerate(keep):
        t = (labels or {}).get(i) or guess(f, rs)
        if t == "bekaar": continue
        y = y / (np.abs(y).max() + 1e-9) * 0.9
        d = TOOL / "mere_sounds" / t; d.mkdir(parents=True, exist_ok=True)
        p = d / f"auto_{stamp}_{len(out)+1:02d}.wav"
        _save(p, y)
        out.append({"n": len(out) + 1, "type": t, "file": str(p), "dur": round(f["dur"], 2), "at": round(a / SR, 2)})
        if len(out) >= maxn: break
    MEM.mkdir(parents=True, exist_ok=True)
    (MEM / "last_sounds.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def preview(sounds, out):
    """Saare nikle sound ek file me (beech me 0.6 sec chup) – phone pe sun lo."""
    gap = np.zeros(int(0.6 * SR), np.float32); parts = []
    for s in sounds:
        try:
            parts += [_load(s["file"]), gap]
        except Exception:
            continue
    if not parts: return None
    wav = Path(out).with_suffix(".wav"); _save(wav, np.concatenate(parts))
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "128k",
                        str(out)], capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
        return Path(out) if Path(out).exists() else wav
    except Exception:
        return wav


def remove(nums):
    """/hatao 3 5 -> pichhli baar ke sound 3 aur 5 hatao."""
    f = MEM / "last_sounds.json"
    if not f.exists(): return []
    lst = json.loads(f.read_text(encoding="utf-8")); gone = []
    for s in lst:
        if s["n"] in nums and Path(s["file"]).exists():
            try: Path(s["file"]).unlink(); gone.append(s)
            except Exception: pass
    return gone
