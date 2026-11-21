"""v3.6 EDL – Edit Decision List.

Har video ke saath:
  <video>_EDL.edl   – CMX3600 (DaVinci Resolve / Premiere me File > Import > Timeline se khulta hai)
  <video>_EDL.json  – tool ke liye: har cut = kaunsi line, kaunsi clip, source ka kaunsa hissa, timeline pe kab
Video Review (video_review.py) isi JSON se har cut ko script ki line se milata hai.
"""
import json
from pathlib import Path


def tc(sec, fps=30):
    f = int(round(max(0.0, sec) * fps))
    return f"{f // (3600 * fps):02d}:{f // (60 * fps) % 60:02d}:{f // fps % 60:02d}:{f % fps:02d}"


def build(plan, line_start, sents, shot_ss=None, shot_files=None, effects=()):
    """plan = [(start, end, item)], line_start = {shot_index: line_index}. Return list of dict cuts."""
    shot_ss = shot_ss or {}
    cuts, cur = [], 0
    tr_at = {round(e[0], 2): (e[1] if len(e) < 3 or not isinstance(e[2], dict) else "transition") for e in effects}
    for n, (a, b, it) in enumerate(plan):
        if n in line_start: cur = line_start[n]
        it = it or {}
        sf = str(shot_files[n]) if shot_files and n < len(shot_files) else ""
        txt = (sents[cur].get("script") or sents[cur]["text"]) if cur < len(sents) else ""
        cuts.append({
            "n": n + 1, "line": cur + 1, "line_text": txt, "new_line": n in line_start,
            "rec_in": round(a, 3), "rec_out": round(b, 3), "dur": round(b - a, 3),
            "kind": it.get("kind", ""), "src": str(it.get("src", "")), "entity": it.get("entity", ""),
            "source": str(it.get("path", "")), "url": it.get("url", ""), "credit": it.get("credit", ""),
            "src_in": shot_ss.get(sf, it.get("ss")), "shot_file": sf,
            "transition": tr_at.get(round(a, 2), ""),
        })
    return cuts


def write(cuts, base, fps=30, title="VG"):
    base = Path(base)
    try:
        base.with_name(base.name + "_EDL.json").write_text(json.dumps(cuts, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    lines = [f"TITLE: {title[:60]}", "FCM: NON-DROP FRAME", ""]
    for c in cuts:
        si = float(c.get("src_in") or 0.0)
        reel = f"AX"
        lines.append(f"{c['n']:03d}  {reel:<8} V     C        {tc(si, fps)} {tc(si + c['dur'], fps)} "
                     f"{tc(c['rec_in'], fps)} {tc(c['rec_out'], fps)}")
        nm = Path(c["source"]).name if c["source"] else (c["src"] or "card")
        lines.append(f"* FROM CLIP NAME: {nm}")
        lines.append(f"* LINE {c['line']}: {c['line_text'][:70]}")
        if c.get("src"): lines.append(f"* SOURCE: {c['src'][:60]}")
        lines.append("")
    try:
        base.with_name(base.name + "_EDL.edl").write_text("\n".join(lines), encoding="utf-8")
        return True
    except Exception:
        return False
