"""v3.16 EDIT KIT – tool ki video me 1-2 visual galat hon to KHUD 10-30 minute me theek karo (CapCut / bina software).

User (16 Nov 2026): "agar last me sab sahi nahi laga to main visual sahi kar sakun – CapCut se jud jaaye ya jisse bhi,
mere HP laptop pe chale. Main busy rehta hoon, aadha-ek ghanta."

Har video ke saath output\\<naam>_EDIT_KIT\\ banta hai:
  shots\\                 har cut ki alag clip (01_L1_shot_000.mp4 ...) – exact lambai, bina captions
  BADLO\\                 yahan apni sahi clip / photo daalo:  line_3.mp4  (poori line 3)  ya  shot_005.jpg (sirf ek cut)
  VISUAL_BADLO.bat       BADLO wali files laga ke NAYI final video bana deta hai (captions, awaaz, music, logo wahi)
  awaaz_poori.wav        voice + music + sound effects (CapCut ke liye)
  sirf_awaaz.wav         sirf narration
  captions.srt           har line ka text + time (CapCut: Text > Captions > Import / local captions)
  video_bina_captions.mp4  poori video bina captions/logo (CapCut me upar se apne captions)
  SHOT_LIST.txt          kaunsa shot kis line ka, kitne second, kahan se aaya
  CAPCUT_ME_KAISE.txt    CapCut desktop me 5 minute me kholne ka tareeka

Telegram se bhi:  /badlo 3   likho, phir sahi clip/photo bhejo (ya  /badlo 3 https://youtu.be/...  45)
-> bot nayi video bana ke bhej deta hai.
"""
import json, re, shutil, subprocess, sys, time
from pathlib import Path

try:
    from common import log, TOOL
except Exception:                                    # VISUAL_BADLO.bat seedha bhi chal sake
    TOOL = Path(__file__).resolve().parent.parent
    def log(m, show=True): print(m)

VEXT = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")
IEXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def _run(cmd, cwd=None, timeout=900):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, stdin=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "")[-500:])
    return r


def _srt_t(t):
    t = max(0.0, float(t)); ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _kit_dir(out):
    out = Path(out)
    return out.with_name(out.stem + "_EDIT_KIT")


def export(out, work, files, plan, line_start, sents, fps, W, H, final, voice_wav=None, credits_of=None):
    """make_video ke aakhir me. final = render.LAST_FINAL. Return kit path ya None."""
    work = Path(work); kit = _kit_dir(out)
    if kit.exists(): shutil.rmtree(kit, ignore_errors=True)
    (kit / "shots").mkdir(parents=True, exist_ok=True)
    (kit / "BADLO").mkdir(exist_ok=True)
    (kit / "_final").mkdir(exist_ok=True)
    # line har shot ki
    cur = 0; line_of = []
    for n in range(len(plan)):
        if n in line_start: cur = line_start[n]
        line_of.append(cur)
    shots = []
    for n, ((a, b, it), f) in enumerate(zip(plan, files)):
        fa = int(round(a * fps)); fb = int(round(b * fps)); frames = max(2, fb - fa)
        li = line_of[n]
        nice = f"{n+1:02d}_L{li+1}_shot_{n:03d}.mp4"
        try:
            shutil.copy2(f, kit / "shots" / nice)
        except Exception as e:
            log(f"   (edit kit: {Path(f).name} copy nahi hua: {e})", show=False)
        src = str((it or {}).get("src") or "")
        shots.append({"n": n, "file": nice, "line": li, "start": round(fa / fps, 3), "frames": frames,
                      "dur": round(frames / fps, 3), "src": src,
                      "from": str((it or {}).get("credit") or (it or {}).get("path") or "")[:200],
                      "kind": (it or {}).get("kind")})
    # final command ke input (relative naam) _final me
    cmd = list(final.get("cmd") or [])
    fcwd = Path(final.get("cwd") or work)
    need = set()
    for k_, a_ in enumerate(cmd):
        if k_ and cmd[k_ - 1] == "-i" and not Path(a_).is_absolute() and not a_.startswith(("color=", "anullsrc")):
            need.add(a_)
        for m in re.finditer(r"ass=([^:,\]\[;]+)", a_):
            need.add(m.group(1))
    for nm in need | {"subs.ass"}:
        p = fcwd / nm
        if p.is_file() and nm not in ("joined.mp4", "loop_first.png"):
            try: shutil.copy2(p, kit / "_final" / nm)
            except Exception: pass
    if (fcwd / "fonts").is_dir():
        shutil.copytree(fcwd / "fonts", kit / "_final" / "fonts", dirs_exist_ok=True)
    # audio + video bina captions + srt
    mix = next((fcwd / a_ for k_, a_ in enumerate(cmd) if k_ and cmd[k_ - 1] == "-i" and a_.endswith(".wav")), None)
    total = float(final.get("total") or 0) or (sum(s["dur"] for s in shots))
    try:
        if mix and mix.exists(): shutil.copy2(mix, kit / "awaaz_poori.wav")
        if voice_wav and Path(voice_wav).exists(): shutil.copy2(voice_wav, kit / "sirf_awaaz.wav")
    except Exception:
        pass
    try:
        j = work / "joined.mp4"
        if j.exists() and (kit / "awaaz_poori.wav").exists():
            _run(["ffmpeg", "-y", "-v", "error", "-i", j, "-i", kit / "awaaz_poori.wav", "-map", "0:v", "-map", "1:a",
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", kit / "video_bina_captions.mp4"])
    except Exception as e:
        log(f"   (edit kit: bina-caption video nahi bani: {str(e)[:100]})", show=False)
    srt = []
    for k_, s in enumerate(sents):
        st = s.get("start", 0.0) if k_ else 0.0
        en = sents[k_ + 1]["start"] if k_ + 1 < len(sents) else total
        srt.append(f"{k_+1}\n{_srt_t(st)} --> {_srt_t(max(st + 0.3, en - 0.05))}\n{s.get('script') or s.get('text')}\n")
    (kit / "captions.srt").write_text("\n".join(srt), encoding="utf-8-sig")
    man = {"version": 1, "out": str(Path(out).resolve()), "fps": fps, "W": W, "H": H, "total": total,
           "cmd": cmd, "shots": shots,
           "lines": [(s.get("script") or s.get("text") or "") for s in sents], "made": time.strftime("%Y-%m-%d %H:%M")}
    (kit / "kit.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = ["SHOT LIST – kaunsa cut kis line ka (BADLO folder me isi naam se file daalo)", ""]
    for k_, ln in enumerate(man["lines"]):
        ss = [s for s in shots if s["line"] == k_]
        if not ss: continue
        rows.append(f"LINE {k_+1}  ({ss[0]['start']:.1f}s, {sum(s['dur'] for s in ss):.1f}s):  {ln[:90]}")
        rows.append(f"    poori line badlo ->  BADLO\\line_{k_+1}.mp4  (ya .jpg)")
        for s in ss:
            rows.append(f"    shot_{s['n']:03d}  {s['dur']:.2f}s  {s['kind'] or ''}  {s['src'][:25]}  {s['from'][:70]}")
        rows.append("")
    (kit / "SHOT_LIST.txt").write_text("\n".join(rows), encoding="utf-8-sig")
    (kit / "CAPCUT_ME_KAISE.txt").write_text(CAPCUT_HELP, encoding="utf-8-sig")
    bat = ("@echo off\r\nchcp 65001 >nul\r\ncd /d \"%~dp0\"\r\ntitle VISUAL BADLO\r\n"
           f"set \"APPD={TOOL}\\app\"\r\n"
           "if exist \"%~dp0..\\..\\app\\edit_kit.py\" set \"APPD=%~dp0..\\..\\app\"\r\n"
           "set \"PY=python\"\r\nwhere py >nul 2>nul && set \"PY=py -3\"\r\n"
           "if exist \"%APPD%\\..\\venv\\Scripts\\python.exe\" set PY=\"%APPD%\\..\\venv\\Scripts\\python.exe\"\r\n"
           "%PY% \"%APPD%\\edit_kit.py\" rebuild \"%~dp0.\"\r\npause\r\n")
    (kit / "VISUAL_BADLO.bat").write_bytes(bat.encode("utf-8"))
    log(f"   🧰 Edit Kit: {kit.name} (galat visual khud badlo – BADLO folder + VISUAL_BADLO.bat, ya Telegram /badlo)")
    return kit


def _conform(src, dst, frames, fps, W, H, ss=0.0):
    src = Path(src)
    enc = ["-an", "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
           "-pix_fmt", "yuv420p", "-r", str(fps), "-video_track_timescale", "15360"]
    if src.suffix.lower() in IEXT:
        # photo -> dheema push-in (Ken Burns), poori screen
        bw, bh = int(W * 1.25) // 2 * 2, int(H * 1.25) // 2 * 2
        vf = (f"scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},setsar=1,"
              f"zoompan=z='1+0.10*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={fps}")
        _run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(fps), "-i", src, "-vf", vf] + enc + [dst])
    else:
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={fps},setsar=1,"
              f"eq=contrast=1.05:saturation=1.08")
        _run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-ss", f"{max(0.0, ss):.2f}", "-i", src,
              "-vf", vf] + enc + [dst])
    return dst


def _parse_badlo(kit, man):
    """BADLO folder -> {shot_index: (file, ss)}"""
    rep = {}
    for f in sorted((kit / "BADLO").iterdir()):
        if f.suffix.lower() not in VEXT + IEXT: continue
        stem = f.stem.lower()
        ss = 0.0
        m_ss = re.search(r"[_@](\d+(?:\.\d+)?)s$", stem)            # line_3_45s.mp4 -> 45 sec se
        if m_ss: ss = float(m_ss.group(1)); stem = stem[:m_ss.start()]
        m = re.match(r"line[_ -]?(\d+)$", stem)
        if m:
            li = int(m.group(1)) - 1
            idx = [s["n"] for s in man["shots"] if s["line"] == li]
            if idx: rep[tuple(idx)] = (f, ss)
            continue
        m = re.match(r"(?:\d+_l\d+_)?shot[_ -]?(\d+)$", stem)
        if m:
            rep[(int(m.group(1)),)] = (f, ss)
    return rep


def rebuild(kit, out_name=None):
    """BADLO folder ki files laga ke nayi final video. Return nayi video ka path."""
    kit = Path(kit).resolve()
    man = json.loads((kit / "kit.json").read_text(encoding="utf-8"))
    fps, W, H = int(man["fps"]), int(man["W"]), int(man["H"])
    rep = _parse_badlo(kit, man)
    if not rep:
        print("\n  BADLO folder khaali hai. Isme apni clip/photo daalo, naam:  line_3.mp4  ya  shot_005.jpg")
        print("  (kaunsa number kis line ka – SHOT_LIST.txt dekho)")
        return None
    fin = kit / "_final"; tmp = fin / "_naye_shots"; tmp.mkdir(exist_ok=True)
    seq = []; done = set()
    for s in man["shots"]:
        if s["n"] in done: continue
        hit = next(((k, v) for k, v in rep.items() if s["n"] in k), None)
        if hit:
            k, (f, ss) = hit
            fr = sum(x["frames"] for x in man["shots"] if x["n"] in k)
            dst = tmp / f"new_{min(k):03d}.mp4"
            print(f"  ✓ {f.name} -> shot {', '.join(str(x) for x in k)} ({fr / fps:.2f}s)")
            _conform(f, dst, fr, fps, W, H, ss)
            seq.append(dst); done.update(k)
        else:
            seq.append(kit / "shots" / s["file"]); done.add(s["n"])
    lst = fin / "list.txt"
    lst.write_text("".join(f"file '{Path(p).as_posix()}'\n" for p in seq), encoding="utf-8")
    print("  ⏳ shots jod raha hoon...")
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-an", "-c:v", "libx264",
          "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", str(fps), "joined.mp4"], cwd=fin)
    _run(["ffmpeg", "-y", "-v", "error", "-ss", "0.05", "-i", "joined.mp4", "-frames:v", "1", "loop_first.png"], cwd=fin)
    cmd = list(man["cmd"])
    old_out = Path(man["out"])
    new_out = old_out.with_name((out_name or (old_out.stem + "_THEEK_" + time.strftime("%H%M"))) + old_out.suffix)
    cmd[-1] = str(new_out)
    print("  ⏳ final video bana raha hoon (captions, awaaz, logo wahi)... 1-4 minute")
    _run(cmd, cwd=fin, timeout=1800)
    print(f"\n  ✅ NAYI VIDEO: {new_out}\n")
    try:                                                    # BADLO ki files 'laga_diya' me (dobara na lage)
        used = kit / "BADLO" / "laga_diya"; used.mkdir(exist_ok=True)
        for _, (f, _) in rep.items():
            if f.exists(): f.replace(used / f.name)
    except Exception:
        pass
    return new_out


def last_kit():
    """output folder ka sabse naya Edit Kit."""
    out = TOOL / "output"
    kits = sorted([p for p in out.glob("*_EDIT_KIT") if (p / "kit.json").exists()], key=lambda p: p.stat().st_mtime)
    return kits[-1] if kits else None


def youtube_part(url, ss, dur, dst):
    """Telegram /badlo 3 <youtube link> <second>: sirf us hisse ko download."""
    a = max(0.0, float(ss)); b = a + max(2.0, float(dur)) + 0.5
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "-f", "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b",
                        "--download-sections", f"*{a:.1f}-{b:.1f}", "--force-keyframes-at-cuts", "-o", str(dst),
                        "--no-playlist", url], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300, stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    got = sorted(Path(dst).parent.glob(Path(dst).stem + "*"))
    if r.returncode != 0 or not got:
        raise RuntimeError((r.stderr or "")[-300:])
    return got[0]


CAPCUT_HELP = """CAPCUT (free, Windows) ME IS VIDEO KO 5 MINUTE ME KHOLNA
===========================================================

SABSE AASAAN (CapCut ki zaroorat bhi nahi):
  1. SHOT_LIST.txt kholo – dekho kaunsi LINE ka visual galat hai (jaise line 3).
  2. Sahi clip / photo dhoondho (YouTube, Pixabay, apne phone se) aur BADLO folder me daalo, naam:
        line_3.mp4        -> poori line 3 ka visual badlega
        shot_005.jpg      -> sirf shot 5 badlega
        line_3_45s.mp4    -> clip ke 45th second se shuru karega
  3. VISUAL_BADLO.bat pe double-click. 1-4 minute me nayi video output folder me ("..._THEEK_....mp4").
     Captions, awaaz, music, logo, subscribe sab waise hi rahenge.
  Phone se: Telegram me  /badlo 3  likho, phir clip/photo bhejo. (Ya: /badlo 3 https://youtu.be/xxxx 45)

CAPCUT ME POORA EDIT (jab zyada badalna ho):
  1. CapCut desktop kholo -> New project -> canvas 9:16.
  2. "shots" folder ki SAARI files select karke timeline pe ek saath kheencho (naam ke kram me hi lagengi:
     01_, 02_ ... – har ek ki lambai pehle se sahi hai).
  3. awaaz_poori.wav ko audio track pe kheencho (shuru 0:00 se). Video ki apni awaaz nahi hai.
  4. Captions: Text -> Captions -> "Import captions" / local captions -> captions.srt
     (ya CapCut ke Auto captions – Hindi).
  5. Jo shot galat hai: us clip pe right-click -> Replace clip -> apni clip. Lambai wahi rahegi.
  6. Export -> 1080p, 30fps.

  Jaldi wala tareeka: video_bina_captions.mp4 ek hi file me poori video (awaaz ke saath, bina captions/logo)
  hai – isse CapCut me daal ke upar se apni clip overlay kar sakte ho.

DaVinci Resolve (free): EDL file bhi output folder me hai (..._EDL.edl) – shots folder se relink karo.
"""


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "rebuild":
        try:
            rebuild(sys.argv[2])
        except Exception as e:
            print(f"\n  GADBAD: {e}\n  (Telegram pe /log bhejo ya ye message Claude ko dikhao)")
    else:
        print("use: edit_kit.py rebuild <EDIT_KIT folder>")
