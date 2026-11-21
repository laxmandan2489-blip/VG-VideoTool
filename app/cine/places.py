"""Jagah pehchaano: Hindi ya English naam -> (city / state / country) + lat/lon.

Data offline hai (app/cine/data): India ke 36 rajya + 726 zile (official boundary, datameet/Survey of India based),
duniya ke 177 desh (Natural Earth, India ki seema official wali se badli hui).
Shehar list me na ho to zile ka naam, phir internet geocode (OpenStreetMap Nominatim) – ye bhi na mile to None.
"""
import json, re
from functools import lru_cache

from . import DATA

STATE_HI = {
    "राजस्थान": "Rajasthan", "महाराष्ट्र": "Maharashtra", "गुजरात": "Gujarat", "उत्तर प्रदेश": "Uttar Pradesh",
    "मध्य प्रदेश": "Madhya Pradesh", "बिहार": "Bihar", "पंजाब": "Punjab", "हरियाणा": "Haryana", "केरल": "Kerala",
    "तमिलनाडु": "Tamil Nadu", "तमिल नाडु": "Tamil Nadu", "कर्नाटक": "Karnataka", "आंध्र प्रदेश": "Andhra Pradesh",
    "तेलंगाना": "Telangana", "ओडिशा": "Odisha", "उड़ीसा": "Odisha", "पश्चिम बंगाल": "West Bengal", "बंगाल": "West Bengal",
    "असम": "Assam", "झारखंड": "Jharkhand", "छत्तीसगढ़": "Chhattisgarh", "उत्तराखंड": "Uttarakhand",
    "हिमाचल प्रदेश": "Himachal Pradesh", "हिमाचल": "Himachal Pradesh", "जम्मू कश्मीर": "Jammu and Kashmir",
    "जम्मू और कश्मीर": "Jammu and Kashmir", "कश्मीर": "Jammu and Kashmir", "लद्दाख": "Ladakh", "गोवा": "Goa",
    "सिक्किम": "Sikkim", "मणिपुर": "Manipur", "मेघालय": "Meghalaya", "मिजोरम": "Mizoram", "मिज़ोरम": "Mizoram",
    "नागालैंड": "Nagaland", "त्रिपुरा": "Tripura", "अरुणाचल प्रदेश": "Arunachal Pradesh", "अरुणाचल": "Arunachal Pradesh",
    "दिल्ली": "Delhi", "अंडमान": "Andaman and Nicobar Islands", "लक्षद्वीप": "Lakshadweep", "पुडुचेरी": "Puducherry",
    "चंडीगढ़": "Chandigarh",
}

# shehar: english, hindi, state, lon, lat
CITIES = [
    ("Jaipur", "जयपुर", "Rajasthan", 75.79, 26.91), ("Jodhpur", "जोधपुर", "Rajasthan", 73.02, 26.24),
    ("Udaipur", "उदयपुर", "Rajasthan", 73.71, 24.59), ("Jaisalmer", "जैसलमेर", "Rajasthan", 70.91, 26.92),
    ("Bikaner", "बीकानेर", "Rajasthan", 73.31, 28.02), ("Ajmer", "अजमेर", "Rajasthan", 74.64, 26.45),
    ("Kota", "कोटा", "Rajasthan", 75.86, 25.18), ("Pushkar", "पुष्कर", "Rajasthan", 74.55, 26.49),
    ("Mumbai", "मुंबई", "Maharashtra", 72.88, 19.08), ("Pune", "पुणे", "Maharashtra", 73.86, 18.52),
    ("Nagpur", "नागपुर", "Maharashtra", 79.09, 21.15), ("Nashik", "नासिक", "Maharashtra", 73.79, 20.00),
    ("Aurangabad", "औरंगाबाद", "Maharashtra", 75.34, 19.88), ("Delhi", "दिल्ली", "Delhi", 77.21, 28.61),
    ("New Delhi", "नई दिल्ली", "Delhi", 77.21, 28.61), ("Kolkata", "कोलकाता", "West Bengal", 88.36, 22.57),
    ("Darjeeling", "दार्जिलिंग", "West Bengal", 88.26, 27.04), ("Chennai", "चेन्नई", "Tamil Nadu", 80.27, 13.08),
    ("Madurai", "मदुरै", "Tamil Nadu", 78.12, 9.93), ("Coimbatore", "कोयंबटूर", "Tamil Nadu", 76.96, 11.02),
    ("Bengaluru", "बेंगलुरु", "Karnataka", 77.59, 12.97), ("Bangalore", "बैंगलोर", "Karnataka", 77.59, 12.97),
    ("Mysuru", "मैसूर", "Karnataka", 76.64, 12.30), ("Hampi", "हम्पी", "Karnataka", 76.46, 15.34),
    ("Hyderabad", "हैदराबाद", "Telangana", 78.49, 17.39), ("Ahmedabad", "अहमदाबाद", "Gujarat", 72.57, 23.02),
    ("Surat", "सूरत", "Gujarat", 72.83, 21.17), ("Vadodara", "वडोदरा", "Gujarat", 73.18, 22.31),
    ("Rajkot", "राजकोट", "Gujarat", 70.80, 22.30), ("Kutch", "कच्छ", "Gujarat", 69.86, 23.73),
    ("Gandhinagar", "गांधीनगर", "Gujarat", 72.64, 23.22), ("Lucknow", "लखनऊ", "Uttar Pradesh", 80.95, 26.85),
    ("Kanpur", "कानपुर", "Uttar Pradesh", 80.33, 26.45), ("Varanasi", "वाराणसी", "Uttar Pradesh", 82.97, 25.32),
    ("Banaras", "बनारस", "Uttar Pradesh", 82.97, 25.32), ("Agra", "आगरा", "Uttar Pradesh", 78.01, 27.18),
    ("Prayagraj", "प्रयागराज", "Uttar Pradesh", 81.85, 25.44), ("Ayodhya", "अयोध्या", "Uttar Pradesh", 82.20, 26.80),
    ("Mathura", "मथुरा", "Uttar Pradesh", 77.67, 27.49), ("Noida", "नोएडा", "Uttar Pradesh", 77.39, 28.54),
    ("Bhopal", "भोपाल", "Madhya Pradesh", 77.41, 23.26), ("Indore", "इंदौर", "Madhya Pradesh", 75.86, 22.72),
    ("Gwalior", "ग्वालियर", "Madhya Pradesh", 78.18, 26.22), ("Ujjain", "उज्जैन", "Madhya Pradesh", 75.78, 23.18),
    ("Jabalpur", "जबलपुर", "Madhya Pradesh", 79.99, 23.18), ("Khajuraho", "खजुराहो", "Madhya Pradesh", 79.93, 24.85),
    ("Patna", "पटना", "Bihar", 85.14, 25.59), ("Gaya", "गया", "Bihar", 85.00, 24.80),
    ("Nalanda", "नालंदा", "Bihar", 85.44, 25.14), ("Chandigarh", "चंडीगढ़", "Chandigarh", 76.78, 30.73),
    ("Amritsar", "अमृतसर", "Punjab", 74.87, 31.63), ("Ludhiana", "लुधियाना", "Punjab", 75.86, 30.90),
    ("Gurugram", "गुरुग्राम", "Haryana", 77.03, 28.46), ("Gurgaon", "गुड़गांव", "Haryana", 77.03, 28.46),
    ("Shimla", "शिमला", "Himachal Pradesh", 77.17, 31.10), ("Manali", "मनाली", "Himachal Pradesh", 77.19, 32.24),
    ("Dehradun", "देहरादून", "Uttarakhand", 78.03, 30.32), ("Rishikesh", "ऋषिकेश", "Uttarakhand", 78.27, 30.09),
    ("Haridwar", "हरिद्वार", "Uttarakhand", 78.16, 29.95), ("Kedarnath", "केदारनाथ", "Uttarakhand", 79.07, 30.73),
    ("Srinagar", "श्रीनगर", "Jammu and Kashmir", 74.80, 34.08), ("Jammu", "जम्मू", "Jammu and Kashmir", 74.86, 32.73),
    ("Leh", "लेह", "Ladakh", 77.58, 34.15), ("Kochi", "कोच्चि", "Kerala", 76.27, 9.93),
    ("Thiruvananthapuram", "तिरुवनंतपुरम", "Kerala", 76.94, 8.52), ("Munnar", "मुन्नार", "Kerala", 77.06, 10.09),
    ("Bhubaneswar", "भुवनेश्वर", "Odisha", 85.82, 20.30), ("Puri", "पुरी", "Odisha", 85.83, 19.81),
    ("Konark", "कोणार्क", "Odisha", 86.09, 19.89), ("Guwahati", "गुवाहाटी", "Assam", 91.74, 26.14),
    ("Kaziranga", "काजीरंगा", "Assam", 93.36, 26.58), ("Ranchi", "रांची", "Jharkhand", 85.31, 23.34),
    ("Raipur", "रायपुर", "Chhattisgarh", 81.63, 21.25), ("Visakhapatnam", "विशाखापत्तनम", "Andhra Pradesh", 83.22, 17.69),
    ("Tirupati", "तिरुपति", "Andhra Pradesh", 79.42, 13.63), ("Panaji", "पणजी", "Goa", 73.83, 15.49),
    ("Gangtok", "गंगटोक", "Sikkim", 88.61, 27.33), ("Shillong", "शिलांग", "Meghalaya", 91.89, 25.58),
    ("Cherrapunji", "चेरापूंजी", "Meghalaya", 91.73, 25.27), ("Mawsynram", "मासिनराम", "Meghalaya", 91.58, 25.30),
    ("Imphal", "इंफाल", "Manipur", 93.94, 24.82), ("Port Blair", "पोर्ट ब्लेयर", "Andaman and Nicobar Islands", 92.73, 11.62),
    ("Rameswaram", "रामेश्वरम", "Tamil Nadu", 79.31, 9.29), ("Kanyakumari", "कन्याकुमारी", "Tamil Nadu", 77.54, 8.08),
    ("Sriharikota", "श्रीहरिकोटा", "Andhra Pradesh", 80.23, 13.72), ("Pokhran", "पोखरण", "Rajasthan", 71.92, 26.92),
    ("Bhuj", "भुज", "Gujarat", 69.67, 23.25), ("Sundarbans", "सुंदरबन", "West Bengal", 88.90, 21.95),
    ("Ladakh", "लद्दाख", "Ladakh", 77.58, 34.15),
]

COUNTRY_EXTRA_HI = {"अमेरिका": "United States of America", "अमरीका": "United States of America", "चीन": "China",
                    "जापान": "Japan", "रूस": "Russia", "पाकिस्तान": "Pakistan", "नेपाल": "Nepal", "भूटान": "Bhutan",
                    "बांग्लादेश": "Bangladesh", "श्रीलंका": "Sri Lanka", "ब्रिटेन": "United Kingdom", "इंग्लैंड": "United Kingdom",
                    "फ्रांस": "France", "जर्मनी": "Germany", "इटली": "Italy", "मिस्र": "Egypt", "इजिप्ट": "Egypt",
                    "ऑस्ट्रेलिया": "Australia", "कनाडा": "Canada", "ब्राजील": "Brazil", "ब्राज़ील": "Brazil",
                    "दुबई": "United Arab Emirates", "सऊदी": "Saudi Arabia", "ईरान": "Iran", "इजराइल": "Israel",
                    "इज़राइल": "Israel", "अफ्रीका": "", "अंटार्कटिका": "Antarctica", "ग्रीनलैंड": "Greenland",
                    "आइसलैंड": "Iceland", "न्यूजीलैंड": "New Zealand", "मेक्सिको": "Mexico", "पेरू": "Peru",
                    "दक्षिण कोरिया": "South Korea", "उत्तर कोरिया": "North Korea", "कोरिया": "South Korea",
                    "इंडोनेशिया": "Indonesia", "थाईलैंड": "Thailand", "सिंगापुर": "Singapore", "मालदीव": "Maldives",
                    "अफगानिस्तान": "Afghanistan", "यूक्रेन": "Ukraine", "तुर्की": "Turkey", "स्विट्जरलैंड": "Switzerland",
                    "नॉर्वे": "Norway", "स्वीडन": "Sweden", "फिनलैंड": "Finland", "स्पेन": "Spain", "अर्जेंटीना": "Argentina"}


@lru_cache(maxsize=1)
def india():
    return json.loads((DATA / "india_map.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def world():
    return json.loads((DATA / "world_map.json").read_text(encoding="utf-8"))


def _norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower().replace("&", "and"))


@lru_cache(maxsize=1)
def _country_index():
    idx = {}
    for nm, c in world().items():
        for a in [nm] + list(c.get("alt") or []):
            if a: idx[_norm(a) if re.search("[a-zA-Z]", a) else a] = nm
    for hi, en in COUNTRY_EXTRA_HI.items():
        if en: idx[hi] = en
    idx.update({"usa": "United States of America", "us": "United States of America", "america": "United States of America",
                "uk": "United Kingdom", "england": "United Kingdom", "britain": "United Kingdom", "uae": "United Arab Emirates",
                "dubai": "United Arab Emirates"})
    return idx


def _world_name(nm):
    w = world()
    if nm in w: return nm
    for k in w:
        if _norm(k) == _norm(nm): return k
    return None


_HW = {}


def _hi_word(w):
    """Devanagari poora shabd (aage-peeche koi Hindi akshar/matra nahi)."""
    r = _HW.get(w)
    if r is None:
        r = _HW[w] = re.compile(r"(?<![\u0900-\u097F])" + re.escape(w) + r"(?![\u0900-\u097F])")
    return r


def find(text_hi="", text_en="", hint=""):
    """Line me pehli map-laayak jagah. Returns dict ya None.
    {kind: city|district|state|country, name, state, lonlat, country}"""
    hi = f"{hint} {text_hi}"
    en = f"{hint} {text_en}"
    en_n = " " + re.sub(r"[^a-z ]", " ", en.lower()) + " "
    # 1) shehar (Hindi ya English)
    # v3.1: poora shabd mile (substring nahi) aur aam Hindi shabd jo shehar ka naam bhi hain unhe chhodo
    # ("गया" = went, "सागर" = ocean ...). Pehle "हो गया" pe Gaya (Bihar) ka map aa jaata tha.
    toks_hi = set(re.findall(r"[\u0900-\u097F]+", hi))
    AMBIG = {"गया", "सागर", "कोटा", "धार", "अमर", "बस्ती", "मंडी", "सीधी", "राजा", "पाली", "बीड", "दमोह", "जालना"}
    for c_en, c_hi, st, lon, lat in CITIES:
        hit_hi = (c_hi in toks_hi or (" " in c_hi and c_hi in hi)) and c_hi not in AMBIG
        if hit_hi or (c_en.lower() not in ("gaya", "sagar", "kota", "dhar") and
                      re.search(r"\b" + re.escape(c_en.lower()) + r"\b", en_n)):
            return {"kind": "city", "name": c_en, "state": st, "lonlat": (lon, lat), "country": "India"}
    # 2) zila (English naam, 5+ akshar taaki galat match na ho)
    for d in india()["districts"]:
        n = d["n"].lower()
        if len(n) >= 5 and re.search(r"\b" + re.escape(n) + r"\b", en_n):
            return {"kind": "district", "name": d["n"], "state": d["s"], "lonlat": tuple(d["c"]), "country": "India"}
    # 3) rajya
    # v3.16 FIX (log 16 Nov: "बिहार और उत्तर प्रदेश" line pe Uttar Pradesh ka map): pehle lamba naam pehle
    # jaanchte the -> jo rajya line me PEHLE bola gaya wahi chuno (hint / Hindi / English sab me sabse pehla).
    hits = []
    for s_hi in sorted(STATE_HI, key=len, reverse=True):
        # v3.17 FIX (Microsoft video: "भेजने में असमर्थ" pe ASSAM ka map): poora shabd hi mile, shabd ka hissa nahi
        m_ = _hi_word(s_hi).search(hi)
        k = m_.start() if m_ else -1
        if k >= 0 and not any(a <= k < a + n for a, n, _ in hits):
            hits.append((k, len(s_hi), STATE_HI[s_hi]))
    if not hits:
        for st in india()["states"]:
            m = re.search(r"\b" + re.escape(st.lower()) + r"\b", en_n)
            if m: hits.append((m.start(), len(st), st))
    if hits:
        st = min(hits)[2]
        return {"kind": "state", "name": st, "state": st, "lonlat": tuple(india()["states"][st]["c"]), "country": "India"}
    # 4) desh
    idx = _country_index()
    for hi_n in sorted([k for k in idx if not re.search("[a-z]", k)], key=len, reverse=True):
        if hi_n and _hi_word(hi_n).search(hi):
            nm = _world_name(idx[hi_n])
            if nm: return {"kind": "country", "name": nm, "state": "", "lonlat": tuple(world()[nm]["c"]), "country": nm}
    for w_ in re.findall(r"[a-z]+(?: [a-z]+){0,3}", en.lower()):
        pass
    toks = en_n.split()
    for size in (4, 3, 2, 1):
        for i in range(len(toks) - size + 1):
            k = _norm(" ".join(toks[i:i + size]))
            if len(k) >= 4 and k in idx:
                nm = _world_name(idx[k])
                if nm and nm != "India":
                    return {"kind": "country", "name": nm, "state": "", "lonlat": tuple(world()[nm]["c"]), "country": nm}
    if re.search(r"\b(india|bharat)\b", en_n) or "भारत" in hi:
        return {"kind": "country", "name": "India", "state": "", "lonlat": tuple(world()["India"]["c"]), "country": "India"}
    return None


def resolve(name):
    """[map: Jaipur, Rajasthan] jaisa naam -> dict (offline, phir geocode)."""
    if not name: return None
    parts = [p.strip() for p in re.split(r"[,|]", name) if p.strip()]
    r = find(" ".join(parts), " ".join(parts), "")
    if r:
        if r["kind"] in ("state", "country") and len(parts) > 1:      # "X, Rajasthan" – X shayad chhota gaon
            g = _geocode(parts[0] + ", " + ", ".join(parts[1:]))
            if g: return dict(g, name=parts[0].title(), state=r.get("state", ""), kind="city")
        return r
    g = _geocode(name)
    return g


def _geocode(q):
    try:
        import fx
        g = fx.geocode(q)
    except Exception:
        g = None
    if not g: return None
    try:
        lat, lon = float(g[0]), float(g[1])
    except Exception:
        try:
            lat, lon = float(g["lat"]), float(g["lon"])
        except Exception:
            return None
    st = state_at(lon, lat)
    return {"kind": "city", "name": q.split(",")[0].strip().title(), "state": st or "", "lonlat": (lon, lat),
            "country": "India" if st else ""}


def _inside(pt, ring):
    x, y = pt; c = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            c = not c
        j = i
    return c


def state_at(lon, lat):
    for st, d in india()["states"].items():
        b = d["b"]
        if not (b[0] - 0.1 <= lon <= b[2] + 0.1 and b[1] - 0.1 <= lat <= b[3] + 0.1): continue
        if any(_inside((lon, lat), r) for r in d["rings"]):
            return st
    return None
