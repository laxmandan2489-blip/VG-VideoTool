"""v5.0 HYBRID DIRECTOR – AI mode + Stock mode ab EK hi system (free).

Kaam (ek hi try me, koi re-render loop nahi):
  1) plan()  – Gemini poori script padh ke har line ke har ~2 sec beat ka ALAG shot likhta hai
               (dikhna kya chahiye + stock search query + AI scene prompt + kis shabd pe cut).
  2) Stock khoj (purana system: YouTube, Pexels, Pixabay, X, Pinterest, Archive.org, Wikimedia, NASA...)
     ab har beat ki apni query se chalti hai (visual_brain.PLAN[i]['beats'] me daal ke).
  3) judge_and_fill() – mili hui HAR clip/photo ka frame Gemini Vision dekhta hai (pehle sirf 16 dekhe jaate the),
     0-10 number deta hai. Har beat ko sabse achha, pehle na laga visual milta hai (video ko thodi preference).
     Jo beat khaali rahe (ya sab visual kamzor) -> us beat ke apne prompt se AI photo -> wo bhi Gemini jaanchta hai
     -> kamzor ho to EK baar naye prompt se dobara (poori video dobara nahi).
  4) report() – asli score: Gemini ne jo number diye unka average (khud ko diya hua number nahi).

Sab kuch fail-safe: Gemini band ho to CLIP se andaza, wo bhi na ho to purana tareeka chalta rahega.
"""
import io
import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import log

PASS = 7.0          # is se upar = beat sahi (Gemini 0-10)
AI_OK = 6.0         # AI photo is se kam -> ek baar dobara
VIDEO_BONUS = 0.6   # barabar ho to chalti video, photo se pehle
STATE = {"on": False, "beats": {}, "lock": {}, "report": {}, "judge": "none"}
_LOCK = threading.Lock()

SKIP_SRC = ("aapki footage", "aapka link", "chehra", "map", "news card", "tweet card", "ai explainer",
            "blender", "film trailer", "my_clips")


# ------------------------------------------------------------------ helpers
def _s(x, n=300):
    return re.sub(r"\s+", " ", str(x or "")).strip()[:n]


def _ask_json(key, parts, temperature=0.2, timeout=150):
    try:
        from ai import ask_json
        return ask_json(key, parts, temperature=temperature, timeout=timeout)
    except Exception as e:
        log(f"   (director gemini: {str(e)[:90]})", show=False)
        return None


def _line_text(s):
    return _s((s or {}).get("script") or (s or {}).get("text"), 400)


# ------------------------------------------------------------------ 1) beat plan
PLAN_PROMPT = """You are the director + B-roll editor of a viral Hindi YouTube Shorts / documentary channel.
Read the WHOLE script first, understand the story, then plan visuals BEAT BY BEAT.

Main subject of the video: {main}
Each numbered line below shows how many beats (shots) it needs: [beats=N]. One beat = one shot of about {step} seconds.

For EVERY beat give:
 "show": ONE concrete, literal English sentence: exactly what the viewer SEES in this shot (subject + action + place).
         It must PROVE the words spoken during that beat. Abstract words -> the closest REAL concrete thing
         (e.g. "paisa doob gaya" -> "worried Indian man looking at falling stock chart on laptop").
         Every beat of a line must be a DIFFERENT shot (different subject, action or place) - never the same thing twice.
 "q": 2 short English stock-footage search queries (2-4 words each) that will find real VIDEO of this shot on
      Pexels/Pixabay/YouTube. Concrete nouns, no abstract words, stay inside the story's world.
 "ai": a photorealistic scene description for an AI photo generator (25-45 words): subject, action, setting,
       time of day, camera angle (wide / medium / close-up / low angle / over-the-shoulder), lighting.
       If the topic is Indian, the people/places must look Indian. NEVER mention text, signs, logos, screens with
       writing, charts, numbers or words. If this beat is about a REAL named person, do NOT ask to draw their face:
       show the context instead (e.g. "silhouette of a politician at a podium in a crowded hall").
 "phrase": the first 1-3 Hindi words (copied EXACTLY from the line) at which this beat should start
           (first beat: the line's first word).
 "real": true if this beat MUST be real footage (a real named person, a real news event, a real brand/product,
         a real sports moment). Else false.

Return ONLY JSON: {{"lines": [{{"n": 1, "beats": [{{"show": "..", "q": ["..",".."], "ai": "..", "phrase": "..", "real": false}}]}}]}}

SCRIPT:
{script}
"""


def plan(sents, eng, spans, keys, main="", long_mode=False, chunk=10):
    """Gemini se har line ke har beat ka shot. STATE['beats'][i] = [beat dict, ...] (len = spans k)."""
    STATE["beats"].clear()
    key = (keys or {}).get("GEMINI")
    n = len(sents)
    step = 4.0 if long_mode else 2.0
    if key:
        for a in range(0, n, chunk):
            idx = list(range(a, min(n, a + chunk)))
            ctx = ""
            if a > 0:
                ctx = "(Earlier lines for context only, do not plan them:)\n" + "\n".join(
                    f"- {_line_text(sents[j])}" for j in range(max(0, a - 3), a)) + "\n"
            body = ctx + "\n".join(
                f"{j + 1}. [beats={spans[j][2]}] {_line_text(sents[j])}"
                + (f"   (English: {_s(eng[j], 220)})" if j < len(eng) and eng[j] else "") for j in idx)
            data = None
            for _try in range(2):
                data = _ask_json(key, [PLAN_PROMPT.format(main=main or "(find it from the script)", step=step,
                                                          script=body)], temperature=0.35, timeout=150)
                if isinstance(data, dict) and isinstance(data.get("lines"), list):
                    break
                data = None
            if not data:
                log(f"   (director plan: lines {a + 1}-{idx[-1] + 1} Gemini se nahi bani – purana plan)", show=False)
                continue
            for x in data["lines"]:
                try:
                    j = int(x.get("n")) - 1
                except Exception:
                    continue
                if j not in idx:
                    continue
                bs = []
                for b in (x.get("beats") or []):
                    if not isinstance(b, dict):
                        continue
                    show = _s(b.get("show"), 200)
                    ai_p = _s(b.get("ai"), 420) or show
                    q = [_s(q_, 50) for q_ in (b.get("q") or []) if isinstance(q_, str) and _s(q_)][:3]
                    if not show and not q:
                        continue
                    bs.append({"show": show or (q[0] if q else ""), "q": q or [show[:40]], "ai": ai_p,
                               "phrase": _s(b.get("phrase"), 40), "real": bool(b.get("real"))})
                if bs:
                    STATE["beats"][j] = bs
    # fallback: Gemini ka purana per-line plan (show / ai_prompt / q)
    try:
        import sources
    except Exception:
        sources = None
    for i in range(n):
        need = max(1, int(spans[i][2]))
        bs = list(STATE["beats"].get(i) or [])
        if not bs:
            rp = (getattr(sources, "RAW_PLAN", {}) or {}).get(i) or {} if sources else {}
            show = _s((getattr(sources, "SHOW", {}) or {}).get(i) if sources else "", 200) or _s(rp.get("show"), 200) \
                or _s(eng[i] if i < len(eng) else "", 200)
            ai_p = _s(rp.get("ai_prompt"), 400) or show
            qs = [q_ for q_ in (rp.get("q") or []) if isinstance(q_, str)][:4] or [show[:40]]
            angles = ("wide establishing shot", "medium shot", "close-up detail shot", "low angle shot")
            bs = [{"show": show, "q": [qs[k % len(qs)]], "ai": f"{angles[k % 4]}, {ai_p}", "phrase": "",
                   "real": False} for k in range(need)]
        while len(bs) < need:                        # Gemini ne kam beat diye -> alag angle se bharo
            b0 = bs[len(bs) % len(bs)]
            bs.append(dict(b0, ai=f"different camera angle, close-up detail, {b0['ai']}", phrase=""))
        STATE["beats"][i] = bs[:need]
    STATE["on"] = True
    good = sum(1 for i in range(n) if STATE["beats"].get(i))
    log(f"   🎬 Director: {good}/{n} lines ke liye {sum(len(v) for v in STATE['beats'].values())} alag beat-shot plan bane")
    return STATE["beats"]


def inject(vb_module):
    """visual_brain.PLAN[i]['beats'] me daalo -> visual_pick har beat ki alag khoj + word-timestamp pe cut."""
    if vb_module is None:
        return
    for i, bs in STATE["beats"].items():
        try:
            p = vb_module.PLAN.get(i)
            if not isinstance(p, dict):
                p = {}
                vb_module.PLAN[i] = p
            p["beats"] = [{"subject": b["show"], "query": (b["q"] or [b["show"]])[0], "phrase": b.get("phrase", "")}
                          for b in bs]
        except Exception:
            pass


def queries(i):
    out = []
    for b in STATE["beats"].get(i) or []:
        out += [q for q in b.get("q") or [] if q]
    return list(dict.fromkeys(out))[:6]


def beat_texts(i):
    return [b["show"] for b in STATE["beats"].get(i) or []]


# ------------------------------------------------------------------ frames
def _frame(item, width=384):
    p = item.get("path")
    if not p or not Path(str(p)).exists():
        return None
    try:
        from PIL import Image
        if item.get("kind") == "image" or Path(str(p)).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            im = Image.open(p).convert("RGB")
        else:
            ss = float(item.get("ss") or 0.0) + 1.0
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{ss:.2f}", "-i", str(p), "-frames:v", "1",
                                "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                               capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            if not r.stdout:
                r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(p), "-frames:v", "1",
                                    "-vf", f"scale={width}:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                                   capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            if not r.stdout:
                return None
            im = Image.open(io.BytesIO(r.stdout)).convert("RGB")
        im.thumbnail((width, width * 2))
        return im
    except Exception:
        return None


def _jpg(im):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=70)
    return b.getvalue()


# ------------------------------------------------------------------ 2) judge (Gemini Vision, sab ke sab)
JUDGE_PROMPT = """You are a very strict B-roll editor checking if each candidate shot matches the narration.
For each candidate you get: the narration line (Hindi + English), the planned beats (what must be seen), and the image.
Score 0-10:
 10 = shows exactly what the line/beat says (right subject, right action, right context)
  8 = clearly the right subject and context, a viewer would instantly connect it to the words
  6 = related and acceptable but generic
  4 = weak: same general topic but wrong subject/action/place
  2 = wrong (different person/country/thing, misleading)
  0 = unrelated, OR big burned-in text/subtitles/watermark/logo, foreign-language text, cartoon/meme, black/blurry frame
Also give "b" = the beat number (1..N) this image fits best, and a 3-8 word "why".
Return ONLY JSON: {"r": [{"c": 1, "s": 7, "b": 1, "why": ".."}]}"""


def _judge_batch(key, rows):
    """rows: [(cid, line_txt, eng_txt, beats[list], PIL)] -> {cid: (score, beat_idx0, why)}"""
    parts = [JUDGE_PROMPT]
    for n, (cid, lt, et, bts, im) in enumerate(rows, 1):
        bl = " | ".join(f"{k + 1}) {b}" for k, b in enumerate(bts)) or "-"
        parts += [f"Candidate {n}: LINE: \"{lt[:220]}\" (English: {et[:200]}) BEATS: {bl[:500]}", {"jpg": _jpg(im)}]
    data = _ask_json(key, parts, temperature=0.1, timeout=150)
    out = {}
    if isinstance(data, dict):
        for r in data.get("r") or data.get("results") or []:
            try:
                n = int(r.get("c") or r.get("n")) - 1
                if 0 <= n < len(rows):
                    s = max(0.0, min(10.0, float(r.get("s") if r.get("s") is not None else r.get("score"))))
                    b = int(r.get("b") or 1) - 1
                    out[rows[n][0]] = (s, b, _s(r.get("why"), 80))
            except Exception:
                continue
    return out


def _clip_judge(rows):
    """Gemini band -> CLIP se andaza (kam bharosemand, report me likha jaata hai)."""
    out = {}
    try:
        import aankh
        if not aankh.ready():
            return out
        for cid, lt, et, bts, im in rows:
            texts = [t for t in ([et] + list(bts)) if t][:5] or [lt]
            sim, neg = aankh.scores_batch([im], texts)
            row = list(sim[0])
            best = max(range(len(row)), key=lambda k: row[k])
            v = float(row[best])
            s = max(0.0, min(10.0, (v - 0.17) / 0.015))      # 0.17 -> 0, ~0.32 -> 10
            if float(neg[0]) > v + 0.02:
                s = min(s, 3.0)
            out[cid] = (round(s, 1), max(0, best - 1), "clip andaza")
    except Exception as e:
        log(f"   (director clip judge skip: {str(e)[:80]})", show=False)
    return out


def judge(rows, keys, batch=10, threads=2):
    key = (keys or {}).get("GEMINI")
    res = {}
    if not rows:
        return res
    chunks = [rows[a:a + batch] for a in range(0, len(rows), batch)]
    if key:
        with ThreadPoolExecutor(max_workers=threads) as ex:
            for r in ex.map(lambda ch: _judge_batch(key, ch), chunks):
                res.update(r or {})
        if res:
            STATE["judge"] = "gemini"
    miss = [r for r in rows if r[0] not in res]
    if miss:
        cl = _clip_judge(miss)
        if cl and STATE["judge"] != "gemini":
            STATE["judge"] = "clip"
        elif cl:
            STATE["judge"] = "gemini+clip"
        res.update(cl)
    return res


# ------------------------------------------------------------------ dedupe (dHash, poori video me)
class _Dedup:
    """Ek hi photo/clip (ya lagbhag same dikhne wali) poori video me dobara nahi. AI photo bhi isme aati hai."""

    def __init__(self, thr=9):
        self.thr = thr
        self.keys = set()
        self.hashes = []
        self._cache = {}

    def _key(self, it):
        return str(it.get("url") or "").split("#")[0].lower() or str(it.get("path") or "")

    def _dh(self, it):
        k = str(it.get("path") or "") + "|" + str(it.get("ss") or "")
        if k not in self._cache:
            try:
                from unique_guard import _dhash
                im = it.get("_im") or _frame(it, 160)
                self._cache[k] = _dhash(im) if im is not None else None
            except Exception:
                self._cache[k] = None
        return self._cache[k]

    def is_duplicate(self, it):
        if self._key(it) in self.keys:
            return True
        h = self._dh(it)
        return h is not None and any(bin(h ^ x).count("1") <= self.thr for x in self.hashes)

    def register(self, it):
        self.keys.add(self._key(it))
        h = self._dh(it)
        if h is not None:
            self.hashes.append(h)


def _prior(it):
    """Jaanch na ho paye to purane picker (CLIP) ke score se andaza; wo bhi na ho to 7 (rakh lo)."""
    try:
        v = it.get("score")
        if v is not None:
            return max(0.0, min(10.0, (float(v) - 0.17) / 0.015))
    except Exception:
        pass
    return 7.0


# ------------------------------------------------------------------ 3) AI fill
def _ai_image(prompt, work, W, H, keys, topic, seed):
    try:
        import cloud_visuals
        p = cloud_visuals.generate_scene_image(prompt, Path(work) / "ai_visuals", topic=topic, W=W, H=H, keys=keys,
                                               variation=seed, raw=True)
        return Path(p) if p and Path(p).exists() else None
    except Exception as e:
        log(f"   (director AI photo fail: {str(e)[:80]})", show=False)
        return None


def _special(items):
    for x in items or []:
        if x.get("face") or x.get("whole"):
            return True
        if str(x.get("src", "")).lower().startswith(SKIP_SRC):
            return True
    return False


def judge_and_fill(found, sents, eng, keys, work, W, H, topic="", skip_lines=(), user_ai=None, face_lines=(),
                   style=None, time_budget_s=420):
    """found[i] = (items, kw). Har normal line ko exactly k beat ke verified visual deta hai (item['dir']=True)."""
    t0 = time.time()
    user_ai = user_ai or {}
    guard = _Dedup()
    try:
        import visual_brain as _vb
    except Exception:
        _vb = None
    n = len(found)
    lines_todo = []
    for i in range(n):
        items = list(found[i][0] or [])
        if i in skip_lines or i in face_lines or _special(items) or not STATE["beats"].get(i):
            # whole-line cards / aapki footage / chehra: un ko guard me register karo (repeat na ho)
            for x in items:
                if guard: guard.register(x)
            continue
        lines_todo.append(i)
    # --- a) saare candidates ka frame + Gemini jaanch (ek saath, batch me)
    rows, cmap = [], {}
    def _prep(i):
        out = []
        for k, it in enumerate(found[i][0] or []):
            if it.get("kind") not in ("video", "image") or not it.get("path"):
                continue
            im = _frame(it)
            if im is not None:
                out.append((f"{i}:{k}", i, it, im))
        return out
    with ThreadPoolExecutor(max_workers=4) as ex:
        for lst in ex.map(_prep, lines_todo):
            for cid, i, it, im in lst:
                cmap[cid] = (i, it)
                rows.append((cid, _line_text(sents[i]), _s(eng[i] if i < len(eng) else "", 220), beat_texts(i), im))
    log(f"   🎯 Director: {len(rows)} mili clips/photos Gemini Vision se jaanch raha hoon ({len(lines_todo)} lines)...")
    J = judge(rows, keys)
    # --- b) har beat ko sabse achha visual (pehle na laga, video ko thodi preference)
    plan_out, need_ai = {}, []
    for i in lines_todo:
        beats = STATE["beats"][i]
        k = len(beats)
        cands = []
        for cid, (ii, it) in cmap.items():
            if ii != i:
                continue
            if cid in J:
                s, b, why = J[cid]
                cands.append({"cid": cid, "it": it, "s": s, "b": b, "why": why, "judged": True})
            else:                                       # jaanch nahi ho payi (Gemini + CLIP dono band):
                cands.append({"cid": cid, "it": it, "s": _prior(it), "b": -1,   # purane picker pe bharosa,
                              "why": "jaanch nahi hui", "judged": False})       # AI se andha nahi badlenge
        line_real = bool(_vb and _vb.is_real_line(i))
        chosen = [None] * k
        used = set()
        for j in range(k):
            best, best_eff = None, -1e9
            for c in cands:
                if c["cid"] in used:
                    continue
                if guard and guard.is_duplicate(c["it"]):
                    continue
                eff = c["s"] + (VIDEO_BONUS if c["it"].get("kind") == "video" else 0.0) + (0.8 if c["b"] == j else 0.0)
                if eff > best_eff:
                    best, best_eff = c, eff
            if best is not None and (best["s"] >= PASS or (beats[j].get("real") and best["s"] >= 5.0)
                                     or (line_real and best["s"] >= 5.0)):
                used.add(best["cid"])
                it = dict(best["it"], dir=True, vscore=best["s"] if best.get("judged") else None, vwhy=best["why"], beat=j)
                chosen[j] = it
                if guard: guard.register(it)
            else:
                need_ai.append((i, j, best))
        plan_out[i] = chosen
    # --- c) khaali beats -> beat ka apna AI prompt (har beat alag)
    def _gen(job):
        i, j, best = job
        b = STATE["beats"][i][j]
        if i in user_ai and user_ai.get(i):
            prompt = f"{user_ai[i]}, {('wide shot', 'medium shot', 'close-up', 'low angle')[j % 4]}"
        else:
            prompt = b.get("ai") or b.get("show")
        if best is not None and not best.get("judged") and best["s"] >= 5.0:
            return (i, j, None, prompt)              # jaanch band – theek-thaak asli clip ko andhe me AI se nahi badlenge
        if b.get("real") and best is not None and best["s"] >= 4.0:
            return (i, j, None, prompt)              # asli event/insaan: nakli AI se behtar asli (thoda kamzor) clip
        if b.get("real") and _vb is not None and not _vb.allow_ai_fill(i, style or {}):
            return (i, j, None, prompt)
        p = _ai_image(prompt, work, W, H, keys, topic, seed=i * 31 + j * 7 + 1)
        return (i, j, p, prompt)
    gen_res = []
    if need_ai and time.time() - t0 < time_budget_s:
        log(f"   🎨 Director: {len(need_ai)} beat ke liye sahi footage nahi mili – unke apne prompt se AI photo...")
        with ThreadPoolExecutor(max_workers=3) as ex:
            gen_res = list(ex.map(_gen, need_ai))
    best_by = {(i, j): best for i, j, best in need_ai}
    # --- d) AI photo bhi Gemini jaanchega; kamzor -> ek baar naye prompt se
    ai_rows, ai_map = [], {}
    for i, j, p, prompt in gen_res:
        if p is None:
            continue
        im = _frame({"kind": "image", "path": p})
        if im is None:
            continue
        cid = f"ai:{i}:{j}"
        ai_map[cid] = (i, j, p, prompt)
        ai_rows.append((cid, _line_text(sents[i]), _s(eng[i] if i < len(eng) else "", 220),
                        [STATE["beats"][i][j]["show"]], im))
    AJ = judge(ai_rows, keys) if ai_rows else {}
    redo = [(cid, v) for cid, v in ai_map.items() if (AJ.get(cid) or (0,))[0] < AI_OK]
    if redo and time.time() - t0 < time_budget_s:
        def _regen(x):
            cid, (i, j, p, prompt) = x
            b = STATE["beats"][i][j]
            why = (AJ.get(cid) or (0, 0, ""))[2]
            p2_prompt = f"{b['show']}. {b.get('ai', '')}. Make the main subject large, clear and obvious in frame"
            p2 = _ai_image(p2_prompt, work, W, H, keys, topic, seed=i * 31 + j * 7 + 977)
            return cid, p2, p2_prompt, why
        with ThreadPoolExecutor(max_workers=3) as ex:
            rg = list(ex.map(_regen, redo))
        r2_rows = []
        for cid, p2, pr2, _w in rg:
            if not p2:
                continue
            im = _frame({"kind": "image", "path": p2})
            if im is None:
                continue
            i, j, _, _ = ai_map[cid]
            r2_rows.append((cid + ":2", _line_text(sents[i]), _s(eng[i] if i < len(eng) else "", 220),
                            [STATE["beats"][i][j]["show"]], im))
            ai_map[cid + ":2"] = (i, j, p2, pr2)
        AJ.update(judge(r2_rows, keys) if r2_rows else {})
    # har beat ka sabse achha AI version
    best_ai = {}
    for cid, (i, j, p, pr) in ai_map.items():
        s = (AJ.get(cid) or (None,))[0]
        s = 5.0 if s is None else s                     # jaanch na ho payi -> neutral (score me nahi gina jaata)
        if (i, j) not in best_ai or s > best_ai[(i, j)][0]:
            best_ai[(i, j)] = (s, p, (AJ.get(cid) or (0, 0, ""))[2])
    # --- e) final: har beat bharo
    for i in lines_todo:
        chosen = plan_out[i]
        for j in range(len(chosen)):
            if chosen[j] is not None:
                continue
            ai = best_ai.get((i, j))
            st = best_by.get((i, j))
            if ai and (st is None or ai[0] >= st["s"] - 0.5):
                it = {"kind": "image", "path": Path(ai[1]), "credit": "", "src": "cloud flux (director)",
                      "fullbleed": True, "score": 0.36, "dir": True, "vscore": ai[0] if AJ else None,
                      "vwhy": ai[2], "beat": j}
                chosen[j] = it
                if guard: guard.register(it)
            elif st is not None and not (guard and guard.is_duplicate(st["it"])):
                it = dict(st["it"], dir=True, vscore=st["s"] if st.get("judged") else None, vwhy=st["why"], beat=j)
                chosen[j] = it
                if guard: guard.register(it)
        # abhi bhi khaali -> line ki koi video ka ALAG hissa (repeat photo nahi)
        for j in range(len(chosen)):
            if chosen[j] is None:
                vids = [c for c in chosen if c is not None and c.get("kind") == "video"]
                if vids:
                    v = vids[j % len(vids)]
                    chosen[j] = dict(v, ss=float(v.get("ss") or 0.0) + 2.5 * (j + 1), beat=j, vscore=v.get("vscore"))
        fin = [c for c in chosen if c is not None]
        if fin:
            found[i] = (fin, found[i][1])
    # --- f) asli score
    sc = []
    per_line = {}
    for i in lines_todo:
        vs = [float(c.get("vscore")) for c in (found[i][0] or []) if c.get("dir") and c.get("vscore") is not None]
        if vs:
            per_line[i + 1] = round(sum(vs) / len(vs) * 10)
            sc += vs
    total = round(sum(sc) / len(sc) * 10) if sc else None
    weak = [l_ for l_, v in per_line.items() if v < 70]
    n_ai = sum(1 for i in lines_todo for c in found[i][0] or [] if str(c.get("src", "")).startswith("cloud flux"))
    n_vid = sum(1 for i in lines_todo for c in found[i][0] or [] if c.get("dir") and c.get("kind") == "video")
    STATE["report"] = {"score": total, "judge": STATE["judge"], "beats": len(sc), "lines": per_line, "weak_lines": weak,
                       "ai_shots": n_ai, "video_shots": n_vid, "special_lines": n - len(lines_todo),
                       "seconds": round(time.time() - t0)}
    log(f"   🎯 Director score: {total if total is not None else '?'}/100 ({STATE['judge']} ne {len(sc)} shot dekhe) – "
        f"{n_vid} asli video, {n_ai} AI photo, kamzor lines: {weak or 'koi nahi'} [{round(time.time() - t0)}s]")
    return STATE["report"]


def report_md():
    r = STATE.get("report") or {}
    if not r:
        return ""
    out = [f"# Director Visual Report – {r.get('score')}/100 (jaanch: {r.get('judge')})", ""]
    for l_, v in sorted((r.get("lines") or {}).items()):
        bs = STATE["beats"].get(l_ - 1) or []
        out.append(f"- line {l_}: {v}/100 – " + " | ".join(b["show"][:60] for b in bs))
    return "\n".join(out)
