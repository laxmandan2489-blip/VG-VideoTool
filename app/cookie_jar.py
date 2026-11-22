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


REF = TOOL / "seekha" / "cookies_ref.json"     # v3.69: Telegram se bheji cookies file ka file_id (cookies NAHI)
SRC = {}                                         # name -> "telegram" / "secret" / "file"
DIAG = {}                                        # v3.70: name -> kyun nahi mili (value kabhi nahi)


def _normalize(raw):
    """v3.70 FIX: phone / Notepad / GitHub box me paste karte waqt TAB aksar SPACE ban jaata hai -> pehle cookies
    'nahi' maani jaati thi. Ab har cookie line (7 hisse) ko wapas TAB se jodte hain."""
    out = []; n = 0
    for ln in (raw or "").replace("\r", "").splitlines():
        t = ln.strip()
        if not t: continue
        if t.startswith("#") and not t.startswith("#HttpOnly_"):
            out.append(t); continue
        parts = t.split("\t") if "\t" in t else t.split(None, 6)
        if len(parts) >= 7 and parts[1].upper() in ("TRUE", "FALSE") and parts[3].upper() in ("TRUE", "FALSE"):
            out.append("\t".join(parts[:6] + ["\t".join(parts[6:]) if "\t" in t else parts[6]])); n += 1
    return ("\n".join(out) + "\n") if n else "", n


def _from_telegram(name):
    """v3.69: phone se Telegram bot ko cookies.txt bhejo -> worker sirf file_id repo me likhta hai ->
    yahan bot token se file Telegram se aati hai. Cookies kabhi repo / log me nahi jaati."""
    try:
        import json, requests
        if not REF.exists(): return ""
        fid = ((json.loads(REF.read_text(encoding="utf-8")) or {}).get(name) or {}).get("file_id")
        tok = (os.environ.get("TG_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
        if not tok:
            try:
                from common import read_keys
                tok = read_keys().get("TELEGRAM") or ""
            except Exception:
                tok = ""
        if not (fid and tok): return ""
        info = requests.get(f"https://api.telegram.org/bot{tok}/getFile", params={"file_id": fid}, timeout=20).json()
        fp = (info.get("result") or {}).get("file_path")
        if not fp: return ""
        r = requests.get(f"https://api.telegram.org/file/bot{tok}/{fp}", timeout=30)
        return r.text if r.ok else ""
    except Exception:
        return ""


def _text(name):
    raw = _from_telegram(name).strip()
    SRC[name] = "telegram" if raw else ""
    env_raw = (os.environ.get(ENV[name]) or "").strip()
    DIAG[name] = ("telegram file mili" if raw else
                  (f"secret pahunchi ({len(env_raw)} akshar)" if env_raw else
                   "abhi koi cookies nahi daali – cookies.txt file Telegram bot ko bhejo"))
    if not raw:
        raw = env_raw
        if raw: SRC[name] = "secret"
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
    norm, n = _normalize(raw)
    if not n:
        if raw: DIAG[name] += " – par cookie format samajh nahi aaya (poori cookies.txt paste karo, kuch kata na ho)"
        return ""
    want = "youtube.com" if name == "youtube" else ("x.com", "twitter.com")
    if isinstance(want, str): want = (want,)
    if not any(w in norm for w in want):
        DIAG[name] += f" – {n} cookie par {want[0]} ki nahi (galat site ki file?)"
        return ""
    DIAG[name] += f" – {n} cookie ✓"
    if not norm.startswith("# Netscape") and not norm.startswith("# HTTP Cookie File"):
        norm = "# Netscape HTTP Cookie File\n" + norm
    return norm


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
    return {"youtube_cookies": bool(path("youtube")), "x_cookies": bool(path("x")), "proxy": bool(proxy()),
            "youtube_from": SRC.get("youtube", ""), "x_from": SRC.get("x", ""),
            "youtube_diag": DIAG.get("youtube", ""), "x_diag": DIAG.get("x", "")}
