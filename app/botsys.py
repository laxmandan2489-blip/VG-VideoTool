"""v2.14: Bot ke system kaam – phone se tool chalane ke liye.

update_from_zip  – Telegram pe bheji ZIP se tool update (backup + style.txt ki settings bachakar)
rollback         – pichhla version wapas (/purana)
safai            – temp/cache/purani videos saaf (/safai, aur apne-aap)
health           – keys, ffmpeg, internet, Drive, jagah ki jaanch
settings         – "captions bade karo" jaisi baat se style.txt badalna (+ /settings, /wapas_setting)
save_asset       – bheje gaye layer / transition / motion / sound sahi folder me
"""
import os, re, json, shutil, zipfile, time, datetime
from pathlib import Path
from common import log, read_style, TOOL, WORK, CACHE, OUT

BACKUP = TOOL / "backup"
STYLE = TOOL / "style.txt"
STYLE_HIST = TOOL / "temp" / "style_history"


# ------------------------------------------------------------------ version
def version():
    try:
        return (TOOL / "app" / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        return "?"


# ------------------------------------------------------------------ style.txt merge


def _split(ln):
    """'key = value   (comment)' -> (key, value, comment) ya None."""
    s = ln.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    k, rest = s.split("=", 1)
    k = k.strip()
    if not re.match(r"^[A-Za-z_]\w*$", k):
        return None
    rest = rest.strip()
    if rest.startswith("("):
        return k, "", rest
    m = re.match(r"^(.*?)(\s{2,}\(.*)?$", rest)
    return k, m.group(1).strip(), (m.group(2) or "").strip()


def _fmt(k, v, c):
    return f"{k.ljust(17)} = {v.ljust(14)} {c}".rstrip()


def _parse_style_lines(txt):
    """key -> value (comment ke bina) sirf asli setting lines se."""
    out = {}
    for ln in txt.splitlines():
        x = _split(ln)
        if x: out[x[0].lower()] = x[1]
    return out


def merge_style(new_txt, old_txt):
    """Naye style.txt ka dhaancha + purane wale ki values (aapki settings bachi rahein)."""
    old = _parse_style_lines(old_txt)
    seen = set(); out = []
    for ln in new_txt.splitlines():
        x = _split(ln)
        if x:
            k = x[0].lower(); seen.add(k)
            if k in old and old[k] != "":
                ln = _fmt(x[0], old[k], x[2])
        out.append(ln)
    extra = [f"{k} = {v}" for k, v in old.items() if k not in seen and v != ""]
    if extra:
        out += ["", "# ---------- aapki purani settings (naye style.txt me nahi thi) ----------"] + extra
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ update / rollback
def update_from_zip(zpath):
    """Returns (ok, message). Restart bot karna padega (caller)."""
    zpath = Path(zpath)
    try:
        z = zipfile.ZipFile(zpath)
    except Exception:
        return False, "Ye ZIP file sahi nahi hai."
    names = z.namelist()
    root = None
    for n in names:
        if n.endswith("app/make_video.py"):
            root = n[: -len("app/make_video.py")]; break
    if root is None:
        return False, "Is ZIP me VideoTool ka app folder nahi mila (galat file?)."
    tmp = WORK / "update_tmp"
    shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    z.extractall(tmp)
    src = tmp / root if root else tmp
    # chhoti jaanch: saari python files sahi hain?
    import py_compile
    for p in (src / "app").glob("*.py"):
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            return False, f"Update file me galti hai ({p.name}) – kuch nahi badla. Claude ko batao."
    # backup
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bk = BACKUP / f"{stamp}_v{version()}"
    bk.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TOOL / "app", bk / "app", dirs_exist_ok=True)
    for f in TOOL.glob("*.bat"):
        shutil.copy2(f, bk / f.name)
    if STYLE.exists():
        shutil.copy2(STYLE, bk / "style.txt")
    # nayi files lagao
    for item in src.iterdir():
        dst = TOOL / item.name
        if item.name == "style.txt":
            old = STYLE.read_text(encoding="utf-8") if STYLE.exists() else ""
            STYLE.write_text(merge_style(item.read_text(encoding="utf-8"), old), encoding="utf-8")
        elif item.is_dir():
            if item.name == "app":
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:                                        # mere_sounds waghera: sirf nayi files jodo
                for f in item.rglob("*"):
                    if f.is_file():
                        t = dst / f.relative_to(item)
                        if not t.exists():
                            t.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, t)
        elif item.is_file():
            if item.name.lower() == "6_telegram_bot.bat":
                continue                     # chalti hui bat file badalne se loop toot sakti hai – chhodo
            if dst.exists() and dst.read_bytes() == item.read_bytes():
                continue
            shutil.copy2(item, dst)
    # sirf aakhri 5 backup rakho
    bks = sorted(BACKUP.glob("*_v*"))
    for old in bks[:-5]:
        shutil.rmtree(old, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return True, f"v{version()}"


def rollback():
    bks = sorted([p for p in BACKUP.glob("*_v*") if (p / "app").exists()])
    if not bks:
        return False, "Koi purana backup nahi mila."
    bk = bks[-1]
    shutil.copytree(bk / "app", TOOL / "app", dirs_exist_ok=True)
    for f in bk.glob("*.bat"):
        shutil.copy2(f, TOOL / f.name)
    if (bk / "style.txt").exists():
        shutil.copy2(bk / "style.txt", STYLE)
    shutil.rmtree(bk, ignore_errors=True)
    return True, bk.name.split("_v")[-1]


# ------------------------------------------------------------------ safai
def _size(p):
    try:
        return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) if Path(p).is_dir() else Path(p).stat().st_size
    except Exception:
        return 0


def safai(days=3, cache_days=10, keep_videos_days=None, drive_root=None):
    """Returns MB khaali hua. Videos sirf tab hatti hain jab unki copy Drive me ho."""
    freed = 0; now = time.time()
    if WORK.exists():
        for d in WORK.iterdir():
            if d.name in ("cache", "bot_jobs", "style_history"): continue
            try:
                if now - d.stat().st_mtime > days * 86400:
                    freed += _size(d); shutil.rmtree(d, ignore_errors=True) if d.is_dir() else d.unlink()
            except Exception:
                pass
    if CACHE.exists():
        files = sorted([f for f in CACHE.iterdir() if f.is_file()], key=lambda f: f.stat().st_mtime)
        total = sum(f.stat().st_size for f in files)
        for f in files:
            old = now - f.stat().st_mtime > cache_days * 86400
            if old or total > 3 * 1024 ** 3 or f.name.endswith(".part.mp4"):
                try:
                    sz = f.stat().st_size; f.unlink(); freed += sz; total -= sz
                except Exception:
                    pass
    jobs = WORK / "bot_jobs"
    if jobs.exists():
        for f in jobs.iterdir():
            try:
                if now - f.stat().st_mtime > 14 * 86400:
                    freed += _size(f); shutil.rmtree(f, ignore_errors=True) if f.is_dir() else f.unlink()
            except Exception:
                pass
    if keep_videos_days and drive_root and OUT.exists():
        for v in OUT.rglob("*.mp4"):
            try:
                if now - v.stat().st_mtime < keep_videos_days * 86400: continue
                if any(c.stat().st_size == v.stat().st_size for c in Path(drive_root).rglob(v.name)):
                    base = str(v.with_suffix(""))
                    for f in [v] + [Path(base + x) for x in ("_UPLOAD.txt", "_credits.txt", "_thumbnail_short.jpg",
                                                              "_thumbnail_16x9.jpg")]:
                        if f.exists(): freed += f.stat().st_size; f.unlink()
            except Exception:
                pass
    return round(freed / 1024 / 1024)


def free_gb():
    try:
        return shutil.disk_usage(str(TOOL)).free / 1024 ** 3
    except Exception:
        return 99


# ------------------------------------------------------------------ health
def health(keys):
    """Returns list of (ok, text)."""
    import requests, subprocess
    out = []
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=20)
        out.append((r.returncode == 0, "ffmpeg"))
    except Exception:
        out.append((False, "ffmpeg nahi mila"))
    try:
        requests.get("https://www.google.com", timeout=10); out.append((True, "internet"))
    except Exception:
        out.append((False, "internet nahi chal raha"))
    if keys.get("PIXABAY"):
        try:
            r = requests.get("https://pixabay.com/api/videos/", params={"key": keys["PIXABAY"], "q": "sea", "per_page": 3},
                             timeout=20)
            out.append((r.status_code == 200, "Pixabay key" + ("" if r.status_code == 200 else f" kaam nahi kar rahi ({r.status_code})")))
        except Exception:
            out.append((False, "Pixabay tak nahi pahunch paya"))
    else:
        out.append((False, "Pixabay key nahi mili"))
    if keys.get("GEMINI"):
        try:
            import ai
            ms = ai.models(keys["GEMINI"])
            out.append((bool(ms), "Gemini key" + ("" if ms else " – models nahi mile")))
        except Exception:
            out.append((False, "Gemini check nahi hua"))
    else:
        out.append((False, "Gemini key nahi mili"))
    try:
        import meta
        d = meta.find_drive(read_style(STYLE))
        out.append((bool(d), "Google Drive" + ("" if d else " nahi mila (Drive for Desktop chalu hai?)")))
    except Exception:
        out.append((False, "Drive check nahi hua"))
    g = free_gb()
    out.append((g > 3, f"laptop me jagah: {g:.1f} GB" + (" – kam hai!" if g <= 3 else "")))
    return out


# ------------------------------------------------------------------ settings
SETTABLE = {
    "caption_size": "number 60-200 (captions ka size, abhi ~135)", "caption_jagah": "upar/beech/neeche",
    "caption_rang": "peela/hara/laal/neela/safed/orange (bolta shabd)", "key_rang": "laal/peela/hara/neela (khaas shabd)",
    "caption_shabd": "1/2/3/4 (ek baar me kitne shabd)", "captions": "haan/nahi", "caption_capital": "haan/nahi",
    "caption_lipi": "hinglish/hindi", "key_shabd": "haan/nahi",
    "transition": "haan/nahi", "flash_har_clip": "haan/nahi", "transition_gap": "seconds 1.5-6",
    "visual_badle_har": "seconds 1.5-4", "music_awaaz": "0-60", "sfx": "haan/nahi", "sfx_awaaz": "0-150",
    "transition_awaaz": "0-200", "intro_awaaz": "0-200", "intro_sound": "haan/nahi", "caption_pop_sound": "haan/nahi",
    "awaaz_bhaari": "0-12", "ai_speed": "-20..30", "gemini_awaaz": "charon/orus/algenib/alnilam/iapetus/fenrir/...",
    "layer": "haan/nahi", "layer_taakat": "0-100", "motion": "haan/nahi", "zoom": "haan/nahi",
    "video_fit": "4:5/poora/bhar", "subscribe_size": "1-1.5", "hook_text": "haan/nahi", "logo": "haan/nahi",
    "color_look": "film/teal/natural/nahi", "photo_3d": "haan/nahi", "punch_shuru": "haan/nahi",
    "number_counter": "haan/nahi", "loop_ending": "haan/nahi", "beat_cut": "haan/nahi", "stabilize": "haan/nahi",
    "check_bot": "haan/nahi", "footage_check": "haan/nahi", "asli_photos": "haan/nahi",
    "video_loudness": "-16..-12", "awaaz_deep": "0-4", "awaaz_noise_saaf": "0-35",
    "lambi_clip_har": "seconds 3-6", "lambi_caption_size": "40-100", "gemini_intezaar": "minutes 0-120", "gemini_try": "0-3 extra tries", "seekha_style": "haan/nahi",
}


def snapshot():
    """Ek command se pehle ek backup (/wapas_setting poora command ulta karta hai)."""
    STYLE_HIST.mkdir(parents=True, exist_ok=True)
    (STYLE_HIST / f"{time.time():.3f}.txt").write_text(STYLE.read_text(encoding="utf-8"), encoding="utf-8")


def set_style(key, value, snap=False):
    """style.txt me ek setting (comment waise hi)."""
    if snap: snapshot()
    txt = STYLE.read_text(encoding="utf-8")
    pat = re.compile(rf"^({re.escape(key)}\s*=\s*)(\S+)", re.M)
    if pat.search(txt):
        txt = pat.sub(lambda m: m.group(1) + str(value), txt, count=1)
    else:
        txt += f"\n{key} = {value}\n"
    STYLE.write_text(txt, encoding="utf-8")
    try:                                     # v2.16: aapne khud badli – seekha hua style isko nahi chhuega
        import seekho; seekho.lock_keys([key])
    except Exception:
        pass


def undo_setting():
    hs = sorted(STYLE_HIST.glob("*.txt"), key=lambda p: float(p.stem)) if STYLE_HIST.exists() else []
    if not hs:
        return False
    shutil.copy2(hs[-1], STYLE); hs[-1].unlink()
    return True


def settings_from_text(key, text):
    """'captions bade aur peele karo' -> {caption_size: 160, caption_rang: peela}."""
    st = read_style(STYLE)
    res = {}
    m = re.match(r"^\s*([a-z_]+)\s*[=:]?\s+([^\s]+)\s*$", text.strip().lower())   # v2.18: seedha "naam value"
    if m and (m.group(1) in st or m.group(1) in SETTABLE or ("_" in m.group(1) and len(m.group(1)) <= 30)):
        return {m.group(1): m.group(2)}, "seedha badla"
    if key:
        from ai import ask_json
        cur = {k: st.get(k, "") for k in SETTABLE}
        r = ask_json(key, [
            "A YouTube creator wants to permanently change settings of his video tool. Map his request (Hindi/Hinglish) "
            "to settings. Use ONLY these settings (name: allowed values / meaning):\n"
            + "\n".join(f"{k}: {v}  (now: {cur[k]})" for k, v in SETTABLE.items())
            + f"\n\nRequest: {text}\n"
            "'bada/zyada/tez' = increase about 20-30%, 'chhota/kam/dheema' = decrease about 20-30% from now.\n"
            'Return ONLY JSON: {"set": {"setting": "value"}, "samjha": "short Hinglish summary"}'],
            temperature=0.1, timeout=60, budget=120)
        if isinstance(r, dict):
            for k, v in (r.get("set") or {}).items():
                if k in SETTABLE: res[k] = str(v).strip().lower()
            if res:
                return res, r.get("samjha") or ""
    def bump(k, f, lo, hi, d):
        try:
            v = float(st.get(k, d))
        except Exception:
            v = float(d)
        return str(int(max(lo, min(hi, v * f))))
    last_subj = None
    for t in re.split(r"\s+aur\s+|,|\band\b", text.lower()):       # har hissa alag samjho
        up = any(w in t for w in ("bada", "bade", "badi", "zyada", "jyada", "tez", "badha", "loud"))
        dn = any(w in t for w in ("chhota", "chote", "chhoti", "kam", "dheema", "halka", "ghata"))
        subj = ("caption" if "caption" in t else "music" if "music" in t else
                "flash" if ("flash" in t or "transition" in t) else "sound" if ("sound" in t or "effect" in t) else last_subj)
        last_subj = subj
        if subj == "caption":
            if up or dn: res["caption_size"] = bump("caption_size", 1.25 if up else 0.8, 60, 200, 135)
            for forms, c in ((("peela", "peele", "peeli", "yellow"), "peela"), (("hara", "hare", "hari", "green"), "hara"),
                             (("laal", "lal", "red"), "laal"), (("neela", "neele", "neeli", "blue"), "neela"),
                             (("safed", "white"), "safed"), (("orange", "narangi"), "orange")):
                if any(re.search(rf"\b{f}\b", t) for f in forms): res["caption_rang"] = c
        elif subj == "music" and (up or dn):
            res["music_awaaz"] = bump("music_awaaz", 1.3 if up else 0.7, 0, 60, 22)
        elif subj == "flash":
            if "band" in t or "hatao" in t: res["flash_har_clip"] = "nahi"
            elif up or dn: res["transition_awaaz"] = bump("transition_awaaz", 1.3 if up else 0.75, 0, 200, 85)
        elif subj == "sound" and (up or dn):
            res["sfx_awaaz"] = bump("sfx_awaaz", 1.3 if up else 0.75, 0, 150, 60)
    return res, ""


def caption_style_from_image(key, jpg_bytes):
    """Screenshot dekh ke caption ki setting (rang, size, jagah, kitne shabd, capital)."""
    if not key:
        return {}
    from ai import ask_json
    r = ask_json(key, [
        "This is a screenshot from a YouTube Short. Describe its burned-in CAPTIONS so a tool can copy the style. "
        "Return ONLY JSON: {\"caption_rang\": highlight color of the spoken word (peela/hara/laal/neela/safed/orange), "
        "\"caption_jagah\": upar/beech/neeche, \"caption_size\": number 90-190 for a 1080x1920 video, "
        "\"caption_shabd\": words shown at once 1-4, \"caption_capital\": haan/nahi, \"caption_lipi\": hinglish/hindi}",
        {"jpg": jpg_bytes}], temperature=0.1, timeout=60, budget=120)
    out = {}
    if isinstance(r, dict):
        for k in ("caption_rang", "caption_jagah", "caption_size", "caption_shabd", "caption_capital", "caption_lipi"):
            if r.get(k) not in (None, ""): out[k] = str(r[k]).lower()
    return out


# ------------------------------------------------------------------ assets (aapke effects)
SOUND_CATS = ("intro", "riser", "whoosh", "flash", "boom", "ding", "pop", "click", "glitch", "wrong", "cash", "typing")


def asset_kind(caption):
    """Caption se pata karo: ('layer'|'transition'|'motion'|'music'|'sound', category) ya None."""
    t = (caption or "").strip().lower()
    if not t: return None
    w = t.split()
    if w[0] in ("layer", "overlay"): return ("layer", None)
    if w[0] in ("transition", "flash", "lightleak", "light"): return ("transition", None)
    if w[0] in ("motion", "graphic"): return ("motion", w[1] if len(w) > 1 else None)
    if w[0] in ("subscribe", "arrow", "gola", "circle"): return ("motion", w[0])
    if w[0] in ("music", "gaana", "bgm"): return ("music", None)
    if w[0] in ("sound", "sfx", "awaaz_effect"):
        cat = w[1] if len(w) > 1 else "whoosh"
        cat = {"hit": "boom", "dhamaka": "boom", "swoosh": "whoosh"}.get(cat, cat)
        return ("sound", cat if re.match(r"^[a-z_]{2,20}$", cat) else "whoosh")
    return None


def save_asset(path, kind, cat=None):
    path = Path(path)
    if kind == "layer": d = TOOL / "mere_layers"
    elif kind == "transition": d = TOOL / "mere_transitions"
    elif kind == "motion": d = TOOL / "mere_motion"
    elif kind == "music": d = TOOL / "music"
    else: d = TOOL / "mere_sounds" / (cat or "whoosh")
    d.mkdir(parents=True, exist_ok=True)
    name = path.name
    if kind == "motion":
        tag = {"subscribe": "subscribe", "arrow": "arrow", "gola": "circle", "circle": "circle"}.get(cat or "")
        if tag and tag not in name.lower():
            name = f"{tag}_{name}"
    dst = d / name
    k = 1
    while dst.exists():
        dst = d / f"{path.stem}_{k}{path.suffix}"; k += 1
    shutil.move(str(path), dst)
    return dst


# ------------------------------------------------------------------ v2.17c: Google Drive backup + guide
SKIP_DIRS = {"temp", "output", "backup", "ai_aankh", "__pycache__", "venv", ".venv", "update_tmp"}
GUIDE_NAME = "SETUP_GUIDE_HINDI.txt"


def drive_backup_dir():
    try:
        import meta
        root = meta.find_drive(read_style_safe())
    except Exception:
        root = None
    return (root / "VG Backup") if root else None


def read_style_safe():
    try:
        from common import read_style
        return read_style(STYLE)
    except Exception:
        return {}


def guide_text():
    v = version()
    notes = []
    for f in sorted(TOOL.glob("V2.*_UPDATE_HINDI.txt")):
        try: notes.append(f.read_text(encoding="utf-8"))
        except Exception: pass
    return f"""VG VIDEO TOOL – NAYE LAPTOP PE WAPAS LAANE KI GUIDE  (version v{v}, {datetime.datetime.now():%d %b %Y})
=====================================================================================

Ye guide har backup ke saath apne-aap update hoti hai.

STEP 1 – Google Drive
  Naye laptop pe "Google Drive for Desktop" install karo, apne Google account se login.
  File Explorer me  G:\\My Drive\\VG Backup  folder dikhega.

STEP 2 – Tool nikaalo
  VG_Backup_LATEST.zip pe right-click -> Extract All
  Jagah:  C:\\Users\\<aapka naam>\\Documents\\   (andar  VideoTool  folder banega)

STEP 3 – Ek click setup
  VideoTool folder me  0_WAPAS_LAAO.bat  pe double-click.
  Ye khud karega: Python + FFmpeg install (internet chahiye, 5-15 min), tool ke packages, bot chalu.
  Agar Windows "protected your PC" bole -> More info -> Run anyway.

STEP 4 – Keys
  api keys.txt backup me hi hai (VideoTool folder me) – kuch nahi karna.
  (Nayi key chahiye to: Gemini – aistudio.google.com/apikey, Pixabay – pixabay.com/api/docs,
   Telegram – @BotFather. Format: GEMINI=...  PIXABAY=...  TELEGRAM=...  har ek nayi line pe)

STEP 5 – Check
  Phone pe bot ko /health bhejo, phir /test jaisa koi chhota script.
  Pehli video pe AI models (AI aankh, Whisper, 3D) khud download honge (~1-2 GB, ek hi baar).

BACKUP ME KYA HAI: poora tool, style.txt (settings), api keys, seekha hua style + effects (seekha),
  mere_sounds / music / transitions / layers / motion, assets (font, logo).
NAHI HAI: AI models (khud download), Python/FFmpeg (0_WAPAS_LAAO install karta hai), bani videos (Drive ke VG Videos me).

DHYAN: VG Backup folder kisi ke saath SHARE mat karna – isme aapki keys hain.

Phone se:  /backup = abhi backup   /backup_status = aakhri backup kab bana

-------------------------------------------------------------------------------------
UPDATES KA ITIHAAS:
""" + "\n\n".join(notes)


def make_backup():
    """Returns (ok, message). Drive ke 'VG Backup' me ZIP + guide. Aakhri 3 dated backup rakhta hai."""
    d = drive_backup_dir()
    if not d:
        return False, "Google Drive laptop pe nahi mila (Drive for Desktop chalu hai?)"
    try:
        d.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d")
        tmp = TOOL / "temp" / "vg_backup_tmp.zip"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for p in TOOL.rglob("*"):
                rel = p.relative_to(TOOL)
                if any(part in SKIP_DIRS for part in rel.parts[:-1]) or (p.is_dir()) or rel.parts[0] in SKIP_DIRS:
                    continue
                if p.suffix.lower() in (".part", ".pyc", ".log") or p.name in ("bot_status.json",):
                    continue
                try:
                    z.write(p, Path("VideoTool") / rel); n += 1
                except Exception:
                    continue
            z.writestr("VideoTool/" + GUIDE_NAME, guide_text())
            try:                                           # keys file kahin aur ho (Downloads) to bhi saath
                from common import read_keys, KEY_SOURCE
                read_keys()
                kp = Path(KEY_SOURCE[0]) if KEY_SOURCE else None
                if kp and kp.exists() and TOOL not in kp.parents:
                    z.write(kp, "VideoTool/api keys.txt")
            except Exception:
                pass
        dated = d / f"VG_Backup_{stamp}.zip"
        shutil.copy2(tmp, dated)
        shutil.copy2(tmp, d / "VG_Backup_LATEST.zip")
        (d / GUIDE_NAME).write_text(guide_text(), encoding="utf-8")
        olds = sorted(d.glob("VG_Backup_20*.zip"))
        for o in olds[:-3]:
            try: o.unlink()
            except Exception: pass
        mb = tmp.stat().st_size / 1e6
        tmp.unlink()
        st = {"t": time.time(), "mb": round(mb, 1), "files": n, "v": version(), "where": str(d)}
        (TOOL / "temp" / "backup_status.json").write_text(json.dumps(st), encoding="utf-8")
        return True, f"✅ Backup ban gaya (v{version()}, {mb:.0f} MB, {n} files) → {d}"
    except Exception as e:
        return False, f"Backup nahi bana: {e}"


def backup_status():
    try:
        st = json.loads((TOOL / "temp" / "backup_status.json").read_text(encoding="utf-8"))
        ago = (time.time() - st["t"]) / 3600
        return (f"💾 Aakhri backup: {datetime.datetime.fromtimestamp(st['t']):%d %b %H:%M} ({ago:.0f} ghante pehle)\n"
                f"Version v{st['v']}, {st['mb']} MB, {st['files']} files\nJagah: {st['where']}")
    except Exception:
        return "💾 Abhi tak koi backup nahi bana. /backup bhejo."
