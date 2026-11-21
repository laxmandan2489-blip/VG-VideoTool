"""v3.37 EMOTION & REACTION GREEN-SCREEN ENGINE (mere_memes/<category>/).

Detects exact Hindi emotion/curiosity phrases in the spoken script and automatically overlays
matching green-screen reaction/meme/3D-symbol clips at the exact spoken timestamp — just like
a human Shorts editor:
  - question : "क्या आपको पता है", "जानते हो", "सवाल", "क्यों", "?"
  - shocked  : "हैरान", "चौंक", "शॉकिंग", "विश्वास नहीं", "असंभव"
  - scared   : "डर जाओगे", "खतरनाक", "भयानक", "डरावना", "मौत"
  - confused : "कंफ्यूज", "उलझन", "समझ नहीं", "रहस्य", "पहेली"
  - money    : "करोड़", "अरब", "डॉलर", "रुपये", "कमाई", "बिलियन"
  - clap     : "इतिहास रच", "सफलता", "जीत", "रिकॉर्ड", "कमाल"
"""
import json
import random
import re
from pathlib import Path

from common import TOOL, log

MEMES_DIR = TOOL / "mere_memes"
VID_EXT = (".mp4", ".mov", ".webm", ".mkv")

RULES = [
    ("question", r"(क्या आप|क्या आपको पता|जानते हो|पता है|सवाल|\?)"),
    ("scared", r"(डर जाओगे|डरावना|खतरनाक|भयानक|खौफनाक)"),
    ("confused", r"(कंफ्यूज|उलझन|समझ नहीं|अजीब रहस्य|पहेली)"),
    ("shocked", r"(हैरान|चौंक|शॉकिंग|विश्वास नहीं|होश उड़|असंभव|रहस्य)"),
    ("money", r"(करोड़|अरब|बिलियन|डॉलर|रुपये|कमाई)"),
    ("clap", r"(इतिहास रच|विश्व रिकॉर्ड|सफलता|जीत हासिल)"),
]


_AUTO_QUERIES = {
    "shocked":  "shocked surprised man reaction green screen meme short",
    "scared":   "scared shocked reaction green screen meme short",
    "confused": "confused thinking reaction green screen meme short",
    "question": "thinking confused man green screen meme short",
    "money":    "money rain flying green screen overlay short",
    "clap":     "clapping applause reaction green screen meme short",
}
_AUTO_TRIED = set()


def _auto_fetch_meme(cat):
    """v3.52: Auto-download 1 real short green-screen reaction meme via yt-dlp if folder is empty (cached forever)."""
    if cat in _AUTO_TRIED or cat not in _AUTO_QUERIES:
        return None
    _AUTO_TRIED.add(cat)
    d = MEMES_DIR / cat
    d.mkdir(parents=True, exist_ok=True)
    out_mp4 = d / f"auto_{cat}_gs.mp4"
    if out_mp4.exists() and out_mp4.stat().st_size > 15000:
        return str(out_mp4)
    try:
        import subprocess
        q = f"ytsearch3:{_AUTO_QUERIES[cat]}"
        cmd = [
            "yt-dlp", "-f", "best[ext=mp4][height<=720]/best[ext=mp4]/best",
            "--max-downloads", "1", "--match-filter", "duration < 25",
            "--download-sections", "*0:00-0:04", "--force-keyframes-at-cuts",
            "--no-playlist", "--no-warnings", "-o", str(out_mp4), q,
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=18)
        if out_mp4.exists() and out_mp4.stat().st_size > 15000:
            log(f"   🎭 Auto-fetched real green-screen meme: {cat} ✓")
            return str(out_mp4)
    except Exception as e:
        log(f"   (auto meme skip {cat}: {str(e)[:60]})", show=False)
    return None


def _pick_clip(cat):
    # v3.59: ONLY use user's own hand-picked clips in mere_memes/<cat>/ (never auto-download random foreign memes!)
    d = MEMES_DIR / cat
    if d.exists():
        clips = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in VID_EXT and p.stat().st_size > 5000 and not p.name.startswith("auto_"))
        if clips:
            return str(random.choice(clips))
    return None


def plan_emotion_overlays(sents, total, work_dir, max_overlays=2, busy=()):
    """Find up to `max_overlays` well-spaced emotion moments that have an actual clip in mere_memes/<cat>/."""
    events = []
    used_cats = set()
    last_t = -99.0
    for i, s in enumerate(sents or []):
        if len(events) >= max_overlays:
            break
        txt = str(s.get("script") or s.get("text") or "")
        st = float(s.get("start") or 0.0)
        en = float(s.get("end") or (st + 2.5))
        # Avoid colliding with opening hook (first 2.8s) or closing Subscribe (last 4.5s)
        # v3.38 ANTI-CLUTTER GUARD: never overlap opening hook, closing Subscribe, Documentary cards, Polaroids, Maps, or big keywords!
        if st < 3.2 or st > max(5.0, total - 5.2) or (st - last_t) < 12.0:
            continue
        if any((b0 - 0.5) < st < (b1 + 0.5) for b0, b1 in (busy or ())):
            continue
        for cat, pat in RULES:
            if cat in used_cats:
                continue
            if re.search(pat, txt, re.I):
                clip = _pick_clip(cat)
                if clip:
                    dur = min(2.4, max(1.2, en - st))
                    events.append({"cat": cat, "path": clip, "t": round(st + 0.15, 3), "dur": round(dur, 3)})
                    used_cats.add(cat)
                    last_t = st
                    break
    out_json = Path(work_dir) / "emotion_events.json"
    out_json.write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")
    if events:
        log(f"   🎭 Emotion Green-Screen FX: {', '.join(e['cat'] for e in events)} ({len(events)} lagi ✓)")
    return events


def build_ffmpeg_chain(work_dir, base_label, start_input_idx, W, H, fps=30):
    """Returns (extra_inputs_list, filter_chain_str, final_label) for _final_mux."""
    ev_f = Path(work_dir) / "emotion_events.json"
    if not ev_f.exists():
        return [], "", base_label
    try:
        events = json.loads(ev_f.read_text(encoding="utf-8"))
    except Exception:
        return [], "", base_label
    if not events:
        return [], "", base_label

    extra_in = []
    chains = []
    cur = base_label
    idx = start_input_idx
    ow = int(W * 0.56) // 2 * 2  # Crisp centered/corner overlay size (never blocks subtitles!)
    for k, ev in enumerate(events[:2]):
        p = Path(ev["path"])
        if not p.exists():
            continue
        t0 = float(ev["t"])
        dur = float(ev["dur"])
        extra_in += ["-t", f"{dur:.3f}", "-i", str(p)]
        lbl_k = f"emk{k}"
        lbl_o = f"emo{k}"
        y_pos = int(H * 0.14) if ev["cat"] == "question" else int(H * 0.24)
        chains.append(
            f"[{idx}:v]fps={fps},scale={ow}:-2:flags=lanczos,"
            f"chromakey=0x00FF00:0.26:0.10,despill=green,format=yuva420p,"
            f"setpts=PTS-STARTPTS+{t0:.3f}/TB[{lbl_k}];"
            f"[{cur}][{lbl_k}]overlay=(W-w)/2:{y_pos}:eof_action=pass:shortest=0[{lbl_o}]"
        )
        cur = lbl_o
        idx += 1
    return extra_in, (";" + ";".join(chains) if chains else ""), cur
