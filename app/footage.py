"""v2.8: Aapki apni footage -> script ki sahi lines.

Gemini har clip ke 3 frame dekhta hai, aapki baat (jaise "rocket wali clip NASA wali line pe") padhta hai,
aur har clip ko sahi line(s) pe lagata hai. Gemini na chale to clips line ke kram me lag jaati hain.
"""
import io
from pathlib import Path
from common import log, run, duration

VID = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".3gp")
IMG = (".jpg", ".jpeg", ".png", ".webp")


def list_clips(folder):
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted([p for p in folder.iterdir() if p.suffix.lower() in VID + IMG], key=lambda p: p.stat().st_mtime)


def _frames(p, work, k):
    from PIL import Image
    out = []
    if p.suffix.lower() in IMG:
        im = Image.open(p).convert("RGB"); im.thumbnail((320, 320))
        b = io.BytesIO(); im.save(b, "JPEG", quality=75); return [b.getvalue()]
    d = duration(p) or 3
    for j, f in enumerate((0.15, 0.5, 0.85)):
        fp = work / f"uf_{k}_{j}.jpg"
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{d*f:.2f}", "-i", p, "-frames:v", "1", "-vf", "scale=320:-2", fp])
            im = Image.open(fp).convert("RGB"); b = io.BytesIO(); im.save(b, "JPEG", quality=70); out.append(b.getvalue())
        except Exception:
            continue
    return out


def assign(folder, lines, notes, key, work):
    """Returns {line_index: [clip_path, ...]}."""
    clips = list_clips(folder)
    if not clips:
        return {}
    log(f"   aapki footage: {len(clips)} clips – script ki lines pe laga raha hoon...")
    res = None
    if key:
        from ai import ask_json
        parts = [("You are a video editor. Assign the user's own clips to the lines of a Hindi Short so the viewer "
                  "SEES what is being said. Follow the user's instructions first. A clip may go on 1-3 lines; "
                  "a line can have up to 2 clips; it is OK to leave lines without a clip if nothing fits "
                  "(stock footage will be used there). Do not put a clip on a line it does not fit.\n"
                  f"User instructions: {notes or '-'}\n\nScript lines:\n"
                  + "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
                  + "\n\nClips (3 frames each):")]
        for k, c in enumerate(clips):
            fr = _frames(c, work, k)
            if not fr: continue
            parts.append(f"Clip {k+1} (file: {c.name}):")
            parts += [{"jpg": b} for b in fr]
        parts.append('Return ONLY JSON: {"assign": [{"clip": number, "lines": [line numbers]}]}')
        res = ask_json(key, parts, temperature=0.2, timeout=120)
    out = {}
    if isinstance(res, dict) and res.get("assign"):
        for a in res["assign"]:
            try:
                c = clips[int(a["clip"]) - 1]
            except Exception:
                continue
            for ln in a.get("lines") or []:
                try:
                    i = int(ln) - 1
                except Exception:
                    continue
                if 0 <= i < len(lines) and c not in out.setdefault(i, []) and len(out[i]) < 2:
                    out[i].append(c)
    if not out:                                   # Gemini nahi: kram se baant do
        step = max(1, len(lines) // max(1, len(clips)))
        for k, c in enumerate(clips):
            out.setdefault(min(len(lines) - 1, k * step), []).append(c)
    log(f"   aapki footage {len(out)} lines pe lagi ✓")
    return out
