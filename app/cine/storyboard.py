"""CREATIVE DIRECTOR + STORYBOARD

Render se PEHLE poori script padh ke har line ka faisla:
  role        : hook / context / explain / turn / reveal / end   (kahani me line ka kaam)
  kw / kw2    : screen pe aane wala EK keyword (+ naam ke saath chhoti line)  – reference jaisa
  kind        : word / number / name / place / none
  anim        : typewriter / blur / track / count / name / spring / pop / glitch
  graphic     : map (asli jagah) / stat (number card) / None (footage)
  transition  : is line ke shuru me kaun sa transition (ya seedha cut)
  sfx         : whoosh / riser / None

Gemini (ya Groq/OpenRouter backup) ho to woh keyword chunta hai; na ho to offline niyam (number, naam, jagah,
zor wale shabd). Dono ka result JSON + Hindi report me save hota hai.
"""
import json, re
from pathlib import Path

from . import places

TURN = re.compile(r"(लेकिन|पर असली|असल में|असलियत|मगर|फिर भी|हैरानी|हैरान|चौंक|सोचो|इमैजिन|कल्पना)")
REVEAL = re.compile(r"(असली वजह|सच|राज़|रहस्य|जवाब|पता चला|खुलासा|यही वजह|इसी वजह|नतीजा|अब)")
ORDINAL = re.compile(r"(पहला|पहली|दूसरा|दूसरी|तीसरा|तीसरी|चौथा|चौथी|पांचवा|आखिरी)")
END = re.compile(r"(फॉलो|फोलो|सब्सक्राइब|subscribe|follow|कमेंट|शेयर|लाइक)", re.I)

STRONG = {   # Hindi shabd -> screen keyword
    "जहर": "POISON", "ज़हर": "POISON", "जहरीला": "TOXIC", "जहरीली": "TOXIC", "खतरनाक": "DANGER", "खतरा": "DANGER",
    "मौत": "DEATH", "रहस्य": "MYSTERY", "राज़": "SECRET", "राज": "SECRET", "रिकॉर्ड": "RECORD", "दुनिया": "WORLD",
    "सबसे बड़ा": "BIGGEST", "सबसे बड़ी": "BIGGEST", "सबसे छोटा": "SMALLEST", "सबसे तेज": "FASTEST",
    "सबसे गहरा": "DEEPEST", "सबसे ऊंचा": "TALLEST", "सबसे पुराना": "OLDEST", "सबसे महंगा": "COSTLIEST",
    "चौंकाने": "SHOCKING", "हैरान": "SHOCKING", "बैन": "BANNED", "प्रतिबंध": "BANNED", "गैरकानूनी": "ILLEGAL",
    "रिजेक्ट": "REJECT", "बर्बाद": "WASTE", "कचरा": "WASTE", "करोड़": "CRORE", "आग": "FIRE",  # v4.14: removed bare अरब->BILLION (triggered on अरब दुनिया / सऊदी अरब)
    "बिजली": "ELECTRICITY", "ऑक्सीजन": "OXYGEN", "दिमाग": "BRAIN", "दिल": "HEART", "खून": "BLOOD", "पानी": "WATER",
    "रद्द": "CANCELLED", "अवैध": "INVALID", "गिरफ्तार": "ARRESTED", "इस्तीफा": "RESIGNED", "इस्तीफ़ा": "RESIGNED",
    "दोषी": "GUILTY", "नकली": "FAKE", "इमरजेंसी": "EMERGENCY", "आपातकाल": "EMERGENCY",
    "सोना": "GOLD", "हीरा": "DIAMOND", "भूकंप": "EARTHQUAKE", "ज्वालामुखी": "VOLCANO", "ब्लैक होल": "BLACK HOLE",
}
WEAK = ("दुनिया", "पानी", "दिल", "सोना", "आग", "बिजली")      # aakhri pasand
UNIT_HI = {"प्रतिशत": "%", "परसेंट": "%", "हजार": "THOUSAND", "हज़ार": "THOUSAND", "लाख": "LAKH", "करोड़": "CRORE",
           "करोड": "CRORE", "अरब": "BILLION", "साल": "YEARS", "सालों": "YEARS", "किलो": "KG", "किलोमीटर": "KM",
           "मीटर": "METRES", "फीट": "FEET", "डिग्री": "°C", "गुना": "X", "रुपये": "₹", "रुपए": "₹", "दिन": "DAYS",
           "घंटे": "HOURS", "मिनट": "MINUTES", "सेकंड": "SECONDS", "टन": "TONNES", "प्रजाति": "SPECIES", "लोग": "PEOPLE",
           "लोगों": "PEOPLE", "मिलियन": "MILLION", "बिलियन": "BILLION"}
HI_NUM = {"एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
          "बीस": 20, "पचास": 50, "सौ": 100}

TRANS = {   # role -> transitions ki pasand (ek ke baad wahi dobara nahi)
    "context": ["smoothleft", "slideleft"],
    "explain": ["hblur", "smoothup", "slideup"],
    "turn": ["zoomin", "smoothleft"],
    "reveal": ["circleopen", "fadewhite", "zoomin"],
    "end": ["fadeblack", "hblur"],
    "section": ["smoothleft", "smoothright", "zoomin"],
}
NOT_LATIN = re.compile(r"[\u0900-\u097F]")


def _num_kw(txt):
    """'30-35 प्रतिशत' -> '30-35%', '2.5 लाख' -> '2.5 LAKH', '1000 साल' -> '1000 YEARS'."""
    t = txt.replace("–", "-")
    m = re.search(r"(\d[\d,]*(?:\.\d+)?(?:\s*(?:-|से|to)\s*\d[\d,]*(?:\.\d+)?)?)\s*(%|[\u0900-\u097F]+)?", t)
    if not m:
        for w, v in HI_NUM.items():
            mm = re.search(r"(?:^|\s)" + w + r"\s+([\u0900-\u097F]+)", t)
            if mm and UNIT_HI.get(mm.group(1)) and v >= 2:
                return f"{v} {UNIT_HI[mm.group(1)]}".replace(" %", "%")
        return None
    n = re.sub(r"\s*(से|to)\s*", "-", m.group(1)).replace(" ", "").strip(",")   # v3.18: 'वॉयेजर 1,' -> '1' (nahi '1,')
    unit = m.group(2) or ""
    rest = t[m.end():].split()
    if not unit and rest: unit = rest[0]
    u = UNIT_HI.get(unit, "%" if unit == "%" else "")
    if u in ("LAKH", "CRORE", "THOUSAND", "MILLION", "BILLION") and len(rest) > 1 and UNIT_HI.get(rest[1]):
        u2 = UNIT_HI[rest[1]]
        if u2 not in ("%",): u = f"{u} {u2}" if len(u + u2) < 13 else u
    if u == "%": return f"{n}%"
    if u == "₹": return f"₹{n}"
    if u == "X": return f"{n}X"
    if u == "°C": return f"{n}°C"
    if len(n) > 9: return None
    return f"{n} {u}".strip() if u else (n if len(n) >= 2 else None)


def _heuristic_kw(hi, en, who):
    hi = hi or ""; en = en or ""
    # v3.34: prioritize dramatic named operations (e.g. Operation Meghdoot) over generic words
    _mop = re.search(r"(?:ऑपरेशन|operation)\s+([\u0900-\u097FA-Za-z0-9\-]+)", hi, re.I)
    if _mop:
        try:
            from translit import word as _tw
            _opn = _tw(_mop.group(1)).upper()
        except Exception:
            _opn = _mop.group(1).upper()
        return f"OPERATION {_opn}", "word", "pop" 
    nk = _num_kw(hi)
    if nk: return nk, "", "number"
    for nm in who or []:
        if nm and len(nm) <= 24 and not NOT_LATIN.search(nm):
            parts = nm.split()
            if len(parts) >= 2 and all(p[:1].isupper() for p in parts[:2]):
                return parts[0].upper(), " ".join(parts[1:]).upper(), "name"
            return nm.upper(), "", "word"
    order = [w for w in STRONG if " " in w] + [w for w in STRONG if " " not in w and w not in WEAK] + list(WEAK)
    toks = set(re.findall(r"[\u0900-\u097F]+", hi))
    for w in order:                                   # poora shabd mile (राज़ != राजस्थान)
        if (" " in w and w in hi) or w in toks:
            # v3.18 FIX ("ये जहरीला नहीं है" pe "TOXIC"): shabd ke turant baad 'नहीं/न' ho to ulta matlab – mat lagao
            if re.search(re.escape(w) + r"\s+(?:\S+\s+)?(नहीं|न|नही)(?![\u0900-\u097F])", hi): continue
            return STRONG[w], "", "word"
    return None, "", "none"


def _llm_plan(lines, eng, keys):
    import ai
    numbered = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
    prompt = ("You are the creative director and motion designer of a premium Hindi science/fact YouTube Short. "
              "Read the WHOLE script, understand the story arc, then for EACH numbered line decide the on-screen "
              "kinetic typography like a premium documentary/reel editor: ONE short punchy keyword that the narrator "
              "actually says in that line (or its exact English meaning), never a summary.\n"
              "Rules: kw = English UPPERCASE, 1-2 words, max 14 characters (numbers exactly as spoken, e.g. 30-35%, "
              "2.5 LAKH, 1000 YEARS). Use type=none for about 40% of lines (calm explanation lines) – text on every "
              "line is amateur. type=name only for a real person's name (kw=first name, kw2=surname). type=place "
              "only if a real city/state/country is mentioned (put it in place, e.g. 'Jaipur, Rajasthan'). "
              "role: hook (line 1), context, explain, turn (but/surprise), reveal (the payoff), end (CTA/last).\n"
              'Return ONLY JSON: {"lines":[{"kw":"","kw2":"","type":"word|number|name|place|none","place":"",'
              '"role":"hook|context|explain|turn|reveal|end"}]} with exactly ' + str(len(lines)) + " items.\n\n"
              "SCRIPT:\n" + numbered)
    d = None; by = ""
    if keys.get("GEMINI"):
        d = ai.ask_json(keys["GEMINI"], [prompt], temperature=0.4, budget=90); by = "Gemini"
    if not (isinstance(d, dict) and len(d.get("lines") or []) == len(lines)):
        try:
            import free_ai
            if free_ai.available(keys):
                txt, by2 = free_ai.ask_text(keys, prompt, max_tokens=min(4000, 90 * len(lines) + 300))
                d = free_ai.parse_json(txt); by = by2 or "Groq"
        except Exception:
            d = None
    if isinstance(d, dict) and len(d.get("lines") or []) == len(lines):
        return d["lines"], by
    return None, ""


def _clean_kw(k):
    k = re.sub(r"[\"'“”{}\\\[\]]", "", str(k or "")).strip().upper()
    return k[:16]


DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
SINGULAR = {"DAYS": "DAY", "YEARS": "YEAR", "HOURS": "HOUR", "MINUTES": "MINUTE", "SECONDS": "SECOND",
            "PEOPLE": "PERSON", "METRES": "METRE", "TONNES": "TONNE"}


def _fix_one(kw):
    """v3.18: '1 DAYS' -> '1 DAY'."""
    m = re.match(r"^1\s+([A-Z]+)$", kw or "")
    return f"1 {SINGULAR[m.group(1)]}" if m and m.group(1) in SINGULAR else kw


def _kw_ok(kw, typ, hi, en, who=None):
    """v3.18 FIX (17 Nov videos: '24 घंटे' pe '20 HOURS', '18 November' se pehle '15', 'Sabse dilchasp baat' pe
    'SAND BOA'): AI ka keyword tabhi lage jab wo ISI line me sach me bola gaya ho.
    number -> uske saare ank line me hon; word/name/place -> uske shabd line ke English / Hindi / naam me hon."""
    hi_ = (hi or "").translate(DEV_DIGITS); en_ = (en or "").lower()
    nums = re.findall(r"\d+(?:\.\d+)?", kw.replace(",", ""))
    if nums or typ == "number":
        # v3.34: skip generic filler phrases like "24 HOURS"
        if kw.strip().upper() in ("24 HOURS", "24 GHANTE", "1 DAY", "1 YEAR"):
            return False
        have = set(re.findall(r"\d+(?:\.\d+)?", (hi_ + " " + en_).replace(",", "")))
        if not nums or any(n not in have for n in nums): return False
        if len(nums) == 1 and len(nums[0]) == 1 and not re.search(r"[A-Z%₹]", kw): return False   # akela '1' / '0'
        return True
    # v3.34 STRICT SPOKEN CHECK: do NOT allow unmentioned entity aliases (e.g. "HAL Cheetah") from who/en
    # unless the word is actually spoken in the Hindi script line!
    hay = hi_.lower()
    try:
        from translit import word as _tw
        hay += " " + " ".join(_tw(w).lower() for w in re.findall(r"[\u0900-\u097F]+", hi or ""))
    except Exception:
        pass
    hay += " " + " ".join(v.lower() for k_, v in STRONG.items() if k_ in (hi or ""))
    ws = [w for w in re.findall(r"[a-z]{3,}", kw.lower())]
    if not ws: return False
    return sum(1 for w in ws if w in hay or w.rstrip("s") in hay) * 2 >= len(ws) + (1 if len(ws) > 1 else 0)


def build(lines, eng, keys=None, style=None, who=None, kinds=None, fx_tags=None, use_llm=True, work=None):
    """lines: Hindi script lines, eng: English (ya plan 'show'), who: {i: [names]}, fx_tags: {i: [(name,val)]}.
    Returns list of scene dicts."""
    style = style or {}; keys = keys or {}; who = who or {}; kinds = kinds or {}; fx_tags = fx_tags or {}
    n = len(lines)
    llm, by = (_llm_plan(lines, eng, keys) if use_llm and (keys.get("GEMINI") or keys.get("GROQ") or keys.get("OPENROUTER"))
               else (None, ""))
    map_max = int(float(style.get("auto_map", "2") or 2))
    stat_max = int(float(style.get("stat_card_max", "2") or 2))
    maps = stats = 0
    MAPPED = set()
    scenes = []
    last_tr = None
    for i, hi in enumerate(lines):
        en = eng[i] if i < len(eng) else ""
        role = "hook" if i == 0 else ("end" if i == n - 1 and (END.search(hi) or n > 3) else
                                      "reveal" if REVEAL.search(hi) and i >= n // 2 else
                                      "turn" if TURN.search(hi) else
                                      "context" if i <= 2 else "explain")
        if ORDINAL.search(hi) and role in ("context", "explain"): role = "section"
        kw, kw2, kind = _heuristic_kw(hi, en, who.get(i))
        place_txt = ""
        if llm and i < len(llm) and isinstance(llm[i], dict):
            L = llm[i]
            lk = _clean_kw(L.get("kw")); lt = str(L.get("type") or "").lower()
            if lt == "none":
                kw, kw2, kind = (kw, kw2, kind) if kind == "number" else (None, "", "none")
            elif lk and _kw_ok(lk, lt, hi, en, who.get(i)):
                kw, kw2, kind = lk, _clean_kw(L.get("kw2")), (lt if lt in ("word", "number", "name", "place") else "word")
            elif lk:                                  # v3.18: AI ka shabd is line me bola hi nahi gaya -> nahi lagega
                if kind != "number": kw, kw2, kind = None, "", "none"
            place_txt = str(L.get("place") or "")
            if str(L.get("role") or "") in TRANS or L.get("role") == "hook":
                role = L["role"] if i not in (0,) else "hook"
        # jagah -> map
        place = None
        tags = fx_tags.get(i, [])
        if any(nm == "map" for nm, _ in tags):
            place = places.resolve(next(v for nm, v in tags if nm == "map").split("|")[0])
        elif kinds.get(i) == "place" or place_txt or kind == "place":
            place = places.find(hi, en, place_txt)
        elif not llm:                                 # offline: sirf shehar/rajya (desh ka naam aksar sirf zikr hota hai)
            p_ = places.find(hi, en, "")
            if p_ and p_["kind"] in ("city", "district", "state"): place = p_
        graphic = None
        # v3.18 (Rajasthan video: pehle SIKAR ka map, phir 6 sec RAJASTHAN ka map dobara): ek hi rajya / desh ka
        # map ek hi baar – doosri baar us line pe asli footage (aapka hint) chalega
        pkey = place and (place.get("state") or place.get("country") or place.get("name") or "").lower()
        explicit_map = any(nm == "map" for nm, _ in tags)
        if place and (explicit_map or (maps < map_max and pkey not in MAPPED)) and i != 0 and role != "end":
            graphic = "map"; maps += 1; MAPPED.add(pkey)
        elif kind == "number" and stats < stat_max and role in ("reveal", "turn", "explain", "section") \
                and yes_(style.get("stat_card", "haan")):
            graphic = "stat_if_weak"           # footage kamzor ho tab hi card (QA decide karega)
            stats += 1
        anim = {"number": "count", "name": "name", "place": "name"}.get(kind) or \
            {"hook": "track", "turn": "spring", "reveal": "pop", "section": "typewriter"}.get(role, "blur")
        if role == "hook": tr = None
        else:
            opts = TRANS.get(role, TRANS["explain"])
            tr = next((o for o in opts if o != last_tr), opts[0])
        sfx = "riser" if role == "reveal" else ("whoosh" if tr else None)
        purpose = {"hook": "viewer ko 1 sec me rokna", "context": "kahani ki duniya dikhana", "explain": "fact samjhana",
                   "turn": "twist – dhyan wapas khinchna", "reveal": "badi baat ka payoff", "end": "yaad rehne wala ant",
                   "section": "naya point shuru"}.get(role, "")
        kw = _fix_one(kw) if kw else kw
        if role == "end" and END.search(hi) and kind != "number":
            kw, kw2, kind = None, "", "none"          # v3.18: 'follow karo' line pe 'SHOCKING' jaisa text nahi
        scenes.append({"i": i, "role": role, "purpose": purpose, "kw": kw, "kw2": kw2, "kind": kind, "anim": anim,
                       "place": place, "graphic": graphic, "transition": tr, "sfx": sfx, "show": en[:140]})
        last_tr = tr or last_tr
    # keyword har line pe nahi: lagatar 3 line pe text ho to beech wala hatao (number/name/map chhod ke)
    run_ = 0
    for s in scenes:
        if s["kw"] and s["graphic"] != "map":
            run_ += 1
            if run_ >= 4 and s["kind"] == "word" and s["role"] not in ("hook", "reveal"):
                s["kw"] = None; s["kind"] = "none"; run_ = 0
        else:
            run_ = 0
    for s in scenes:                     # map wali line pe alag keyword nahi (map khud naam dikhata hai)
        if s["graphic"] == "map": s["kw"] = None
    if work:
        save(scenes, work, by)
    return scenes


def yes_(v):
    return str(v or "").strip().lower() in ("haan", "han", "ha", "yes", "y", "on", "true", "1")


def report(scenes, by=""):
    """Telegram / file ke liye chhota Hindi storyboard."""
    RL = {"hook": "🎣 HOOK", "context": "🌍 context", "explain": "🔬 samjhao", "turn": "⚡ twist", "reveal": "💥 REVEAL",
          "end": "🏁 end", "section": "🔢 naya point"}
    out = [f"🎬 STORYBOARD ({len(scenes)} scenes)" + (f" – keyword: {by}" if by else " – offline niyam")]
    for s in scenes:
        bits = [f"{s['i']+1}. {RL.get(s['role'], s['role'])}"]
        if s["graphic"] == "map" and s["place"]:
            bits.append(f"🗺️ 3D map: {s['place']['name']}" + (f", {s['place']['state']}" if s['place'].get('state') and s['place']['state'] != s['place']['name'] else ""))
        elif s["kw"]:
            bits.append(f"🔤 {s['kw']}" + (f" {s['kw2']}" if s["kw2"] else "") + f" ({s['anim']})")
        if s["transition"]: bits.append(f"↪ {s['transition']}")
        out.append("  ".join(bits))
    return "\n".join(out)


def save(scenes, work, by=""):
    try:
        Path(work, "storyboard.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        Path(work, "storyboard.txt").write_text(report(scenes, by), encoding="utf-8")
    except Exception:
        pass
