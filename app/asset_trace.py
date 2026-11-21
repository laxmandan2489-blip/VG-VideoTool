"""v3.13 ASSET TRACE (Bug D: "footage download hui par lagi nahi").

Har line ke liye ek jagah sab kuch:
  candidates (visual_pick: provider, title, CLIP score)  ->  downloaded/chosen items (found)  ->  plan shots
  ->  rendered shot file (frames)  ->  EDL cut.
Aur ek saaf list: kaunsi downloaded VIDEO kisi shot me nahi lagi (aur kyun – jaise 'line me 1 hi shot tha').
Output: <video>_TRACE.json (output folder me, EDL ke paas). Token/keys kabhi nahi likhte.
"""
import json
from pathlib import Path


def _frames(p):
    try:
        import shotfix
        i = shotfix.probe(p)
        return i["frames"] if i else 0
    except Exception:
        return None


def build(sents, found, plan, files, line_start, cuts=(), pick_trace=None, rejected=None, fps=30):
    rows = []
    shot_line = {}
    cur = 0
    for n in range(len(plan)):
        if n in line_start: cur = line_start[n]
        shot_line[n] = cur
    used_paths = {str(it.get("path")) for _, _, it in plan}
    unused = []
    for i, s in enumerate(sents):
        items = (found[i][0] if i < len(found) and found[i] else []) or []
        shots = []
        for n, (a, b, it) in enumerate(plan):
            if shot_line.get(n) != i: continue
            f = files[n] if n < len(files) else None
            want = max(2, int(round((b - a) * fps)))
            got = _frames(f) if f and Path(f).exists() else 0
            shots.append({"shot": n + 1, "t": [round(a, 2), round(b, 2)], "kind": it.get("kind"),
                          "src": str(it.get("src", "")), "source_file": str(it.get("path")),
                          "rendered_file": str(f) if f else None, "frames_want": want, "frames_got": got,
                          "ok": bool(f and got and abs(got - want) <= 1)})
        for it in items:
            if str(it.get("path")) not in used_paths and it.get("kind") == "video":
                unused.append({"line": i + 1, "file": str(it.get("path")), "src": str(it.get("src", "")),
                               "why": "line ke shot kam the (sabse achhe score wali pehle lagi)"})
        rows.append({
            "line": i + 1, "text": (s.get("script") or s.get("text") or "")[:200],
            "found": [{"kind": it.get("kind"), "src": str(it.get("src", "")), "file": str(it.get("path")),
                       "score": it.get("score"), "part": it.get("part")} for it in items],
            "picker": (pick_trace or {}).get(i),
            "rejected": [{"file": str(r["path"]), "score": round(float(r["score"]), 3), "why": r["why"]}
                         for r in ((rejected or {}).get(i) or [])][:12],
            "shots": shots,
        })
    n_video = sum(1 for _, _, it in plan if it.get("kind") == "video" and "card" not in str(it.get("src", "")))
    n_img = sum(1 for _, _, it in plan if it.get("kind") == "image")
    img_paths = [str(it.get("path")) for _, _, it in plan if it.get("kind") == "image"]
    summary = {"shots": len(plan), "video_shots": n_video, "image_shots": n_img,
               "repeated_images": sorted({p for p in img_paths if img_paths.count(p) > 1}),
               "bad_length_shots": [sh["shot"] for r in rows for sh in r["shots"] if not sh["ok"]],
               "downloaded_but_unused_videos": unused,
               "edl_cuts": len(cuts or [])}
    return {"summary": summary, "lines": rows}


def write(data, base):
    p = Path(str(base) + "_TRACE.json")
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return p


def one_line(data):
    s = data["summary"]
    msg = f"{s['shots']} shots: {s['video_shots']} video, {s['image_shots']} photo"
    if s["repeated_images"]: msg += f", ⚠️ {len(s['repeated_images'])} photo dobara"
    if s["bad_length_shots"]: msg += f", ⚠️ shot lambai galat: {s['bad_length_shots'][:5]}"
    if s["downloaded_but_unused_videos"]: msg += f", {len(s['downloaded_but_unused_videos'])} video mili par nahi lagi"
    return msg
