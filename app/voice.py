"""Voice: AI (edge-tts) or user's own recording (faster-whisper).

Output of both modes:
    wav path (44.1k mono), and a list of sentences:
    [{"text": str, "start": s, "end": e, "words": [{"w": str, "start": s, "end": e}, ...]}]
"""
import asyncio, re, difflib
import numpy as np
from pathlib import Path
from common import log, fail, run, duration, num, yes, TOOL

SR = 44100
VOICES = {"madhur": "hi-IN-MadhurNeural", "swara": "hi-IN-SwaraNeural"}


def load_wav(path):
    """Decode any audio to float32 mono 44.1k via ffmpeg."""
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="replace")[-400:])
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def save_wav(path, x):
    import wave
    x = np.clip(np.asarray(x, dtype=np.float32), -1, 1)
    ch = 2 if (x.ndim == 2 and x.shape[1] == 2) else 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def _snap_silence(x, t_sec, search_ms=260):
    """v3.20: Snap splice cut to quietest 25ms valley so adjacent words are never clipped."""
    n = len(x)
    if n < int(0.1 * SR):
        return t_sec
    c = int(max(0, min(n - 1, t_sec * SR)))
    rad = int(search_ms * SR / 1000)
    win = max(64, int(0.025 * SR))
    lo, hi = max(0, c - rad), min(n - win, c + rad)
    if hi <= lo:
        return t_sec
    best_i, best_e = c, float("inf")
    step = max(32, win // 4)
    for idx in range(lo, hi, step):
        seg = x[idx:idx + win]
        e = float(np.mean(seg * seg))
        if e < best_e:
            best_e, best_i = e, idx + win // 2
    return best_i / SR


def edge_fade(x, ms=12):
    """v3.1: kate hue awaaz ke tukde ke dono kinare pe chhota fade – 'tik/chatak' awaaz nahi aayegi."""
    x = np.asarray(x, dtype=np.float32).copy()
    k = min(len(x) // 2, int(SR * ms / 1000))
    if k > 1:
        r = np.linspace(0, 1, k, dtype=np.float32)
        x[:k] *= r; x[-k:] *= r[::-1]
    return x


def split_words(text):
    return [w for w in re.split(r"\s+", text.strip()) if w]


def spread_words(text, start, end):
    """Fallback: share time between words by length."""
    words = split_words(text)
    if not words:
        return []
    lens = [max(2, len(w)) for w in words]
    tot = sum(lens); t = start; out = []
    for w, L in zip(words, lens):
        d = (end - start) * L / tot
        out.append({"w": w, "start": t, "end": t + d}); t += d
    return out


# ------------------------------------------------------------------ AI voice
async def _tts_one(text, voice, rate, mp3, pitch="+0Hz"):
    import edge_tts
    words = []
    try:
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:
        com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / 1e7
                words.append({"w": ch["text"], "start": s, "end": s + ch["duration"] / 1e7})
    return words


def ai_voice(lines, style, work):
    voice = VOICES.get(style.get("ai_awaaz", "madhur"), VOICES["madhur"])
    sp = int(num(style, "ai_speed", -50, 50))
    rate = f"{sp:+d}%"
    pitch = f"-{int(num(style, 'awaaz_bhaari', 0, 15))}Hz"
    gap = 0.12  # small breath between sentences
    full = []; sents = []; t = 0.0
    for i, text in enumerate(lines):
        mp3 = work / f"tts_{i:02d}.mp3"
        words = None
        for attempt in range(3):
            try:
                words = asyncio.run(_tts_one(text, voice, rate, mp3, pitch))
                if mp3.exists() and mp3.stat().st_size > 1000:
                    break
            except Exception as e:
                log(f"  AI awaaz dobara try... ({e})", show=attempt == 2)
        if not mp3.exists() or mp3.stat().st_size < 1000:
            fail("AI awaaz nahi ban payi. Internet check karo. Ya style.txt me voice = meri karke apni recording use karo.")
        x = load_wav(mp3)
        # trim leading/trailing silence
        thr = 0.01; idx = np.where(np.abs(x) > thr)[0]
        lead = 0
        if len(idx):
            lead = max(0, idx[0] - int(0.03 * SR)); x = x[lead: idx[-1] + int(0.06 * SR)]
        d = len(x) / SR
        if words:
            ws = []
            for w in words:
                s = max(0, w["start"] - lead / SR); e = min(d, w["end"] - lead / SR)
                ws.append({"w": w["w"], "start": t + s, "end": t + max(e, s + 0.08)})
            # if engine returned wrong count, fall back
            if abs(len(ws) - len(split_words(text))) > max(2, len(ws) // 3):
                ws = spread_words(text, t, t + d)
        else:
            ws = spread_words(text, t, t + d)
        sents.append({"text": text, "start": t, "end": t + d, "words": ws})
        full.append(x); full.append(np.zeros(int(gap * SR), np.float32))
        t += d + gap
        log(f"  awaaz: line {i+1}/{len(lines)} ✓")
    audio = np.concatenate(full)
    wav = work / "voice.wav"; save_wav(wav, audio)
    warm_voice(wav, style)
    return wav, sents


def warm_voice(wav, style):
    """Make AI voice fuller/deeper: bass + presence + compression."""
    g = num(style, "awaaz_bhaari", 0, 15)
    if g <= 0:
        return
    tmp = wav.with_name("voice_warm.wav")
    af = (f"bass=g={min(9, g*0.75):.1f}:f=110,equalizer=f=250:t=q:w=1:g={min(3, g*0.25):.1f},"
          "equalizer=f=3000:t=q:w=1.2:g=2.5,"
          "dynaudnorm=f=150:g=11:p=0.90:m=6.0,"
          "acompressor=threshold=-22dB:ratio=3.0:attack=5:release=80:makeup=2.0,"
          "alimiter=limit=0.93:attack=3:release=60:level=disabled")   # v3.21: steady voice volume across entire video   # v3.5: bass+makeup ke baad 16-bit clipping nahi
    try:
        run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-af", af, "-ar", str(SR), "-ac", "1", tmp])
        tmp.replace(wav)
    except Exception as e:
        log(f"  awaaz warm nahi hui ({e})", show=False)


# ------------------------------------------------------------------ Gemini voice
_ALL = ("Zephyr Puck Charon Kore Fenrir Leda Orus Aoede Callirrhoe Autonoe Enceladus Iapetus Umbriel Algieba "
        "Despina Erinome Algenib Rasalgethi Laomedeia Achernar Alnilam Schedar Gacrux Pulcherrima Achird "
        "Zubenelgenubi Vindemiatrix Sadachbia Sadaltager Sulafat").split()
GEMINI_VOICES = {v.lower(): v for v in _ALL}                   # v2.10: saari 30 awaazein
DEEP_MALE = ["Charon", "Orus", "Algenib", "Alnilam", "Iapetus", "Fenrir", "Rasalgethi", "Sadaltager", "Schedar",
             "Enceladus"]
DEFAULT_NOTE = ("Deep, heavy, serious male Hindi narrator with full chest resonance - not soft, not sweet, "
                "not whispery. Confident and gripping documentary tone, stresses key words and numbers, "
                "medium-fast pace, clear Hindi pronunciation, short natural pause between lines.")


def tts_prompt(note, text, strict_plain=False):
    """v3.96: Topic-neutral verbatim TTS prompt (no 'science fact channel' bias or markdown headings that cause hallucination)."""
    if strict_plain:
        return ("Read the following Hindi script aloud verbatim, word for word. "
                "Do not change the topic or add any extra words:\n\n" + text.strip())
    return ("Read the following Hindi script aloud word for word in this voice style: " + note.strip() +
            "\nSpeak ONLY the exact lines below. Do not improvise, change the topic, translate, or add extra words:\n\n"
            + text.strip())


def _tts_models(key):
    """v3.91: Prefer latest Gemini 3.8 Flash TTS / Flash-Lite TTS first, then live-discovered TTS models."""
    try:
        import ai
        ms = ai.models(key, "tts")
    except Exception:
        ms = []
    preferred = ("gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts",
                 "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts",
                 "gemini-2.5-pro-preview-tts")
    # Put discovered newer 3.x/4.x TTS models first, then preferred list without duplicates
    ordered = [m for m in ms if "tts" in m.lower()]
    for m in preferred:
        if m not in ordered:
            ordered.append(m)
    return ordered


def _gemini_key_pool(primary_key):
    """v3.93: Multi-key rotation supporting comma-separated GEMINI_KEY (key1,key2,key3) + GEMINI_KEY_2/3/4."""
    import os
    keys = []
    for raw in (primary_key, os.environ.get("GEMINI_KEY_2"), os.environ.get("GEMINI_KEY_3"),
                os.environ.get("GEMINI_KEY_4")):
        for k in str(raw or "").split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


TTS_BUSY = {"flag": False}
TTS_QUOTA = {"out": False}


def gemini_tts_raw(key, text, vname, timeout=180):
    """v3.91: Gemini TTS -> (pcm bytes, mime) ya (None, None). Tries latest 3.8 TTS models + backup keys."""
    import requests, base64, time
    TTS_BUSY["flag"] = False
    TTS_QUOTA["out"] = False
    busy_only = True
    key_pool = _gemini_key_pool(key)
    for ki, k_cur in enumerate(key_pool):
        models = _tts_models(k_cur)[:4]
        for model in models:
            for attempt in range(2):
                try:
                    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                      params={"key": k_cur}, headers={"x-goog-api-key": k_cur}, timeout=timeout, json={
                                          "contents": [{"parts": [{"text": text}]}],
                                          "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
                                              "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": vname}}}}})
                    if r.status_code == 429 and re.search(r"PerDay|per day|daily", r.text or "", re.I):
                        log(f"  gemini tts {model} (key#{ki+1}): aaj ki awaaz limit khatam", show=False)
                        TTS_QUOTA["out"] = True; break
                    if r.status_code in (429, 500, 503):
                        log(f"  gemini tts {model} (key#{ki+1}): {r.status_code}, ruk ke dobara", show=False)
                        time.sleep(4); continue
                    if r.status_code == 404:
                        log(f"  gemini tts {model}: 404 retired – agla model try...", show=False)
                        break
                    if r.status_code != 200:
                        busy_only = False
                        log(f"  gemini tts {model}: {r.status_code} {r.text[:200]}", show=False); break
                    part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
                    TTS_QUOTA["out"] = False
                    return base64.b64decode(part["data"]), part.get("mimeType", "")
                except Exception as e:
                    log(f"  gemini tts {model} error: {e}", show=False); time.sleep(3)
    TTS_BUSY["flag"] = busy_only
    return None, None


def gemini_demo(key, line, names, out_dir, note=None):
    """v2.10: ek line kai awaazon me -> [(naam, ogg path)] (Telegram voice note)."""
    out = []
    for n in names:
        pcm, mime = gemini_tts_raw(key, tts_prompt(note or DEFAULT_NOTE, line), GEMINI_VOICES.get(n.lower(), n), 120)
        if not pcm: continue
        rate = int((re.search(r"rate=(\d+)", mime or "") or [None, 24000])[1])
        raw = out_dir / f"demo_{n}.raw"; raw.write_bytes(pcm)
        ogg = out_dir / f"demo_{n}.ogg"
        try:
            run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", raw,
                 "-c:a", "libopus", "-b:a", "48k", ogg])
            out.append((n, ogg))
        except Exception as e:
            log(f"  demo {n}: {e}", show=False)
    return out


def gemini_voice(lines, style, work, key, strict_plain=False):
    """One call to Gemini TTS for the whole script, then split into lines at pauses."""
    import requests, base64
    vname = GEMINI_VOICES.get(style.get("gemini_awaaz", "charon").lower(), "Charon")
    note = (style.get("gemini_andaaz") or "").strip() or DEFAULT_NOTE        # aapki AI Studio wali style line
    text = tts_prompt(note, "\n".join(lines), strict_plain=strict_plain)
    pcm, mime = gemini_tts_raw(key, text, vname)
    if not pcm:
        return None
    rate = 24000
    m = re.search(r"rate=(\d+)", mime or "")
    if m: rate = int(m.group(1))
    raw = work / "gemini.raw"; raw.write_bytes(pcm)
    wav = work / "voice.wav"
    sp = num(style, "ai_speed", -50, 50)
    tempo = f",atempo={1 + sp/100:.3f}" if abs(sp) >= 3 else ""
    run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", raw,
         "-af", f"silenceremove=start_periods=1:start_threshold=-45dB{tempo}", "-ar", str(SR), "-ac", "1", wav])
    warm_voice(wav, style)
    trim_extra_speech(wav, lines, style)
    x = load_wav(wav); total = len(x) / SR
    # pauses (quiet stretches > 0.18s) as candidate line boundaries
    hop = int(0.01 * SR); fr = len(x) // hop
    e = np.sqrt(np.mean(x[:fr * hop].reshape(fr, hop) ** 2, axis=1))
    quiet = e < max(0.008, np.percentile(e, 20) * 1.5)
    pauses = []; i = 0
    while i < fr:
        if quiet[i]:
            j = i
            while j < fr and quiet[j]: j += 1
            if (j - i) * 0.01 >= 0.18: pauses.append((i + j) / 2 * 0.01)
            i = j
        else:
            i += 1
    lens = [max(3, len(l)) for l in lines]; tot = sum(lens)
    bounds = [0.0]; acc = 0
    for L in lens[:-1]:
        acc += L; guess = total * acc / tot
        near = [p for p in pauses if abs(p - guess) < 1.0 and p > bounds[-1] + 0.4]
        bounds.append(min(near, key=lambda p: abs(p - guess)) if near else guess)
    bounds.append(total)
    sents = []
    for k, l in enumerate(lines):
        a, b = bounds[k], bounds[k + 1]
        sents.append({"text": l, "start": a, "end": b, "words": spread_words(l, a + 0.05, b - 0.1)})
    return wav, sents


def _coverage(lines, wav, style):
    try:
        import align
        return align.line_coverage(lines, wav, style.get("whisper_model", "base"))
    except Exception as e:
        log(f"  (line check skip: {e})", show=False); return None


def gemini_voice_checked(lines, style, work, key):
    """v2.15: Gemini awaaz bana ke Whisper se SUNO – koi line chhooti / kati to sirf wahi hissa (3-3 lines ke tukde)
    dobara bulwao. Isse video me script ki har line aati hai, aadhi kati nahi lagti."""
    r = gemini_voice(lines, style, work, key)
    if not r or not yes(style.get("awaaz_check", "haan")) or len(lines) < 2:
        return r
    cov = _coverage(lines, r[0], style)
    if cov is None:
        return r
    try:
        import align as _al
        ratio = _al.LAST_RATIO["v"]
    except Exception:
        ratio = 1.0
    if ratio > num(style, "awaaz_repeat_had", 1.1, 2.0) if style.get("awaaz_repeat_had") else ratio > 1.3:
        # v2.17d: Gemini ne line(s) DOBARA boli (repeat) – ek baar poori nayi awaaz, jo script ke kareeb ho wahi rakho
        log(f"  awaaz check: Gemini ne kuch dobara bola (script se {ratio:.1f}x lambi) – ek baar nayi bana raha hoon...")
        sub = work / "repeat_fix"; sub.mkdir(exist_ok=True)
        r2 = gemini_voice(lines, style, sub, key)
        if r2:
            cov2 = _coverage(lines, r2[0], style)
            try:
                ratio2 = _al.LAST_RATIO["v"]
            except Exception:
                ratio2 = 9
            if cov2 is not None and abs(ratio2 - 1) < abs(ratio - 1):
                import shutil as _sh
                _sh.copy(r2[0], work / "voice.wav")
                r, cov, ratio = (work / "voice.wav", r2[1]), cov2, ratio2
                log(f"  nayi awaaz behtar ✓ ({ratio:.2f}x)", show=False)
        if ratio > 1.3:
            log("  ⚠️ awaaz me ab bhi thoda repeat ho sakta hai", show=False)
    # v3.21 FIX: 0.45 triggered unnecessary partial Gemini TTS re-calls (causing mid-video voice/speed changes).
    # Only splice if a line is genuinely missing (<0.22 coverage).
    lim = num(style, "awaaz_check_had", 0.1, 0.9) if style.get("awaaz_check_had") else 0.22
    miss = [i for i, c in enumerate(cov) if c < lim]
    if not miss:
        log(f"  awaaz check: saari {len(lines)} lines boli gayi ✓", show=False)
        return r
    if len(miss) >= max(3, int(len(lines) * 0.55)):
        # v3.96 HALLUCINATION GUARD: If Whisper clearly heard speech (ratio >= 0.30) but >=55% of script lines
        # did not match, Gemini TTS hallucinated a wrong topic/script! Retry with clean verbatim prompt (Charon locked).
        avg_cov = sum(cov) / max(1, len(cov))
        if ratio >= 0.30 and avg_cov < 0.45:
            log(f"  ⚠️ awaaz check: Gemini TTS topic/script mismatch ({len(miss)}/{len(lines)} lines, avg={avg_cov:.2f}) – "
                "clean verbatim prompt se Charon awaaz dobara bana raha hoon...")
            best_r, best_cov, best_avg = r, cov, avg_cov
            for h_try in range(2):
                h_sub = work / f"halluc_fix_{h_try}"; h_sub.mkdir(exist_ok=True)
                rh = gemini_voice(lines, style, h_sub, key, strict_plain=True)
                if not rh:
                    continue
                ch = _coverage(lines, rh[0], style)
                if ch is None:
                    continue
                ah = sum(ch) / max(1, len(ch))
                if ah > best_avg:
                    best_r, best_cov, best_avg = rh, ch, ah
                if ah >= 0.65:
                    break
            if best_r is not r:
                import shutil as _sh
                _sh.copy(best_r[0], work / "voice.wav")
                r = (work / "voice.wav", best_r[1])
                cov = best_cov
                miss = [i for i, c in enumerate(cov) if c < lim]
                log(f"  ✅ awaaz hallucination fixed! Naya script match = {best_avg*100:.0f}% ✓")
                if not miss:
                    return r
        if len(miss) >= max(3, int(len(lines) * 0.55)):
            log(f"  awaaz check: Whisper {len(miss)}/{len(lines)} lines pakad nahi paya – best available awaaz rakhi")
            return r
    log(f"  awaaz check: line {', '.join(str(i+1) for i in miss)} theek se nahi boli – SIRF wahi dobara bana raha hoon...")
    # v2.17d: sirf chhooti line(s) dobara (pehle saari lines dobara banti thi -> Gemini ki awaaz limit jaldi khatam)
    sents0 = [dict(x, words=[dict(w) for w in x["words"]]) for x in r[1]]
    try:
        import align
        aligned = align.align(sents0, r[0], style.get("whisper_model", "base"))
    except Exception:
        aligned = False
    if not aligned:
        log("   (line ki sahi jagah nahi mili – pehli awaaz hi rakhi, limit bachayi)", show=False)
        return r
    groups = []
    for i in miss:                                     # lagaataar chhooti lines = ek hi Gemini call
        if groups and i == groups[-1][1] + 1: groups[-1][1] = i
        else: groups.append([i, i])
    if len(groups) > 3:
        log("   bahut jagah chhooti – sirf 3 sabse pehle wale hisse theek karunga", show=False); groups = groups[:3]
    x0 = load_wav(r[0]); total = len(x0) / SR
    gap = np.zeros(int(0.15 * SR), dtype=np.float32)
    out_a, out_s = [], []; t = 0.0; cursor = 0.0; li = 0
    def keep(c0, c1, upto):
        nonlocal t, li
        seg = edge_fade(x0[int(c0 * SR):int(c1 * SR)])
        for k in range(li, upto):
            ss = dict(sents0[k]); sh = t - c0
            ss["start"] = max(t, ss["start"] + sh); ss["end"] = max(ss["start"] + 0.1, ss["end"] + sh)
            ss["words"] = [dict(w, start=w["start"] + sh, end=w["end"] + sh) for w in ss["words"]]
            out_s.append(ss)
        out_a.append(seg); t += len(seg) / SR; li = upto
    fixed = 0
    for gi, (a, b) in enumerate(groups):
        raw0 = (sents0[a - 1]["end"] + 0.06) if a > 0 else 0.0
        raw1 = (sents0[b + 1]["start"] - 0.04) if b + 1 < len(lines) else total
        cut0 = _snap_silence(x0, raw0) if a > 0 else 0.0
        cut1 = _snap_silence(x0, raw1) if b + 1 < len(lines) else total
        cut0 = max(cursor, min(cut0, total)); cut1 = max(cut0, min(cut1, total))
        keep(cursor, cut0, a)
        sub = work / f"fix_{gi}"; sub.mkdir(exist_ok=True)
        part = lines[a:b + 1]; best = None
        for attempt in range(2):                       # max 2 Gemini call is hisse ke liye
            rr = gemini_voice(part, dict(style, faltu_awaaz_kaato="haan"), sub, key)
            if not rr: break
            cc = _coverage(part, rr[0], style)
            sc = min(cc) if cc else 0.5
            if best is None or sc > best[0]: best = (sc, rr)
            if sc >= lim: break
        if best:
            xn = edge_fade(load_wav(best[1][0]))
            # v3.21 FIX: Match spliced chunk RMS loudness to main narration track so volume never jumps
            _ref_rms = float(np.sqrt(np.mean(x0[np.abs(x0) > 0.01] ** 2))) if np.any(np.abs(x0) > 0.01) else 0.12
            _new_rms = float(np.sqrt(np.mean(xn[np.abs(xn) > 0.01] ** 2))) if np.any(np.abs(xn) > 0.01) else _ref_rms
            if _new_rms > 1e-4:
                xn = np.clip(xn * (_ref_rms / _new_rms), -0.95, 0.95).astype(np.float32)
            out_a.append(gap); t += len(gap) / SR
            for ss in best[1][1]:
                ss = dict(ss); ss["start"] += t; ss["end"] += t
                ss["words"] = [dict(w, start=w["start"] + t, end=w["end"] + t) for w in ss["words"]]
                out_s.append(ss)
            out_a += [xn, gap]; t += (len(xn) + len(gap)) / SR
            li = b + 1; fixed += 1
        else:                                          # nayi nahi bani – purana hissa waise hi
            keep(cut0, cut1, b + 1)
        cursor = cut1
    keep(cursor, total, len(lines))
    if len(out_s) != len(lines) or not fixed:
        return r
    wav = work / "voice.wav"; save_wav(wav, np.concatenate(out_a))
    for k, ss in enumerate(out_s):
        ss["text"] = lines[k]
    # v3.20 FIX: Mandatory post-splice Whisper alignment so captions NEVER drift out of sync
    try:
        import align as _al_post
        _al_post.align(out_s, wav, style.get("whisper_model", "base"))
    except Exception as _ae:
        log(f"   (post-splice align skip: {_ae})", show=False)
    log(f"  awaaz theek ki – sirf {sum(b - a + 1 for a, b in groups)} line dobara bani ✓")
    return wav, out_s


def trim_extra_speech(wav, lines, style):
    """Whisper se suno: script ke pehle shabd se pehle (ya aakhri ke baad) kuch faltu bola ho
    (jaise English hidaayat) to us hisse ko kaat do. Kuch fail ho to awaaz waise hi rehti hai."""
    if not yes(style.get("faltu_awaaz_kaato", "haan")) or not lines:
        return False
    try:
        import align
        words, _ = align.transcribe(wav, style.get("whisper_model", "base"), "hi", prompt=" ".join(lines)[:600])
    except Exception:
        return False
    if not words:
        return False
    norm = align._norm
    first = [norm(w) for w in split_words(lines[0])][:4]
    last = [norm(w) for w in split_words(lines[-1])][-3:]
    def sim(a, b):
        return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0
    x = load_wav(wav); dur = len(x) / SR
    nw = [norm(w["w"]) for w in words]
    def hit(n, ref):
        return bool(n) and max((sim(n, f) for f in ref if f), default=0) > 0.7
    # v2.15: shuruaat – pehli line ke KAM SE KAM 2 shabd lagaataar mile tabhi wahan se shuru (sirf 1 shabd = bharosa nahi)
    start = None
    for i in range(min(len(words) - 1, 60)):
        if hit(nw[i], first) and hit(nw[i + 1], first):
            start = words[i]["start"]; break
    # v2.15: aakhir – aakhri line ke 2 shabd lagaataar, aur sirf awaaz ke aakhri 25% me (pehle beech se kat jaata tha)
    end = None
    for i in range(len(words) - 1, 0, -1):
        if words[i]["end"] < dur * 0.75: break
        if hit(nw[i], last) and hit(nw[i - 1], last):
            end = words[i]["end"]; break
    a = max(0.0, (start or 0) - 0.15); b = min(dur, (end or dur) + 0.45)
    MAX_START, MAX_END = 10.0, 4.0                  # v2.15: isse zyada kabhi nahi kaatega
    if a > MAX_START: a = 0.0
    if dur - b > MAX_END: b = dur
    if a < 1.0 and dur - b < 1.0:
        return False                                # sab theek, kuch nahi kaatna
    if b - a < dur * 0.75:
        log("  (faltu awaaz check: bharosa nahi, kuch nahi kaata)", show=False); return False
    save_wav(wav, edge_fade(x[int(a * SR):int(b * SR)]))
    log(f"  awaaz me faltu hissa kaata ✓ (shuru {a:.1f}s, aakhir {dur-b:.1f}s)")
    return True


# ------------------------------------------------------------------ own voice
def find_recording():
    import os
    if os.environ.get("VG_VOICE") and Path(os.environ["VG_VOICE"]).exists():     # Telegram bot se aayi recording
        return Path(os.environ["VG_VOICE"])
    folder = TOOL / "meri_awaaz"
    exts = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".opus", ".amr", ".3gp", ".flac", ".mp4", ".webm"}
    files = [p for p in folder.glob("*") if p.suffix.lower() in exts] if folder.exists() else []
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _norm(s):
    return re.sub(r"[^\wऀ-ॿ]+", "", s.lower())


def my_voice(script_lines, style, work):
    rec = find_recording()
    if not rec:
        fail("meri_awaaz folder me koi recording nahi mili. Phone ki recording (m4a/mp3/wav) us folder me daalo.")
    log(f"  recording: {rec.name}")
    x = load_wav(enhance_file(rec, style, work))
    # loudness normalise roughly
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * min(8.0, 0.1 / rms)
    wav16 = work / "rec16k.wav"
    save_wav(wav16, x)  # whisper resamples itself

    log("  awaaz ko sun raha hoon (pehli baar model download hoga, 5-10 min lag sakte hain)...")
    import align
    model = align.load(style.get("whisper_model_meri", "small"))
    if not model:
        fail("Whisper install/load nahi hua (internet chahiye pehli baar). log.txt Claude ko bhejo.")
    prompt = " ".join(script_lines)[:400] if script_lines else None
    segs, _ = model.transcribe(str(wav16), language="hi", word_timestamps=True,
                               vad_filter=True, initial_prompt=prompt)
    words = []
    for s in segs:
        for w in (s.words or []):
            if w.word.strip():
                words.append({"w": w.word.strip(), "start": w.start, "end": w.end})
    if not words:
        fail("Recording me koi awaaz samajh nahi aayi. Shaant jagah pe dobara record karo.")

    # --- phrases split by gaps > 0.6s
    phrases = []; cur = [words[0]]
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] > 0.6:
            phrases.append(cur); cur = []
        cur.append(b)
    phrases.append(cur)

    # --- retake removal: if a phrase is repeated (similar) soon after, drop the earlier one
    keep = [True] * len(phrases)
    texts = [_norm(" ".join(w["w"] for w in p)) for p in phrases]
    for i in range(len(phrases)):
        for j in range(i + 1, min(i + 3, len(phrases))):
            a, b = texts[i], texts[j]
            if not a or not b:
                continue
            r = difflib.SequenceMatcher(None, a, b).ratio()
            if r > 0.6 or (len(a) > 6 and b.startswith(a[: max(6, len(a) // 2)])):
                keep[i] = False
                log(f"  galti/dobara wali line hataayi: {' '.join(w['w'] for w in phrases[i])[:40]}")
                break
    phrases = [p for p, k in zip(phrases, keep) if k]

    # --- cut long pauses, rebuild timeline
    maxp = num(style, "pause_kaato", 0.15, 2.0)
    pad = 0.06
    out = []; t = 0.0; sents = []
    fade = int(0.008 * SR)
    for p in phrases:
        # inside a phrase, also shorten gaps > maxp
        chunks = []; cs = p[0]["start"]; prev = p[0]
        for w in p[1:]:
            if w["start"] - prev["end"] > maxp:
                chunks.append((cs, prev["end"])); cs = w["start"]
            prev = w
        chunks.append((cs, prev["end"]))
        new_words = []
        for (cs, ce) in chunks:
            a = max(0, int((cs - pad) * SR)); b = min(len(x), int((ce + pad) * SR))
            seg = x[a:b].copy()
            if len(seg) > 2 * fade:
                seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
            off = t - a / SR
            for w in p:
                if cs - 1e-3 <= w["start"] <= ce + 1e-3:
                    new_words.append({"w": w["w"], "start": w["start"] + off, "end": w["end"] + off})
            out.append(seg); t += len(seg) / SR
            gap = np.zeros(int(0.10 * SR), np.float32); out.append(gap); t += len(gap) / SR
        text = " ".join(w["w"] for w in p)
        if new_words:
            sents.append({"text": text, "start": new_words[0]["start"], "end": new_words[-1]["end"],
                          "words": new_words})
    audio = np.concatenate(out)
    wav = work / "voice.wav"; save_wav(wav, audio)
    log(f"  recording saaf ho gayi: {len(x)/SR:.1f}s -> {len(audio)/SR:.1f}s")

    # use script lines (correct spelling) for visual keywords if counts match roughly
    if script_lines and abs(len(script_lines) - len(sents)) <= 1:
        for s, line in zip(sents, script_lines):
            s["script"] = line
    return wav, sents


def sync_voice(path, script_lines, style, work):
    """v2.8 chehra mode: recording ko kaata nahi jaata (taaki chehra aur awaaz sync rahe)."""
    import align
    x = load_wav(enhance_file(path, style, work))
    rms = np.sqrt(np.mean(x ** 2)) + 1e-9
    x = x * min(8.0, 0.1 / rms)
    wav = work / "voice.wav"; save_wav(wav, x)
    words, segs = align.transcribe(wav, style.get("whisper_model_meri", "small"), "hi",
                                   prompt=" ".join(script_lines)[:800] if script_lines else None)
    if not words:
        fail("Recording me awaaz samajh nahi aayi. Shaant jagah pe dobara record karo.")
    sents = []; cur = [words[0]]
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] > 0.55:
            sents.append(cur); cur = []
        cur.append(b)
    sents.append(cur)
    sents = [{"text": " ".join(w["w"] for w in p), "start": p[0]["start"], "end": p[-1]["end"], "words": p}
             for p in sents]
    log(f"  recording (chehra mode, bina kaate): {len(x)/SR:.1f}s, {len(sents)} lines")
    return wav, sents


# ------------------------------------------------------------------ v2.9: apni awaaz ko professional banana
def _noise_floor(src):
    """Recording ke sabse shaant hisson se shor ka level naapo (amplitude)."""
    try:
        x = load_wav(src)
        hop = int(0.02 * SR); n = len(x) // hop
        if n < 20: return None
        e = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
        return float(max(1e-5, np.percentile(e, 10)))
    except Exception:
        return None


def _chain(style, pitch_mode, noise=None):
    nr = num(style, "awaaz_noise_saaf", 0, 40)          # noise kitna hatana (dB)
    st = num(style, "awaaz_deep", 0, 4)                 # kitne semitone neeche (deep)
    crisp = yes(style.get("awaaz_crisp", "haan"))
    f = 2 ** (-st / 12)
    parts = ["highpass=f=75", "lowpass=f=15000"]
    if nr > 0:
        nf = 20 * np.log10(noise) if noise else -45
        nf = float(min(-20, max(-80, nf)))
        parts.append(f"afftdn=nr={nr:.0f}:nf={nf:.0f}:tn=1")
        thr = min(0.05, max(0.003, (noise or 0.005) * 2.5))               # shor se thoda upar
        parts.append(f"agate=threshold={thr:.4f}:ratio=10:range=0.03:attack=3:release=200")   # chup me shor band
    if st > 0.05:
        if pitch_mode == "rubberband":
            parts.append(f"rubberband=pitch={f:.4f}:transients=smooth")
        else:                                            # rubberband na ho to: speed same, pitch neeche
            parts.append(f"asetrate={int(SR * f)},aresample={SR},atempo={1 / f:.4f}")
    parts += ["equalizer=f=120:t=q:w=1.0:g=4.5",         # seene ki bhaari awaaz
              "equalizer=f=220:t=q:w=1.2:g=1.5",         # gale ki garmahat
              "equalizer=f=380:t=q:w=1.0:g=-2",          # dabi hui (muddy) awaaz kam
              "equalizer=f=1000:t=q:w=1.3:g=-3.5"]       # NAAK wali awaaz kam
    if crisp:
        parts += ["equalizer=f=3800:t=q:w=1.4:g=3",       # saaf shabd
                  "equalizer=f=9500:t=q:w=1.5:g=1.5",      # chamak
                  "deesser=i=0.35"]                        # 'ss' ki seeti kam
    parts += ["acompressor=threshold=-22dB:ratio=4:attack=5:release=100:makeup=3.5",   # ghani / bhaari
              "asoftclip=type=tanh",                       # halki garmahat (radio jaisi)
              "alimiter=limit=0.93"]
    return ",".join(parts)


def enhance_file(src, style, work):
    """Recording: noise saaf + deep + crisp + barabar awaaz. Lambai bilkul same (chehra sync rehta hai).
    Kuch fail ho to original hi lauta deta hai."""
    if not yes(style.get("awaaz_sudhaaro", "haan")):
        return Path(src)
    out = work / "voice_enhanced.wav"
    noise = _noise_floor(src)
    for mode in ("rubberband", "simple"):
        try:
            run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR),
                 "-af", _chain(style, mode, noise), out])
            if out.exists() and out.stat().st_size > 1000:
                log(f"  awaaz saaf + deep + crisp ki ✓ ({'rubberband' if mode == 'rubberband' else 'simple'})")
                return out
        except Exception as e:
            log(f"  awaaz sudhaar ({mode}) nahi hua: {str(e)[:120]}", show=False)
    return Path(src)
