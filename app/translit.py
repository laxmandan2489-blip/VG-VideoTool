"""Devanagari -> casual Hinglish (Roman) for captions, e.g. 'मंगल ग्रह की धूल' -> 'mangal grah ki dhool'."""
import re

V = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e", "ऐ": "ai",
     "ओ": "o", "औ": "au", "ऑ": "o", "ॲ": "e"}
M = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o",
     "ौ": "au", "ॉ": "o", "ॅ": "e"}
C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh",
     "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d",
     "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r",
     "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h", "क़": "q", "ख़": "kh", "ग़": "g",
     "ज़": "z", "ड़": "d", "ढ़": "rh", "फ़": "f", "य़": "y"}
NUKTA = "़"; HAL = "्"; ANU = "ं"; CHB = "ँ"; VIS = "ः"
DIG = {chr(0x0966 + i): str(i) for i in range(10)}

# common words where simple rules look odd
FIX = {"है": "hai", "हैं": "hain", "मैं": "main", "में": "mein", "नहीं": "nahi", "क्या": "kya", "क्यों": "kyon",
       "और": "aur", "यह": "yeh", "वह": "woh", "ये": "ye", "वो": "wo", "हम": "hum", "तुम": "tum", "आप": "aap",
       "कि": "ki", "की": "ki", "के": "ke", "का": "ka", "को": "ko", "से": "se", "पर": "par", "भी": "bhi",
       "एक": "ek", "दो": "do", "तीन": "teen", "सौ": "sau", "हजार": "hazaar", "हज़ार": "hazaar", "लाख": "lakh",
       "करोड़": "crore", "फैक्ट": "fact", "फॉलो": "follow", "नासा": "NASA", "सुनो": "suno", "सोचो": "socho",
       "जरा": "zara", "ज़रा": "zara", "मतलब": "matlab", "लेकिन": "lekin", "इसलिए": "isliye", "इसीलिए": "isiliye",
       "सबसे": "sabse", "ज्यादा": "zyada", "ज़्यादा": "zyada", "इंसान": "insaan", "इंसानों": "insaanon",
       "फैक्ट्स": "facts", "केमिकल": "chemical", "रोवर": "rover", "एस्ट्रोनॉट": "astronaut", "स्पेससूट": "spacesuit",
       "पर्सिवरेंस": "Perseverance", "नैनोमीटर": "nanometer", "परक्लोरेट": "perchlorate", "थायरॉइड": "thyroid",
       "बेस": "base", "लिए": "liye", "गई": "gayi", "नई": "nayi", "गए": "gaye", "हुई": "hui", "हुए": "hue",
       "साइंटिस्ट": "scientist", "प्लैनेट": "planet", "स्पेस": "space", "वीडियो": "video", "फोन": "phone",
       "जी": "Ji", "हाँ": "Haan", "हां": "Haan", "प्रतिशत": "pratishat", "मामलों": "maamlon",
       "रेलवे": "railway", "ट्रेन": "train", "पैसेंजर": "passenger", "टिकट": "ticket", "बर्थ": "berth",
       "सीट": "seat", "कंफर्म": "confirm", "अपग्रेड": "upgrade", "आरएसी": "RAC", "टीटीई": "TTE"}


# v3.1: English se aaye shabd English spelling me (pehle "गेमिंग" -> "geming", "करियर" -> "kariyar" aata tha)
LOAN = {"गेमिंग": "gaming", "गेम": "game", "गेम्स": "games", "गेमर": "gamer", "रोस्टिंग": "roasting", "रोस्ट": "roast",
        "रोस्टर": "roaster", "स्ट्रीमिंग": "streaming", "स्ट्रीमर": "streamer", "स्ट्रीम": "stream", "शूटिंग": "shooting",
        "एडिटिंग": "editing", "एडिटर": "editor", "ट्रेंडिंग": "trending", "ट्रेंड": "trend", "मार्केटिंग": "marketing",
        "करियर": "career", "कैरियर": "career", "चैनल": "channel", "चैनलों": "channels", "यूट्यूब": "YouTube",
        "यूट्यूबर": "YouTuber", "यूट्यूबर्स": "YouTubers", "सब्सक्राइब": "subscribe", "सब्सक्राइबर": "subscribers",
        "सब्सक्राइबर्स": "subscribers", "व्यूज": "views", "व्यूज़": "views", "व्यू": "view", "कंटेंट": "content",
        "क्रिएटर": "creator", "क्रिएटर्स": "creators", "कमेंट्री": "commentary", "कमेंट": "comment", "रिएक्शन": "reaction",
        "वायरल": "viral", "इंटरनेट": "internet", "सोशल": "social", "मीडिया": "media", "ऑनलाइन": "online",
        "स्टूडियो": "studio", "फैंस": "fans", "फैन": "fan", "मिलियन": "million", "बिलियन": "billion", "कंपनी": "company",
        "बिजनेस": "business", "ब्रांड": "brand", "मोबाइल": "mobile", "कंप्यूटर": "computer", "लैपटॉप": "laptop",
        "टेक्नोलॉजी": "technology", "पॉडकास्ट": "podcast", "म्यूजिक": "music", "म्यूज़िक": "music", "सॉन्ग": "song",
        "रैप": "rap", "फिल्म": "film", "मूवी": "movie", "सीरीज": "series", "शो": "show", "एपिसोड": "episode",
        "लाइव": "live", "स्टार": "star", "सुपरस्टार": "superstar", "रिकॉर्ड": "record", "अवॉर्ड": "award",
        "ऐप": "app", "एआई": "AI", "चिप": "chip", "डेटा": "data", "स्मार्टफोन": "smartphone", "प्रोडक्ट": "product",
        "मार्केट": "market", "शेयर": "share", "लाइक": "like", "कमेंट्स": "comments", "फॉलोअर्स": "followers",
        "इंस्टाग्राम": "Instagram", "फेसबुक": "Facebook", "गूगल": "Google", "एप्पल": "Apple", "टेस्ला": "Tesla",
        "एनवीडिया": "NVIDIA", "माइक्रोसॉफ्ट": "Microsoft", "अमेज़न": "Amazon", "अमेजन": "Amazon", "नेटफ्लिक्स": "Netflix",
        "इमरजेंसी": "Emergency", "कांग्रेस": "Congress", "बॉलीवुड": "Bollywood", "क्रिकेट": "cricket",
        "काउंटर": "Counter", "स्ट्राइक": "Strike", "स्ट्रीट": "street", "टीम": "team", "प्लेयर": "player",
        "वीडियोज": "videos", "वीडियोज़": "videos", "क्लिप": "clip", "क्लिप्स": "clips", "ट्रोल": "troll",
        "मीम": "meme", "मीम्स": "memes", "स्पॉन्सर": "sponsor", "डील": "deal", "करोड़ों": "croron", "पॉपुलर": "popular",
        "कमेंटेटर": "commentator", "कमेंटेटरों": "commentators", "रोस्टर": "roaster", "ट्रेंड्स": "trends",
        "ऑडियंस": "audience", "रियल": "real", "फेक": "fake", "पर्सनल": "personal", "प्रोफेशनल": "professional",
        "कैमरा": "camera", "माइक": "mic", "सेटअप": "setup", "प्लेटफॉर्म": "platform", "अपलोड": "upload",
        "डाउनलोड": "download", "थंबनेल": "thumbnail", "टाइटल": "title", "फैक्ट्स": "facts", "स्टोरी": "story",
        # v3.17
        "जनवरी": "January", "फरवरी": "February", "मार्च": "March", "अप्रैल": "April", "मई": "May", "जून": "June", "जुलाई": "July", "अगस्त": "August", "सितंबर": "September", "सितम्बर": "September", "अक्टूबर": "October", "नवंबर": "November", "नवम्बर": "November", "दिसंबर": "December", "दिसम्बर": "December", "आउटेज": "outage", "आउटेज़": "outage", "सर्विस": "service", "सर्विसेज": "services", "सर्विसेज़": "services", "प्रोडक्ट्स": "products", "यूज़र": "user", "यूजर": "user", "यूज़र्स": "users", "यूजर्स": "users", "ईमेल": "email", "ईमेल्स": "emails", "मेल": "mail", "रिपोर्ट": "report", "रिपोर्ट्स": "reports", "रिपोर्टों": "reports", "ऑफिस": "office", "ऑफिसों": "offices", "ऑफ़िस": "office", "आउटलुक": "Outlook", "टीम्स": "Teams", "कोपायलट": "Copilot", "को-पायलट": "Copilot", "विंडोज": "Windows", "विंडोज़": "Windows", "क्लाउड": "cloud", "सर्वर": "server", "सर्वरों": "servers", "सॉफ्टवेयर": "software", "सॉफ़्टवेयर": "software", "अपडेट": "update", "सिस्टम": "system", "नेटवर्क": "network", "वेबसाइट": "website", "ब्राउज़र": "browser", "पासवर्ड": "password", "हैकर": "hacker", "हैकर्स": "hackers", "साइबर": "cyber", "अटैक": "attack", "बग": "bug", "ग्लिच": "glitch", "क्रैश": "crash", "डाउन": "down", "सीईओ": "CEO", "सीएफओ": "CFO", "सीटीओ": "CTO", "फाउंडर": "founder", "बोर्ड": "board", "इन्वेस्टर": "investor", "इन्वेस्टर्स": "investors", "स्टॉक": "stock", "शेयर्स": "shares", "डॉलर": "dollar", "डॉलर्स": "dollars", "ट्रिलियन": "trillion", "रेवेन्यू": "revenue", "प्रॉफिट": "profit", "स्टार्टअप": "startup", "टेक": "tech", "जीपीयू": "GPU", "सीपीयू": "CPU", "चिप्स": "chips", "ग्राफिक्स": "graphics", "रोबोट": "robot", "ड्रोन": "drone", "इलेक्ट्रिक": "electric", "बैटरी": "battery", "चार्जिंग": "charging", "आईफोन": "iPhone", "एंड्रॉयड": "Android", "एंड्रॉइड": "Android", "चैटजीपीटी": "ChatGPT", "ओपनएआई": "OpenAI", "जेमिनी": "Gemini", "ट्विटर": "Twitter", "व्हाट्सएप": "WhatsApp", "व्हाट्सऐप": "WhatsApp", "पॉलिसी": "policy", "न्यूज़": "news", "न्यूज": "news", "ब्रेकिंग": "breaking", "ऑफिशियल": "official", "अनाउंस": "announce", "अनाउंसमेंट": "announcement", "लॉन्च": "launch", "मॉडल": "model", "वर्जन": "version", "फीचर": "feature", "फीचर्स": "features", "स्क्रीन": "screen", "कीबोर्ड": "keyboard", "पावर": "power", "प्लांट": "plant", "मिशन": "mission", "रॉकेट": "rocket", "सैटेलाइट": "satellite", "नासा": "NASA", "इसरो": "ISRO", "स्पेस": "space", "बैंक": "bank", "एटीएम": "ATM", "कार्ड": "card", "पेमेंट": "payment", "यूपीआई": "UPI", "ऑनलाइन": "online", "ऑफलाइन": "offline", "एयरपोर्ट": "airport", "फ्लाइट": "flight", "फ्लाइट्स": "flights", "ट्रेन": "train", "स्टेशन": "station", "होटल": "hotel", "फैक्ट": "fact", "शॉकिंग": "shocking", "सीक्रेट": "secret", "मिस्ट्री": "mystery", "प्लान": "plan", "टारगेट": "target", "फोन": "phone", "फ़ोन": "phone", "टीवी": "TV", "रेडियो": "radio", "पब्लिक": "public", "प्राइवेट": "private", "सरकारी": "sarkari",
         # v3.20 space, science & tech spelling fixes
         "यूरोप": "Europe", "एनर्जी": "energy", "सर्वे": "survey", "विज्ञान": "vigyaan",
         "असंभव": "asambhav", "ईंधन": "indhan", "क्वासार": "quasar", "आर्टेमिस": "Artemis",
         "ओरियन": "Orion", "डार्क": "dark", "मैटर": "matter", "सेंसर": "sensor",
         "थर्मल": "thermal", "हाई": "high", "रेजोल्यूशन": "resolution", "रोबोटिक्स": "robotics",
         "स्पेससूट": "spacesuit", "रोवर": "rover", "अंतरिक्ष": "antariksh", "ब्रह्मांड": "brahmaand",
         "गैलेक्सी": "galaxy", "गैलेक्सीज": "galaxies", "टेलीस्कोप": "telescope", "रोबोट्स": "robots",
         "आकाशगंगाओं": "aakaashgangaon", "सैनिकों": "sainikon", "भविष्य": "bhavishya",
         "मीटर": "meter", "प्लेटेड": "plated", "वैज्ञानिकों": "vaigyanikon", "सेंटीग्रेड": "centigrade",
         "सेल्सियस": "Celsius", "माइनस": "minus", "डिग्री": "degree", "टेलीस्कोप": "telescope"}
OVERRIDE = {}      # v3.1: Gemini ka "roman" + entity naam (har video ke liye) – sabse pehle yahi


def word(w):
    core = re.sub(r"[।,!?.\"'“”‘’:;()\-]+$", "", w)
    tail = w[len(core):].replace("।", ".")
    if core in OVERRIDE:
        return OVERRIDE[core] + tail
    if core in FIX:
        return FIX[core] + tail
    if core in LOAN:
        return LOAN[core] + tail
    if core.endswith("िंग") and len(core) > 4:          # ...ing (English) : स्केटिंग -> sketing+ing
        return word(core[:-3]).rstrip("i") + "ing" + tail
    if not re.search(r"[\u0900-\u097F]", core):
        return w.replace("।", ".")
    # 1) split into units: [cons, vowel]  (vowel None = halant, 'A' = inherent a)
    units = []; i = 0; n = len(core)
    while i < n:
        ch = core[i]
        if i + 1 < n and core[i + 1] == NUKTA:
            ch = ch + NUKTA; i += 1
        if ch in C:
            nxt = core[i + 1] if i + 1 < n else ""
            if nxt == HAL: units.append([C[ch], None]); i += 2; continue
            if nxt in M: units.append([C[ch], M[nxt]]); i += 2; continue
            units.append([C[ch], "A"]); i += 1; continue
        if ch in V: units.append(["", V[ch]])
        elif ch in (ANU, CHB): units.append(["n", None])
        elif ch == VIS: units.append(["h", None])
        elif ch in DIG: units.append([DIG[ch], None])
        else: units.append([ch, None])
        i += 1
    # 2) schwa deletion: final inherent a dropped; medial a dropped in V C a C V pattern
    if units and units[-1][1] == "A" and len(units) > 1:
        units[-1][1] = None
    for k in range(1, len(units) - 1):
        if units[k][1] == "A" and units[k - 1][1] not in (None,) and units[k + 1][1] not in (None,) \
                and units[k + 1][0] not in ("", "n", "h"):
            units[k][1] = None
    s = "".join(c + ("a" if v == "A" else (v or "")) for c, v in units)
    s = s.replace("ee", "i").replace("ph", "f")
    if s.endswith("aa") and len(s) > 3: s = s[:-1]
    return s + tail


def to_hinglish(text):
    return " ".join(word(w) for w in text.split())


if __name__ == "__main__":
    for t in ["मंगल ग्रह की धूल इंसानों के लिए खतरनाक हो सकती है।", "नासा के पर्सिवरेंस रोवर ने नई खोज की है।",
              "पहला फैक्ट, कुछ कण सिर्फ 100 नैनोमीटर के हैं।", "इस धूल में परक्लोरेट नाम का केमिकल है।",
              "ऐसे और पागल फैक्ट्स के लिए फॉलो कर लो।", "सोचो जरा, अगर ये धूल एस्ट्रोनॉट के बेस के अंदर आ गई तो?"]:
        print(to_hinglish(t))


def _phon(s):
    s = s.lower()
    for a, b in (("aa", "a"), ("ee", "i"), ("oo", "u"), ("ph", "f"), ("c", "k"), ("q", "k"), ("y", "i"), ("w", "v"),
                 ("z", "j")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z]", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


LABELS = set()


def learn_name(line, label):
    """v3.1: line me Devanagari me likha naam (कैरी मिनाटी) -> sahi English spelling (Carry Minati / CarryMinati).
    Label ko capital/space pe todta hai, 1-3 lagaataar Hindi shabdon se phonetic milaan. Kitne shabd seekhe – lautata hai."""
    import difflib
    parts = [p for p in re.findall(r"[A-Z][a-z0-9]+|[A-Z]+(?![a-z])|[a-z0-9]+", label or "")]
    if not parts: return 0
    if label and " " not in label.strip() and len(parts) > 1:
        LABELS.add(label.strip())                # v3.5: 'Carry Minati' -> captions me 'CarryMinati' (ek shabd)
    key = _phon("".join(parts))
    toks = [re.sub(r"[।,!?.\"'“”‘’:;()\-]+$", "", t) for t in (line or "").split()]
    best = (0.0, None, None)
    for n in (1, 2, 3):
        for i in range(len(toks) - n + 1):
            grp = toks[i:i + n]
            if not all(re.search(r"[ऀ-ॿ]", g) for g in grp): continue
            r = difflib.SequenceMatcher(None, _phon("".join(word(g) for g in grp)), key).ratio()
            if r > best[0]: best = (r, i, n)
    r, i, n = best
    if r < 0.78 or i is None: return 0
    grp = toks[i:i + n]
    # v4.30 FIX: NEVER let learn_name overwrite common Hindi stop-words / FIX / LOAN words
    # (fixes "जी हाँ" -> "Indian Haan" and "कि ट्रेन" -> "Indian Railways" caption corruption!)
    _PROTECTED_HI = {
        "जी", "हाँ", "हां", "कि", "की", "के", "का", "को", "से", "पर", "में", "है", "हैं", "था", "थी", "थे",
        "यह", "वह", "ये", "वो", "इस", "उस", "इन", "उन", "और", "या", "लेकिन", "मगर", "अगर", "तो", "भी",
        "नहीं", "ना", "क्या", "क्यों", "कब", "कैसे", "जब", "तब", "अब", "फिर", "सिर्फ", "बहुत", "सब",
        "एक", "दो", "तीन", "चार", "पांच", "ट्रेन", "रेलवे", "भारत", "भारतीय", "नियम", "काम", "लोग", "बात",
        "दुनिया", "देश", "शहर", "साल", "दिन", "रात", "समय", "जगह", "नाम", "तरीका", "असली", "अनोखे",
    }
    def _is_safe(g):
        return (g not in _PROTECTED_HI) and (g not in FIX) and (g not in LOAN) and len(g) >= 2
    if n == len(parts):
        # Require EVERY paired word to individually match phonetically (prevents mismatched 2-word overrides)
        for g, p in zip(grp, parts):
            if not _is_safe(g):
                return 0
            if difflib.SequenceMatcher(None, _phon(word(g)), _phon(p)).ratio() < 0.58:
                return 0
        for g, p in zip(grp, parts):
            OVERRIDE[g] = p
    elif n == 1:
        if not _is_safe(grp[0]):
            return 0
        OVERRIDE[grp[0]] = "".join(parts) if len(parts) <= 2 else " ".join(parts)
    else:                                    # 2 Hindi shabd, 1 label (CarryMinati): pehla = poora naam ka aadha
        if not all(_is_safe(g) for g in grp):
            return 0
        cut = max(1, round(len(parts) * 1 / n))
        OVERRIDE[grp[0]] = "".join(parts[:cut]) or label
        OVERRIDE[grp[-1]] = "".join(parts[cut:]) or ""
    return n
