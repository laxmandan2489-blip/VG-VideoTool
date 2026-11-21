"""v3.6 HYPERFRAMES HOOK – video ke pehle ~2.4 sec ka animated title (HeyGen HyperFrames, Apache-2.0).

HTML + GSAP se transparent WebM banta hai, final video me footage ke upar (captions ke upar wali jagah se door).
Zaroorat: Node.js 22+ aur  INSTALL_HYPERFRAMES.bat  (ek baar). Na ho / fail ho -> chupchaap skip, video nahi rukti.
style.txt:  hf_hook = haan / nahi      (sirf tab chalta hai jab script me  TITLE: ... | ...  line ho)
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path
from common import log, TOOL

HF_DIR = TOOL / "hyperframes"                         # INSTALL_HYPERFRAMES.bat yahan npm install karta hai
TPL = TOOL / "assets" / "hyperframes" / "hook"
STATE = {"ok": None, "why": ""}


def _npx():
    return "npx.cmd" if os.name == "nt" else "npx"


def available():
    if STATE["ok"] is not None: return STATE["ok"]
    STATE["ok"] = False
    node = shutil.which("node")
    if not node:
        STATE["why"] = "Node.js nahi mila (INSTALL_HYPERFRAMES.bat chalao)"; return False
    try:
        v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        if int(re.sub(r"[^\d.]", "", v).split(".")[0]) < 22:
            STATE["why"] = f"Node {v} purana – 22+ chahiye"; return False
    except Exception as e:
        STATE["why"] = f"node check fail: {e}"; return False
    if not (HF_DIR / "node_modules" / "hyperframes").exists():
        STATE["why"] = "hyperframes install nahi (INSTALL_HYPERFRAMES.bat chalao)"; return False
    if not (TPL / "index.html").exists():
        STATE["why"] = "hook template nahi mila"; return False
    STATE["ok"] = True
    return True


def render_hook(line1, line2, out, hl="", timeout=300):
    """Return out (transparent .webm) ya None."""
    if not available():
        log(f"   (HyperFrames hook skip: {STATE['why']})", show=False); return None
    out = Path(out)
    tc = lambda t: " ".join(w if any(c.isupper() for c in w) else w[:1].upper() + w[1:] for w in (t or "").split())
    vars_ = {"line1": tc(line1)[:28], "line2": tc(line2)[:70], "hl": hl or ""}
    # v3.13 FIX (round 2: "[WinError 183] ... hf_hook already exists"): Windows pe purana folder lock rehta tha ->
    # rmtree chupchaap fail -> copytree error -> round 2 me hook gayab. Ab: wahi text pehle bana ho to wahi webm
    # dobara; warna har baar naya (alag naam ka) project folder.
    stamp = out.with_suffix(".vars.json")
    try:
        if out.exists() and out.stat().st_size > 5000 and stamp.exists() and \
                json.loads(stamp.read_text(encoding="utf-8")) == vars_:
            log("   ✨ HyperFrames hook: pichhla wahi title dobara use ✓", show=False)
            return out
    except Exception:
        pass
    n = 0
    while (out.parent / f"hf_hook_{n}").exists() and n < 50: n += 1
    proj = out.parent / f"hf_hook_{n}"
    try:
        for old_ in out.parent.glob("hf_hook*"):
            if old_.is_dir(): shutil.rmtree(old_, ignore_errors=True)
        shutil.copytree(TPL, proj, dirs_exist_ok=True)
        vf = proj / "vars.json"; vf.write_text(json.dumps(vars_, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1", HYPERFRAMES_NO_AUTO_INSTALL="1")
        cmd = [_npx(), "--no-install", "hyperframes", "render", str(proj), "--format", "webm", "-o", str(out),
               "--quality", "draft", "--fps", "30", "--workers", "1", "--variables-file", str(vf), "--quiet"]
        r = subprocess.run(cmd, cwd=str(HF_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, env=env, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode == 0 and out.exists() and out.stat().st_size > 5000:
            log("   ✨ HyperFrames hook title ban gaya ✓")
            try: stamp.write_text(json.dumps(vars_, ensure_ascii=False), encoding="utf-8")
            except Exception: pass
            return out
        log(f"   (HyperFrames hook fail: {(r.stderr or r.stdout or '')[-200:]})", show=False)
    except Exception as e:
        log(f"   (HyperFrames hook error: {str(e)[:160]})", show=False)
    return None
