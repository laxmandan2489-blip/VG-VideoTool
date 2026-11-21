"""v3.12 "MERA KAAM" – aapko (user ko) kya karna baaki hai, ek list. Telegram: /kaam  ya  ✅ Mera kaam button.

Har cheez khud jaanchta hai (keys, sounds, HyperFrames, version, pichhli video ka Review) aur batata hai ki
Telegram se hi kaise theek karo (jaise  /key PEXELS abc123).
"""
import json, re
from pathlib import Path
from common import TOOL, OUT, read_keys

KEY_INFO = {
    "GEMINI": ("Gemini (script samajhna, awaaz, jaanch)", "aistudio.google.com -> Get API key"),
    "PIXABAY": ("Pixabay (free video/photo)", "pixabay.com/api/docs -> login -> key"),
    "PEXELS": ("Pexels (free HD video – zyada cinematic B-roll)", "pexels.com/api -> Your API key"),
    "GROQ": ("Groq (Gemini ki limit khatam ho to BACKUP dimaag, free)", "console.groq.com -> API Keys"),
    "OPENROUTER": ("OpenRouter (doosra backup, free models)", "openrouter.ai -> Keys"),
    "YOUTUBE": ("YouTube Data API (official clips + film trailer)", "console.cloud.google.com -> YouTube Data API v3 -> key"),
    "BRAVE": ("Brave Search (video + photo khoj – YouTube quota bachata hai)", "api-dashboard.search.brave.com -> API keys"),
}
ALLOWED_KEYS = set(KEY_INFO) | {"SARVAM", "BRAVE2"}


def _key_file():
    for p in TOOL.iterdir():
        n = p.name.lower()
        if p.is_file() and n.endswith(".txt") and "key" in n:
            return p
    return TOOL / "api keys.txt"


def set_key(name, value):
    """api keys.txt me  NAME = value  (purani line badal deta hai). Return (ok, msg)."""
    name = re.sub(r"[^A-Za-z0-9]", "", name or "").upper()     # v3.13: BRAVE2 (digit) bhi
    if name not in ALLOWED_KEYS: name = re.sub(r"[0-9]", "", name)
    value = (value or "").strip().strip("\"'")
    if name not in ALLOWED_KEYS:
        return False, f"'{name}' nahi pehchana. Ye chalte hain: {', '.join(sorted(ALLOWED_KEYS))}"
    if len(value) < 8 or " " in value:
        return False, "Key chhoti / galat lag rahi hai (beech me space nahi hona chahiye)."
    p = _key_file()
    lines = p.read_text(encoding="utf-8-sig").splitlines() if p.exists() else []
    out, done = [], False
    for ln in lines:
        k = re.sub(r"[^A-Za-z0-9]", "", ln.split("=", 1)[0] if "=" in ln else ln.split(":", 1)[0]).upper()
        if "=" in ln or ":" in ln:
            same = (k == name) if name.startswith("BRAVE") else re.sub(r"[0-9]", "", k).startswith(name)
            if same:
                if not done: out.append(f"{name} = {value}"); done = True
                continue
        out.append(ln)
    if not done: out.append(f"{name} = {value}")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return True, f"{name} key '{p.name}' me lag gayi ✓ (…{value[-4:]})"


def _sounds():
    try:
        import render
        bad, good = {}, {}
        for cat in ("whoosh", "ding", "click", "pop"):
            d = TOOL / "mere_sounds" / cat
            files = [f for f in d.iterdir() if f.suffix.lower() in (".wav", ".mp3", ".m4a", ".ogg")] if d.exists() else []
            for f in files:
                try:
                    x = render.load_wav(f)
                    (bad if render.sfx_broken(x) else good).setdefault(cat, []).append(f.name)
                except Exception:
                    bad.setdefault(cat, []).append(f.name)
        return good, bad
    except Exception:
        return {}, {}


def last_review():
    try:
        rs = sorted(OUT.glob("*_REVIEW.json"), key=lambda p: p.stat().st_mtime)
        if not rs: return None
        return json.loads(rs[-1].read_text(encoding="utf-8")), rs[-1].name
    except Exception:
        return None


def report():
    keys = read_keys()
    L = ["✅ MERA KAAM – aapko kya karna hai (khud jaancha)\n"]
    todo = 0
    try:
        v = (TOOL / "app" / "VERSION").read_text(encoding="utf-8").strip()
        L.append(f"🏷 Tool version: v{v}")
    except Exception:
        pass
    L.append("\n🔑 KEYS")
    for k, (what, where) in KEY_INFO.items():
        if keys.get(k):
            L.append(f"  ✅ {k} – {what}")
        else:
            todo += 1
            L.append(f"  ❌ {k} – {what}\n      lo: {where}\n      phir yahan bhejo:  /key {k} aapki_key")
    if not (keys.get("GROQ") or keys.get("OPENROUTER")):
        L.append("  ⚠️ Gemini ki roz ki limit khatam hoti hai (pichhle logs me 2 baar) – GROQ key zaroor lagao (free).")
    good, bad = _sounds()
    L.append("\n🔊 SOUNDS")
    for cat in ("whoosh", "ding", "click", "pop"):
        g = len(good.get(cat, [])); b = len(bad.get(cat, []))
        if g: L.append(f"  ✅ {cat}: {g} saaf file" + (f" ({b} kharab – tool khud chhod deta hai)" if b else ""))
        else:
            todo += 1
            L.append(f"  ❌ {cat}: ek bhi saaf file nahi – VG_Sound_Transition_Pack.zip ka mere_sounds lagao")
    try:
        import hf_hook
        ok = hf_hook.available()
        L.append("\n✨ HyperFrames (shuru ka title): " + ("✅ chalu" if ok else f"❌ {hf_hook.STATE.get('why')}  -> laptop pe INSTALL_HYPERFRAMES.bat"))
        if not ok: todo += 1
    except Exception:
        pass
    try:                                               # v3.13: Node.js / Deno (YouTube clips + HyperFrames)
        import shutil as _sh
        nd, dn = _sh.which("node"), _sh.which("deno")
        L.append("\n🟢 Node.js: " + ("✅ hai" if nd else "❌ nahi – INSTALL_DEPENDENCIES.bat chalao (Node.js khud lagega)")
                 + "   |   Deno: " + ("✅ hai" if dn else ("➖ nahi (Node se kaam chalega)" if nd else "❌ nahi")))
        if not nd: todo += 1
        if not (keys.get("BRAVE")):
            L.append("  💡 BRAVE key lagao (2 tak: /key BRAVE ...  aur  /key BRAVE2 ...) – YouTube quota khatam hone pe "
                     "bhi video milegi")
    except Exception:
        pass
    lr = last_review()
    if lr:
        R, nm = lr
        L.append(f"\n🧐 Pichhli video ka Review: {R.get('score')}/100 {R.get('verdict', '')}")
        for _, m, _ in sorted(R.get("issues") or [], key=lambda x: -x[2])[:3]:
            L.append(f"  • {m}")
        lines = sorted({int(x) for x in re.findall(r"line (\d+)", " ".join(m for _, m, _ in R.get("issues") or []))})[:4]
        if lines:
            L.append("  Sudhaar ke liye bas likho:  " + ", ".join(f"line {n}" for n in lines) + " ki footage badlo")
    L.append("\n📌 ROZ KA TAREEKA")
    L.append("  1) ▶️ Aaj shuru karo -> prompt copy -> MERA TOPIC likho -> ChatGPT/Gemini -> jawab yahan")
    L.append("  2) Video aane ke baad galti ho to likho:  line 5 ki footage badlo  (sirf wahi badlegi)")
    L.append("  3) Sirf EK bot chalao (START_VIDEO_TOOL ya 7_BOT_HAMESHA_CHALU – dono nahi)")
    L.append(f"\n{'🎉 Sab theek hai!' if not todo else f'👉 {todo} kaam baaki'}")
    return "\n".join(L)
