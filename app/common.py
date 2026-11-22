"""Common helpers: paths, settings, logging, ffmpeg."""
import os, re, sys, json, shutil, subprocess, datetime
from pathlib import Path

# v3.2 FIX (Windows): text=True wale subprocess Hindi file-naam / emoji wala output cp1252 se padhte the ->
# UnicodeDecodeError / khaali output (QC ne sahi video ko "stream nahi" bola). Sab jagah UTF-8 + replace.
_orig_run = subprocess.run


def _utf8_run(*a, **k):
    if (k.get("text") or k.get("universal_newlines")) and not k.get("encoding"):
        k["encoding"] = "utf-8"; k.setdefault("errors", "replace")
    return _orig_run(*a, **k)


subprocess.run = _utf8_run
_orig_popen_init = subprocess.Popen.__init__


def _utf8_popen(self, *a, **k):
    if (k.get("text") or k.get("universal_newlines")) and not k.get("encoding"):
        k["encoding"] = "utf-8"; k.setdefault("errors", "replace")
    _orig_popen_init(self, *a, **k)


subprocess.Popen.__init__ = _utf8_popen

TOOL = Path(__file__).resolve().parent.parent
ASSETS = TOOL / "assets"
OUT = TOOL / "output"
WORK = Path(os.environ.get("VG_WORK_DIR", str(TOOL / "temp"))).expanduser().resolve()
CACHE = TOOL / "temp" / "cache"
LOG_FILE = TOOL / "log.txt"

UA = "VGFactVideoTool/2.0 (personal YouTube video tool; contact: owner)"

_SECRET = re.compile(r"(bot\d{6,12}:)[A-Za-z0-9_\-]{20,}|(\b\d{7,12}:)[A-Za-z0-9_\-]{30,}|(AIza)[0-9A-Za-z_\-]{30,}|"
                     r"(key=)[A-Za-z0-9_\-\.]{12,}|(AQ\.)[A-Za-z0-9_\-\.]{16,}|(gsk_)[A-Za-z0-9]{20,}|(sk-or-)[A-Za-z0-9_\-]{20,}|"
                     r"(Bearer )[A-Za-z0-9_\-\.]{16,}|(BSA)[A-Za-z0-9_\-]{16,}|(api_key=)[A-Za-z0-9_\-]{12,}|"
                     r"(X-Subscription-Token.{0,4})[A-Za-z0-9_\-]{12,}")   # v3.12/v3.15: Groq/OpenRouter/Brave/Smithsonian


def redact(msg):
    """v3.1: log me Telegram bot token / Google key kabhi na likhe (log.txt share hota hai)."""
    return _SECRET.sub(lambda m: next(g for g in m.groups() if g) + "***HIDDEN***", str(msg))


def log(msg, show=True):
    msg = redact(msg)
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    if show:
        try:
            print(msg, flush=True)
        except UnicodeEncodeError:
            print(msg.encode("ascii", "replace").decode(), flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def fail(msg):
    log("\n" + "=" * 60 + "\n  GADBAD: " + msg + "\n" + "=" * 60)
    log("  (log.txt file Claude ko bhej do, wo theek kar dega)")
    sys.exit(1)

# ---------------- settings ----------------
DEFAULTS = {
    "format": "short", "quality": "achhi",
    "voice": "gemini", "gemini_awaaz": "charon", "awaaz_bhaari": "9", "ai_awaaz": "madhur", "ai_speed": "10", "pause_kaato": "0.4",
    "captions": "haan", "caption_shabd": "2", "caption_size": "135",
    "caption_rang": "peela", "caption_jagah": "beech", "caption_lipi": "hinglish", "caption_capital": "haan",
    "visual_badle_har": "2.5", "zoom": "haan", "flash": "haan", "flash_rang": "orange", "shake": "nahi", "effect_har": "0",
    "logo": "haan", "logo_size": "120", "logo_jagah": "upar_left",
    "title": "nahi", "progress_bar": "haan",
    "sfx": "haan", "sfx_awaaz": "60", "intro_sound": "haan", "caption_pop_sound": "nahi", "music_awaaz": "22",
    "transition": "haan", "transition_gap": "3.5", "photo": "kam", "layer": "haan", "layer_taakat": "30", "motion": "haan", "motion_gap": "2",
    "subscribe_end": "haan", "subscribe_hamesha": "nahi", "video_fit": "4:5", "footage_check": "haan", "strict_visual_match": "haan", "caption_timing_sahi": "haan", "whisper_model": "base", "script_pehle_dikhao": "nahi", "channel_naam": "", "hashtags": "#facts #hindifacts", "youtube_kholo": "haan", "shorts_kitne": "3", "transition_awaaz": "85", "intro_awaaz": "90", "gemini_intezaar": "45", "gemini_check_har": "3", "line_max_clips": "3", "flash_har_clip": "nahi", "pro_editing": "haan", "transition_file_awaaz": "haan", "khali_line_pichhli_clip": "nahi", "check_bot": "haan", "check_bot_round": "1", "drive_folder": "auto", "drive_naam": "VG Videos", "whisper_model_meri": "small", "subscribe_size": "1.2", "hook_text": "haan",
}

def read_style(path):
    s = dict(DEFAULTS)
    if not path.exists():
        log("style.txt nahi mili, default style use kar raha hoon.")
        return s
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().lower()
        v = v.split("(")[0]
        if k not in ("hashtags",):
            v = v.split("#")[0]
        v = v.strip() if k in ("hashtags", "channel_naam", "drive_naam", "drive_folder", "gemini_andaaz") else v.strip().lower()
        if v:
            s[k] = v
    return s

def yes(v):
    return str(v).strip().lower() in ("haan", "han", "ha", "yes", "y", "1", "on", "true")

def num(s, key, lo=None, hi=None):
    try:
        x = float(s.get(key, DEFAULTS.get(key, "0")))
    except ValueError:
        log(f"style.txt me '{key}' ki value number nahi hai, default le raha hoon.")
        x = float(DEFAULTS.get(key, "0"))
    if lo is not None: x = max(lo, x)
    if hi is not None: x = min(hi, x)
    return x

# ---------------- files the user keeps ----------------
def user_dirs():
    home = Path.home()
    c = [TOOL, home / "Documents", home / "Downloads", home / "Desktop",
         home / "OneDrive" / "Documents", home / "OneDrive" / "Desktop"]
    return [d for d in c if d.exists()]

def find_script():
    found = []
    for d in user_dirs():
        p = d / "script.txt"
        if p.exists():
            found.append(p)
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)

KEY_SOURCE = []


def read_keys():
    """api keys.txt dhoondho. Naam/format thoda galat ho tab bhi key pehchaan leta hai."""
    keys = {}
    files = []
    for d in user_dirs():
        try:
            for p in d.iterdir():
                n = p.name.lower()
                if p.is_file() and n.endswith(".txt") and ("key" in n or "api" in n) and p.stat().st_size < 20000:
                    files.append(p)
        except Exception:
            pass
    pix_re = re.compile(r"\b\d{5,12}-[0-9a-fA-F]{20,40}\b")
    gem_re = re.compile(r"\b(?:AIza[0-9A-Za-z_\-]{30,}|AQ\.[0-9A-Za-z_\-\.]{20,})")
    for p in files:
        try:
            txt = p.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            continue
        for line in txt.splitlines():
            for sep in ("=", ":"):
                if sep in line:
                    k, v = line.split(sep, 1)
                    raw_k = re.sub(r"[^A-Za-z0-9]", "", k).upper()
                    k = re.sub(r"[^A-Za-z]", "", k).upper(); v = v.strip().strip('"\'').strip()
                    if k.startswith("BRAVE") and v and " " not in v:     # v3.13: Brave ki 2 keys (BRAVE, BRAVE2)
                        if not keys.get("BRAVE"): keys["BRAVE"] = v
                        elif v != keys["BRAVE"] and not keys.get("BRAVE2"): keys["BRAVE2"] = v
                        break
                    for name in ("PIXABAY", "GEMINI", "PEXELS", "TELEGRAM"):        # "Gemini key=" bhi chalega
                        if k.startswith(name) or (name == "GEMINI" and k.startswith("GOOGLE")): k = name
                    # v3.66 FIX (cloud): cloud_run "GROQ_API_KEY=" likhta hai -> pehle "GROQAPIKEY" ban jaata tha aur
                    # Groq/OpenRouter backup KABHI chalu nahi hota tha (Gemini limit khatam -> offline kamzor visuals)
                    for name in ("GROQ", "OPENROUTER", "YOUTUBE", "SMITHSONIAN"):
                        if k.startswith(name) and k in (name, name + "KEY", name + "APIKEY", name + "API", name + "TOKEN"):
                            k = name
                    if k and v and " " not in v:
                        keys.setdefault(k, v)
                    break
        m = pix_re.search(txt)
        if m and not keys.get("PIXABAY"): keys["PIXABAY"] = m.group(0)
        m = gem_re.search(txt)
        if m and not keys.get("GEMINI"): keys["GEMINI"] = m.group(0)
        m = re.search(r"\b\d{7,12}:[A-Za-z0-9_\-]{30,}\b", txt)
        if m and not keys.get("TELEGRAM"): keys["TELEGRAM"] = m.group(0)
        if keys.get("PIXABAY") or keys.get("GEMINI") or keys.get("TELEGRAM"):
            KEY_SOURCE.append(str(p))
    try:                                         # v3.15: .env bhi (BRAVE_API_KEY_1/2, SEARXNG_BASE_URL, SMITHSONIAN_API_KEY ...)
        import providers
        for k, v in providers.read_env(user_dirs()).items():
            keys.setdefault(k, v)
    except Exception:
        pass
    return keys

# ---------------- ffmpeg ----------------
def check_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        fail("FFmpeg nahi mila. cmd me 'ffmpeg -version' chala ke dekho. "
             "Nahi chale to 'winget install Gyan.FFmpeg' karo aur cmd band karke dobara kholo.")

def run(cmd, cwd=None, quiet=True):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("RUN: " + " ".join(str(c) for c in cmd) + "\n")
    cmd = [str(c) for c in cmd]
    if cmd and cmd[0] == "ffmpeg" and "-nostdin" not in cmd:
        cmd = cmd[:1] + ["-nostdin"] + cmd[1:]
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, stdin=subprocess.DEVNULL,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(r.stderr[-4000:] + "\n")
        raise RuntimeError(f"ffmpeg error: {r.stderr[-600:]}")
    return r

def run_progress(cmd, total, cwd=None, label="Final video", stall=240):
    """ffmpeg chalao, % dikhao. ffmpeg ka output alag thread padhta hai, isliye black window
    me click/select karne se bhi ffmpeg nahi rukta. `stall` second tak kuch na badhe to rok ke error."""
    import tempfile, threading, time as _t
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("RUN: " + " ".join(str(c) for c in cmd) + "\n")
    cmd = [str(c) for c in cmd]
    cmd = cmd[:1] + ["-nostdin", "-progress", "pipe:1", "-nostats"] + cmd[1:]
    state = {"t": 0.0, "moved": _t.time()}
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as errf:
        p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=errf, stdin=subprocess.DEVNULL,
                             text=True, encoding="utf-8", errors="replace")

        def reader():
            for line in p.stdout:
                if line.startswith(("out_time_us=", "out_time_ms=")):
                    try:
                        t = int(line.split("=", 1)[1]) / 1e6
                    except ValueError:
                        continue
                    if t > state["t"]:
                        state["t"] = t; state["moved"] = _t.time()
        th = threading.Thread(target=reader, daemon=True); th.start()
        last = -10
        while p.poll() is None:
            _t.sleep(1)
            pct = int(max(0, min(99, state["t"] / max(total, 0.1) * 100)))
            if pct >= last + 10:
                last = pct - pct % 10
                log(f"   {label}: {last}% ...")
            if _t.time() - state["moved"] > stall:
                p.kill()
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"STALL: {stall}s se aage nahi badha ({state['t']:.1f}s par)\n")
                raise RuntimeError(f"ffmpeg {stall}s se ruka hua tha")
        th.join(timeout=5)
        if p.returncode != 0:
            errf.seek(0); err = errf.read()
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(err[-4000:] + "\n")
            raise RuntimeError(f"ffmpeg error: {err[-600:]}")
    log(f"   {label}: 100% ✓")


def no_console_freeze():
    """Windows: black window me galti se click/select karne pe program na ruke (QuickEdit band)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-10)
        mode = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(mode)):
            k.SetConsoleMode(h, (mode.value & ~0x0040) | 0x0080)
    except Exception:
        pass


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0

def has_video_stream(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return "video" in r.stdout

def safe_name(text, n=40):
    t = re.sub(r"[\\/:*?\"<>|\n\r\t]", "", text).strip()
    return (t[:n] or "video").strip()


def copy_font(src, dst):
    """v2.16b: font temp folder me – pehle se hai to dobara mat likho (Windows pe khuli file pe likhna = Errno 22)."""
    import shutil
    try:
        src, dst = Path(src), Path(dst)
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            return dst
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    except Exception as e:
        log(f"   (font copy skip: {e})", show=False)
    return dst
