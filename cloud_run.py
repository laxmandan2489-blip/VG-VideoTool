"""Cloud Runner for The Viral Gyaan VideoTool (GitHub Actions -> Google Drive + Telegram)."""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "temp" / "cloud_jobs"
JOBS.mkdir(parents=True, exist_ok=True)


def tg_send_text(token, chat_id, text):
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text[:4000]},
            timeout=30,
        )
    except Exception as e:
        print("TG text error:", e)


def tg_send_video(token, chat_id, video_path, caption=""):
    if not token or not chat_id:
        return False
    vp = Path(video_path)
    if not vp.exists():
        return False
    size_mb = vp.stat().st_size / (1024 * 1024)
    if size_mb > 49.0:
        return False
    try:
        with open(vp, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={"chat_id": chat_id, "caption": caption[:900], "supports_streaming": "true"},
                files={"video": (vp.name, f, "video/mp4")},
                timeout=300,
            )
        print("TG sendVideo status:", r.status_code)
        return r.ok
    except Exception as e:
        print("TG video error:", e)
        return False


def upload_to_gdrive(video_path):
    """Upload video to Google Drive VG Videos/YYYY-MM-DD/ via rclone if RCLONE_CONF is set."""
    conf = (os.environ.get("RCLONE_CONF") or "").strip()
    if not conf:
        return None
    try:
        rclone_cfg = Path.home() / ".config" / "rclone" / "rclone.conf"
        rclone_cfg.parent.mkdir(parents=True, exist_ok=True)
        rclone_cfg.write_text(conf + "\n", encoding="utf-8")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        remote_dir = f"gdrive:VG Videos/{today}"
        remote_file = f"{remote_dir}/{Path(video_path).name}"
        subprocess.run(["rclone", "copy", str(video_path), remote_dir], check=True, timeout=300)
        # Also upload matching thumbnails & UPLOAD.txt so phone editing/upload is 1-tap!
        stem = Path(video_path).stem
        for ext_f in Path(video_path).parent.glob(f"{stem}*"):
            if ext_f.is_file() and ext_f != Path(video_path):
                subprocess.run(["rclone", "copy", str(ext_f), remote_dir], check=False, timeout=120)
            elif ext_f.is_dir() and ext_f.name.endswith("_EDIT_KIT"):
                # v3.60: Upload full _EDIT_KIT (separate shots/, sirf_awaaz.wav, awaaz_poori.wav, captions.srt) for 2-min phone editing in VN/CapCut!
                subprocess.run(["rclone", "copy", str(ext_f), f"{remote_dir}/{ext_f.name}"], check=False, timeout=300)
        lk = subprocess.run(["rclone", "link", remote_file], capture_output=True, text=True, timeout=60)
        url = (lk.stdout or "").strip()
        return url if url.startswith("http") else f"Google Drive: VG Videos/{today}/{Path(video_path).name}"
    except Exception as e:
        print("Google Drive rclone upload error:", e)
        return None


def main():
    script_text = (os.environ.get("INPUT_SCRIPT") or "").strip()
    video_mode = (os.environ.get("INPUT_MODE") or "SHORT").strip().upper()
    tg_token = (os.environ.get("TG_TOKEN") or "").strip()
    tg_chat = (os.environ.get("TG_CHAT_ID") or "").strip()

    if not script_text:
        print("ERROR: Script khali hai!")
        sys.exit(1)

    if video_mode == "LONG" and not script_text.upper().startswith("LONG"):
        script_text = "LONG\n" + script_text

    # Build api keys.txt safely from GitHub Secrets at runtime
    keys_lines = []
    for env_k, file_k in [
        ("GEMINI_KEY", "GEMINI_API_KEY"),
        ("PIXABAY_KEY", "PIXABAY_API_KEY"),
        ("PEXELS_KEY", "PEXELS_API_KEY"),
        ("YOUTUBE_KEY", "YOUTUBE_API_KEY"),
    ]:
        if os.environ.get(env_k):
            keys_lines.append(f"{file_k}={os.environ[env_k].strip()}")
    if tg_token:
        keys_lines.append(f"TELEGRAM_BOT_TOKEN={tg_token}")
    if tg_chat:
        keys_lines.append(f"TELEGRAM_CHAT_ID={tg_chat}")
    (ROOT / "api keys.txt").write_text("\n".join(keys_lines) + "\n", encoding="utf-8")

    sp = JOBS / "script_cloud.txt"
    res = JOBS / "result_cloud.json"
    sp.write_text(script_text + "\n", encoding="utf-8")

    first_line = next((l.strip() for l in script_text.splitlines() if l.strip() and l.strip().upper() not in ("LONG", "SHORT")), "Cloud Video")[:60]

    env = dict(os.environ)
    env["VG_SCRIPT"] = str(sp)
    env["VG_RESULT"] = str(res)
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.run([sys.executable, str(ROOT / "app" / "make_video.py")], cwd=str(ROOT), env=env)
    rc = proc.returncode
    print("make_video.py exit code:", rc)

    out_mp4 = None
    if res.exists():
        try:
            data = json.loads(res.read_text(encoding="utf-8"))
            cand = data.get("video") or data.get("out") or data.get("path")
            if cand and Path(cand).exists():
                out_mp4 = Path(cand)
        except Exception as e:
            print("result parse err:", e)

    if not out_mp4 and (ROOT / "output").exists():
        mp4s = sorted((ROOT / "output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            out_mp4 = mp4s[0]

    if out_mp4 and out_mp4.exists():
        art = ROOT / "cloud_output.mp4"
        art.write_bytes(out_mp4.read_bytes())
        size_mb = out_mp4.stat().st_size / (1024 * 1024)

        # 1. Always upload to Google Drive if RCLONE_CONF is configured
        drive_info = upload_to_gdrive(out_mp4)
        cap = f"✅ Cloud Video Ready ({size_mb:.1f} MB)\n{first_line}"
        if drive_info:
            cap += f"\n📁 Drive: {drive_info}"

        # 2. Send video directly to Telegram if < 49 MB, else send Drive/Artifact link!
        sent_vid = tg_send_video(tg_token, tg_chat, out_mp4, caption=cap)
        if not sent_vid:
            msg = cap + "\n(50 MB se badi file hai — Google Drive ya GitHub Actions Artifacts se download kar lo!)"
            tg_send_text(tg_token, tg_chat, msg)
        sys.exit(0)
    else:
        log_file = ROOT / "log.txt"
        tail = "\n".join(log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-25:]) if log_file.exists() else "No log.txt"
        tg_send_text(tg_token, tg_chat, f"❌ Cloud video nahi ban payi (rc={rc}).\nLast log:\n{tail}")
        sys.exit(rc or 1)


if __name__ == "__main__":
    main()
