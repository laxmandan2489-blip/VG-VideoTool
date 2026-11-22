"""v3.64 Cloud Runner for The Viral Gyaan VideoTool (Live Telegram Progress Card + Instant Drive & Telegram Delivery)."""
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "temp" / "cloud_jobs"
JOBS.mkdir(parents=True, exist_ok=True)


def tg_send_text(token, chat_id, text):
    if not token or not chat_id:
        return None
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text[:4000]},
            timeout=30,
        )
        if r.ok:
            return r.json().get("result", {}).get("message_id")
    except Exception as e:
        print("TG text error:", e)
    return None


def tg_edit_text(token, chat_id, msg_id, text):
    if not (token and chat_id and msg_id):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            data={"chat_id": chat_id, "message_id": msg_id, "text": text[:4000]},
            timeout=20,
        )
    except Exception:
        pass


def _stage_from_line(line):
    lo = line.lower()
    if "2)" in line or "awaaz" in lo or "whisper" in lo or "voice" in lo:
        return "🎙️ आवाज़ और Whisper टाइमिंग बन रही है..."
    if "3)" in line or "visuals:" in lo or "footage" in lo or "dhoondh" in lo:
        if "visuals:" in lo:
            return f"🎬 फुटेज और AI विज़ुअल्स ढूँढ रहा है ({line.strip()[-18:]})..."
        return "🎬 स्क्रिप्ट के हिसाब से फुटेज और विज़ुअल्स ढूँढ रहा है..."
    if "4)" in line or "shot " in lo or "shots" in lo or "blender" in lo or "remotion" in lo:
        return "✂️ शॉट्स, कार्ड्स और इफेक्ट्स एडिट हो रहे हैं..."
    if "5)" in line or "captions" in lo or "sound" in lo or "music" in lo:
        return "🎵 कैप्शन, साउंड इफेक्ट्स और म्यूज़िक लग रहे हैं..."
    if "final video" in lo or "final_mux" in lo:
        return "🎞️ फाइनल 1080p HD वीडियो रेंडर हो रही है..."
    if "thumbnail" in lo or "upload kit" in lo:
        return "🖼️ थंबनेल और Upload Kit तैयार हो रही है..."
    return None


def _fmt_elapsed(sec):
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def _make_tg_copy(video_path):
    """If master MP4 > 48 MB, build a crisp < 44 MB Telegram-playable copy in ~10s so user ALWAYS gets instant video!"""
    vp = Path(video_path)
    out_tg = JOBS / "tg_preview.mp4"
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(vp),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
             "-maxrate", "3200k", "-bufsize", "6400k",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_tg)],
            capture_output=True, text=True, timeout=180,
        )
        if r.returncode == 0 and out_tg.exists() and out_tg.stat().st_size < 49 * 1024 * 1024:
            return out_tg
    except Exception as e:
        print("TG compress error:", e)
    return None


def tg_send_document(token, chat_id, path, caption=""):
    """v3.66: chhoti report file (VISUAL_REPORT.md) Telegram par."""
    p = Path(path) if path else None
    if not (token and chat_id and p and p.exists()) or p.stat().st_size > 45 * 1024 * 1024:
        return False
    try:
        with open(p, "rb") as f:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                              data={"chat_id": chat_id, "caption": caption[:950]},
                              files={"document": (p.name, f, "text/markdown")}, timeout=120)
        return r.ok
    except Exception as e:
        print("TG doc error:", e)
        return False


def tg_send_video(token, chat_id, video_path, caption=""):
    if not token or not chat_id:
        return False
    vp = Path(video_path)
    if not vp.exists():
        return False
    size_mb = vp.stat().st_size / (1024 * 1024)
    send_p = vp
    extra_note = ""
    if size_mb > 48.0:
        comp = _make_tg_copy(vp)
        if comp:
            send_p = comp
            extra_note = f"\n(Telegram preview {comp.stat().st_size/(1024*1024):.1f} MB — Full {size_mb:.1f} MB HD Master Drive par hai!)"
        else:
            return False
    try:
        with open(send_p, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={"chat_id": chat_id, "caption": (caption + extra_note)[:950], "supports_streaming": "true"},
                files={"video": (vp.name, f, "video/mp4")},
                timeout=300,
            )
        print("TG sendVideo status:", r.status_code)
        return r.ok
    except Exception as e:
        print("TG video error:", e)
        return False


def public_link(video_path):
    """v3.75: phone ke liye SEEDHA download link (login nahi, Drive setup nahi).
    Litterbox (catbox.moe) – link 72 ghante chalta hai; fail ho to 0x0.st. Link jiske paas ho wahi khol sakta hai.
    Band karna ho: GitHub Secret / env VG_PUBLIC_LINK = nahi."""
    if (os.environ.get("VG_PUBLIC_LINK") or "haan").strip().lower() in ("nahi", "no", "0", "off"):
        return None, "band hai"
    vp = Path(video_path)
    if not vp.exists():
        return None, "file nahi"
    errs = []
    hosts = [
        ("litterbox", "https://litterbox.catbox.moe/resources/internals/api.php",
         {"reqtype": "fileupload", "time": "72h"}, "fileToUpload", 1000),
        ("0x0", "https://0x0.st", {}, "file", 512),
    ]
    size_mb = vp.stat().st_size / (1024 * 1024)
    for name, url, data, field, max_mb in hosts:
        if size_mb > max_mb:
            errs.append(f"{name}: file badi"); continue
        for attempt in range(2):
            try:
                with open(vp, "rb") as f:
                    r = requests.post(url, data=data, files={field: (f"VG_video_{time.strftime('%Y%m%d_%H%M')}.mp4", f, "video/mp4")},
                                      headers={"User-Agent": "VG-VideoTool/3.75"}, timeout=300)
                link = (r.text or "").strip()
                if r.ok and link.startswith("http") and " " not in link and len(link) < 200:
                    return link, ("72 ghante" if name == "litterbox" else "kam se kam 30 din")
                errs.append(f"{name}: HTTP {r.status_code}")
            except Exception as e:
                errs.append(f"{name}: {str(e)[:60]}")
    return None, "; ".join(errs)[:160]


def _prepare_rclone():
    conf = (os.environ.get("RCLONE_CONF") or "").strip()
    if not conf:
        return None, "RCLONE_CONF secret khali hai"
    idx = conf.find("[gdrive]")
    if idx != -1:
        conf = conf[idx:]
    rclone_cfg = Path.home() / ".config" / "rclone" / "rclone.conf"
    rclone_cfg.parent.mkdir(parents=True, exist_ok=True)
    rclone_cfg.write_text(conf.strip() + "\n", encoding="utf-8")
    return rclone_cfg, None


def upload_video_first(video_path):
    """STEP 1 (INSTANT): Upload ONLY the master MP4 to Google Drive first & return (url_or_path, err_msg)."""
    cfg, err = _prepare_rclone()
    if err:
        return None, err
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    remote_dir = f"gdrive:VG Videos/{today}"
    remote_file = f"{remote_dir}/{Path(video_path).name}"
    try:
        cp = subprocess.run(["rclone", "copy", str(video_path), remote_dir], capture_output=True, text=True, timeout=300)
        if cp.returncode != 0:
            return None, (cp.stderr or cp.stdout or "rclone copy failed").strip()[-220:]
        lk = subprocess.run(["rclone", "link", remote_file], capture_output=True, text=True, timeout=60)
        url = (lk.stdout or "").strip()
        return (url if url.startswith("http") else f"VG Videos/{today}/{Path(video_path).name}"), None
    except Exception as e:
        return None, str(e)[:200]


def upload_extras_background(video_path):
    """STEP 3 (AFTER USER ALREADY HAS VIDEO): Upload thumbnails, UPLOAD.txt, EDL, and _EDIT_KIT/ to Drive."""
    cfg, err = _prepare_rclone()
    if err:
        return
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    remote_dir = f"gdrive:VG Videos/{today}"
    stem = Path(video_path).stem
    for ext_f in Path(video_path).parent.glob(f"{stem}*"):
        try:
            if ext_f.is_file() and ext_f != Path(video_path):
                subprocess.run(["rclone", "copy", str(ext_f), remote_dir], check=False, timeout=120)
            elif ext_f.is_dir() and ext_f.name.endswith("_EDIT_KIT"):
                subprocess.run(["rclone", "copy", str(ext_f), f"{remote_dir}/{ext_f.name}"], check=False, timeout=300)
        except Exception as e:
            print("Extra upload skip:", e)


def auto_setup():
    """v3.68: Deno (YouTube ke liye) + naya yt-dlp KHUD – workflow file badalne ki zaroorat nahi."""
    import shutil
    bindir = str(Path(sys.executable).parent)
    if bindir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")
    if shutil.which("deno"):
        print("auto_setup: deno mila ✓")
        return
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "deno", "yt-dlp[default]"],
                           capture_output=True, text=True, timeout=240)
        print("auto_setup:", "deno + yt-dlp lag gaye ✓" if r.returncode == 0 else r.stderr[-200:])
    except Exception as e:
        print("auto_setup skip:", e)


def main():
    t0 = time.time()
    auto_setup()
    script_text = (os.environ.get("INPUT_SCRIPT") or "").strip()
    video_mode = (os.environ.get("INPUT_MODE") or "SHORT").strip().upper()
    tg_token = (os.environ.get("TG_TOKEN") or "").strip()
    tg_chat = (os.environ.get("TG_CHAT_ID") or "").strip()

    if not script_text:
        print("ERROR: Script khali hai!")
        sys.exit(1)

    if video_mode == "LONG" and not script_text.upper().startswith("LONG"):
        script_text = "LONG\n" + script_text

    keys_lines = []
    for env_k, file_k in [
        ("GEMINI_KEY", "GEMINI_API_KEY"),
        ("PIXABAY_KEY", "PIXABAY_API_KEY"),
        ("PEXELS_KEY", "PEXELS_API_KEY"),
        ("YOUTUBE_KEY", "YOUTUBE_API_KEY"),
        ("GROQ_KEY", "GROQ_API_KEY"),
        ("OPENROUTER_KEY", "OPENROUTER_API_KEY"),   # v3.66: Gemini limit khatam -> free backup AI
        ("BRAVE_KEY", "BRAVE_API_KEY"),             # v3.66: optional extra video/photo search
    ]:
        if os.environ.get(env_k):
            keys_lines.append(f"{file_k}={os.environ[env_k].strip()}")
    if tg_token:
        keys_lines.append(f"TELEGRAM_BOT_TOKEN={tg_token}")
    if tg_chat:
        keys_lines.append(f"TELEGRAM_CHAT_ID={tg_chat}")
    (ROOT / "api keys.txt").write_text("\n".join(keys_lines) + "\n", encoding="utf-8")

    # v3.67: "SYSTEM JAANCH KARO" -> video nahi, sirf cloud ki har cheez test karke Telegram report
    _first = script_text.strip().splitlines()[0].strip().upper() if script_text.strip() else ""
    if _first.startswith(("SYSTEM JAANCH", "YTDLP JAANCH", "SYSTEM CHECK")):
        sid = tg_send_text(tg_token, tg_chat, "🩺 SYSTEM JAANCH shuru – 1-3 minute (video nahi banegi)...")
        try:
            sys.path.insert(0, str(ROOT / "app"))
            import net_check
            msg, _rows = net_check.run(full=True)
        except Exception as e:
            msg = f"🩺 SYSTEM JAANCH fail: {e}"
        print(msg)
        tg_edit_text(tg_token, tg_chat, sid, msg[:4000]) if sid else tg_send_text(tg_token, tg_chat, msg)
        sys.exit(0)

    sp = JOBS / "script_cloud.txt"
    res = JOBS / "result_cloud.json"
    sp.write_text(script_text + "\n", encoding="utf-8")
    try: res.unlink()                                 # v3.74: pichhli video ka result galti se na uthe
    except Exception: pass

    first_line = next((l.strip() for l in script_text.splitlines() if l.strip() and l.strip().upper() not in ("LONG", "SHORT")), "Cloud Video")[:55]

    # v3.64: Create ONE live-updating Telegram progress card for THIS video!
    status_id = tg_send_text(
        tg_token, tg_chat,
        f"🎬 [{video_mode}] {first_line}\n⏳ क्लाउड सर्वर तैयार हो गया — काम शुरू हो रहा है..."
    )

    env = dict(os.environ)
    env["VG_SCRIPT"] = str(sp)
    env["VG_RESULT"] = str(res)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["VG_STYLE_JSON"] = json.dumps({"remotion_beats": "haan", "blender_doc_stage": "haan", "ek_saath_shots": "2"})
    env.setdefault("VG_VISUAL_THREADS", "5")   # v3.78: cloud pe 5 lines ek saath (RAM 7 GB pe pehle 2 hi chalti thi)
    # v3.77: quality loop ko kitna samay mil sakta hai (GitHub job limit se pehle video bhejni hai)
    _hl = float(os.environ.get("VG_HARD_LIMIT_MIN", "46"))
    env.setdefault("VG_TIME_BUDGET_MIN", str(max(20.0, _hl - 6 - (time.time() - t0) / 60)))

    proc = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "app" / "make_video.py")],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        start_new_session=(os.name != "nt"),         # v3.74: bache hue Chrome/ffmpeg ko poore group ke saath band kar sakein
    )
    last_stage = "⏳ स्क्रिप्ट पढ़ी जा रही है..."
    last_edit = 0.0
    # v3.73 WATCHDOG: atke / bahut der chale to KHUD Telegram par batao + log bhejo (raat ko bhi pata chale)
    import collections, threading
    W = {"last_out": time.time(), "tail": collections.deque(maxlen=40), "killed": "", "warned": False,
         "stage": last_stage}
    STALL_WARN = float(os.environ.get("VG_STALL_WARN_MIN", "10")) * 60
    STALL_KILL = float(os.environ.get("VG_STALL_KILL_MIN", "22")) * 60
    HARD_LIMIT = float(os.environ.get("VG_HARD_LIMIT_MIN", "46")) * 60   # GitHub job 55 min pe chupchaap katta hai

    def _kill_all():
        """v3.74: make_video + uske bache hue bachche (Chrome thumbnail, ffmpeg, yt-dlp) sab band."""
        try:
            if hasattr(os, "killpg"):
                import signal
                os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass

    def _video_ready():
        try:
            if res.exists():
                d_ = json.loads(res.read_text(encoding="utf-8"))
                v_ = d_.get("video")
                return bool(v_ and Path(v_).exists())
        except Exception:
            return False
        return False

    def watchdog():
        last_beat = time.time()
        while proc.poll() is None:
            time.sleep(max(1.0, min(20.0, STALL_WARN / 3)))
            now_ = time.time()
            idle = now_ - W["last_out"]; el = now_ - t0
            if idle >= STALL_WARN and not W["warned"]:
                W["warned"] = True
                tg_send_text(tg_token, tg_chat,
                             f"⚠️ [{video_mode}] {first_line}\n{int(idle // 60)} minute se koi progress nahi.\n"
                             f"Kahan atka: {W['stage']}\nAakhri lines:\n" + "".join(list(W["tail"])[-8:])[-1500:] +
                             f"\n(Agar {int(STALL_KILL // 60)} min tak aise raha to main khud band karke log bhejunga.)")
            if idle < min(60.0, STALL_WARN / 2) and W["warned"]:      # nayi hal-chal aayi -> agli baar phir chetavni
                W["warned"] = False
            reason = ""
            if _video_ready() and idle >= 60:                # v3.74: video ban chuki, program band nahi ho raha -> aage badho
                W["done_but_stuck"] = True
                _kill_all(); return
            if idle >= STALL_KILL:
                reason = f"{int(idle // 60)} minute se atki hui thi ({W['stage']})"
            elif el >= HARD_LIMIT:
                reason = f"{int(el // 60)} minute ho gaye – GitHub 55 min pe chupchaap kaat deta, isliye pehle hi roki"
            if reason:
                W["killed"] = reason
                _kill_all()
                return
            if now_ - last_beat >= 150:                    # har 2.5 min: card par 'zinda hai' + samay
                last_beat = now_
                tg_edit_text(tg_token, tg_chat, status_id,
                             f"🎬 [{video_mode}] {first_line}\n{W['stage']}\n⏱ समय: {_fmt_elapsed(el)}"
                             f" | आखिरी हलचल: {int(idle)} सेकंड पहले")

    threading.Thread(target=watchdog, daemon=True).start()

    def _lines():
        try:
            for ln in proc.stdout:
                yield ln
        except Exception:
            return

    import queue
    LQ = queue.Queue()

    def _reader():                                   # v3.74: padhna alag thread me – EOF ka intezaar main kaam na roke
        for ln in _lines():
            LQ.put(ln)
        LQ.put(None)

    threading.Thread(target=_reader, daemon=True).start()

    def _stream():
        exited_at = None
        while True:
            try:
                ln = LQ.get(timeout=2)
            except queue.Empty:
                if proc.poll() is not None:
                    exited_at = exited_at or time.time()
                    if time.time() - exited_at > 15:   # program khatam, par koi bachcha pipe pakde baitha -> mat ruko
                        print("cloud_run: make_video khatam – bache hue process band kar raha hoon")
                        _kill_all()
                        return
                continue
            if ln is None:
                return
            yield ln

    for raw_line in _stream():
        sys.stdout.write(raw_line)
        sys.stdout.flush()
        W["last_out"] = time.time(); W["tail"].append(raw_line[:300])
        st = _stage_from_line(raw_line)
        if st: W["stage"] = st
        now = time.time()
        if st and (st != last_stage or (now - last_edit) >= 18):
            last_stage = st
            if (now - last_edit) >= 8:
                tg_edit_text(
                    tg_token, tg_chat, status_id,
                    f"🎬 [{video_mode}] {first_line}\n{last_stage}\n⏱ समय: {_fmt_elapsed(now - t0)}"
                )
                last_edit = now
    rc = proc.wait()
    _kill_all()                                       # v3.74: Chrome jaise bache process bhi band (disk/RAM free)
    if W.get("done_but_stuck") and _video_ready():
        rc = 0
    print("make_video.py exit code:", rc)

    out_mp4 = None
    vrep_md = None; vrep_sum = None; review_sc = None
    if res.exists():
        try:
            data = json.loads(res.read_text(encoding="utf-8"))
            cand = data.get("video") or data.get("out") or data.get("path")
            vrep_md = data.get("visual_report"); vrep_sum = data.get("visual_summary")
            review_sc = (data.get("review") or {}).get("score")
            if cand and Path(cand).exists():
                out_mp4 = Path(cand)
        except Exception as e:
            print("result parse err:", e)

    if not out_mp4 and (ROOT / "output").exists():
        mp4s = sorted([p for p in (ROOT / "output").glob("*.mp4") if p.stat().st_mtime >= t0 - 5],   # v3.74: purani nahi
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            out_mp4 = mp4s[0]

    if out_mp4 and out_mp4.exists():
        art = ROOT / "cloud_output.mp4"
        art.write_bytes(out_mp4.read_bytes())
        size_mb = out_mp4.stat().st_size / (1024 * 1024)

        tg_edit_text(
            tg_token, tg_chat, status_id,
            f"🎬 [{video_mode}] {first_line}\n☁️ वीडियो बन गई ({size_mb:.1f} MB)! 5 TB Google Drive और Telegram पर भेज रहा हूँ...\n⏱ समय: {_fmt_elapsed(time.time() - t0)}"
        )

        # v3.75 STEP 0: seedha download link (phone pe turant) – sabse pehle, taaki Telegram fail ho tab bhi mile
        dl_link, dl_err = public_link(out_mp4)
        if dl_link:
            tg_send_text(tg_token, tg_chat, f"⬇️ Video download link ({dl_err} chalega):\n{dl_link}\n\n"
                                            f"Tap karo -> browser me chalegi; ⋮ -> Download se phone me save.\n{first_line}")
        else:
            print("public link fail:", dl_err)

        # STEP 1: INSTANT Master MP4 upload to Google Drive FIRST!
        drive_info, drive_err = upload_video_first(out_mp4)
        _gh_srv = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        _gh_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
        _gh_rid = os.environ.get("GITHUB_RUN_ID", "").strip()
        _gh_url = f"{_gh_srv}/{_gh_repo}/actions/runs/{_gh_rid}" if (_gh_repo and _gh_rid) else ""
        cap = f"✅ Cloud Video Ready ({size_mb:.1f} MB • {_fmt_elapsed(time.time() - t0)})\n{first_line}"
        if review_sc is not None:
            cap += f"\n🎯 Visual score: {review_sc}/100" + (" ✅" if float(review_sc) >= 90 else " (90 se kam – report dekho)")
        if dl_link:
            cap += f"\n⬇️ Download: {dl_link}"
        if drive_info:
            cap += f"\n📁 Drive HD: {drive_info}"
        if _gh_url:
            cap += f"\n⬇️ Direct HD Download: {_gh_url}"
        if not drive_info and drive_err and "khali" not in drive_err:   # Drive set nahi hai to faltu chetavni nahi
            cap += f"\n⚠️ Drive: {drive_err[:100]}"

        # STEP 2: INSTANT playable video in Telegram (auto-compressed <45MB if master >48MB!)
        sent_vid = tg_send_video(tg_token, tg_chat, out_mp4, caption=cap)
        if not sent_vid:
            tg_send_text(tg_token, tg_chat, cap + "\n(Telegram video upload fail — upar Drive link ya GitHub Actions se download kar lo)")

        tg_edit_text(
            tg_token, tg_chat, status_id,
            f"✅ [{video_mode}] {first_line}\nपूरा हो गया! ({size_mb:.1f} MB • {_fmt_elapsed(time.time() - t0)})"
            + (f"\n⬇️ {dl_link}" if dl_link else "") + "\n📦 अब बैकग्राउंड में _EDIT_KIT और थंबनेल Drive पर सेव हो रहे हैं..."
        )

        # v3.66: Visual Report (har line: kya samjha, kya chuna, kyun, kya reject) – Telegram par file
        if vrep_md:
            try:
                _s = vrep_sum or {}
                _cap = (f"🧾 Visual Report: {_s.get('category', '?')} | asli/achha match {_s.get('real_or_good_pct', '?')}% | "
                        f"AI photo {_s.get('ai_shots', 0)}" + (f" | ⚠️ {_s['fact_flags']} fact flag" if _s.get("fact_flags") else ""))
                _y = _s.get("youtube") or {}; _so = _s.get("social") or {}
                if _y or _so:
                    _cap += (f"\n🎞 YouTube clip {_y.get('clips', 0)}" + (f" (block {_y['blocked']})" if _y.get("blocked") else "")
                             + f" | X {_so.get('x', 0)} | Pinterest {_so.get('pinterest', 0)}")
                    if _y.get("why") and not _y.get("clips"): _cap += f"\n⚠️ {_y['why'][:120]}"
                tg_send_document(tg_token, tg_chat, vrep_md, _cap)
            except Exception as _e:
                print("visual report send skip:", _e)

        # STEP 3: Upload _EDIT_KIT & thumbnails in background AFTER user already received the video!
        upload_extras_background(out_mp4)
        tg_edit_text(
            tg_token, tg_chat, status_id,
            f"✅ [{video_mode}] {first_line}\nसब कुछ पूरा हो गया! ({size_mb:.1f} MB • {_fmt_elapsed(time.time() - t0)})"
            + (f"\n⬇️ {dl_link}" if dl_link else "") + ("\n📁 Drive पर भी सेव ✓" if drive_info else "")
        )
        sys.exit(0)
    else:
        log_file = ROOT / "log.txt"
        tail = "\n".join(log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-25:]) if log_file.exists() else "No log.txt"
        why = W.get("killed") or f"program band ho gaya (rc={rc})"
        try: (JOBS / "tg_notified").write_text("1")      # workflow ka 'fail' step dobara message na bheje
        except Exception: pass
        tg_edit_text(tg_token, tg_chat, status_id, f"❌ [{video_mode}] {first_line}\nवीडियो नहीं बन पाई – {why}")
        tg_send_text(tg_token, tg_chat, f"❌ Cloud video nahi ban payi – {why}\nAakhri stage: {W.get('stage')}\n"
                                         f"Last log:\n{tail}"[:3900])
        if log_file.exists():                          # v3.73: poori log file – seedha Claude/Gemini ko forward karo
            try:
                lp = JOBS / "log_for_fix.txt"
                lp.write_text(log_file.read_text(encoding="utf-8", errors="ignore")[-400000:], encoding="utf-8")
                tg_send_document(tg_token, tg_chat, lp, "📋 Poori log file – ye file Claude/Gemini ko bhej do, wo wajah pakad lenge.")
            except Exception as e:
                print("log send skip:", e)
        sys.exit(rc or 1)


if __name__ == "__main__":
    main()
