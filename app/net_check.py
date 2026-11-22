"""v3.67 SYSTEM JAANCH – cloud par sach me kya chal raha hai (Telegram par "SYSTEM JAANCH KARO" bhejo).

Video nahi banti – sirf 1-3 minute me har cheez test hoti hai aur Telegram par saaf report aati hai:
ffmpeg, yt-dlp, JS runtime, keys (sirf haan/nahi – value kabhi nahi), Gemini, Groq, Pixabay, Pexels,
YouTube search + asli clip kaatna, Twitter/X clip, Pinterest clip, AI aankh (CLIP), cookies/proxy.
"""
import json, shutil, subprocess, sys, time
from pathlib import Path

from common import read_keys, CACHE


def _t(fn):
    t0 = time.time()
    try:
        ok, msg = fn()
    except Exception as e:
        ok, msg = False, f"error: {str(e)[:120]}"
    return ok, msg, time.time() - t0


def run(full=True):
    import requests
    keys = read_keys()
    rows = []

    def add(name, fn, hint=""):
        ok, msg, dt = _t(fn)
        rows.append((ok, name, msg, hint if not ok else "", dt))

    def ffm():
        return bool(shutil.which("ffmpeg")), "mili" if shutil.which("ffmpeg") else "nahi mili"

    def ytdlp():
        r = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True, text=True, timeout=30)
        return r.returncode == 0, (r.stdout.strip() or r.stderr.strip()[-80:])

    def jsrt():
        d, n = shutil.which("deno"), shutil.which("node")
        return bool(d or n), ("deno" if d else "node" if n else "koi nahi") + " (YouTube ke liye zaroori)"

    def keyrow():
        have = [k for k in ("GEMINI", "PIXABAY", "PEXELS", "YOUTUBE", "GROQ", "OPENROUTER", "BRAVE") if keys.get(k)]
        miss = [k for k in ("GEMINI", "PIXABAY", "GROQ") if not keys.get(k)]
        return not miss, "lagi: " + (", ".join(have) or "koi nahi") + (f" | nahi: {', '.join(miss)}" if miss else "")

    def cookies():
        import cookie_jar
        st = cookie_jar.status()
        fr = lambda k: f" ({st.get(k + '_from')})" if st.get(k + "_from") else ""
        return True, f"YouTube cookies: {'haan' if st['youtube_cookies'] else 'nahi'}{fr('youtube')}, X cookies: " \
                     f"{'haan' if st['x_cookies'] else 'nahi'}{fr('x')}, proxy: {'haan' if st['proxy'] else 'nahi'}"

    def gemini():
        k = keys.get("GEMINI")
        if not k: return False, "key nahi"
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": k, "pageSize": 5},
                         timeout=20)
        return r.ok, f"HTTP {r.status_code}"

    def groq():
        k = keys.get("GROQ")
        if not k: return False, "key nahi (Gemini limit khatam hone pe backup nahi chalega)"
        r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {k}"}, timeout=20)
        return r.ok, f"HTTP {r.status_code}"

    def pixabay():
        k = keys.get("PIXABAY")
        if not k: return False, "key nahi"
        r = requests.get("https://pixabay.com/api/videos/", params={"key": k, "q": "ocean", "per_page": 3}, timeout=20)
        return r.ok and bool(r.json().get("hits")), f"HTTP {r.status_code}, {len(r.json().get('hits', [])) if r.ok else 0} video"

    def pexels():
        k = keys.get("PEXELS")
        if not k: return True, "key nahi (optional)"
        r = requests.get("https://api.pexels.com/videos/search", params={"query": "ocean", "per_page": 3},
                         headers={"Authorization": k}, timeout=20)
        return r.ok, f"HTTP {r.status_code}"

    def yt_search():
        import youtube_sources
        res = youtube_sources.ytdlp_search("NASA rocket launch", 3)
        return bool(res), f"{len(res)} result" + (f" (pehla: {res[0]['title'][:40]})" if res else "")

    def yt_cut():
        import yt_clips
        yt_clips.reset()
        d = CACHE / "ytclips"; d.mkdir(parents=True, exist_ok=True)
        p = yt_clips._cut("jNQXAC9IVRw", 3.0, 3.0, d / "jaanch_jNQXAC9IVRw_3")
        st = yt_clips.status()
        return bool(p), "clip kat gayi ✓" if p else (st.get("why") or "fail")[:160]

    def x_clip():
        import social_visuals as so
        so.reset()
        pages = so.find_pages("NASA rocket launch", "x", 4)
        if not pages:
            return False, "X ke post nahi mile (" + (so.GEM.get("why") or json.dumps(so.status()["search"])[:120]) + ")"
        for pg in pages[:3]:
            c = so.grab(pg)
            if c: return True, f"clip mili ✓ ({pg[:60]})"
        return False, so.status()["x"].get("why") or "post mile par video nahi kati"

    def pin_clip():
        import social_visuals as so
        pages = so.find_pages("ocean waves", "pin", 4)
        if not pages:
            return False, "Pinterest pins nahi mile (" + (so.GEM.get("why") or json.dumps(so.status()["search"])[:120]) + ")"
        for pg in pages[:3]:
            c = so.grab(pg)
            if c: return True, f"clip mili ✓ ({pg[:60]})"
        return False, so.status()["pinterest"].get("why") or "pins mile par video wali nahi thi"

    def clip_eye():
        import aankh
        return bool(aankh.ready()), "CLIP ready" if aankh.STATE.get("ok") else "load nahi hui"

    add("FFmpeg", ffm)
    add("yt-dlp", ytdlp, "requirements me yt-dlp hai – workflow log dekho")
    add("JS runtime", jsrt, "v3.68 khud lagata hai – agli baar apne aap theek ho jaayega")
    add("API keys", keyrow, "GitHub Secrets me GROQ_KEY / PIXABAY_KEY / GEMINI_KEY lagao")
    add("Cookies/proxy", cookies)
    add("Gemini", gemini, "key / quota check karo")
    add("Groq (backup AI)", groq, "console.groq.com se free key -> GitHub Secret GROQ_KEY")
    add("Pixabay", pixabay, "key check karo")
    add("Pexels", pexels)
    if full:
        add("YouTube search (yt-dlp)", yt_search, "yt-dlp purana ya block – YT_COOKIES lagao")
        add("YouTube clip kaatna", yt_cut, "cookies.txt phone se Telegram bot ko bhejo (nayi cookies) – purani/galat ho sakti hain")
        add("Twitter/X clip", x_clip, "X ki cookies.txt Telegram bot ko bhejo (optional) – baaki sources phir bhi chalenge")
        add("Pinterest clip", pin_clip, "cloud pe search khaali aaya – koi baat nahi, baaki sources chalenge")
        add("AI aankh (CLIP)", clip_eye, "pehli baar model download hota hai – dobara chalao")
    ok_n = sum(1 for r in rows if r[0])
    lines = [f"🩺 SYSTEM JAANCH: {ok_n}/{len(rows)} theek"]
    for ok, name, msg, hint, dt in rows:
        lines.append(f"{'✅' if ok else '❌'} {name}: {msg}" + (f"\n   👉 {hint}" if hint else ""))
    return "\n".join(lines), rows


if __name__ == "__main__":
    print(run()[0])
