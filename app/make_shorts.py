"""v2.6: Lambi video -> Shorts.

   VideoTool\\lambi_video\\ me apni lambi video daalo  ->  5_SHORTS_BANAO chalao
   -> Whisper sunta hai -> Gemini sabse achhe 25-58 sec hisse chunta hai -> 9:16 Shorts + captions + upload kit
"""
import sys, os, time, shutil, datetime, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
from common import (log, fail, read_style, yes, num, read_keys, check_ffmpeg, no_console_freeze, run,
                    duration, safe_name, TOOL, OUT, WORK, LOG_FILE)

VID = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")


def pick_clips(key, segs, total, n):
    """Gemini se best hisse chunwao; na ho to sabse zyada bolne wale hisse."""
    from ai import ask_json
    clips = []
    if key and segs:
        tx = "\n".join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in segs)[:60000]
        res = ask_json(key, [
            "You are a viral YouTube Shorts editor. From this timestamped Hindi transcript of a long video pick the "
            f"{n} BEST moments for Shorts. Each clip: 25 to 58 seconds, starts with a strong hook line, is "
            "self-contained (makes sense alone), ends on a complete sentence. No overlaps.\n"
            "Return ONLY JSON list: [{\"start\": sec, \"end\": sec, \"title\": \"2-5 word Hindi hook text\", "
            "\"yt_title\": \"Hindi title under 70 chars\"}]\n\n" + tx], temperature=0.4, timeout=120)
        if isinstance(res, list):
            for c in res:
                try:
                    a, b = float(c["start"]), float(c["end"])
                except Exception:
                    continue
                # segment boundaries pe snap
                a = max([s["start"] for s in segs if s["start"] <= a + 0.5] or [a])
                b = min([s["end"] for s in segs if s["end"] >= b - 0.5] or [b])
                if 15 <= b - a <= 62:
                    clips.append({"start": a, "end": min(b, total), "title": str(c.get("title", "")),
                                  "yt_title": str(c.get("yt_title", ""))})
    if not clips:
        # fallback: ~45s windows with most speech
        win = 45.0; t = 0.0; cand = []
        while t + 20 < total:
            ss = [s for s in segs if s["start"] >= t and s["end"] <= t + win]
            words = sum(len(s["text"].split()) for s in ss)
            if ss: cand.append((words, ss[0]["start"], ss[-1]["end"], ss[0]["text"]))
            t += win
        cand.sort(reverse=True)
        for w, a, b, txt in sorted(cand[:n], key=lambda x: x[1]):
            clips.append({"start": a, "end": b, "title": " ".join(txt.split()[:4]), "yt_title": txt[:70]})
    clips.sort(key=lambda c: c["start"])
    out = []
    for c in clips:
        if out and c["start"] < out[-1]["end"]: continue
        out.append(c)
    return out[:n]


def main():
    t0 = time.time()
    no_console_freeze()
    LOG_FILE.write_text(f"=== SHORTS {datetime.datetime.now()} ===\n", encoding="utf-8")
    print("\n" + "=" * 56 + "\n   VG SHORTS MAKER  –  lambi video se Shorts, ruko...\n" + "=" * 56 + "\n")
    check_ffmpeg()
    style = read_style(TOOL / "style.txt")
    keys = read_keys()
    folder = TOOL / "lambi_video"; folder.mkdir(exist_ok=True)
    vids = sorted([p for p in folder.iterdir() if p.suffix.lower() in VID], key=lambda p: p.stat().st_mtime)
    if not vids and not os.environ.get("VG_LONG_VIDEO"):
        fail(f"Koi lambi video nahi mili. Apni video yahan daalo: {folder}")
    vids = vids or [Path(os.environ["VG_LONG_VIDEO"])]
    src = vids[-1]
    if os.environ.get("VG_LONG_VIDEO") and Path(os.environ["VG_LONG_VIDEO"]).exists():   # bot se aayi video
        src = Path(os.environ["VG_LONG_VIDEO"])
    total = duration(src)
    log(f"1) Lambi video: {src.name}  ({total/60:.1f} minute)")
    log(f"   Gemini key: {'mili ✓' if keys.get('GEMINI') else 'NAHI MILI ✗ (hisse andaze se chunega)'}")

    import render, motion, align, meta
    from voice import SR
    work = WORK / ("shorts_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    (work / "fonts").mkdir(parents=True, exist_ok=True)
    from common import copy_font
    copy_font(render.FONT, work / "fonts" / render.FONT.name)
    audio = work / "full.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", audio])

    log("2) Whisper video sun raha hai (lambi video me kuch minute lagenge)...")
    words, segs = align.transcribe(audio, style.get("whisper_model_shorts", "small"), "hi")
    if not segs:
        fail("Whisper video sun nahi paya. log.txt Claude ko bhejo.")
    log(f"   {len(segs)} vakya mile ✓")

    n = int(num(style, "shorts_kitne", 1, 10))
    log(f"3) Sabse achhe {n} hisse chun raha hoon...")
    clips = pick_clips(keys.get("GEMINI"), segs, total, n)
    if not clips:
        fail("Koi achha hissa nahi mila (video bahut chhoti?).")
    for i, c in enumerate(clips):
        log(f"   short {i+1}: {c['start']:.0f}s – {c['end']:.0f}s  {c['title']}")

    outdir = OUT / "shorts"; outdir.mkdir(parents=True, exist_ok=True)
    W, H = render.size_for({"format": "short"})
    st = dict(style); st["format"] = "short"; st["layer"] = style.get("shorts_layer", "nahi")
    overlay = work / "overlay.png"; render.overlay_png(st, overlay)
    for i, c in enumerate(clips):
        a, b = c["start"], c["end"]; d = b - a
        log(f"4) Short {i+1}/{len(clips)} bana raha hoon ({d:.0f} sec)...")
        vid = work / f"clip_{i}.mp4"; wav = work / f"clip_{i}.wav"
        vf = render.video_frame_vf(src, W, H, st) + f",fps={render.FPS},setsar=1"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.2f}", "-t", f"{d:.2f}", "-i", src, "-vf", vf, "-an",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "17", "-pix_fmt", "yuv420p", vid])
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.2f}", "-t", f"{d:.2f}", "-i", src, "-vn", "-ac", "1",
             "-ar", str(SR), wav])
        # captions: whisper ke shabd is hisse ke
        sents = []
        for s in segs:
            if s["end"] <= a or s["start"] >= b: continue
            ws = [{"w": w["w"], "start": w["start"] - a, "end": w["end"] - a} for w in (words or [])
                  if w["start"] >= s["start"] - 0.05 and w["end"] <= s["end"] + 0.05 and a <= w["start"] < b]
            if ws:
                sents.append({"text": s["text"], "start": ws[0]["start"], "end": ws[-1]["end"], "words": ws})
        events = motion.find_events(sents, st, d) if sents else []
        hook = [c["title"]] if c.get("title") else None
        ass = work / f"subs_{i}.ass"
        render.write_ass(sents, ass, st, d, events, hook)
        # music halka, asli awaaz
        mix = work / f"mix_{i}.wav"
        st2 = dict(st); st2["sfx"] = "nahi"
        try:
            render.mix_audio(wav, sents, [], [], st2, mix, d, motion.sounds_for(events))
        except Exception:
            shutil.copy(wav, mix)
        name = f"{datetime.datetime.now():%Y-%m-%d}_{safe_name(src.stem, 20)}_short{i+1}"
        out = outdir / f"{name}.mp4"
        shutil.copy(vid, work / "joined.mp4")
        render.final_mux(work / "joined.mp4", overlay, ass, mix, out, st, d, work, events)
        try:
            md = meta.make_meta(keys.get("GEMINI"), [s["text"] for s in sents] or [c["title"]],
                                {"yt_title": c.get("yt_title"), "thumb_text": c.get("title")}, style, [])
            meta.upload_kit(out, md, [], dict(style, youtube_kholo="nahi"), work, ai_voice=False, frame_src=vid)
        except Exception as e:
            log(f"   (upload kit nahi bana: {e})", show=False)
        try:
            meta.to_drive(out, style)
        except Exception:
            pass
        log(f"   short {i+1} ✓  {out.name}")

    print("\n" + "=" * 56)
    print(f"  {len(clips)} SHORTS TAIYAAR!  ({(time.time()-t0)/60:.1f} minute)")
    print(f"  {outdir}")
    print("=" * 56 + "\n")
    if os.name == "nt" and not os.environ.get("VG_BOT"):
        try: os.startfile(outdir)
        except Exception: pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        fail(f"{type(e).__name__}: {e}")
