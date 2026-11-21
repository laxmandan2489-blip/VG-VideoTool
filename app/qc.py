"""v2.7: Check bot – bani hui video ko insaan ki tarah dekhta hai.

1) Technical: kaale frame / atki hui video (ffmpeg blackdetect, freezedetect)
2) Gemini: har line ka ek frame dekh ke – footage line se match karti hai? caption sahi/padhne layak?
   kuch kata hua / toota hua to nahi?
Kharab lines ki list lautata hai – make_video unki footage badal ke dobara banata hai.
"""
import re, io, subprocess
from pathlib import Path
from common import log, run


def _times(cmd, pat):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=600, stdin=subprocess.DEVNULL)
        return [float(m) for m in re.findall(pat, r.stderr)]
    except Exception:
        return []


def _line_at(t, sents):
    for i, s in enumerate(sents):
        nxt = sents[i + 1]["start"] if i + 1 < len(sents) else 1e9
        if s["start"] - 0.05 <= t < nxt:
            return i
    return len(sents) - 1


def technical(video, sents):
    bad = {}
    for t in _times(["ffmpeg", "-nostdin", "-v", "info", "-i", str(video), "-vf", "blackdetect=d=0.25:pix_th=0.06",
                     "-an", "-f", "null", "-"], r"black_start:([\d.]+)"):
        if t > 0.3: bad.setdefault(_line_at(t, sents), "kaala frame")
    for t in _times(["ffmpeg", "-nostdin", "-v", "info", "-i", str(video), "-vf", "freezedetect=n=0.002:d=1.6",
                     "-an", "-f", "null", "-"], r"freeze_start: ([\d.]+)"):
        i = _line_at(t, sents)
        if i < len(sents) - 1: bad.setdefault(i, "video atki hui")       # aakhri line pe subscribe – normal
    return bad


def gemini_review(key, video, sents, work, complaint=""):
    from ai import ask_json
    from PIL import Image
    parts = [("You are a strict but fair human video editor checking a finished Hindi YouTube Short before upload.\n"
              "For each numbered line you get the spoken Hindi line and one frame from the middle of it "
              "(captions are burned in at the bottom).\n"
              "Mark a line BAD only for a clear problem:\n"
              " - footage is unrelated to / misleading for what is being said\n"
              " - caption is missing, garbled, cut off at the edges, or overlapping other text badly\n"
              " - frame is broken, black, stretched, or important subject is cut off\n"
              + (f"The creator already complained: \"{complaint}\" – be STRICT about that.\n" if complaint else "") +
              "Small style issues are OK. Return ONLY JSON: {\"bad\": [{\"line\": number, \"why\": \"short reason\"}]}\n")]
    n = 0
    for i, s in enumerate(sents):
        nxt = sents[i + 1]["start"] if i + 1 < len(sents) else s["end"]
        t = (s["start"] + max(s["start"] + 0.3, nxt)) / 2
        f = work / f"qc_{i:02d}.jpg"
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                 "-vf", "scale=360:-2", "-q:v", "4", f])
            b = io.BytesIO(); Image.open(f).convert("RGB").save(b, "JPEG", quality=75)
            parts += [f"Line {i+1}: {s.get('script') or s['text']}", {"jpg": b.getvalue()}]; n += 1
        except Exception:
            continue
    if n < 2:
        return None
    res = ask_json(key, parts, temperature=0.1, timeout=120)
    if not isinstance(res, dict):
        return None
    out = {}
    for x in res.get("bad") or []:
        try:
            i = int(x.get("line")) - 1
        except Exception:
            continue
        if 0 <= i < len(sents):
            out[i] = str(x.get("why", ""))[:80]
    return out


def gemini_watch_review(key, video, sents, work, complaint=""):
    """v2.17: Gemini POORI video dekhe (awaaz ke saath) aur har line ko 0-10 number de – visual line se mila?"""
    from ai import ask_json
    try:
        sm = Path(work) / "qc_small.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf", "scale=-2:480,fps=10", "-c:v", "libx264", "-preset",
             "veryfast", "-crf", "33", "-c:a", "aac", "-b:a", "48k", "-ac", "1", sm])
        if sm.stat().st_size > 14 * 1024 * 1024:
            return None
        lines = "\n".join(f"{i+1}. [{s['start']:.1f}s] {s.get('script') or s['text']}" for i, s in enumerate(sents))
        prompt = ("You are a strict PRO video editor reviewing this finished Hindi YouTube Short (watch it fully, with audio).\n"
                  "Lines with their start time:\n" + lines + "\n\n"
                  "For EACH line give a score 0-10: does the footage on screen during that line clearly SHOW what is being "
                  "said? 10 = exactly it, 6 = related but weak, 0-3 = unrelated / misleading / broken / black.\n"
                  + (f"The creator complained: \"{complaint}\" – be strict about that.\n" if complaint else "") +
                  'Return ONLY JSON: {"lines": [{"line": number, "score": 0-10, "why": "short reason if < 6"}]}')
        r = ask_json(key, [prompt, {"mp4": sm.read_bytes()}], temperature=0.1, timeout=180, budget=200)
        if not isinstance(r, dict) or not r.get("lines"):
            return None
        lim = 6
        out = {}
        for x in r["lines"]:
            try:
                i = int(x["line"]) - 1; sc = float(x["score"])
            except Exception:
                continue
            if 0 <= i < len(sents) and sc < lim:
                out[i] = f"score {sc:.0f}/10 – " + str(x.get("why", ""))[:70]
        log(f"   Gemini ne poori video dekhi ✓ ({len(out)} line kamzor)", show=False)
        return out
    except Exception as e:
        log(f"   (video review skip: {e})", show=False)
        return None


def check(video, sents, key, work, complaint=""):
    """Returns {line_index: reason} of lines to fix (empty = sab theek)."""
    log("8) Check bot video dekh raha hai (insaan ki tarah)...")
    bad = technical(video, sents)
    LAST.update({"gemini": False, "bad": 0, "lines": len(sents)})
    if key:
        g = gemini_watch_review(key, video, sents, work, complaint)
        if g is None:
            g = gemini_review(key, video, sents, work, complaint)
        if g is None:
            log("   ⚠️ Gemini review nahi ho paya – sirf technical check hua")
        else:
            LAST["gemini"] = True; LAST["bad"] = len(g)
            for i, why in g.items(): bad.setdefault(i, why)
    if bad:
        for i in sorted(bad):
            log(f"   line {i+1}: {bad[i]}")
    else:
        log("   sab theek laga ✓" if LAST["gemini"] else "   technical check theek (Gemini review nahi hua)")
    return bad


LAST = {"gemini": False, "bad": 0, "lines": 0}
