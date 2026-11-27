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
MIN_USE = 6.0       # v5.3: is se kam number wala stock KABHI nahi lagta (pehle AI na bane to 3/10 bhi lag jaata tha)
CLIP_MAX = 6.0      # v5.3: CLIP (kamzor aankh) akela kisi visual ko PASS nahi kara sakta
AI_CAP = {"short": 12, "long": 26}   # v5.3: ek video me max AI photo (Cloudflare ki roz ki free limit bachao)
EXPLAIN_CAP = {"short": 2, "long": 4}
AI_OK = 6.0         # AI photo is se kam -> ek baar dobara
VIDEO_BONUS = 0.6   # barabar ho to chalti video, photo se pehle
STATE = {"on": False, "beats": {}, "lock": {}, "report": {}, "judge": "none", "planner": "rules", "ai_fail": 0}
_LOCK = threading.Lock()

SKIP_SRC = ("aapki footage", "aapka link", "chehra", "ai explainer", "blender", "film trailer", "my_clips")
CARD_SRC = ("map", "news card", "tweet card")      # v5.1: poori line ka card nahi – sirf pehla beat, baaki asli footage


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


# ------------------------------------------------------------------ 0) GitHub Models (FREE, alag quota)
# v5.1: GitHub Actions ka apna GITHUB_TOKEN (workflow me "permissions: models: read") se GPT-4.1 / GPT-4.1-mini
# FREE milta hai – Gemini ki free limit se bilkul alag. Plan + photo jaanch pehle yahin se, phir Gemini, phir Groq.
GH_URL = "https://models.github.ai/inference/chat/completions"
GEO_RE = re.compile(r"(देश|शहर|राज्य|गाँव|गांव|बॉर्डर|सीमा|नक्शा|महाद्वीप|सफर|यात्रा|किलोमीटर|नदी|पहाड़|समुद्र|द्वीप|"
                    r"country|city|state|border|continent|route|journey|km|river|mountain|ocean|island|map|"
                    r"[A-Z][a-z]+ (?:में|से|तक|की|के|का))")
GH = {"dead": set(), "used": ""}


def _gh_token():
    import os
    return (os.environ.get("GH_MODELS_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()


def _gh_chat(content, model, max_tokens=3000, timeout=120):
    tok = _gh_token()
    if not tok or model in GH["dead"]:
        return None
    try:
        import requests
        r = requests.post(GH_URL, timeout=timeout, headers={"Authorization": f"Bearer {tok}",
                                                            "Content-Type": "application/json"},
                          json={"model": model, "temperature": 0.15, "max_tokens": max_tokens,
                                "messages": [{"role": "user", "content": content}]})
        if r.status_code in (401, 403, 404):
            GH["dead"].add(model)
            log(f"   (GitHub Models {model}: {r.status_code} – workflow me 'models: read' + GITHUB_TOKEN chahiye)", show=False)
            return None
        if r.status_code == 429:
            GH["dead"].add(model)
            log(f"   (GitHub Models {model}: aaj/abhi ki limit – Gemini pe ja raha hoon)", show=False)
            return None
        if r.status_code != 200:
            log(f"   (GitHub Models {model}: HTTP {r.status_code} {r.text[:100]})", show=False)
            return None
        txt = r.json()["choices"][0]["message"]["content"]
        from ai import parse_json
        data = parse_json(txt)
        if data is not None:
            GH["used"] = model
        return data
    except Exception as e:
        log(f"   (GitHub Models fail: {str(e)[:90]})", show=False)
        return None


def gh_text(prompt, model="openai/gpt-4.1", max_tokens=4000, timeout=150):
    """GitHub Models se seedha text (HTML waghera) – JSON nahi."""
    tok = _gh_token()
    if not tok or model in GH["dead"]:
        return None
    try:
        import requests
        r = requests.post(GH_URL, timeout=timeout, headers={"Authorization": f"Bearer {tok}",
                                                            "Content-Type": "application/json"},
                          json={"model": model, "temperature": 0.35, "max_tokens": max_tokens,
                                "messages": [{"role": "user", "content": prompt}]})
        if r.status_code in (401, 403, 404, 429):
            GH["dead"].add(model); return None
        if r.status_code != 200:
            return None
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


# ------------------------------------------------------------------ 1) beat plan
PLAN_PROMPT = """You are the director + B-roll editor of a top Hindi YouTube Shorts / documentary channel.
Read the WHOLE script first. Understand its TOPIC and GENRE (science, history, money, tech, health, crime...).
Every visual must stay INSIDE that topic. Never drift to another genre (science video -> no random history or
fantasy; nutrition video -> no random space or vault doors). Show what the words are ABOUT, literally.

EXPLAIN LIKE A GREAT TEACHER: break every line into its pieces. Every important noun AND every action in the line
gets its own beat, in the SAME order as spoken. For "if X then Y" / "because X, Y" lines show X happening, then Y
happening (cause -> effect). Example: "agar nashedi cigarette dustbin me phenk de to aag lag jayegi" ->
1) drunk man secretly smoking, 2) he throws the burning cigarette into a dustbin full of paper, 3) paper starts
smoking, 4) flames burst out of the dustbin. Abstract words (rule, law, danger, risk) -> show the concrete thing.

Main subject of the video: {main}
Each numbered line shows how many beats (shots) it needs: [beats=N]. One beat = one shot of about {step} seconds.

For EVERY beat give:
 "show": ONE concrete, literal English sentence: exactly what the viewer SEES (who + doing what + where).
         It must PROVE the words spoken in that beat. If the line talks about something humans made, show humans
         making / using it. If the line names a country, show that country's people/streets. If it names food,
         show that food being eaten/made. Abstract words -> the closest REAL concrete scene.
         The beats of one line must be DIFFERENT shots (different subject, action, place or camera distance).
 "q": 3 English stock-VIDEO search queries, from exact to easy:
      [0] exact shot (3-5 words, e.g. "man throwing cigarette into dustbin"),
      [1] simple version that surely exists on Pexels/Pixabay (2-3 words, e.g. "throwing cigarette"),
      [2] mood/close-up fallback (2-3 words, e.g. "trash can fire").
      Concrete nouns + action only. No abstract words, no text/infographic/sign words.
 "ai": a photorealistic scene for an AI photo generator (25-45 words): subject, action, setting, era, time of day,
       camera distance/angle, lighting. Indian topic -> Indian people/places. Historical line -> that era's
       clothes and places. NEVER ask for text, signs, logos, screens with writing, charts or numbers.
 "phrase": the first 1-3 Hindi words (copied EXACTLY from the line) where this beat starts (beat 1 = line start).
 "real": true ONLY if the beat shows a specific REAL named person, a brand logo/product, or one specific recent
         news event that must not be faked. Generic historical or everyday scenes are NOT real (false).
 "type": how to show it:
         "footage" = real stock / YouTube video (default, best),
         "archive" = real old footage/photos of a historical event or era (before ~1995),
         "person"  = a real named person (put the exact English name in "who"; q must contain the name),
         "map"     = a satellite map zoom to a place - ONLY when WHERE something is IS the point of the beat
                     (a country/city/route/border being talked about). Max 1 map in the whole script.
                     Put the place's English name in "place". Never use map for food, science, people or money.
         "ai"      = no real footage can exist (imagination, inside the body, far future, impossible scene),
         "explain" = an animated diagram is clearer than any footage: a rule, a process, a comparison, numbers,
                     how something works step by step. Max 2 "explain" beats in a Short. Put a 1-line
                     description of the animation in "show".
For each line also give "means": one short English sentence - what the line is really saying.

Return ONLY JSON: {{"topic": "..", "genre": "..", "lines": [{{"n": 1, "means": "..", "beats": [{{"show": "..", "q": ["..",".."], "ai": "..", "phrase": "..", "real": false, "type": "footage", "place": "", "who": ""}}]}}]}}

SCRIPT:
{script}
"""


def plan(sents, eng, spans, keys, main="", long_mode=False, chunk=8):
    """Gemini se har line ke har beat ka shot. STATE['beats'][i] = [beat dict, ...] (len = spans k)."""
    STATE["beats"].clear()
    key = (keys or {}).get("GEMINI")
    n = len(sents)
    step = 4.0 if long_mode else 2.0
    if key or _gh_token():
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
            _pp = PLAN_PROMPT.format(main=main or "(find it from the script)", step=step, script=body)
            for mdl in ("openai/gpt-4.1", "openai/gpt-4.1-mini"):        # v5.1: GitHub Models (alag free quota)
                data = _gh_chat(_pp, mdl, max_tokens=4000, timeout=150)
                if isinstance(data, dict) and isinstance(data.get("lines"), list):
                    STATE["planner"] = "github " + mdl.split("/")[-1]
                    break
                data = None
            for _try in range(2):
                if data or not key:
                    break
                data = _ask_json(key, [_pp], temperature=0.35, timeout=150)
                if isinstance(data, dict) and isinstance(data.get("lines"), list):
                    STATE["planner"] = "gemini/backup"
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
                if data.get("topic") and not STATE.get("topic"):
                    STATE["topic"] = _s(data.get("topic"), 80) + (f" ({_s(data.get('genre'), 30)})" if data.get("genre") else "")
                if x.get("means"):
                    STATE.setdefault("means", {})[j] = _s(x.get("means"), 200)
                bs = []
                for b in (x.get("beats") or []):
                    if not isinstance(b, dict):
                        continue
                    show = _s(b.get("show"), 200)
                    ai_p = _s(b.get("ai"), 420) or show
                    q = [_s(q_, 50) for q_ in (b.get("q") or []) if isinstance(q_, str) and _s(q_)][:3]
                    if not show and not q:
                        continue
                    typ = _s(b.get("type"), 12).lower() or "footage"
                    if typ not in ("footage", "archive", "person", "map", "ai", "explain"):
                        typ = "footage"
                    who = _s(b.get("who"), 60)
                    if typ == "person" and who and not any(who.lower() in q_.lower() for q_ in q):
                        q = [f"{who}"] + q
                    if typ == "archive":
                        q = q + [f"{q[0]} archive footage"] if q else q
                    bs.append({"show": show or (q[0] if q else ""), "q": (q or [show[:40]])[:4], "ai": ai_p,
                               "phrase": _s(b.get("phrase"), 40), "real": bool(b.get("real")) or typ == "person",
                               "type": typ, "place": _s(b.get("place"), 60), "who": who})
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
JUDGE_PROMPT = """You are a very strict B-roll editor of a top Hindi Shorts channel. Topic of the video: {topic}.
For each candidate you get the narration line (Hindi + English), the planned beats (what must be seen) and one frame.
Score 0-10 how well the frame SHOWS what is being said:
 10 = exactly what the line/beat says (right subject, right action, right place/era)
  8 = clearly the right subject and context - a viewer instantly connects it to the words
  6 = right topic, generic but acceptable
  4 = weak: same broad topic but wrong subject/action/place/era
  2 = wrong or misleading (different person/country/thing, different genre than the video)
  0 = unrelated; OR burned-in titles/subtitles/big text/watermark/logo; OR a slide/diagram/whiteboard/screenshot
      of a web page; OR cartoon/clip-art when real footage is needed; OR black, washed-out, blurry or tiny frame
"b" = beat number (1..N) the frame fits best, "why" = 3-8 words.
Return ONLY JSON: {{"r": [{{"c": 1, "s": 7, "b": 1, "why": ".."}}]}}"""


def _row_text(n, row):
    cid, lt, et, bts, im = row
    bl = " | ".join(f"{k + 1}) {b}" for k, b in enumerate(bts)) or "-"
    return f"Candidate {n}: LINE: \"{lt[:220]}\" (English: {et[:200]}) BEATS: {bl[:500]}"


def _parse_judge(data, rows):
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


def _judge_gh(rows):
    """GitHub Models GPT-4.1-mini vision: har candidate ka text + uski photo saath-saath (detail low = sasta)."""
    import base64
    content = [{"type": "text", "text": JUDGE_PROMPT.format(topic=STATE.get("topic") or "see lines")}]
    for n, row in enumerate(rows, 1):
        content.append({"type": "text", "text": _row_text(n, row)})
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/jpeg;base64," + base64.b64encode(_jpg(row[4])).decode(), "detail": "low"}})
    for mdl in ("openai/gpt-4.1-mini", "openai/gpt-4.1"):
        data = _gh_chat(content, mdl, max_tokens=1500, timeout=120)
        res = _parse_judge(data, rows)
        if res:
            return res, "github " + mdl.split("/")[-1]
    return {}, ""


def _judge_gemini(key, rows):
    parts = [JUDGE_PROMPT.format(topic=STATE.get("topic") or "see lines")]
    for n, row in enumerate(rows, 1):
        parts += [_row_text(n, row), {"jpg": _jpg(row[4])}]
    try:
        from ai import _ask_gemini, parse_json        # sirf Gemini (backup Groq 5 photo se zyada nahi le sakta)
        txt = _ask_gemini(key, parts, True, False, 0.1, 150, 3, 240)
        return _parse_judge(parse_json(txt), rows)
    except Exception as e:
        log(f"   (director gemini judge: {str(e)[:90]})", show=False)
        return {}


def _judge_backup(keys, rows):
    """Groq / OpenRouter free vision: 1 request me max 3 photo, photo usi kram me jaise candidates likhe."""
    out = {}
    try:
        import free_ai
        bk = {k: v for k, v in (keys or {}).items() if k in ("GROQ", "OPENROUTER") and v}
        if not bk:
            return out
        for a in range(0, len(rows), 3):
            ch = rows[a:a + 3]
            prompt = JUDGE_PROMPT.format(topic=STATE.get("topic") or "see lines") + \
                "\nThe images are attached in the SAME order as the candidates.\n" + \
                "\n".join(_row_text(n, r) for n, r in enumerate(ch, 1)) + "\nReply with JSON only."
            txt, who = free_ai.ask_vision(bk, prompt, [_jpg(r[4]) for r in ch])
            if txt:
                from ai import parse_json
                out.update(_parse_judge(parse_json(txt), ch))
    except Exception as e:
        log(f"   (director backup judge: {str(e)[:90]})", show=False)
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
            out[cid] = (round(min(s, CLIP_MAX), 1), max(0, best - 1), "clip andaza")
    except Exception as e:
        log(f"   (director clip judge skip: {str(e)[:80]})", show=False)
    return out


def judge(rows, keys, batch=8, threads=2):
    """v5.1 jaanch ki chain: GitHub Models (alag free quota) -> Gemini -> Groq/OpenRouter -> CLIP andaza."""
    key = (keys or {}).get("GEMINI")
    res, who = {}, set()
    if not rows:
        return res
    chunks = [rows[a:a + batch] for a in range(0, len(rows), batch)]
    if _gh_token():
        with ThreadPoolExecutor(max_workers=threads) as ex:
            for r, w in ex.map(_judge_gh, chunks):
                if r:
                    res.update(r); who.add(w)
    miss = [r for r in rows if r[0] not in res]
    if miss and key:
        chunks = [miss[a:a + batch] for a in range(0, len(miss), batch)]
        with ThreadPoolExecutor(max_workers=threads) as ex:
            for r in ex.map(lambda ch: _judge_gemini(key, ch), chunks):
                if r:
                    res.update(r); who.add("gemini")
    miss = [r for r in rows if r[0] not in res]
    if miss:
        r = _judge_backup(keys, miss)
        if r:
            res.update(r); who.add("groq/openrouter")
    miss = [r for r in rows if r[0] not in res]
    if miss:
        r = _clip_judge(miss)
        if r:
            res.update(r); who.add("clip")
    if who:
        old = set(x for x in str(STATE.get("judge") or "").split("+") if x and x != "none")
        STATE["judge"] = "+".join(sorted(old | who))
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
                im = _frame(it, 160)
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
                   style=None, time_budget_s=420, search_fn=None, map_fn=None, spans=None, max_maps=1,
                   explain_fn=None, long_mode=False):
    """found[i] = (items, kw). Har normal line ko verified visual deta hai (item['dir']=True). Jo beat sahi na bhare,
    wo hata diya jaata hai (pichhla shot lamba chalega) – ek hi clip 2 baar NAHI."""
    t0 = time.time()
    user_ai = user_ai or {}
    STATE["judge"] = "none"; STATE["ai_fail"] = 0
    if topic and not STATE.get("topic"):
        STATE["topic"] = _s(topic, 80)
    vertical = H > W
    guard = _Dedup()
    # v5.1: map / news / tweet card -> sirf pehla beat; us line ke baaki beat ke liye asli footage khojo
    cards = {}
    for i in range(len(found)):
        its = list(found[i][0] or [])
        if i in skip_lines or i in face_lines or not its or not STATE["beats"].get(i):
            continue
        if any(str(x.get("src", "")).lower().startswith(CARD_SRC) for x in its) and \
                not any(str(x.get("src", "")).lower().startswith(SKIP_SRC) or x.get("face") for x in its):
            card = next(x for x in its if str(x.get("src", "")).lower().startswith(CARD_SRC))
            cards[i] = dict(card, whole=False, ss=0.0, dir=True, vscore=None, vwhy="card", beat=0)
            found[i] = ([], found[i][1])
    if cards and search_fn is not None:
        def _srch(i):
            try:
                r = search_fn(i)
                return i, list((r[0] if isinstance(r, tuple) else r) or [])
            except Exception:
                return i, []
        with ThreadPoolExecutor(max_workers=3) as ex:
            for i, its in ex.map(_srch, list(cards)):
                its = [x for x in its if not str(x.get("src", "")).lower().startswith(CARD_SRC + SKIP_SRC)
                       and not x.get("whole")]
                found[i] = (its, found[i][1])
        log(f"   🗺 Director: {len(cards)} card-line (map/news/tweet) – card sirf pehle beat pe, baaki asli footage")
    # v5.3: jis line pe koi footage hi nahi (jaise subscribe wali aakhri line) -> uske beats ki khoj
    empties = [i for i in range(len(found)) if i not in cards and i not in skip_lines and i not in face_lines
               and STATE["beats"].get(i) and not (found[i][0] or [])]
    if empties and search_fn is not None:
        def _srch2(i):
            try:
                r = search_fn(i)
                return i, [x for x in list((r[0] if isinstance(r, tuple) else r) or [])
                           if not x.get("whole") and not str(x.get("src", "")).lower().startswith(CARD_SRC + SKIP_SRC)]
            except Exception:
                return i, []
        with ThreadPoolExecutor(max_workers=3) as ex:
            for i, its in ex.map(_srch2, empties):
                found[i] = (its, found[i][1])
    # v5.3: apni LIBRARY (pichhli videos me 8/10+ pass hui clips) se bhi candidates
    try:
        import clip_library as _lib
        _lib.load()
        lib_jobs = []
        for i in range(len(found)):
            if i in skip_lines or i in face_lines or not STATE["beats"].get(i):
                continue
            if any(x.get("face") or x.get("whole") for x in (found[i][0] or [])):
                continue
            texts = [b["show"] for b in STATE["beats"][i]] + [q for b in STATE["beats"][i] for q in (b.get("q") or [])]
            have = {str(x.get("url") or "") for x in (found[i][0] or [])}
            for e in _lib.find(texts, n=3, exclude=have):
                lib_jobs.append((i, e))
        if lib_jobs:
            def _mat(x):
                i, e = x
                return i, _lib.materialize(e)
            with ThreadPoolExecutor(max_workers=4) as ex:
                got = [(i, it) for i, it in ex.map(_mat, lib_jobs) if it]
            for i, it in got:
                found[i] = (list(found[i][0] or []) + [it], found[i][1])
            if got:
                log(f"   📚 Library: pichhli videos ki {len(got)} pass hui clips bhi muqable me")
    except Exception as _le:
        log(f"   (library skip: {str(_le)[:80]})", show=False)
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
                cmap[cid] = (i, dict(it, _ar=round(im.width / max(1, im.height), 3)))
                rows.append((cid, _line_text(sents[i]), _s(eng[i] if i < len(eng) else "", 220), beat_texts(i), im))
    log(f"   🎯 Director: {len(rows)} mili clips/photos AI aankh (GitHub/Gemini) se jaanch raha hoon ({len(lines_todo)} lines)...")
    J = judge(rows, keys)
    # --- a2) Planner ne jahan "map" kaha (aur line sach me jagah ki baat kare) -> asli satellite map (Google Earth jaisa)
    map_items = {}
    if map_fn is not None and max_maps > 0:
        mj = []
        for i in lines_todo:
            if i in cards:
                continue
            if not GEO_RE.search(_line_text(sents[i])):
                continue
            for j, b in enumerate(STATE["beats"].get(i) or []):
                if b.get("type") == "map" and b.get("place"):
                    mj.append((i, j, b["place"])); break
            if len(mj) >= max_maps:
                break
        def _mk(x):
            i, j, place = x
            try:
                k = len(STATE["beats"][i]) or 1
                dur = (float(spans[i][1]) - float(spans[i][0])) if spans else 4.0
                dur = max(2.6, dur * min(1.0, 2.0 / k) + 0.3)          # map ko kam se kam 2 beat ka samay
                out = Path(work) / "shots" / f"dmap_{i:02d}_{j}.mp4"
                out.parent.mkdir(parents=True, exist_ok=True)
                p = map_fn(place, dur, out)
                return (i, j, p, place)
            except Exception as e:
                log(f"   (director map skip: {str(e)[:80]})", show=False)
                return (i, j, None, place)
        with ThreadPoolExecutor(max_workers=2) as ex:
            for i, j, p, place in ex.map(_mk, mj):
                if p and Path(str(p)).exists():
                    map_items[(i, j)] = {"kind": "video", "path": Path(str(p)), "credit": "Satellite imagery (map tiles)",
                                         "src": "map (director)", "ss": 0.0, "dir": True, "vscore": None,
                                         "vwhy": f"map: {place}", "beat": j}
                    log(f"   🛰 line {i + 1}: satellite map – {place}")
    # --- a3) v5.3: "explain" beats -> chalti hui animated diagram video (rule / process / comparison)
    exp_items = {}
    ecap = EXPLAIN_CAP["long" if long_mode else "short"]
    if explain_fn is not None and ecap > 0:
        ej = []
        for i in lines_todo:
            if i in cards:
                continue
            for j, b in enumerate(STATE["beats"].get(i) or []):
                if b.get("type") == "explain" and (i, j) not in map_items:
                    ej.append((i, j)); break
            if len(ej) >= ecap:
                break
        def _ex(x):
            i, j = x
            try:
                k = len(STATE["beats"][i]) or 1
                dur = (float(spans[i][1]) - float(spans[i][0])) if spans else 4.0
                dur = max(3.0, dur * min(1.0, 2.0 / k) + 0.3)
                out = Path(work) / "shots" / f"dexp_{i:02d}_{j}.mp4"
                out.parent.mkdir(parents=True, exist_ok=True)
                b = STATE["beats"][i][j]
                p = explain_fn(f"{b['show']} | line meaning: {(STATE.get('means') or {}).get(i, '')}", _line_text(sents[i]),
                               dur, out)
                return i, j, p
            except Exception as e:
                log(f"   (director explain skip: {str(e)[:80]})", show=False)
                return i, j, None
        with ThreadPoolExecutor(max_workers=2) as ex:
            for i, j, p in ex.map(_ex, ej):
                if p and Path(str(p)).exists():
                    exp_items[(i, j)] = {"kind": "video", "path": Path(str(p)), "credit": "", "src": "explainer (director)",
                                         "ss": 0.0, "dir": True, "vscore": None, "vwhy": "animated explain", "beat": j}
                    log(f"   ✨ line {i + 1}: animated explainer beat ready")
    # --- b) har beat ko sabse achha visual (pehle na laga, video ko thodi preference)
    plan_out, need_ai = {}, []
    for i in lines_todo:
        beats = STATE["beats"][i]
        k = len(beats)
        cands = []
        start_j = 0
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
        skip_j = set()
        if i in cards:
            chosen[0] = cards[i]; start_j = 1
            if str(cards[i].get("src", "")).startswith("map") and k >= 3:
                skip_j.add(1)                        # map ki zoom animation ko 2 beat ka samay
        for (mi, mj_), mit in list(map_items.items()) + list(exp_items.items()):
            if mi == i:
                chosen[mj_] = mit
                if mj_ + 1 < k:
                    skip_j.add(mj_ + 1)
        for j in range(start_j, k):
            if chosen[j] is not None or j in skip_j:
                continue
            best, best_eff = None, -1e9
            for c in cands:
                if c["cid"] in used:
                    continue
                if guard and guard.is_duplicate(c["it"]):
                    continue
                ar = float(c["it"].get("_ar") or 1.0)
                eff = c["s"] + (VIDEO_BONUS if c["it"].get("kind") == "video" else 0.0) + (0.8 if c["b"] == j else 0.0) \
                    + (0.7 if vertical and ar < 0.8 else 0.0) - (0.4 if vertical and ar > 1.9 else 0.0) \
                    + (0.3 if str(c["it"].get("src", "")).startswith("library") else 0.0)
                if eff > best_eff:
                    best, best_eff = c, eff
            if best is not None and (best["s"] >= PASS or (beats[j].get("real") and best["s"] >= 5.0)):
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
        if b.get("real") and _vb is not None and (_vb.PLAN.get(i) or {}).get("person"):
            return (i, j, None, prompt)              # asli insaan ki nakli AI photo kabhi nahi
        p = _ai_image(prompt, work, W, H, keys, topic, seed=i * 31 + j * 7 + 1)
        if p is None:
            STATE["ai_fail"] += 1
        return (i, j, p, prompt)
    gen_res = []
    if need_ai:
        # v5.3: AI kabhi samay ki wajah se chhoot-ta nahi (v5.2 me 7 min ki seema se chupchaap chhoot jaata tha).
        # Limit bachane ke liye max AI_CAP photo – pehle wo beat jinka stock sabse kamzor / bilkul nahi; har line ka
        # pehla beat pehle (line ki shuruaat khaali na lage).
        cap = AI_CAP["long" if long_mode else "short"]
        order = sorted(need_ai, key=lambda x: (x[1] > 0, (x[2]["s"] if x[2] is not None else -1), x[0], x[1]))
        todo_ai = order[:cap]
        if len(need_ai) > cap:
            log(f"   🎨 Director: {len(need_ai)} khaali beat – AI limit bachane ke liye sirf {cap} sabse zaroori pe AI photo")
        log(f"   🎨 Director: {len(todo_ai)} beat ke liye sahi footage nahi mili – unke apne prompt se AI photo...")
        with ThreadPoolExecutor(max_workers=4) as ex:
            gen_res = list(ex.map(_gen, todo_ai))
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
            elif st is not None and st["s"] >= MIN_USE and not (guard and guard.is_duplicate(st["it"])):
                it = dict(st["it"], dir=True, vscore=st["s"] if st.get("judged") else None, vwhy=st["why"], beat=j)
                chosen[j] = it
                if guard: guard.register(it)
            # v5.3: 6 se kam wala stock nahi lagta – beat hat jaata hai (Terms of Service jaisi photo kabhi nahi)
        # v5.1: abhi bhi khaali beat -> HATA do (pichhla sahi shot thoda lamba chalega). Pehle yahan wahi clip
        # dobara lagti thi -> video me ek hi cheez 2-3 baar dikhti thi.
        fin = [c for c in chosen if c is not None]
        if not fin and explain_fn is not None and len(exp_items) < ecap + 1:
            try:                                       # poori line khaali -> animated explainer (galat photo se behtar)
                dur = (float(spans[i][1]) - float(spans[i][0]) + 0.3) if spans else 4.0
                out = Path(work) / "shots" / f"dexp_{i:02d}_all.mp4"
                p = explain_fn(" ; ".join(b["show"] for b in STATE["beats"][i]), _line_text(sents[i]), dur, out)
                if p and Path(str(p)).exists():
                    fin = [{"kind": "video", "path": Path(str(p)), "credit": "", "src": "explainer (director)",
                            "ss": 0.0, "dir": True, "vscore": None, "vwhy": "line khaali – explainer", "beat": 0}]
                    exp_items[(i, 0)] = fin[0]
            except Exception:
                pass
        if fin:
            found[i] = (fin, found[i][1])
        else:
            found[i] = ([], found[i][1])           # kamzor/galat visual nahi; purana system pichhla shot chalayega
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
    try:                                               # v5.3: 8/10+ asli clips library me (agli videos ke liye)
        import clip_library as _lib2
        n_saved = 0
        for i in lines_todo:
            for c in found[i][0] or []:
                if c.get("dir") and (c.get("vscore") or 0) >= 8 and "judged_by_clip" not in str(c.get("vwhy")):
                    bs = STATE["beats"].get(i) or []
                    b = bs[c.get("beat") or 0] if bs and (c.get("beat") or 0) < len(bs) else {}
                    if _lib2.add(c, [b.get("show", "")] + list(b.get("q") or []), c.get("vscore"), STATE.get("topic", "")):
                        n_saved += 1
        _lib2.save()
        if n_saved:
            log(f"   📚 Library: {n_saved} nayi pass hui clips yaad rakhi (kul {_lib2.size()})")
    except Exception as _lse:
        log(f"   (library save skip: {str(_lse)[:80]})", show=False)
    try:
        import cloud_visuals as _cvr
        ai_why = _cvr.last_error_summary()
    except Exception:
        ai_why = ""
    STATE["report"] = {"score": total, "judge": STATE["judge"], "planner": STATE.get("planner"), "ai_fail": STATE["ai_fail"],
                       "ai_why": ai_why if STATE["ai_fail"] else "",
                       "beats": len(sc), "lines": per_line, "weak_lines": weak,
                       "ai_shots": n_ai, "video_shots": n_vid, "special_lines": n - len(lines_todo),
                       "seconds": round(time.time() - t0)}
    if STATE["ai_fail"]:
        try:
            import cloud_visuals as _cvl
            _w = _cvl.last_error_summary()
        except Exception:
            _w = ""
        log(f"   ⚠️ Director: {STATE['ai_fail']} AI photo nahi bani ({_w or 'wajah upar log me'}) – un beats pe agla shot lamba chala")
    log(f"   🎯 Director score: {total if total is not None else '?'}/100 ({STATE['judge']} ne {len(sc)} shot dekhe) – "
        f"{n_vid} asli video, {n_ai} AI photo, kamzor lines: {weak or 'koi nahi'} [{round(time.time() - t0)}s]")
    return STATE["report"]


def report_md(sents=None, found=None):
    """v5.2 VISUAL SCRIPT: har line – tool ne kya samjha, har beat me kya dikhana tha, kya laga, kitne number, kyun.
    Ye file Gemini / kisi editor ko seedhe de sakte ho."""
    r = STATE.get("report") or {}
    out = [f"# Visual Script – {r.get('score', '?')}/100", "",
           f"Topic: {STATE.get('topic') or '-'} | Plan: {STATE.get('planner')} | Jaanch: {r.get('judge', '-')}", ""]
    n = len(sents) if sents else (max(STATE["beats"]) + 1 if STATE["beats"] else 0)
    for i in range(n):
        bs = STATE["beats"].get(i) or []
        line = _line_text(sents[i]) if sents else ""
        out.append(f"## Line {i + 1}" + (f" – {(r.get('lines') or {}).get(i + 1)}/100" if (r.get('lines') or {}).get(i + 1) else ""))
        if line:
            out.append(f"> {line}")
        if (STATE.get("means") or {}).get(i):
            out.append(f"- **Matlab:** {STATE['means'][i]}")
        its = list((found[i][0] if found and i < len(found) else []) or [])
        by_beat = {x.get("beat"): x for x in its if x.get("beat") is not None}
        for j, b in enumerate(bs):
            got = by_beat.get(j)
            tag = b.get("type", "footage") + (f": {b.get('place') or b.get('who')}" if (b.get("place") or b.get("who")) else "")
            line_b = f"- Beat {j + 1}" + (f" (\"{b['phrase']}\" se)" if b.get("phrase") else "") + f" [{tag}] – dikhana: {b['show']}"
            if got:
                sc = got.get("vscore")
                line_b += f"  \n  → laga: {str(got.get('src', ''))[:40]}" + (f" – {sc:.0f}/10" if sc is not None else "") + \
                          (f" ({got.get('vwhy')})" if got.get("vwhy") else "")
            elif str((by_beat.get(j - 1) or {}).get("src", "")).startswith("map"):
                line_b += "  \n  → map ki zoom animation ko yahan tak ka samay diya"
            else:
                line_b += "  \n  → ye beat hata diya (sahi visual nahi mila, pichhla shot lamba chala)"
            out.append(line_b)
        if not bs and its:
            out.append("- (special: " + ", ".join(sorted({str(x.get('src', ''))[:30] for x in its})) + ")")
        out.append("")
    return "\n".join(out)
