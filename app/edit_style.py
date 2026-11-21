"""v3.16 EDITING STYLE LIBRARY – video ke VISHAY (genre) ke hisaab se pro editing ke niyam.

User ki shikayat (16 Nov 2026): "professional editing nahi lagti". Log me dikha:
  * Chhath Puja (tyohaar) ki sunehri shaam B&W "archive" rang me (Gemini ne line ko 'history' bola tha),
  * upar se "purani_film" scratch layer (random chuni gayi),
  * Edit Director ka "mystery_dust" effect ek bhakti wali line pe,
  * har clip badalne pe light-leak flash.
Pro editor har vishay ke liye ALAG rang, layer, cut ki raftaar aur effect chunta hai. Wahi niyam yahan ek jagah hain.
Reference reels (REFERENCE_STYLE_ANALYSIS.md): Tomatoes = garam rang, tez cut (~1.3 s); Emergency = archive B&W
sirf purane daur pe, ~3.4 s cut + camera move, khatre pe laal.

style.txt:  edit_style = auto   (auto = vishay se khud / nahi = purana tareeka / ya naam: history, festival, tech,
                                 science, news, mystery, person, general)
"""
import re

PRESETS = {
    #            rang (render.LOOKS)  layer file-naam me ye shabd  layer taakat  transition gap  har cut flash  B&W allowed
    "history":  dict(look="film",    layer_kw=("purani", "film", "old", "scratch", "dust", "grain"), layer_max=30,
                     gap=4.0, flash_every=False, archive=True, hook_cuts=3,
                     fx_block=("danger_sparks", "drop_spin"), about="itihaas – film rang, purana daur ho to B&W"),
    "festival": dict(look="warm",    layer_kw=("light", "leak", "bokeh", "dust", "grain"), layer_max=15,
                     gap=4.5, flash_every=False, archive=False, hook_cuts=2,
                     fx_block=("mystery_dust", "danger_sparks", "drop_spin", "card_flip", "tilt_card", "zoom_hit"),
                     about="tyohaar / sanskriti / bhakti – garam sunehra rang, naram cut, koi darawna effect nahi"),
    "tech":     dict(look="teal",    layer_kw=("grain", "digital", "dust", "particle"), layer_max=12,
                     gap=3.5, flash_every=False, archive=False, hook_cuts=3,
                     fx_block=("mystery_dust", "danger_sparks"), about="tech / company / business – saaf teal rang, tez seedhe cut"),
    "science":  dict(look="teal",    layer_kw=("particle", "dust", "grain", "space"), layer_max=15,
                     gap=4.0, flash_every=False, archive=False, hook_cuts=2,
                     fx_block=("danger_sparks", "drop_spin"), about="science / space – thanda rang, dheemi camera chaal"),
    "news":     dict(look="film",    layer_kw=("grain", "dust"), layer_max=15,
                     gap=3.0, flash_every=False, archive=True, hook_cuts=3,
                     fx_block=("mystery_dust", "drop_spin"), about="news / rajneeti – seedhe hard cut, saal/stamp text"),
    "mystery":  dict(look="teal",    layer_kw=("dust", "grain", "film", "smoke"), layer_max=25,
                     gap=3.5, flash_every=False, archive=True, hook_cuts=3,
                     fx_block=(), about="rahasya / crime / khatra – gehra rang, dust layer"),
    "person":   dict(look="film",    layer_kw=("grain", "dust"), layer_max=15,
                     gap=3.5, flash_every=False, archive=False, hook_cuts=3,
                     fx_block=("danger_sparks",), about="insaan / celebrity – film rang, chehre pe dhyan"),
    "general":  dict(look="film",    layer_kw=("grain", "dust"), layer_max=18,
                     gap=3.5, flash_every=False, archive=True, hook_cuts=3,
                     fx_block=("danger_sparks",), about="aam facts – film rang, halki grain"),
}

KW = {
    "festival": r"(त्योहार|त्यौहार|पर्व|पूजा|व्रत|उत्सव|मेला|आरती|घाट|मंदिर|भगवान|देवी|देवता|छठ|दिवाली|होली|ईद|नवरात्रि|"
                r"गणेश|परंपरा|रिवाज|श्रद्धा|भक्त|प्रसाद|festival|puja|pooja|temple|devotee|ritual|diwali|holi|eid|"
                r"navratri|tradition|prasad|ghat)",
    "history":  r"(इतिहास|ऐतिहासिक|प्राचीन|राजा|सम्राट|मुगल|अंग्रेज|ब्रिटिश|आज़ादी|आजादी|स्वतंत्रता|युद्ध|साम्राज्य|"
                r"history|historic|ancient|empire|emperor|king|british|independence|war|dynasty|mughal)",
    "tech":     r"(कंपनी|टेक्नोलॉजी|टेक|एआई|सॉफ्टवेयर|कंप्यूटर|स्मार्टफोन|इंटरनेट|ऐप|चिप|शेयर|बिज़नेस|बिजनेस|स्टार्टअप|"
                r"माइक्रोसॉफ्ट|गूगल|एप्पल|एनवीडिया|एनविडिया|ओपनएआई|टेस्ला|अमेज़न|मेटा|सीईओ|सीएफओ|आउटेज|सर्वर|ईमेल|"
                r"आउटलुक|टीम्स|कोपायलट|प्रोडक्ट|यूज़र|यूजर|"
                r"company|technology|tech|\bai\b|software|computer|smartphone|internet|app|chip|gpu|nvidia|microsoft|"
                r"google|apple|startup|business|share|market|ceo|outage)",
    "science":  r"(विज्ञान|वैज्ञानिक|ग्रह|अंतरिक्ष|ब्रह्मांड|तारा|सूरज की सतह|नासा|इसरो|कोशिका|डीएनए|परमाणु|science|"
                r"scientist|planet|space|universe|galaxy|nasa|isro|cell|dna|atom|physics|chemistry|biology)",
    "news":     r"(सरकार|चुनाव|मंत्री|प्रधानमंत्री|संसद|कोर्ट|अदालत|कानून|पुलिस|ब्रेकिंग|government|election|minister|"
                r"parliament|court|law|police|breaking|policy|emergency|आपातकाल)",
    "mystery":  r"(रहस्य|रहस्यमय|डरावना|हत्या|अपराध|भूत|गायब|खौफ|mystery|mysterious|murder|crime|ghost|disappear|haunted)",
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
        if d in ("space", "science", "biology", "ocean"): sc["science"] += 1
        elif d == "technology": sc["tech"] += 1
        elif d == "history": sc["history"] += 0.5          # Gemini ka 'history' kamzor saboot (tyohaar bhi purane hote hain)
    mt = str((lock or {}).get("main_type") or "").lower()
    if mt == "person" and sc["festival"] < 2 and sc["history"] < 2:
        sc["person"] = 2.5
    if mt == "brand": sc["tech"] += 1.5
    best = max(sc.items(), key=lambda kv: kv[1]) if sc else ("general", 0)
    if best[1] < 1.5:
        return "general", "koi saaf vishay nahi"
    return best[0], f"shabd-milaan {round(best[1], 1)}"


def apply(style, lines_hi, lines_en, lock=None, scenes=None, log=None):
    """style dict me genre ke niyam daalta hai (sirf andar ke liye – style.txt nahi badalti)."""
    mode = str(style.get("edit_style", "auto") or "auto").strip().lower()
    if mode in ("nahi", "no", "off", "band"):
        style["_genre"] = "general"; return "general"
    if mode in PRESETS:
        g, why = mode, "style.txt me chuna"
    else:
        g, why = detect(lines_hi, lines_en, lock, scenes)
    p = PRESETS[g]
    style["_genre"] = g
    style["_layer_kw"] = ",".join(p["layer_kw"])
    style["_fx_block"] = ",".join(p["fx_block"])
    # rang: user ne apna khaas rang (teal/natural/danger) chuna ho to wahi; default 'film' ho to genre ka
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
        log(f"   🎨 edit style: {g} ({why}) – {p['about']}; rang {style['color_look']}, layer max {style['layer_taakat']}%, "
            f"transition har ~{style['transition_gap']}s")
    return g


def archive_ok(text_hi, text_en, style):
    """B&W archive rang sirf jab line me sach me purana daur ho aur genre allow kare."""
    g = style.get("_genre") or "general"
    if g in PRESETS and not PRESETS[g]["archive"]:
        return False
    return bool(HIST_EVIDENCE.search(f"{text_hi} {text_en}"))


def layer_ok(name, style):
    kw = [k for k in str(style.get("_layer_kw") or "").split(",") if k]
    if not kw: return True
    n = name.lower()
    return any(k in n for k in kw)


def fx_blocked(style):
    return {k for k in str(style.get("_fx_block") or "").split(",") if k}
