"""v3.17 BRAND / PRODUCT SENSE – English shabd jinka doosra aam matlab bhi hai.

User ki video (16 Nov, "Microsoft outage"): line "Outlook, Teams aur Copilot jaise products me pareshaani" pe
Red Bull AIR RACE ka plane aur aag bujhaane wala hawai jahaz aaya – kyunki search/AI aankh ne "Copilot" = hawai
jahaz ka co-pilot samjha. "Teams" = khel ki team, "Outlook" = nazara, "Windows" = khidki, "Apple" = phal ...
Yahan har aise shabd ka SAHI (tech/brand) matlab + search shabd + kya NAHI dikhna chahiye.
Sirf tab lagta hai jab script me us brand ka context ho (company / app / software / phone / AI ...).
"""
import re

# naam: (pehchaan regex (Hindi + English), sahi search shabd, CLIP ke liye 'galat' cheez, context jo chahiye)
SENSES = {
    "copilot":   (r"(copilot|को-?पायलट|कोपायलट)", ["Microsoft Copilot AI app screen", "Copilot AI assistant laptop"],
                  "an airplane, aircraft cockpit or pilot", "microsoft|ai|app|software|windows|office|एआई|माइक्रोसॉफ्ट"),
    "outlook":   (r"(outlook|आउटलुक)", ["Microsoft Outlook email inbox screen", "Outlook email app laptop"],
                  "a scenic landscape view", "microsoft|email|mail|office|ईमेल|माइक्रोसॉफ्ट"),
    "teams":     (r"(\bteams\b|टीम्स)", ["Microsoft Teams video meeting screen", "Teams video call laptop office"],
                  "a sports team playing a match", "microsoft|meeting|office|call|माइक्रोसॉफ्ट|मीटिंग"),
    "windows":   (r"(\bwindows\b|विंडोज़?)", ["Windows 11 computer screen", "Windows laptop desktop screen"],
                  "glass windows of a building", "microsoft|computer|laptop|pc|software|कंप्यूटर|माइक्रोसॉफ्ट|लैपटॉप"),
    "office":    (r"(microsoft 365|office 365|ऑफिस 365|माइक्रोसॉफ्ट 365)", ["Microsoft 365 apps on laptop screen"],
                  "", "microsoft|माइक्रोसॉफ्ट"),
    "azure":     (r"(azure|एज़्योर|अज़ूर)", ["Microsoft Azure data center servers"], "a blue sky or sea", "microsoft|cloud|क्लाउड"),
    "edge":      (r"(microsoft edge|एज ब्राउज़र)", ["Microsoft Edge browser screen"], "", ""),
    "apple":     (r"(\bapple\b|एप्पल|ऐपल)", ["Apple iPhone and Mac products", "Apple Store logo"],
                  "an apple fruit", "iphone|mac|ipad|company|कंपनी|आईफोन|टिम कुक|tim cook"),
    "amazon":    (r"(amazon|अमेज़न|अमेजन)", ["Amazon warehouse delivery boxes", "Amazon logo office"],
                  "the amazon rainforest or river", "delivery|shopping|company|कंपनी|ऑनलाइन|jeff|बेजोस|aws"),
    "meta":      (r"(\bmeta\b|मेटा)", ["Meta Facebook Instagram apps phone", "Meta headquarters logo"], "",
                  "facebook|instagram|whatsapp|zuckerberg|ज़करबर्ग|फेसबुक|इंस्टाग्राम|company|कंपनी"),
    "x":         (r"(\bx\.com\b|ट्विटर|twitter)", ["X Twitter app on phone screen"], "a bird", ""),
    "tesla":     (r"(tesla|टेस्ला)", ["Tesla electric car driving", "Tesla factory"], "a portrait of Nikola Tesla",
                  "car|elon|musk|मस्क|कार|company|कंपनी"),
    "oracle":    (r"(oracle|ओरेकल)", ["Oracle company office logo"], "a fortune teller", "company|कंपनी|software|database"),
    "python":    (r"(python|पायथन)", ["Python code on computer screen"], "a python snake",
                  "code|coding|programming|कोडिंग|प्रोग्रामिंग|language"),
    "java":      (r"(\bjava\b|जावा)", ["Java code on computer screen"], "coffee or an island", "code|coding|programming|कोडिंग"),
    "chrome":    (r"(chrome|क्रोम)", ["Google Chrome browser screen"], "shiny chrome metal", "google|browser|गूगल|ब्राउज़र"),
    "galaxy":    (r"(samsung galaxy|सैमसंग गैलेक्सी)", ["Samsung Galaxy smartphone"], "a galaxy in space", ""),
    "nvidia":    (r"(nvidia|एनवीडिया|एनविडिया)", ["NVIDIA GPU chip close up", "NVIDIA headquarters logo"],
                  "", ""),
    "jaguar":    (r"(jaguar|जगुआर)", ["Jaguar luxury car"], "a jaguar animal", "car|कार|tata|टाटा|motors"),
    "shell":     (r"(\bshell\b|शेल कंपनी)", ["Shell petrol station logo"], "a sea shell", "oil|petrol|company|कंपनी|तेल"),
    "outage":    (r"(outage|आउटेज|आउटेज)", ["error message on laptop screen", "office workers frustrated computer down",
                                             "server room red warning lights"], "", ""),
}


def detect(text_hi="", text_en="", whole_script=""):
    """Line me kaunse ambiguous brand shabd hain (script ke context ke saath). Return list of sense names."""
    t = f"{text_hi} {text_en}".lower()
    ctx = f"{whole_script} {t}".lower()
    out = []
    for name, (pat, _, _, need) in SENSES.items():
        if re.search(pat, t, re.I) and (not need or re.search(need, ctx, re.I)):
            out.append(name)
    return out


def queries(senses):
    q = []
    for s in senses:
        q += SENSES[s][1]
    return list(dict.fromkeys(q))


def negatives(senses):
    return [(f"galat-matlab:{s}", SENSES[s][2]) for s in senses if SENSES[s][2]]


def fix_query(q, senses):
    """'copilot plane' jaisi query me brand ka naam saaf karo (Microsoft Copilot)."""
    for s in senses:
        if s == "copilot" and re.search(r"\bco-?pilot\b", q, re.I) and "microsoft" not in q.lower():
            q = re.sub(r"\bco-?pilot\b", "Microsoft Copilot app", q, flags=re.I)
        if s == "teams" and re.search(r"\bteams?\b", q, re.I) and "microsoft" not in q.lower():
            q = re.sub(r"\bteams?\b", "Microsoft Teams app", q, flags=re.I)
        if s == "outlook" and re.search(r"\boutlook\b", q, re.I) and "microsoft" not in q.lower():
            q = re.sub(r"\boutlook\b", "Microsoft Outlook email", q, flags=re.I)
    return q
