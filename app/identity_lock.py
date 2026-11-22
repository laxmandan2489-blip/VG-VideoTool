"""v3.2 GLOBAL VISUAL IDENTITY LOCK – poori script padh ke, KOI BHI visual dhoondhne se PEHLE.

Pipeline me jagah: make_video.py step 3 – Gemini ki EK call poori script dekhti hai (sources.gemini_queries,
top-level "lock" + har line ke fields). Ye module us data (ya Gemini na ho to offline niyam) se lock banata hai:

  main_subject / main_type / topic / story / secondary_subjects / allowed_subjects / forbidden_subjects
  consistency = STRICT
  scenes[i]: subject, uses_main, action, context, objects, footage_type, query, gen_prompt, negative, verify

Offline niyam (Gemini busy):
  * mukhya naam = hints/WHO me sabse zyada aane wala naam, ya script ke Latin naam
  * "उनका / उन्होंने / वो / उसका ..." (sarvanaam) wali line = mukhya insaan ki line (pronoun resolution)
  * domain ke hisaab se allowed (gaming -> gaming setup, controller, gameplay ...) aur forbidden (random fire,
    unrelated science/space/animals, different people, abstract animation)
Sab jagah (search, verify, Blender, AI photo, gate) yahi lock maana jaata hai.
"""
import json, re
from collections import Counter
from pathlib import Path

PRONOUN = re.compile(r"(^|\s)(उनका|उनकी|उनके|उन्होंने|उन्हें|उनको|वो|वह|उसका|उसकी|उसके|उसने|उसे|इनका|इनकी|इन्होंने|"
                     r"इसका|इसकी|इसके|इसने|वे|ये)(\s|$|[,।])")
# v3.9 FIX: "random stock footage", "a different person", "unrelated people" HATAYE – har stock clip "stock footage"
# jaisi hi dikhti hai aur har insaan "a different person" – CLIP inhe har jagah zyada deta tha -> sab footage reject
# -> 7/9 line pe sirf text card (15 Nov wali Yash video). "a different person" ab sirf insaan wali line pe (neeche).
GENERIC_FORBIDDEN = ["random abstract animation", "random fire or flames", "glowing eyes", "unrelated science footage",
                     "unrelated space scene", "unrelated animals", "random nature landscape"]
DOMAIN_ALLOWED = {
    "gaming": ["gaming setup", "gamer playing video games", "game controller", "gaming monitor with gameplay",
               "headset and microphone streaming", "esports", "video game gameplay"],
    "youtube": ["YouTube channel page", "video creator recording", "camera and microphone studio",
                "subscriber count", "video editing timeline", "content creator setup"],
    "roast": ["comedy reaction video", "creator talking to camera", "funny reaction"],
    "business": ["office", "company building", "product", "factory", "charts and graphs", "money"],
    "space": ["planet", "stars", "galaxy", "rocket", "astronaut", "telescope"],
    "ocean": ["deep sea", "underwater", "marine animals", "ocean waves"],
    "biology": ["cells under microscope", "human body", "DNA", "laboratory"],
    "history": ["archival photo", "historical building", "old documents", "map"],
    "military": ["soldiers", "army", "military vehicles", "parade", "uniform"],
    "cricket": ["cricket match", "stadium", "batsman", "cricket ball"],
    "film": ["film set", "movie scene", "red carpet", "cinema", "film camera on movie set", "film crew behind the scenes",
             "green screen studio", "video editing visual effects", "clapperboard"],
}
DOMAIN_WORDS = {
    "gaming": "गेमिंग गेम गेमर gaming game gamer gameplay pubg minecraft counter strike esports स्ट्रीम",
    "youtube": "यूट्यूब यूट्यूबर चैनल वीडियो सब्सक्राइबर youtube youtuber channel video subscriber",
    "roast": "रोस्टिंग रोस्ट रोस्टर मजाक roast roasting comedy",
    "business": "बिजनेस कंपनी करोड़ पैसा business company startup brand",
    "space": "अंतरिक्ष ग्रह तारे नासा space planet nasa galaxy",
    "ocean": "समुद्र महासागर ocean sea underwater",
    "biology": "कोशिका शरीर डीएनए cell body dna",
    "history": "इतिहास साल राजा युद्ध history war king",
    "military": "सैनिक सेना फौज soldier army military",
    "cricket": "क्रिकेट मैच cricket match",
    "film": "फिल्म बॉलीवुड मूवी सीन शूट एक्टर वीएफएक्स कैमरा film movie bollywood scene shoot actor vfx camera",
}
FOOTAGE_TYPES = ("real_subject_clip", "subject_photo", "stock", "map", "3d", "graphic")


def _domains(text):
    t = text.lower()
    return [d for d, w in DOMAIN_WORDS.items() if any(x.lower() in t for x in w.split())]


NAME_STOP = set("""But And In Just The You Your Follow This That These Those It Its He She They We I So Or If When
What Why How Who Do Did Does Is Are Was Were Be Not No Yes Imagine Also Then There Here Now Today One Two Ten Many
Lord Shri Sri VFX CGI AI TV HD Hindi India Indian YouTube Shorts""".split())


def _eng_names(eng):
    """English anuvaad se naam: bade akshar wale shabd jo vakya ke shuru me na hon (Yash, Ravana) – Counter."""
    c = Counter(); first = {}
    for k, e in enumerate(eng or []):
        toks = re.findall(r"[A-Za-z][A-Za-z']+", e or "")
        for j, t in enumerate(toks):
            t = re.sub(r"'s$", "", t)
            if not t[:1].isupper() or t in NAME_STOP or len(t) < 3: continue   # vakya ka pehla shabd bhi (Yash was ...)
            t = re.sub(r"(as|s)$", "a", t) if t.lower().endswith("anas") else t     # Ravanas -> Ravana
            c[t] += 1; first.setdefault(t, k * 100 + j)
    return c, first


def _main_from(hints, who, lines, eng=None):
    c = Counter()
    for v in (who or {}).values():
        if v: c[v] += 2
    for h in hints or []:
        for nm in re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b|\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b|\b[A-Z]{3,}\b", h or ""):
            c[nm] += 1
    for l in lines:
        for nm in re.findall(r"\b[A-Z][A-Za-z]{2,}\b", l):
            c[nm] += 1
    ec, first = _eng_names(eng)
    if ec:                                              # v3.9: Gemini na ho to bhi 'Yash' pakdo (anuvaad se)
        top = max(ec.values())
        best = sorted([n for n, v in ec.items() if v >= max(2, top - 1)], key=lambda n: first[n])
        if best: c[best[0]] += ec[best[0]] + 1
    if not c: return None
    nm, n = c.most_common(1)[0]
    return nm if n >= 2 else None


def build(lines, eng=None, hints=None, who=None, raw=None, scenes=None, work=None):
    """raw = Gemini ka poora JSON (sources.GEMINI_RAW) ya None. Return validated lock dict."""
    eng = eng or [""] * len(lines); hints = hints or [""] * len(lines)
    raw = raw if isinstance(raw, dict) else {}
    g = raw.get("lock") if isinstance(raw.get("lock"), dict) else {}
    per = raw.get("lines") if isinstance(raw.get("lines"), list) else []
    main = (g.get("main_subject") or "").strip() or _main_from(hints, who, lines, eng)
    mtype = (g.get("main_type") or ("person" if main and (who or {}) and main in (who or {}).values() else
                                     ("topic" if not main else "person"))).lower()
    alltxt = " ".join(lines) + " " + " ".join(eng) + " " + " ".join(hints)
    doms = _domains(alltxt)
    allowed = [a for a in (g.get("allowed_subjects") or []) if isinstance(a, str) and a.strip()]
    if main: allowed = [main, f"{main} content"] + allowed
    for d in doms:
        allowed += DOMAIN_ALLOWED.get(d, [])
    forbidden = [f for f in (g.get("forbidden_subjects") or []) if isinstance(f, str) and f.strip()]
    for f in GENERIC_FORBIDDEN:                        # domain ke khilaaf na ho tab hi
        if ("space" in f and "space" in doms) or ("science" in f and ("biology" in doms or "space" in doms)) \
                or ("animals" in f and "ocean" in doms) or ("people" in f and mtype != "person"):
            continue
        forbidden.append(f)
    if mtype in ("person",) and main:
        forbidden.append("a different person")         # v3.9: sirf jab video kisi insaan pe ho
    if not g:                                          # v3.9 offline: doosre naam bhi (Ravana) – shot list / rivals ke liye
        ec, first = _eng_names(eng)
        sec_off = [n for n, v in sorted(ec.items(), key=lambda x: (-x[1], first[x[0]])) if n != main and v >= 1][:5]
    else:
        sec_off = []
    lock = {
        "version": "3.9",
        "main_subject": main or "",
        "main_type": mtype if mtype in ("person", "brand", "place", "topic", "thing") else "topic",
        "topic": (g.get("topic") or (f"{main} {' '.join(doms[:2])}".strip() if main else " ".join(doms[:2]))
                  or (eng[0] if eng else "")).strip(),
        "story": (g.get("story") or "").strip()[:500],
        "secondary_subjects": ([s for s in (g.get("secondary_subjects") or []) if isinstance(s, str)] or sec_off)[:10],
        "domains": doms,
        "allowed_subjects": list(dict.fromkeys(allowed))[:24],
        "forbidden_subjects": list(dict.fromkeys(forbidden))[:16],
        "visual_consistency": "STRICT", "subject_consistency": "STRICT" if main else "TOPIC",
        "topic_consistency": "STRICT",
        "source": "gemini+rules" if g else "offline-rules",
        "scenes": [],
    }
    n = len(lines)
    for i, hi in enumerate(lines):
        L = per[i] if i < len(per) and isinstance(per[i], dict) else {}
        sc = (scenes[i] if scenes and i < len(scenes) else {}) or {}
        show = (L.get("show") or "").strip() or kw_show(eng[i] if i < len(eng) else "", main)   # v3.9: chhota (pura vakya nahi)
        uses = L.get("uses_main")
        if uses is None:                               # offline: naam ya sarvanaam = mukhya insaan
            mn = (main or "").lower().replace(" ", "")
            uses = bool(main) and (mn in (show + hints[i]).lower().replace(" ", "") or bool(PRONOUN.search(" " + hi))
                                   or (who or {}).get(i) == main or lock["main_type"] == "person" and i == 0)
        is_cta = bool(re.search(r"(फॉलो|फोलो|सब्सक्राइब|subscribe|follow|लाइक कर|कमेंट कर|शेयर कर)", hi.lower())) \
            and i == n - 1                              # "कमेंट्री" CTA nahi
        action = (L.get("action") or sc.get("action") or "").strip()
        ctxt = (L.get("context") or L.get("environment") or sc.get("environment") or "").strip()
        subj = (main if uses and main else (L.get("subject") or sc.get("subject") or show)).strip()
        if len(subj.split()) > 5:                      # v3.13 FIX: offline scene plan poora vakya subject bana deta tha
            subj = kw_show(subj, main) or show         # ("But do you know, shooting this scene ..." -> "shooting scene film")
        ftype = L.get("footage_type") if L.get("footage_type") in FOOTAGE_TYPES else (
            "real_subject_clip" if uses and lock["main_type"] in ("person", "brand") else "stock")
        q = (L.get("query") or "").strip()
        if not q:
            q = (f"{main} {show}" if uses and main and main.lower() not in show.lower() else show)[:90]
        prev_ = lines[i - 1] if i else ""; next_ = lines[i + 1] if i + 1 < n else ""
        verify = (f"must show {subj}" + (f" {action}" if action else "") +
                  (f" in {ctxt}" if ctxt else "") + f"; must fit topic '{lock['topic']}'")
        lock["scenes"].append({
            "i": i, "narration": hi, "subject": subj, "uses_main": bool(uses), "cta": is_cta,
            "action": action, "context": ctxt, "objects": [o for o in (L.get("objects") or []) if isinstance(o, str)][:6],
            "footage_type": ftype, "query": q, "show": show,
            "gen_prompt": (f"{show}, consistent with the story: {lock['story'][:160]}" if lock["story"] else show)[:300],
            "negative": ", ".join(lock["forbidden_subjects"][:8]),
            "verify": verify, "prev": prev_[:120], "next": next_[:120],
        })
    if work:
        try:
            Path(work, "identity_lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return lock


def allows_template(lock, tpl, scene):
    """Blender template is lock me chalega? Person/brand video me sirf topic se jude templates (gaming -> technology,
    number -> infographic); mystery/energy/abstract/space jaisa 'sundar par bematlab' scene NAHI."""
    if not tpl: return False
    if lock.get("main_type") not in ("person", "brand"):
        return tpl != "abstract"
    ok = {"infographic"}
    if any(d in lock.get("domains", []) for d in ("gaming", "youtube")): ok.add("technology")
    if "space" in lock.get("domains", []): ok |= {"space", "planet", "solar_system"}
    if "history" in lock.get("domains", []): ok.add("history")
    return tpl in ok


def summary(lock):
    return (f"main={lock['main_subject'] or '-'} ({lock['main_type']}), topic={lock['topic']}, "
            f"allowed={len(lock['allowed_subjects'])}, forbidden={len(lock['forbidden_subjects'])}, "
            f"main-lines={sum(1 for s in lock['scenes'] if s['uses_main'])}/{len(lock['scenes'])} [{lock['source']}]")


# ------------------------------------------------------------------ v3.8: har line ka SHOT LIST + "doosre kirdaar"
def _names_in(lock):
    """Script ke kirdaar / mukhya cheezein (English): main + secondary + chhote scene-subject (naam jaise)."""
    out = []
    for x in [lock.get("main_subject")] + list(lock.get("secondary_subjects") or []) + \
             [sc.get("subject") for sc in lock.get("scenes") or []]:
        x = (x or "").strip()
        proper = all(w[:1].isupper() or w[:1].isdigit() for w in x.split() if len(w) > 2)   # naam (Lord Rama), 'film crew' nahi
        if x and proper and len(x.split()) <= 4 and not re.search(r"[ऀ-ॿ]", x) and x.lower() not in [o.lower() for o in out]:
            out.append(x)
    return out[:12]


def _mentions(name, text):
    t = " " + re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()) + " "
    toks = [w for w in re.sub(r"[^a-z0-9 ]", " ", name.lower()).split() if len(w) > 2 and w not in
            ("lord", "the", "king", "god", "shri", "sri", "and", "with", "film", "movie")]
    return bool(toks) and any(f" {w} " in t or f" {w}s " in t for w in toks)


def shot_plan(lock, eng=None):
    """Return [{subject, verify, rivals, queries}] har line ke liye.
    * subject  : is line me kaun / kya dikhna chahiye (Ram wali line -> Ram)
    * rivals   : script ke DOOSRE kirdaar jo is line me NAHI hain (Ram ki line pe 'Ravana') – inka visual reject
    * queries  : 3-4 alag shot (action, close-up, jagah/wide) – ek hi search ki jagah"""
    eng = eng or []
    names = _names_in(lock or {})
    plan = []
    for i, sc in enumerate((lock or {}).get("scenes") or []):
        subj = (sc.get("subject") or "").strip()
        if re.search(r"[ऀ-ॿ]", subj): subj = ""
        text = " ".join([subj, sc.get("show") or "", sc.get("action") or "", eng[i] if i < len(eng) else ""])
        mainn = ((lock or {}).get("main_subject") or "").strip().lower()
        # v3.13 FIX (Yash video): mukhya insaan rival SIRF tab jab line ka subject koi DOOSRA naam wala kirdaar ho
        # (Ram ki line pe Yash nahi). Aam line ("shooting this scene") pe Yash rival nahi – pehle tha -> Yash ki
        # har clip reject.
        subj_named = bool(subj) and subj.lower() in [x.lower() for x in names] and subj.lower() != mainn
        rivals = [n for n in names if n.lower() != subj.lower() and (subj_named or n.lower() != mainn)
                  and not _mentions(n, text)
                  and not (subj and _mentions(subj, n))][:3]
        act = (sc.get("action") or "").strip(); ctx = (sc.get("context") or "").strip()
        objs = [o for o in (sc.get("objects") or []) if isinstance(o, str)]
        qs = [sc.get("query") or ""]
        if subj and act: qs.append(f"{subj} {act}")
        # v3.80: Never generate generic "X close up" / "context wide shot" junk — always anchor to concrete subject
        if subj and ctx and ctx.lower() not in subj.lower() and len(ctx.split()) <= 4:
            qs.append(f"{subj} {ctx}")
        elif subj and objs and objs[0].lower() not in subj.lower():
            qs.append(f"{subj} {objs[0]}")
        qs = [q[:90] for q in dict.fromkeys(q.strip() for q in qs) if q]
        plan.append({"subject": subj, "verify": (f"{subj} {act}".strip() or sc.get("show") or "")[:120],
                     "rivals": rivals, "queries": qs[:4]})
    return plan



# ------------------------------------------------------------------ v3.9: Gemini na ho to bhi CHHOTI search line
KW_STOP = set("""a an the of to in on at and or but with for is are was were be been being have has had do does did you your
we they he she it its this that these those there here what why how who which when where just only also very so such
must would could should can will may might one same each other another more most all any some every than then into from
by as like about over under after before again really actually know imagine think see seen look looks appear appears
appeared shown show shows showing used use using make made makers difficult important essential exactly real alive
together different repeatedly behind hidden screen words other follow facts cinematic surprised entire tasks task
including whole many multiple well even still let us our me my his her their them him importantly keep help
combined interacting positions shot shots""".split())


def kw_show(eng_line, main=""):
    """'You must have been surprised to see Yash's ten heads like Ravana.' -> 'Yash ten heads Ravana'
    (CLIP aur stock search dono chhoti line pe hi theek chalte hain)."""
    toks = re.findall(r"[A-Za-z][A-Za-z'-]+|\d+", eng_line or "")
    out = []
    for t in toks:
        t2 = re.sub(r"'s$", "", t)
        if t2.lower() in KW_STOP or len(t2) < 3 and not t2.isdigit(): continue
        if t2.lower() not in [o.lower() for o in out]: out.append(t2)
    return " ".join(out[:6])
