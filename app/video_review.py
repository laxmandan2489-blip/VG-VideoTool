"""v3.6 VIDEO REVIEW – video banne ke BAAD poori jaanch (insaan ki tarah, lekin naap-tol se).

Kya dekhta hai (sab local, internet / Gemini nahi chahiye):
  CAPTIONS : do caption ek saath (overlap), beech me jhapak (chhota gap), akela 1 shabd ka tukda,
             screen se bahar jaata lamba caption, bolte waqt caption gayab
  VISUAL   : har cut ka beech wala frame -> AI aankh (CLIP) se us line se kitna milta hai (aankh na ho to skip)
             same frame / same clip baar-baar, full-screen (upar-neeche kaali/blur patti), atki (static) video
  TIMING   : line badli par cut nahi / cut line se aage-peeche (>0.3s)
  PACE     : shuru ke 3 sec me kitne cut (hook), sabse lamba shot, average shot
Output: <video>_REVIEW.md + _REVIEW.json, aur Telegram ke liye ek line ka saar.
Jo check nahi ho paya wo report me "nahi hua" likha jaata hai (jhooth PASS nahi).
"""
import json, re, subprocess
from pathlib import Path
import numpy as np

try:
    from common import log
except Exception:                                   # tests
    def log(*a, **k): pass


# ------------------------------------------------------------------ helpers
def _t(s):
    h, m, x = s.split(":"); return int(h) * 3600 + int(m) * 60 + float(x)


def parse_ass(path, style="Cap"):
    ev = []
    try:
        for ln in Path(path).read_text(encoding="utf-8").splitlines():
            if not ln.startswith("Dialogue:"): continue
            p = ln.split(",", 9)
            if len(p) < 10 or p[3].strip() != style or p[0].split(":")[1].strip() != "0": continue   # sirf captions (layer 0)
            txt = re.sub(r"\{[^}]*\}", "", p[9]).replace("\\N", " ").strip()
            ev.append((_t(p[1]), _t(p[2]), txt))
    except Exception:
        return None
    return sorted(ev)


def frame_at(video, t, w=270):
    """Ek frame (RGB numpy, chhota) – review ke liye."""
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(video),
                        "-frames:v", "1", "-vf", f"scale={w}:-2", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=60)
    n = len(r.stdout)
    if r.returncode != 0 or n < w * 3: return None
    h = n // (w * 3)
    return np.frombuffer(r.stdout[: w * 3 * h], np.uint8).reshape(h, w, 3)


def dhash(img, n=8):
    from PIL import Image
    g = Image.fromarray(img).convert("L").resize((n + 1, n))
    a = np.asarray(g, dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).flatten()


def _sharp(a):
    g = a.mean(axis=2) if a.ndim == 3 else a
    if g.shape[0] < 3 or g.shape[1] < 3: return 0.0
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var())


def bars(img):
    """Upar/neeche patti: kaali (bahut andheri + ek rang) ya blur (beech se bahut kam sharp). '' = full screen."""
    h = img.shape[0]; b = max(4, int(h * 0.12))
    top, bot, mid = img[:b], img[-b:], img[int(h * 0.35):int(h * 0.65)]
    def black(x): return float(x.mean()) < 14 and float(x.std()) < 8
    if black(top) and black(bot): return "kaali patti"
    sm = _sharp(mid)
    if sm > 60 and _sharp(top) < sm * 0.08 and _sharp(bot) < sm * 0.08: return "blur patti (chhota frame)"
    # card/frame: poori chaudai pe seedhi aadi lakeer – upar (5-45%) AUR neeche (50-95%) dono
    g = img.mean(axis=2)
    d = np.abs(np.diff(g, axis=0))                       # (h-1, w)
    cover = (d > 14).mean(axis=1)                        # har row pe kitne % columns me tez badlav
    def edge(a, b):
        seg = cover[int(h * a):int(h * b)]
        return len(seg) and float(seg.max()) > 0.82
    if edge(0.05, 0.45) and edge(0.50, 0.95): return "chhota frame (upar-neeche patti)"
    # blur background wala card: upar (logo chhod ke) aur neeche (caption chhod ke) dhundhla, beech tez,
    # aur beech me kahin seedhi lakeer (kam se kam aadhi chaudai)
    gx = np.abs(np.diff(g[:, int(img.shape[1] * 0.2):], axis=1)).mean(axis=1)
    def gm(a, b): return float(gx[int(h * a):int(h * b)].mean())
    mid_s = gm(0.30, 0.55)
    soft = mid_s > 3 and gm(0.03, 0.09) < mid_s * 0.3 and gm(0.86, 0.96) < mid_s * 0.3
    e2 = lambda a, b: float((np.abs(np.diff(g[int(h * a):int(h * b)], axis=0)) > 8).mean(axis=1).max()) > 0.6
    if soft and (e2(0.05, 0.40) or e2(0.55, 0.92)): return "chhota frame (blur background)"
    return ""


def text_width(text, size, font_path):
    try:
        from PIL import ImageFont
        f = ImageFont.truetype(str(font_path), int(size))
        return f.getlength(text) * 0.567            # libass me Poppins asal me ~0.57x (yahan naap ke dekha: 82 -> 769px)
    except Exception:
        return len(text) * size * 0.55


def voice_envelope(video, hop=0.05):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "8000",
                        "-f", "f32le", "-"], capture_output=True, timeout=120)
    x = np.frombuffer(r.stdout, np.float32) if r.returncode == 0 else np.zeros(0, np.float32)
    k = int(8000 * hop)
    if len(x) < k * 4: return None
    m = len(x) // k
    e = np.sqrt((x[: m * k].reshape(m, k) ** 2).mean(1))
    return e


# ------------------------------------------------------------------ main
def review(video, cuts, sents, ass, W, H, total, style=None, lock=None):
    style = style or {}
    R = {"video": str(video), "checks": {}, "issues": [], "not_done": [], "cuts": []}
    issues = R["issues"]; C = R["checks"]

    # ---- CAPTIONS
    ev = parse_ass(ass) if ass else None
    if ev is None:
        R["not_done"].append("captions file nahi padhi")
    else:
        ov = [(a, b) for a, b in zip(ev, ev[1:]) if a[1] > b[0] + 0.01]
        flick = [(a, b) for a, b in zip(ev, ev[1:]) if 0.01 < b[0] - a[1] < 0.12]
        C["caption_events"] = len(ev); C["caption_overlap"] = len(ov); C["caption_flicker"] = len(flick)
        if ov: issues.append(("caption", f"{len(ov)} jagah do caption ek saath (pehla {ov[0][0][0]:.1f}s pe)", 8))
        if flick: issues.append(("caption", f"{len(flick)} jagah caption jhapakta hai (pehla {flick[0][0][1]:.1f}s)", 4))
        try:
            import render
            n = int(float(style.get("caption_ref_shabd") or 4))
            orph = [g for s in sents for g in render.cap_groups(s.get("words") or [], n) if len(g) == 1
                    and len(s.get("words") or []) > 1]
            C["caption_single_word"] = len(orph)
            if orph: issues.append(("caption", f"{len(orph)} caption tukde me akela 1 shabd", 3))
            size = float(style.get("caption_ref_size") or 82) * (W / 1080)
            font = render.ASSETS / "fonts" / "Poppins-SemiBold.ttf"
            wide = sorted({t for _, _, t in ev if text_width(t, size, font) > W * 0.88})
            C["caption_too_wide"] = len(wide)
            if wide: issues.append(("caption", f"{len(wide)} caption screen se bahar ja sakte (jaise: \"{wide[0][:40]}\")", 4))
        except Exception as e:
            R["not_done"].append(f"caption shabd/chaudai check: {str(e)[:80]}")
        env = voice_envelope(video)
        if env is not None:
            hop = 0.05; thr = max(0.01, float(np.percentile(env, 60)) * 0.5)
            spk = env > thr
            cov = np.zeros(len(env), bool)
            for a, b, _ in ev:
                cov[int(a / hop):int(b / hop) + 1] = True
            miss = float((spk & ~cov[: len(spk)]).sum() / max(1, spk.sum()))
            C["speech_without_caption_pct"] = round(miss * 100, 1)
            if miss > 0.12: issues.append(("caption", f"bolte waqt {miss*100:.0f}% samay caption nahi dikhta", 5))
        else:
            R["not_done"].append("awaaz vs caption mel (awaaz padh nahi paya)")

    # ---- VISUAL + TIMING (EDL se)
    if not cuts:
        R["not_done"].append("EDL nahi mila – cut-wise visual jaanch nahi hui")
    else:
        aankh_ok = False
        try:
            import aankh
            aankh_ok = bool(aankh.ready())
        except Exception:
            aankh_ok = False
        if not aankh_ok: R["not_done"].append("AI aankh (CLIP) nahi chali – visual-line mel ka score nahi")
        hashes = []; low = []; barred = []; static = []
        for c in cuts:
            mid = (c["rec_in"] + c["rec_out"]) / 2
            img = frame_at(video, mid)
            row = {"n": c["n"], "line": c["line"], "t": round(mid, 2), "src": c.get("src", "")}
            if img is None:
                row["note"] = "frame nahi nikla"; R["cuts"].append(row); continue
            bb = bars(img)
            # v3.13: user ne maanga "poori photo dikhe" -> photo (image) cut pe blur background galti nahi
            if bb and not (c.get("kind") == "image" and str((style or {}).get("photo_poora", "haan")).lower() != "nahi"):
                barred.append((c, bb)); row["bars"] = bb
            hashes.append((c, dhash(img)))
            if c.get("kind") == "video" and c["dur"] > 1.0:
                a2 = frame_at(video, c["rec_in"] + 0.15); b2 = frame_at(video, c["rec_out"] - 0.15)
                if a2 is not None and b2 is not None and a2.shape == b2.shape:
                    if float(np.abs(a2.astype(np.int16) - b2.astype(np.int16)).mean()) < 1.0:
                        static.append(c); row["static"] = True
            if aankh_ok:
                q = ""
                if lock and lock.get("scenes") and c["line"] - 1 < len(lock["scenes"]):
                    q = lock["scenes"][c["line"] - 1].get("show") or lock["scenes"][c["line"] - 1].get("query") or ""
                q = q or c.get("line_text", "")
                try:
                    from PIL import Image
                    sc, ng = aankh.scores([Image.fromarray(img)], q[:200])
                    row["clip"] = round(float(sc[0]), 3); row["query"] = q[:80]
                    if float(sc[0]) < 0.205: low.append((c, float(sc[0]), q))
                except Exception as e:
                    row["note"] = f"aankh: {str(e)[:60]}"
            R["cuts"].append(row)
        # repeats (same frame on non-neighbour cuts)
        rep = []
        for i in range(len(hashes)):
            for j in range(i + 2, len(hashes)):
                if int((hashes[i][1] != hashes[j][1]).sum()) <= 5:
                    rep.append((hashes[i][0]["n"], hashes[j][0]["n"]))
        srcs = {}
        for c in cuts:
            if c.get("source"): srcs[c["source"]] = srcs.get(c["source"], 0) + 1
        over = {Path(k).name: v for k, v in srcs.items() if v > 2 and "kcard" not in k}
        C.update(cuts=len(cuts), visual_low_match=len(low), repeat_frames=len(rep), bars=len(barred),
                 static_video=len(static), source_used_3plus=over)
        if low:
            issues.append(("visual", "line se kam mel: " + ", ".join(f"cut {c['n']} (line {c['line']})"
                                                                    for c, _, _ in low[:6]), 4 * min(len(low), 5)))
        if rep: issues.append(("visual", f"same visual dobara: cut {rep[0][0]} = cut {rep[0][1]}" +
                               (f" (+{len(rep)-1} aur)" if len(rep) > 1 else ""), 3 * min(len(rep), 4)))
        if over: issues.append(("visual", "ek clip 3+ baar: " + ", ".join(f"{k} x{v}" for k, v in list(over.items())[:3]), 4))
        if barred: issues.append(("visual", f"{len(barred)} cut full-screen nahi ({barred[0][1]}, cut {barred[0][0]['n']})", 5 * min(len(barred), 3)))
        if static: issues.append(("visual", f"{len(static)} video cut atke hue (hil nahi rahe)", 4))
        # timing: line start vs cut
        off = []
        for s_i, s in enumerate(sents):
            first = next((c for c in cuts if c["line"] == s_i + 1 and c.get("new_line")), None)
            if first is None: continue
            d = first["rec_in"] - s["start"]
            if abs(d) > 0.3: off.append((s_i + 1, d))
        C["line_cut_offset"] = [(l, round(d, 2)) for l, d in off]
        if off: issues.append(("timing", "visual line se aage/peeche: " + ", ".join(f"line {l} ({d:+.1f}s)" for l, d in off[:5]), 3 * min(len(off), 4)))
        durs = [c["dur"] for c in cuts]
        hook_cuts = sum(1 for c in cuts if c["rec_in"] < 3.0)
        C.update(avg_shot=round(float(np.mean(durs)), 2), max_shot=round(float(max(durs)), 2), cuts_first_3s=hook_cuts)
        if max(durs) > 4.5: issues.append(("pace", f"ek shot {max(durs):.1f}s lamba (4 se kam rakho)", 2))
        if hook_cuts < 2: issues.append(("pace", "shuru ke 3 sec me sirf 1 visual – hook dheema", 3))

    score = max(0, 100 - sum(p for _, _, p in issues))
    R["score"] = score
    R["verdict"] = "BADHIYA" if score >= 85 else "THEEK" if score >= 70 else "KAMZOR"
    try:
        base = Path(video).with_suffix("")
        Path(str(base) + "_REVIEW.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        md = [f"# Video Review – {score}/100 ({R['verdict']})", ""]
        md += [f"- **{k}**: {m}" for k, m, _ in issues] or ["- koi dikkat nahi mili"]
        if R["not_done"]: md += ["", "## Ye check NAHI ho paye"] + [f"- {x}" for x in R["not_done"]]
        md += ["", "## Har cut", "| cut | line | sec | source | CLIP | note |", "|---|---|---|---|---|---|"]
        for r in R["cuts"]:
            md.append(f"| {r['n']} | {r['line']} | {r['t']} | {r.get('src','')[:30]} | {r.get('clip','-')} | "
                      f"{r.get('bars','')}{' atka' if r.get('static') else ''}{r.get('note','')} |")
        Path(str(base) + "_REVIEW.md").write_text("\n".join(md), encoding="utf-8")
    except Exception:
        pass
    return R


def summary(R):
    top = "; ".join(m for _, m, _ in sorted(R.get("issues", []), key=lambda x: -x[2])[:3])
    return f"{R.get('score', '?')}/100 {R.get('verdict', '')}" + (f" – {top}" if top else " – sab theek")
