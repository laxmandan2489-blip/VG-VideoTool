"""v3.67 CLOUD yt-dlp LOGIN HELPER – aapke APNE account ki cookies (GitHub Secret) se yt-dlp chalana.

Kyun: GitHub Actions ke server (data-center IP) se YouTube / X aksar "Sign in to confirm you're not a bot" ya
"login required" bolte hain. Laptop pe ghar ka internet tha isliye chalta tha. yt-dlp ka apna standard tareeka hai:
--cookies cookies.txt (browser me login karke export ki hui file). Yahi yahan hota hai.

Secrets (GitHub -> Settings -> Secrets -> Actions), sab OPTIONAL:
  YT_COOKIES   = YouTube cookies.txt ka poora text (Netscape format; base64 bhi chalega)
  X_COOKIES    = x.com cookies.txt ka poora text
  YTDLP_PROXY  = aapka apna proxy (http://user:pass@host:port) – na ho to khaali chhodo

Suraksha: cookies sirf temp/secrets/ me file banti hai (0600), kabhi log / report / Telegram / ZIP me nahi jaati.
Salaah: ALAG (second) Google / X account use karo – main account nahi.
"""
import base64, os, threading
from pathlib import Path

from common import TOOL

_DIR = TOOL / "temp" / "secrets"
_LOCK = threading.Lock()
_FILES = {}
ENV = {"youtube": "YT_COOKIES", "x": "X_COOKIES"}


def _text(name):
    raw = (os.environ.get(ENV[name]) or "").strip()
    if not raw:
        f = TOOL / f"{name}_cookies.txt"                    # local / laptop: tool folder me file bhi chalegi
        if f.exists():
            try: raw = f.read_text(encoding="utf-8", errors="ignore").strip()
            except Exception: raw = ""
    if raw and "\t" not in raw and not raw.startswith("#"):
        try:                                                # base64 me rakhi ho to
            dec = base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", errors="ignore")
            if "\t" in dec: raw = dec
        except Exception:
            pass
    if not raw or "\t" not in raw:
        return ""
    if not raw.startswith("# Netscape") and not raw.startswith("# HTTP Cookie File"):
        raw = "# Netscape HTTP Cookie File\n" + raw
    return raw + "\n"


def path(name):
    """name = youtube / x -> cookies file Path ya None."""
    with _LOCK:
        if name in _FILES:
            return _FILES[name]
        txt = _text(name); p = None
        if txt:
            try:
                _DIR.mkdir(parents=True, exist_ok=True)
                p = _DIR / f"{name}_cookies.txt"
                p.write_text(txt, encoding="utf-8")
                try: os.chmod(p, 0o600)
                except Exception: pass
            except Exception:
                p = None
        _FILES[name] = p
        return p


def proxy():
    return (os.environ.get("YTDLP_PROXY") or "").strip()


def args(name):
    """yt-dlp ke extra args (cookies + proxy)."""
    a = []
    p = path(name)
    if p: a += ["--cookies", str(p)]
    if proxy(): a += ["--proxy", proxy()]
    return a


def for_url(url):
    u = (url or "").lower()
    if "youtube.com" in u or "youtu.be" in u: return args("youtube")
    if "x.com/" in u or "twitter.com/" in u: return args("x")
    return ["--proxy", proxy()] if proxy() else []


def status():
    """Diagnostics ke liye (koi secret value nahi)."""
    return {"youtube_cookies": bool(path("youtube")), "x_cookies": bool(path("x")), "proxy": bool(proxy())}
