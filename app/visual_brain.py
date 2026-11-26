"""v3.66 VISUAL BRAIN – Universal script samajh + category ke hisaab se visual strategy (ADD-ON, kuch hataya nahi).

Kyun bana (audit, 22 Nov 2026 – "visuals script se match nahi kar rahe"):
  1. v3.55 router har line ki PEHLI clip ko AI (Flux) photo se badal deta tha jab CLIP score < 0.30 – jabki CLIP
     ViT-B/32 me SAHI clip ka score bhi aksar 0.22-0.30 hota hai. Nateeja: asli footage (Elon Musk ki asli clip
     bhi) hata ke AI ki nakli photo. Ab ye module tay karta hai ki AI photo kab chal sakti hai (allow_ai_override).
  2. AI aankh (CLIP) ki NEG list "person talking to camera / logo / news lower third / camera on desk" ko kharab
     maanti thi – YouTuber, news, business wali line pe yahi SAHI footage hoti hai -> sahi clip reject. Ab line ki
     category ke hisaab se ye NEG dheele hote hain (neg_relax).
  3. Har line ki category (news / influencer / history / science / tech / business / crime / sports / geography /
     general) + asli insaan / event pehchaan -> exact-pehle search queries (person/event specific).
  4. Har video ki VISUAL_REPORT (.json + .md): line -> samjha kya, search kya kiya, kya chuna, kyun, exact ya
     illustrative ya AI ya fallback, kya reject hua. + Fact warnings (sirf report me – script KABHI nahi badalti).

Offline bhi chalta hai (rules). AI mile (Gemini -> Groq/OpenRouter backup, ai.ask_json se) to behtar samajh.
Koi naya paid API nahi. Keys kabhi log/report me nahi.
"""
import json, re, threading, time
from pathlib import Path

from common import log

CATS = ("news", "influencer", "history", "science", "technology", "business", "crime", "sports", "geography",
        "general")
MODES = {"auto": None, "news": "news", "current_news": "news", "influencer": "influencer", "history": "history",
         "science": "science", "technology": "technology", "tech": "technology", "business": "business",
         "crime": "crime", "mystery": "crime", "sports": "sports", "documentary": None, "general": "general",
         "facts": "general"}

PLAN = {}                      # line -> dict (category, subject, person, event, place, time, queries ...)
SCRIPT = {"category": "general", "mixed": False, "mode": "auto", "how": "rules", "main": ""}
FACTS = {"status": "not_run", "rows": [], "note": ""}
_FACT_THREAD = {"t": None}

# ------------------------------------------------------------------ 1) rules (offline)
_R = {
    "news": r"(हाल ही|ताज़ा|ताजा|आज |कल |बयान|सरकार|मंत्री|प्रधानमंत्री|राष्ट्रपति|चुनाव|संसद|हमला|युद्ध|जंग|मिसाइल|सेना|"
            r"तनाव|सीमा|बॉर्डर|प्रतिबंध|समझौता|ब्रेकिंग|news|breaking|minister|president|election|war|missile|army|"
            r"strike|attack|sanction|treaty|ceasefire|government|parliament|announced)",
    "influencer": r"(यूट्यूबर|youtuber|यूट्यूब चैनल|चैनल|सब्सक्राइबर|subscriber|इंस्टाग्राम|instagram|influencer|"
                  r"इन्फ्लुएंसर|क्रिएटर|creator|vlog|व्लॉग|रील|reels?|फॉलोअर्स|followers|streamer|podcast|पॉडकास्ट)",
    "history": r"(साम्राज्य|सम्राट|राजा|रानी|बादशाह|मुगल|मुग़ल|सल्तनत|किला|युद्ध .*साल पहले|सदी|शताब्दी|प्राचीन|इतिहास|"
               r"वंश|empire|emperor|king|queen|dynasty|mughal|sultan|century|ancient|medieval|battle of|fort|"
               r"civilization|सभ्यता|साल पहले|ईसा पूर्व)",
    "science": r"(वैज्ञानिक|विज्ञान|ग्रह|तारा|आकाशगंगा|ब्रह्मांड|अंतरिक्ष|नासा|इसरो|ब्लैक होल|डीएनए|कोशिका|शरीर|दिमाग|"
               r"समुद्र की गहराई|scientist|science|planet|galaxy|universe|space|nasa|isro|black hole|dna|cell|brain|"
               r"ocean|atom|telescope|asteroid|mars|moon|chandrayaan|चंद्रयान)",
    "technology": r"(एआई|ai\b|आर्टिफिशियल|रोबोट|चिप|स्मार्टफोन|ऐप|सॉफ्टवेयर|इंटरनेट|हैक|साइबर|कंप्यूटर|chatgpt|gpt|"
                  r"robot|chip|smartphone|iphone|app\b|software|internet|computer|processor|gpu|nvidia|openai|google|"
                  r"microsoft|apple|tesla|5g|quantum)",
    "business": r"(कंपनी|स्टार्टअप|अरबपति|करोड़|अरब डॉलर|शेयर|बाज़ार|बाजार|मुनाफा|घाटा|निवेश|फाउंडर|संस्थापक|सीईओ|ब्रांड|"
                r"company|startup|billionaire|crore|billion|shares?|stock market|profit|loss|invest|founder|ceo|brand|"
                r"revenue|valuation|ipo)",
    "crime": r"(हत्या|कत्ल|मर्डर|अपराध|चोरी|डकैती|पुलिस|जांच|जाँच|रहस्य|रहस्यमय|गायब|लापता|केस|सीबीआई|अदालत|कोर्ट|"
             r"murder|crime|theft|robbery|police|investigation|mystery|missing|case|cbi|court|forensic|unsolved|scam|"
             r"घोटाला|धोखा|fraud)",
    "sports": r"(क्रिकेट|फुटबॉल|ओलंपिक|मैच|वर्ल्ड कप|विश्व कप|खिलाड़ी|शतक|विकेट|गोल|टूर्नामेंट|आईपीएल|cricket|football|"
              r"olympics?|match|world cup|player|century|wicket|goal|tournament|ipl|fifa|medal|मेडल|athlete|record)",
    "geography": r"(देश|शहर|नदी|पहाड़|पर्वत|रेगिस्तान|जंगल|द्वीप|ज्वालामुखी|भूकंप|बाढ़|सुनामी|country|city|river|"
                 r"mountain|desert|forest|island|volcano|earthquake|flood|tsunami|glacier|border)",
}
_RC = {k: re.compile(v, re.I) for k, v in _R.items()}
# kis category me "asli insaan / asli event" ki footage sabse zaroori hai (AI nakli photo kabhi nahi)
REAL_FIRST = {"news", "influencer", "business", "sports", "crime"}
# NEG labels (aankh.NEG) jo is category me SAHI footage ho sakte hain -> dheele
# v3.85 FIX: NEVER relax "a person talking to the camera" on business/news/sports/crime —
# warna random YouTubers (webcam talking heads) faceless documentary me ghus jaate hain!
_RELAX = {
    "influencer": {"a person talking to the camera", "camera equipment tripod microphone or filming gear on a desk",
                   "person setting up a video camera indoors", "subtitles or captions at the bottom of the screen"},
    "news": {"news broadcast lower third text banner"},
    "business": {"a logo"},
    "technology": {"a logo"},
    "sports": set(),
    "crime": {"news broadcast lower third text banner"},
}
_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b|\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2}\b")
_YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b|[०-९]{4}")
_NOT_NAMES = {"The", "This", "That", "When", "What", "India", "Indian", "Hindi", "English", "YouTube", "Instagram"}
_PLACE_MULTI = {"south africa", "united states", "united kingdom", "saudi arabia", "sri lanka", "new zealand",
                "north korea", "south korea", "west indies", "middle east", "south america", "north america",
                "united arab emirates", "hong kong", "new york", "new delhi"}
_GENERIC = {"first", "second", "third", "battle", "war", "empire", "kingdom", "dynasty", "world", "cup", "case",
            "telescope", "mission", "company", "group", "the", "of", "in", "on", "and", "great", "new", "old", "army",
            "government", "ministry", "university", "river", "ocean", "sea", "mountain", "temple", "fort", "palace"}
_EVENT_RE = re.compile(r"\b((?:First|Second|Third)\s+)?(Battle|Siege|War|Treaty|Revolution|Mutiny|Massacre)\s+of\s+"
                       r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?|\b[A-Z][A-Za-z]+-\d+\b|\b[A-Z][a-z]+\s+(?:War|Cup|Olympics|"
                       r"Mission|Telescope|Empire)\b")


def _rule_cats(text):
    sc = {k: len(rc.findall(text or "")) for k, rc in _RC.items()}
    return sorted(((v, k) for k, v in sc.items() if v), reverse=True)


def detect(line, eng=""):
    """Ek line ki category (rules). 'general' agar kuch na mile."""
    r = _rule_cats(f"{line} {eng}")
    return r[0][1] if r else "general"


def _names(eng):
    """Offline: English line ke bade naam (insaan/brand jaise). 'First Battle', 'Mughal Empire' jaise NAHI."""
    out = []
    ev = " ".join(m.group(0) for m in _EVENT_RE.finditer(eng or ""))
    for n in _NAME_RE.findall(eng or ""):
        n = n.strip()
        ws = n.split()
        if ws[0] in _NOT_NAMES or n.lower() in _PLACE_MULTI or n in out or n in ev: continue
        if any(w.lower() in _GENERIC for w in ws): continue
        out.append(n)
    return out[:3]


def _event(eng):
    m = _EVENT_RE.search(eng or "")
    return m.group(0).strip() if m else ""


# ------------------------------------------------------------------ 2) AI samajh (ek call, poori script)
def _llm_plan(lines, eng, keys, main=""):
    try:
        import ai
        key = (keys or {}).get("GEMINI") or ""
        if not key and not (ai.BACKUP["keys"].get("GROQ") or ai.BACKUP["keys"].get("OPENROUTER")):
            return None
        rows = "\n".join(f"{k+1}. {l}" + (f"  [EN: {e}]" if e else "") for k, (l, e) in
                         enumerate(zip(lines, list(eng) + [""] * len(lines))))
        prompt = (
            "You are a documentary video researcher for a Hindi YouTube channel that covers ANY topic (news, "
            "influencers, history, science, tech, business, crime, sports, geography, general facts).\n"
            "Read the WHOLE script first, resolve every pronoun to the real person/thing, then for EACH line give the "
            "visual research plan. NEVER invent names, dates or events that the script does not imply. If unsure, "
            "leave the field empty.\n"
            f"Current year is {__import__('datetime').date.today().year}. Never default to 2024 unless the script explicitly says 2024.\n"
            "Per line fields (short):\n"
            " cat: one of news/influencer/history/science/technology/business/crime/sports/geography/general\n"
            " subject: main subject in English\n"
            " person: exact full English name of the REAL person the line is about (as on Wikipedia), else \"\"\n"
            " org: exact real company/organisation/team/country name, else \"\"\n"
            " event: the specific real event (e.g. 'Agni-5 missile test', 'Battle of Panipat 1526'), else \"\"\n"
            " place: location, else \"\"; time: date/year/era if implied, else \"\"\n"
            " action: what is happening\n"
            " real: true if the line describes a REAL specific person/event/company/place (needs REAL footage, "
            "never AI-generated); false for general/abstract statements\n"
            " exact_q: 2-3 search queries (2-6 words) to find REAL footage/photos of exactly this person/event "
            "(for YouTube / Wikimedia / news archives), e.g. 'Elon Musk Starship announcement 2025'. "
            "CRITICAL: ALWAYS anchor EVERY exact_q AND stock_q to the EXACT country/city/person/domain of the line (e.g. 'Pakistan Karachi street protest', 'Asim Munir Pakistan army', 'Chandrayaan 3 Shiv Shakti Point lunar landing site' — NEVER bare 'protest flag', 'tv screen', 'phone in hand', 'statue', 'new year 2025'). If a REAL person is named, put their exact English name in 'person' and lead exact_q with their name!\n"
            " stock_q: 2 short generic stock-video queries that honestly ILLUSTRATE the line without pretending to "
            "be the real event (Pixabay/Pexels), anchored to this story world, never abstract trap words, never cartoon mascots or unrelated flags\n"
            " avoid: 2-3 things that would be WRONG/misleading to show (3d cartoon mascot, devotional deity poster, unrelated flag, wrong person/event/era)\n"
            " emotion: one of neutral/shock/danger/wonder/proud/sad/curiosity\n"
            " must_show: short concrete English phrase of what MUST be visible on screen\n"
            " beats: 1-3 visual beats inside the line if it names 2+ distinct people/places/actions "
            '(each: {"phrase": "exact Hindi/English trigger word from line", "subject": "..", "query": "2-5 word query"})\n'
            " shot: wide/medium/close-up/aerial/archival/map/graphic\n"
            " fallback: best honest fallback if no real footage exists (map / timeline / name card / diagram / "
            "labelled reconstruction)\n"
            'Also top-level: "category" (main category of the whole video), "main" (main subject).\n'
            'Return ONLY JSON: {"category": "..", "main": "..", "lines": [{"cat": "..", "subject": "..", '
            '"person": "..", "org": "..", "event": "..", "place": "..", "time": "..", "action": "..", '
            '"emotion": "..", "must_show": "..", "beats": [{"phrase": "..", "subject": "..", "query": ".."}], '
            '"real": true, "exact_q": [".."], "stock_q": [".."], "avoid": [".."], "shot": "..", "fallback": ".."}]}'
            + (f"\nMain subject hint: {main}" if main else "") + "\n\nSCRIPT:\n" + rows)
        # v4.14 BATCHED LONG-VIDEO AI PLANNER: Split >16-line Long scripts into 14-line batches
        # so LLM response never truncates and falls back to 'samajh: rules'!
        if len(lines) <= 16:
            data = ai.ask_json(key, [prompt], temperature=0.2, timeout=90, budget=150)
            if isinstance(data, list): data = {"lines": data}
            if not isinstance(data, dict) or not isinstance(data.get("lines"), list): return None
            if len(data["lines"]) < max(1, int(len(lines) * 0.8)): return None
            return data
        merged_lines = []
        top_cat = ""
        top_main = main or ""
        chunk_sz = 14
        for off in range(0, len(lines), chunk_sz):
            sub_l = lines[off:off + chunk_sz]
            sub_e = (list(eng) + [""] * len(lines))[off:off + chunk_sz]
            sub_rows = "\n".join(f"{k+1}. {l_}" + (f"  [EN: {e_}]" if e_ else "") for k, (l_, e_) in enumerate(zip(sub_l, sub_e)))
            sub_prompt = prompt.split("\n\nSCRIPT:\n")[0] + (f"\nContext main subject: {top_main}" if top_main else "") + "\n\nSCRIPT:\n" + sub_rows
            cd = ai.ask_json(key, [sub_prompt], temperature=0.2, timeout=75, budget=110)
            if isinstance(cd, list): cd = {"lines": cd}
            # v4.18: Auto-retry once if a Long-video batch returns empty/truncated (fixes Batch-2 'Samjha: -' drop!)
            if not (isinstance(cd, dict) and isinstance(cd.get("lines"), list) and len(cd["lines"]) >= max(1, int(len(sub_l) * 0.6))):
                try:
                    import time as _t_vb
                    _t_vb.sleep(1.2)
                    cd = ai.ask_json(key, [sub_prompt], temperature=0.15, timeout=80, budget=120)
                    if isinstance(cd, list): cd = {"lines": cd}
                except Exception:
                    pass
            if isinstance(cd, dict) and isinstance(cd.get("lines"), list) and len(cd["lines"]) >= max(1, int(len(sub_l) * 0.6)):
                if not top_cat and _s(cd.get("category"), 20): top_cat = _s(cd.get("category"), 20)
                if not top_main and _s(cd.get("main"), 60): top_main = _s(cd.get("main"), 60)
                cl = cd["lines"][:len(sub_l)]
                while len(cl) < len(sub_l):
                    cl.append({})
                merged_lines.extend(cl)
            else:
                merged_lines.extend([{} for _ in sub_l])
        filled = sum(1 for x in merged_lines if isinstance(x, dict) and x)
        if filled < max(1, int(len(lines) * 0.45)):
            return None
        return {"category": top_cat or "general", "main": top_main, "lines": merged_lines}
    except Exception as e:
        log(f"   (visual brain AI skip: {str(e)[:100]})", show=False)
        return None


def _s(v, n=90):
    return str(v or "").strip()[:n]


def _ql(v, n=3):
    return [str(q).strip()[:80] for q in (v or []) if isinstance(q, str) and q.strip()][:n]

_TRAP_STOCK_RE = re.compile(
    r"\b(shocked\s*face|view\s*counter|subscribe\s*(button|icon|screen|animation)|"
    r"thank\s*you\s*for\s*watching|question\s*mark|locked\s*door|calendar\s*dates|"
    r"clock\s*time\s*lapse|analytics\s*graph|new\s*year\s*balloons?|tv\s*screen\s*news?|"
    r"person\s*holding\s*phone|hand\s*holding\s*phone|rock\s*concert|what\s*is\s*the\s*capital)\b",
    re.I,
)


def _clean_stock_q(qs):
    """v4.13: Filter out generic trap stock queries that pull end-screens or random shocked faces."""
    try:
        import visual_quality_gate as _vqg
        if not _vqg.is_enabled():
            return qs
    except Exception:
        pass
    return [q for q in (qs or []) if not _TRAP_STOCK_RE.search(q)]



def build(lines, eng, keys, mode="auto", main="", raw_plan=None, use_ai=True, work=None):
    """Har line ka plan. mode = auto / news / influencer / history / ... (style.txt: content_mode)."""
    PLAN.clear()
    forced = MODES.get(str(mode or "auto").strip().lower().replace(" ", "_"))
    SCRIPT.update(mode=str(mode or "auto"), how="rules", main=main or "")
    data = _llm_plan(lines, eng, keys, main) if use_ai else None
    if data:
        SCRIPT["how"] = "AI"
        if _s(data.get("main")) and not SCRIPT["main"]: SCRIPT["main"] = _s(data.get("main"), 60)
    raw_plan = raw_plan or {}
    for i, l in enumerate(lines):
        e = eng[i] if i < len(eng) else ""
        x = (data["lines"][i] if data and i < len(data["lines"]) and isinstance(data["lines"][i], dict) else {})
        rp = raw_plan.get(i) or {}
        cat = _s(x.get("cat"), 20).lower()
        if cat not in CATS: cat = detect(l, e)
        if forced: cat = forced if cat == "general" or forced != "general" else cat
        names = _names(e)
        who = _s(rp.get("who"), 60)
        wtype = _s(rp.get("who_type"), 12).lower()
        person = _s(x.get("person"), 60) or (who if wtype == "person" else "")
        org = _s(x.get("org"), 60) or (who if wtype == "brand" else "")
        place = _s(x.get("place"), 60) or (who if wtype == "place" else "")
        if not (person or org) and names and not data:
            person = names[0]                               # offline: English line me bada naam
        yr = _YEAR_RE.search(f"{l} {e}")
        _has_pron = bool(re.search(r"(उन्होंने|उसने|उनके|उनका|उनकी|उसका|उसकी|इसी|इसकी|इसमें|यहाँ|इसने|\b(?:he|she|his|her|they|their|it|its|this)\b)", f"{l} {e}", re.I))
        if not (person or org or place) and _has_pron and i > 0 and (i - 1) in PLAN:
            _prev = PLAN[i - 1]
            if _prev.get("person"): person = _prev["person"]
            elif _prev.get("org"): org = _prev["org"]
            elif _prev.get("place"): place = _prev["place"]
        _emo = _s(x.get("emotion"), 20).lower()
        if _emo not in ("neutral", "shock", "danger", "wonder", "proud", "sad", "curiosity"):
            _emo = _detect_emotion(f"{l} {e}")
        _beats = _clean_beats(x.get("beats"), l, e, person, org, place)
        _must = _s(x.get("must_show"), 90) or _s(x.get("subject")) or (person or org or place)
        p = {"line": i + 1, "text": l, "eng": e, "category": cat,
             "subject": _s(x.get("subject")) or _s(rp.get("subject")) or (person or org or place),
             "person": person, "org": org, "event": _s(x.get("event")) or (_event(e) if not x else ""), "place": place,
             "time": _s(x.get("time"), 40) or (yr.group(0) if yr else "") or _s(rp.get("time"), 40),
             "action": _s(x.get("action")) or _s(rp.get("action")),
             "emotion": _emo, "must_show": _must, "beats": _beats,
             "real": bool(x.get("real")) if "real" in x else bool(person or org or (cat in REAL_FIRST and names)
                                                                   or (_event(e) and cat in REAL_FIRST | {"history"})),
             "exact_q": _ql(x.get("exact_q")), "stock_q": _clean_stock_q(_ql(x.get("stock_q"), 2)),
             "avoid": _ql(x.get("avoid")), "shot": _s(x.get("shot"), 20), "fallback": _s(x.get("fallback"), 80),
             "how": "AI" if x else "rules"}
        if not p["exact_q"]:
            p["exact_q"] = _template_queries(p)
        PLAN[i] = p
    cats = [p["category"] for p in PLAN.values()]
    if cats:
        from collections import Counter
        c = Counter(cats).most_common()
        top = _s((data or {}).get("category"), 20).lower()
        non_gen = [(k, v) for k, v in c if k != "general"]
        maj_cat = non_gen[0][0] if (non_gen and non_gen[0][1] >= max(2, int(len(cats) * 0.35))) else c[0][0]
        if forced:
            SCRIPT["category"] = forced
        elif top in CATS and top != "general":
            SCRIPT["category"] = top
        else:
            SCRIPT["category"] = maj_cat
        SCRIPT["mixed"] = len([k for k, v in c if v >= max(2, len(cats) // 5)]) >= 2
    if work:
        try:
            Path(work, "VISUAL_PLAN.json").write_text(json.dumps({"script": SCRIPT, "lines": PLAN}, ensure_ascii=False,
                                                                  indent=2), encoding="utf-8")
        except Exception:
            pass
    n_real = sum(1 for p in PLAN.values() if p["real"])
    log(f"   🧠 visual brain ({SCRIPT['how']}): video = {SCRIPT['category']}"
        + (" (mixed)" if SCRIPT["mixed"] else "") + f", {n_real}/{len(PLAN)} lines asli insaan/event wali")
    return PLAN


def _template_queries(p):
    """AI na ho to category ke hisaab se exact-pehle queries."""
    who = p["person"] or p["org"]
    ev, pl, t, act = p["event"], p["place"], p["time"], p["action"]
    c = p["category"]; q = []
    subj = who or ev or pl
    if not subj:
        return []                                  # bina naam/event ke "official" / "case" jaisi kachra query nahi
    if c == "influencer" and who:
        q = [f"{who} {act}".strip(), f"{who} interview", f"{who} early videos"]
    elif c == "news":
        q = [f"{subj} {t}".strip(), f"{subj} test footage" if re.search(r"-\d", subj) else f"{subj} news"]
    elif c == "history":
        h = ev or subj
        q = [f"{h} painting", f"{h} map", f"{who} portrait" if who and who != h else f"{h} historical"]
    elif c == "business" and p["org"]:
        q = [f"{p['org']} logo", f"{p['org']} headquarters", f"{p['person'] or p['org']} interview"]
    elif c == "business" and who:
        q = [f"{who} interview", f"{who} {act}".strip()[:60], f"{who} portrait"]
    elif c == "sports":
        q = [f"{subj} {t}".strip() + " highlights", f"{subj} {t}".strip()]
    elif c == "crime":
        q = [f"{subj} case", f"{subj} archive footage"]
    elif who:
        q = [f"{who} {act}".strip(), who]
    else:
        q = [f"{subj} {act}".strip()[:60], subj]
    return [re.sub(r"\s+", " ", x).strip() for x in dict.fromkeys(q) if x and len(x.strip()) > 2][:3]



_EMO_RULES = [
    ("danger", r"(खतरनाक|मौत|हमला|युद्ध|बम|जंग|तबाही|विनाश|हत्या|मर्डर|danger|attack|war|death|crash|kill|alert)"),
    ("shock", r"(चौंकाने|हैरान|असंभव|होश उड़|शॉकिंग|रहस्य|गायब|सुलझा नहीं|shocking|unbelievable|mystery|vanished|unsolved)"),
    ("proud", r"(जीत|इतिहास रच|पहला|विश्व रिकॉर्ड|दोहरा शतक|सफलता|महान|victory|first ever|historic|record|champion|triumph)"),
    ("wonder", r"(सबसे ऊँची|अद्भुत|अनोखा|खिलौने|अंतरिक्ष|चाँद|आतिशबाज़ी|tallest|space|moon|fireworks|giant|wonder)"),
    ("sad", r"(दुखद|तबाह|बर्बाद|नुकसान|गरीबी|मौत|tragic|disaster|lost|sad)"),
    ("curiosity", r"(क्या आप जानते|क्यों|कैसे|राज़|सवाल|\?|did you know|why|how|secret)"),
]


def _detect_emotion(text):
    t = text or ""
    for emo, pat in _EMO_RULES:
        if re.search(pat, t, re.I):
            return emo
    return "neutral"


def _clean_beats(raw_beats, hi_line, eng_line, person="", org="", place=""):
    out = []
    for b in (raw_beats or []):
        if not isinstance(b, dict):
            continue
        ph = _s(b.get("phrase"), 50)
        sb = _s(b.get("subject"), 60)
        q = _s(b.get("query"), 80)
        if q or sb:
            out.append({"phrase": ph, "subject": sb or q, "query": q or sb})
        if len(out) >= 3:
            break
    if out:
        return out
    ents = list(_names(eng_line))
    ev_txt = _event(eng_line)
    for m in re.finditer(r"(?<=\s)([A-Z][a-z]{3,}(?:-\d+)?)(?=\b)", eng_line or ""):
        w = m.group(1)
        if w in _NOT_NAMES or w.lower() in _GENERIC or w.lower() in _PLACE_MULTI:
            continue
        if any(w.lower() in e.lower() for e in ents) or (ev_txt and w.lower() in ev_txt.lower()):
            continue
        ents.append(w)
    if ev_txt and len(ents) == 1:
        ents.insert(0, ev_txt)
    if len(ents) >= 2:
        return [{"phrase": e, "subject": e, "query": e} for e in ents[:3]]
    return []


def beats_for(i):
    return list((PLAN.get(i) or {}).get("beats") or [])


def emotion_for(i):
    return (PLAN.get(i) or {}).get("emotion") or "neutral"


def _lat_norm(s):
    try:
        from translit import word as _tw
        s = " ".join(_tw(x) for x in str(s or "").split())
    except Exception:
        s = str(s or "")
    s = s.lower()
    s = re.sub(r"aa+", "a", s); s = re.sub(r"ee+|ii+", "i", s); s = re.sub(r"oo+|uu+", "u", s)
    return re.sub(r"[^a-z0-9]", "", s)


def beat_cut_times(i, sent, st, en, k):
    """v3.84: Align k cuts inside line i to exact Whisper word timestamps (reads w['w'] + cross-script match)."""
    dur = float(en) - float(st)
    if k < 2 or dur < 1.8:
        return None
    beats = beats_for(i)
    words = (sent or {}).get("words") or []
    if len(beats) < 2 or not words:
        return None
    cuts = [float(st)]
    for b in beats[1:k]:
        ph = str(b.get("phrase") or b.get("subject") or "").strip().lower()
        toks = [w for w in re.findall(r"[a-z0-9\u0900-\u097f]{2,}", ph)]
        ltoks = [_lat_norm(t) for t in toks if len(_lat_norm(t)) >= 3]
        hit = None
        for w in words:
            # v3.84 FIX: voice.py/align.py store word text in key "w" (was missing before -> always None!)
            wt = str(w.get("w") or w.get("word") or w.get("text") or "").strip().lower()
            wlat = _lat_norm(wt)
            ws = float(w.get("start") or 0.0)
            if ws <= cuts[-1] + 0.75 or ws >= float(en) - 0.75:
                continue
            if (toks and any(t in wt or wt in t for t in toks if len(t) >= 3)) or (
                ltoks and wlat and any(t in wlat or wlat in t for t in ltoks if len(t) >= 3)
            ):
                hit = ws
                break
        if hit is not None:
            cuts.append(round(hit, 3))
    if len(cuts) == k:
        cuts.append(float(en))
        return cuts
    return None


# ------------------------------------------------------------------ 3) pipeline me lagana
def queries(i):
    """make_video.job(): ye queries USER hint ke baad, heuristics (close up / wide shot) se PEHLE."""
    p = PLAN.get(i)
    if not p: return []
    out = list(p["exact_q"]) if p["real"] else []
    for b in (p.get("beats") or [])[:3]:
        if b.get("query"): out.append(b["query"])
    out += p["stock_q"]
    if not p["real"]:
        out += p["exact_q"][:1]
    return [q for q in dict.fromkeys(out) if q][:6]


def who_for(i):
    """Line asli insaan/brand ke baare me ho aur sources.WHO khaali ho -> naam (Wikidata/Commons/YouTube path)."""
    p = PLAN.get(i) or {}
    if not p.get("real"): return ""
    n = p.get("person") or p.get("org") or ""
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", n)            # "Ajey Nagar (CarryMinati)" -> mashhoor naam
    if m: n = m.group(2).strip() or m.group(1).strip()
    return n[:60]


def avoid(i):
    return tuple((PLAN.get(i) or {}).get("avoid") or ())


def neg_relax(i):
    """aankh.NEG me se kaunse label is line pe 'kharab' NAHI maane jaayenge."""
    p = PLAN.get(i) or {}
    out = set(_RELAX.get(p.get("category", ""), set()))
    if p.get("person"): out |= {"a person talking to the camera"}
    if p.get("org"): out |= {"a logo"}
    return out


def is_real_line(i):
    p = PLAN.get(i) or {}
    return bool(p.get("real") and (p.get("person") or p.get("org") or p.get("event") or p.get("category") in REAL_FIRST))


REAL_SRC = ("youtube", "trailer", "entity", "person:", "brand:", "place:", "photo:", "wikimedia", "nasa", "archive",
            "aapki", "aapka", "chehra", "map", "news card", "film", "my_clips", "pool")


def _is_real_item(it):
    s = str(it.get("src", "")).lower()
    return bool(it.get("hero") or it.get("entity") or it.get("yt") or any(k in s for k in REAL_SRC))


def allow_ai_override(i, it, needs_ai, user_hint, style=None):
    """v3.55 router ki jagah: kya is shot ko AI (Flux) photo se badla ja sakta hai?
    style.txt: ai_override = kam (default) / purana (v3.55 jaisa) / nahi (kabhi nahi, sirf || AI: hint)."""
    mode = str((style or {}).get("ai_override", "kam")).strip().lower()
    if user_hint: return True                                   # aapne khud || AI: likha
    if mode == "nahi": return False
    score = it.get("score")
    if mode == "purana":
        return bool(needs_ai or (score is not None and float(score or 1.0) < 0.30))
    # v3.85 (v3.35 Exact-Scene AI power restored safely): real named PERSON ke chehre par AI kabhi nahi,
    # lekin baaki kisi bhi line par agar stock/YouTube clip kamzor hai (score < 0.24) to exact cinematic AI scene banao!
    p = PLAN.get(i) or {}
    if p.get("person"): return False                            # asli insaan ka chehra -> kabhi AI nahi
    if score is None: return False
    sc = float(score)
    if _is_real_item(it):
        return sc < 0.215                                       # YouTube/Wikimedia bhi bilkul bemel ho to AI scene
    lim = 0.25 if needs_ai else 0.235                           # v3.35 jaisa crisp threshold
    return sc < lim


def allow_ai_fill(i, style=None):
    """Line ki koi footage hi nahi mili -> AI photo bana sakte hain? Asli insaan/event wali line pe NAHI
    (nakli photo misleading) – wahan name card / doc card lagega."""
    if str((style or {}).get("ai_override", "kam")).strip().lower() == "purana": return True
    return not is_real_line(i)


# ------------------------------------------------------------------ 4) fact warnings (sirf report)
def fact_check_async(lines, keys, style=None):
    if str((style or {}).get("fact_check", "haan")).strip().lower() in ("nahi", "no", "0", "off"):
        FACTS.update(status="off"); return
    def run():
        FACTS.update(status="running")
        try:
            import ai
            key = (keys or {}).get("GEMINI") or ""
            numbered = "\n".join(f"{k+1}. {l}" for k, l in enumerate(lines))
            prompt = ("Fact-check this Hindi video script line by line using Google Search. Do NOT rewrite it. Only "
                      "list lines that contain a checkable factual claim (date, number, name, event). For each give "
                      "status: verified / unverified / disputed / incorrect / outdated / opinion, a one-line English "
                      "note (what is wrong or what the reliable figure is) and up to 2 source URLs you actually found. "
                      "If you could not search, say status unverified. Return ONLY JSON: "
                      '{"rows": [{"line": 1, "claim": "..", "status": "..", "note": "..", "sources": [".."]}]}\n\n'
                      + numbered)
            data = None
            if key:
                data = ai.parse_json(ai._ask_gemini(key, [prompt], False, True, 0.1, 90, 2, 120))
            if not data:
                data = ai.ask_json(key, [prompt.replace("using Google Search", "from your knowledge (mark anything "
                                                        "recent as unverified)")], temperature=0.1, budget=90)
                if data: FACTS["note"] = "bina live search (AI ki jaankari se) – recent baatein khud check karo"
            rows = (data or {}).get("rows") if isinstance(data, dict) else None
            if isinstance(rows, list):
                FACTS["rows"] = [{"line": r.get("line"), "claim": _s(r.get("claim"), 160),
                                  "status": _s(r.get("status"), 20).lower(), "note": _s(r.get("note"), 220),
                                  "sources": _ql(r.get("sources"), 2)} for r in rows if isinstance(r, dict)][:40]
                FACTS["status"] = "done"
            else:
                FACTS["status"] = "failed"
        except Exception as e:
            FACTS.update(status="failed", note=str(e)[:120])
    t = threading.Thread(target=run, daemon=True); t.start(); _FACT_THREAD["t"] = t


def fact_wait(sec=60):
    t = _FACT_THREAD.get("t")
    if t is not None: t.join(timeout=sec)


# ------------------------------------------------------------------ 5) report
def classify(it, i):
    s = str(it.get("src", "")).lower()
    if not s and not it.get("path"): return "empty"
    if "cloud flux" in s or "ai photo" in s or "ai scene" in s or "pending_ai" in s: return "AI illustration"
    if any(k in s for k in ("kinetic", "card", "safe fallback", "blender", "remotion", "name card")): return "graphic/fallback"
    if "map" in s: return "map/graphic"
    if "best-rejected" in s: return "weak (best rejected)"
    if any(k in s for k in ("aapki", "aapka", "chehra", "my_clips")): return "your footage"
    if "twitter" in s or "pinterest" in s: return "social clip (X/Pinterest)"
    if _is_real_item(it): return "exact/real source"
    sc = it.get("score")
    if sc is not None and float(sc) >= 0.25: return "illustrative (good match)"
    return "illustrative (stock)"


def write_report(base, sents, plan_shots, line_start, found, pick_trace=None, rejected=None, vrep=None):
    """base = output/<name> (bina .mp4). Returns (json_path, md_path, summary)."""
    shot_line, cur = {}, 0
    for n in range(len(plan_shots)):
        if n in line_start: cur = line_start[n]
        shot_line[n] = cur
    rows = []; cnt = {}
    facts = {}
    for r in FACTS.get("rows") or []:
        try: facts.setdefault(int(r.get("line")) - 1, []).append(r)
        except Exception: pass
    for i, s in enumerate(sents):
        p = PLAN.get(i) or {}
        shots = []
        for n, (a, b, it) in enumerate(plan_shots):
            if shot_line.get(n) != i: continue
            cl = classify(it, i); cnt[cl] = cnt.get(cl, 0) + 1
            shots.append({"t": [round(a, 2), round(b, 2)], "kind": it.get("kind"), "src": str(it.get("src", "")),
                          "class": cl, "score": it.get("score"), "url": it.get("url") or "",
                          "credit": str(it.get("credit", ""))[:160], "entity": it.get("entity") or "",
                          "file": Path(str(it.get("path", ""))).name})
        tr = (pick_trace or {}).get(i) or {}
        rej = [{"src": c.get("src"), "title": c.get("title"), "url": c.get("url"), "score": c.get("score"),
                "why": c.get("reject")} for c in (tr.get("candidates") or []) if c.get("reject")][:8]
        rej += [{"file": Path(str(r_["path"])).name, "score": round(float(r_["score"]), 3), "why": r_["why"]}
                for r_ in ((rejected or {}).get(i) or [])][:8]
        rows.append({
            "line": i + 1, "text": (s.get("script") or s.get("text") or ""),
            "category": p.get("category"), "understood": {k: p.get(k) for k in ("subject", "person", "org", "event",
                                                                              "place", "time", "action", "real")},
            "queries": {"exact": p.get("exact_q"), "stock": p.get("stock_q"), "picker": tr.get("queries")},
            "avoid": p.get("avoid"), "shots": shots, "rejected": rej, "fallback_plan": p.get("fallback"),
            "why_no_video": tr.get("why_no_video") or "", "fact_flags": facts.get(i, [])})
    total = sum(cnt.values()) or 1
    good = sum(v for k, v in cnt.items() if k in ("exact/real source", "your footage", "illustrative (good match)",
                                                    "map/graphic", "social clip (X/Pinterest)"))
    summary = {"category": SCRIPT["category"], "mixed": SCRIPT["mixed"], "planner": SCRIPT["how"],
               "shots": total, "classes": cnt, "real_or_good_pct": round(100.0 * good / total),
               "ai_shots": cnt.get("AI illustration", 0), "fact_status": FACTS.get("status"),
               "fact_flags": sum(1 for r in FACTS.get("rows") or [] if r.get("status") not in ("verified", "opinion")),
               "gate": {k: (vrep or {}).get(k) for k in ("relevance_pct", "failed_lines")} if vrep else None}
    data = {"summary": summary, "script": SCRIPT, "facts_note": FACTS.get("note", ""), "lines": rows}
    jp = Path(str(base) + "_VISUAL_REPORT.json")
    jp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md = [f"# Visual Report", "",
          f"Video category: **{SCRIPT['category']}**" + (" (mixed)" if SCRIPT["mixed"] else "")
          + f" | samajh: {SCRIPT['how']} | shots: {total} | asli/achha match: {summary['real_or_good_pct']}%"
          + f" | AI photo: {summary['ai_shots']}", ""]
    md.append("Shot classes: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1])))
    md.append("")
    for r in rows:
        u = r["understood"]
        md.append(f"## Line {r['line']} [{r['category']}]")
        md.append(r["text"])
        bits = [f"{k}: {u[k]}" for k in ("subject", "person", "org", "event", "place", "time", "action") if u.get(k)]
        md.append("- Samjha: " + ("; ".join(bits) or "-") + (" | ASLI footage chahiye" if u.get("real") else ""))
        if r["queries"]["exact"] or r["queries"]["stock"]:
            md.append("- Search: " + " | ".join((r["queries"]["exact"] or []) + (r["queries"]["stock"] or []))[:300])
        for sh in r["shots"]:
            md.append(f"- Chuna: {sh['class']} – {sh['src']}" + (f" (score {sh['score']:.3f})" if isinstance(sh['score'], (int, float)) else "")
                      + (f" – {sh['url']}" if sh["url"] else ""))
        if r["why_no_video"]: md.append(f"- Video kyun nahi: {r['why_no_video']}")
        for rj in r["rejected"][:3]:
            md.append(f"- Reject: {rj.get('src') or rj.get('file')} – {rj.get('why')}")
        for f in r["fact_flags"]:
            if f.get("status") in ("verified", "opinion"): continue
            md.append(f"- ⚠️ Fact ({f.get('status')}): {f.get('note')}" + (f" [{', '.join(f.get('sources') or [])}]" if f.get("sources") else ""))
        md.append("")
    if FACTS.get("note"): md.append(f"_Fact check note: {FACTS['note']}_")
    mp = Path(str(base) + "_VISUAL_REPORT.md")
    mp.write_text("\n".join(md), encoding="utf-8")
    return jp, mp, summary


def one_line(summary):
    s = summary or {}
    msg = (f"{s.get('category')}{' (mixed)' if s.get('mixed') else ''}: {s.get('shots')} shots, "
           f"asli/achha {s.get('real_or_good_pct')}%, AI photo {s.get('ai_shots')}")
    if s.get("fact_flags"): msg += f", ⚠️ {s['fact_flags']} fact flag"
    return msg
