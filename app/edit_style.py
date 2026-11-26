"""v4.29 VIRAL EDITING STYLE LIBRARY – video ke VISHAY (category) + format (Short vs Long) ke hisaab se pro viral editing.

Shorts (40-55s) aur Longs (5-6 min) dono ke liye har category ka alag look, cut pacing, hook badge,
accent color, SFX flavor, aur documentary proof-beat profile:
  - history / news / army: archival film look, bold Year Reveals, yellow highlighter clippings, paper/boom SFX
  - business / sports / festival: natural warm 35mm Indian storytelling look (Pulse Candy / Balaji style), rolling counters, click/ding SFX
  - science / tech: crisp cinematic teal look, step-by-step explainers, glowing stat popups, whoosh/boom SFX
  - mystery: dark documentary tone (Fern / MagnatesMedia style), dramatic pacing, sub-boom SFX
  - geography: tactile natural map/comparison look (Rice vs Roti / PM Languages style), crisp pop/click SFX

style.txt:  edit_style = auto   (auto = vishay se khud / nahi = purana tareeka / ya naam: history, festival, tech,
                                 science, news, mystery, person, army, business, sports, geography, general)
"""
import re

PRESETS = {
    "history": dict(
        look="film", layer_kw=("purani", "film", "old", "scratch", "dust", "grain"), layer_max=28,
        gap=3.5, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=True, hook_cuts=3,
        hook_badge="HISTORY FILE", accent="#F59E0B", sfx_accent="paper", year_beat=True,
        fx_block=("danger_sparks", "drop_spin"),
        about="itihaas – archival film rang, giant Year Reveal, yellow highlighter clippings",
    ),
    "festival": dict(
        look="warm", layer_kw=("light", "leak", "bokeh", "dust", "grain"), layer_max=15,
        gap=4.2, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=2,
        hook_badge="CULTURE & HERITAGE", accent="#F59E0B", sfx_accent="ding", year_beat=False,
        fx_block=("mystery_dust", "danger_sparks", "drop_spin", "card_flip", "tilt_card", "zoom_hit"),
        about="tyohaar / sanskriti – garam sunehra rang, naram cut, koi darawna effect nahi",
    ),
    "tech": dict(
        look="teal", layer_kw=("grain", "digital", "dust", "particle"), layer_max=12,
        gap=3.2, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=3,
        hook_badge="TECH INSIGHT", accent="#38BDF8", sfx_accent="click", year_beat=True,
        fx_block=("mystery_dust", "danger_sparks"),
        about="tech / AI – saaf teal rang, tez seedhe cut, crisp data beats",
    ),
    "science": dict(
        look="teal", layer_kw=("particle", "dust", "grain", "space"), layer_max=15,
        gap=3.6, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=2,
        hook_badge="SCIENCE BRIEF", accent="#38BDF8", sfx_accent="boom", year_beat=True,
        fx_block=("danger_sparks", "drop_spin"),
        about="science / space – cinematic teal rang, step-by-step explainers, stat popups",
    ),
    "news": dict(
        look="film", layer_kw=("grain", "dust"), layer_max=15,
        gap=2.8, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=True, hook_cuts=3,
        hook_badge="BREAKING BRIEF", accent="#EF4444", sfx_accent="paper", year_beat=True,
        fx_block=("mystery_dust", "drop_spin"),
        about="news / rajneeti – tez hard cut, yellow highlighter clippings, year/stamp beats",
    ),
    "mystery": dict(
        look="doc", layer_kw=("dust", "grain", "film", "smoke"), layer_max=24,
        gap=3.4, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=True, hook_cuts=3,
        hook_badge="MYSTERY FILE", accent="#EF4444", sfx_accent="boom", year_beat=True,
        fx_block=(),
        about="rahasya / crime – dark documentary rang, suspense pacing, sub-boom accents",
    ),
    "person": dict(
        look="film", layer_kw=("grain", "dust"), layer_max=15,
        gap=3.4, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=3,
        hook_badge="UNTOLD STORY", accent="#FACC15", sfx_accent="paper", year_beat=True,
        fx_block=("danger_sparks",),
        about="insaan / biography – natural film rang, chehre pe dhyan, year/quote cards",
    ),
    "army": dict(
        look="film", layer_kw=("grain", "dust", "smoke"), layer_max=22,
        gap=2.8, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=True, hook_cuts=3,
        hook_badge="DEFENCE FILE", accent="#EF4444", sfx_accent="boom", year_beat=True,
        fx_block=("drop_spin",),
        about="fauj / army / defence – tactical film rang, tez cut, impact boom focus",
    ),
    "business": dict(
        look="warm", layer_kw=("grain", "dust"), layer_max=12,
        gap=3.0, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=3,
        hook_badge="BUSINESS CASE", accent="#FACC15", sfx_accent="click", year_beat=True,
        fx_block=("mystery_dust", "danger_sparks", "drop_spin"),
        about="business / economy – warm 35mm Indian look, rolling ₹/% counters, rise-and-fall flow",
    ),
    "sports": dict(
        look="warm", layer_kw=("light", "grain", "dust"), layer_max=14,
        gap=2.6, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=3,
        hook_badge="SPORTS FILE", accent="#22C55E", sfx_accent="ding", year_beat=True,
        fx_block=("mystery_dust", "danger_sparks"),
        about="sports / cricket – high-energy tez cut, garam rang, record stat popups",
    ),
    "geography": dict(
        look="natural", layer_kw=("grain", "dust"), layer_max=12,
        gap=3.2, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=False, hook_cuts=3,
        hook_badge="INDIA & WORLD DATA", accent="#22C55E", sfx_accent="click", year_beat=False,
        fx_block=("mystery_dust", "danger_sparks", "drop_spin"),
        about="geography / comparisons – natural satellite map look, crisp split/label cuts",
    ),
    "general": dict(
        look="film", layer_kw=("grain", "dust"), layer_max=18,
        gap=3.3, short_cut=2.0, long_cut=4.0, long_hook_cut=2.4, flash_every=False, archive=True, hook_cuts=3,
        hook_badge="VIRAL FACT", accent="#FACC15", sfx_accent="click", year_beat=True,
        fx_block=("danger_sparks",),
        about="aam facts – balanced viral documentary look, halki grain",
    ),
}

KW = {
    "festival": r"(त्योहार|त्यौहार|पर्व|पूजा|व्रत|उत्सव|मेला|आरती|घाट|मंदिर|भगवान|देवी|देवता|छठ|दिवाली|होली|ईद|नवरात्रि|"
                r"गणेश|परंपरा|रिवाज|श्रद्धा|भक्त|प्रसाद|festival|puja|pooja|temple|devotee|ritual|diwali|holi|eid|"
                r"navratri|tradition|prasad|ghat)",
    "history":  r"(इतिहास|ऐतिहासिक|प्राचीन|राजा|सम्राट|मुगल|अंग्रेज|ब्रिटिश|आज़ादी|आजादी|स्वतंत्रता|युद्ध|साम्राज्य|"
                r"आपातकाल|इमरजेंसी|बंटवारा|history|historic|ancient|empire|emperor|king|british|independence|war|dynasty|mughal)",
    "tech":     r"(टेक्नोलॉजी|टेक|एआई|सॉफ्टवेयर|कंप्यूटर|स्मार्टफोन|इंटरनेट|ऐप|चिप|माइक्रोसॉफ्ट|गूगल|एप्पल|एनवीडिया|एनविडिया|"
                r"ओपनएआई|टेस्ला|अमेज़न|मेटा|आउटेज|सर्वर|ईमेल|आउटलुक|टीम्स|कोपायलट|यूज़र|यूजर|"
                r"technology|tech|\bai\b|software|computer|smartphone|internet|app|chip|gpu|nvidia|microsoft|"
                r"google|apple|outage|algorithm|robot)",
    "science":  r"(विज्ञान|वैज्ञानिक|ग्रह|अंतरिक्ष|ब्रह्मांड|तारा|ब्लैक होल|सूरज|नासा|इसरो|कोशिका|डीएनए|परमाणु|फ्यूजन|"
                r"science|scientist|planet|space|universe|galaxy|black hole|nasa|isro|cell|dna|atom|physics|chemistry|biology|nuclear)",
    "news":     r"(सरकार|चुनाव|मंत्री|प्रधानमंत्री|संसद|कोर्ट|अदालत|कानून|पुलिस|ब्रेकिंग|सुप्रीम|पेट्रोल|टैक्स|बजट|"
                r"government|election|minister|parliament|court|law|police|breaking|policy|emergency|supreme court|scam|ghotala)",
    "mystery":  r"(रहस्य|रहस्यमय|डरावना|हत्या|अपराध|भूत|गायब|खौफ|साजिश|जेल|mystery|mysterious|murder|crime|ghost|disappear|haunted|conspiracy)",
    "army":     r"(सेना|फौज|आर्मी|मिसाइल|टैंक|फाइटर जेट|बॉर्डर|कमांडो|डिफेंस|सर्जिकल|army|military|missile|fighter jet|soldier|defence|commando|navy|air force)",
    "business": r"(बिज़नेस|बिजनेस|कंपनी|स्टार्टअप|अरबपति|करोड़|कमाई|शेयर|बाज़ार|ब्रांड|मुनाफा|दुकान|फैक्ट्री|मार्केट|सीईओ|रुपये|"
                r"रेलवे|ट्रेन|टिकट|यात्री|पैसेंजर|बैंक|लोन|ग्राहक|अर्थव्यवस्था|नियम|business|company|startup|billionaire|"
                r"profit|revenue|valuation|ipo|brand|market|crore|turnover|ceo|kirana|railway|ticket|passenger|bank|economy)",
    "sports":   r"(क्रिकेट|फुटबॉल|ओलंपिक|मैच|वर्ल्ड कप|खिलाड़ी|शतक|विकेट|गोल|आईपीएल|cricket|football|olympics|world cup|century|wicket|athlete|ipl)",
    "geography": r"(राज्य|नदी|पहाड़|सीमा|नक्शा|मैप|भाषा|जनसंख्या|उत्तर भारत|दक्षिण भारत|राजधानी|देशों|महाद्वीप|"
                 r"state|river|mountain|border|map|language|population|north india|south india|continent|geography|capital|region)",
}

HIST_EVIDENCE = re.compile(r"(अंग्रेज|ब्रिटिश|आज़ादी|आजादी|स्वतंत्रता संग्राम|विश्व युद्ध|आपातकाल|इमरजेंसी|बंटवारा|विभाजन|"
                           r"मुगल|british|independence|world war|emergency|partition|colonial|mughal|freedom struggle|"
                           r"\b1[89]\d\d\b|\b19[0-8]\d\b|\b199[0-5]\b|[१][८९][०-९][०-९])", re.I)


def detect(lines_hi, lines_en, lock=None, scenes=None):
    """Video ka genre. Return (naam, wajah)."""
    txt = " ".join(list(lines_hi or []) + list(lines_en or [])).lower()
    sc = {g: len(re.findall(p, txt, re.I)) for g, p in KW.items()}
    for s in scenes or []:
        d = str(s.get("domain") or "").lower()
        if d in ("space", "science", "biology", "ocean"):
            sc["science"] += 1
        elif d == "technology":
            sc["tech"] += 1
        elif d == "history":
            sc["history"] += 0.5
        elif d in ("geography", "map"):
            sc["geography"] += 1
    mt = str((lock or {}).get("main_type") or "").lower()
    if mt == "person" and sc["festival"] < 2 and sc["history"] < 2 and sc["news"] < 2:
        sc["person"] = 2.5
    if mt == "brand":
        sc["business"] += 1.5
    cat_l = str((lock or {}).get("category") or "").strip().lower()
    if cat_l in PRESETS and cat_l != "general":
        sc[cat_l] = sc.get(cat_l, 0) + 2.5
    best = max(sc.items(), key=lambda kv: kv[1]) if sc else ("general", 0)
    if best[1] < 1.5:
        return "general", "koi saaf vishay nahi"
    return best[0], f"shabd-milaan {round(best[1], 1)}"


def apply(style, lines_hi, lines_en, lock=None, scenes=None, log=None):
    """style dict me genre ke viral editing niyam daalta hai (sirf andar ke liye – style.txt nahi badalti)."""
    mode = str(style.get("edit_style", "auto") or "auto").strip().lower()
    if mode in ("nahi", "no", "off", "band"):
        style["_genre"] = "general"
        style["_hook_badge"] = "VIRAL FACT"
        style["_hook_accent"] = "#FACC15"
        style["_sfx_accent"] = "click"
        style["_year_beat"] = "haan"
        return "general"
    if mode in PRESETS:
        g, why = mode, "style.txt me chuna"
    else:
        g, why = detect(lines_hi, lines_en, lock, scenes)
    p = PRESETS[g]
    style["_genre"] = g
    style["_layer_kw"] = ",".join(p["layer_kw"])
    style["_fx_block"] = ",".join(p["fx_block"])
    style["_hook_badge"] = p["hook_badge"]
    style["_hook_accent"] = p["accent"]
    style["_sfx_accent"] = p["sfx_accent"]
    style["_short_cut"] = str(p["short_cut"])
    style["_long_cut"] = str(p["long_cut"])
    style["_long_hook_cut"] = str(p["long_hook_cut"])
    style["_year_beat"] = "haan" if p.get("year_beat", True) else "nahi"

    if str(style.get("color_look", "film")).strip().lower() in ("film", "", "auto"):
        style["color_look"] = p["look"]
    try:
        lt = float(str(style.get("layer_taakat", "30")).split()[0])
    except Exception:
        lt = 30.0
    style["layer_taakat"] = str(int(min(lt, p["layer_max"])))
    try:
        gp = float(str(style.get("transition_gap", "3.5")).split()[0])
    except Exception:
        gp = 3.5
    style["transition_gap"] = str(max(gp, p["gap"]))
    if not p["flash_every"]:
        style["flash_har_clip"] = "nahi"
    style["_hook_cuts"] = str(p["hook_cuts"])
    if log:
        log(f"   🎨 viral edit style: {g} ({why}) – {p['about']}; rang {style['color_look']}, "
            f"badge '{p['hook_badge']}', sfx '{p['sfx_accent']}', cut {p['short_cut']}s/{p['long_cut']}s")
    return g


def archive_ok(text_hi, text_en, style):
    """B&W archive rang sirf jab line me sach me purana daur ho aur genre allow kare."""
    g = style.get("_genre") or "general"
    if g in PRESETS and not PRESETS[g]["archive"]:
        return False
    return bool(HIST_EVIDENCE.search(f"{text_hi} {text_en}"))


def layer_ok(name, style):
    kw = [k for k in str(style.get("_layer_kw") or "").split(",") if k]
    if not kw:
        return True
    n = name.lower()
    return any(k in n for k in kw)


def fx_blocked(style):
    return {k for k in str(style.get("_fx_block") or "").split(",") if k}
