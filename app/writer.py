"""v2.6: Auto script – script.txt me sirf  TOPIC: ...  likho, Gemini poori script likhega.

Script insaan jaisi: bolchaal ki Hindi, chhote vakya, tagda hook, sirf sach facts (Google search se check).
Likhne ke baad script.txt me hi save ho jaati hai (purana topic upar comment me), taaki aap padh/badal sako.
"""
import re, json, datetime
from common import log
from ai import ask, parse_json

STYLE_GUIDE = """You are a top Hindi YouTube Shorts scriptwriter for a fact channel (like the best Indian fact creators).
Write a script about the TOPIC below that sounds 100% like a real Indian guy talking to his friend — NOT like AI.

HOW IT MUST SOUND
- Spoken Hindi in Devanagari, the way people actually talk. Use common English words people say in Hindi
  (scientist, NASA, rover, report, actually) written in Devanagari where natural.
- Short punchy lines, 5 to 13 words each. One idea per line. 14 to 18 lines total (about 50-60 seconds).
- Line 1 = HOOK: a shocking or curiosity line that makes people stop scrolling (a surprising claim, a question,
  or "ये चीज़ ... कर सकती है"). No greetings. Never start with "दोस्तों", "क्या आप जानते हैं", "आज हम".
- Line 2-3: quick context — what happened / who found it.
- Then an open loop like "और सुनो, असली कहानी अब शुरू होती है" or "लेकिन रुको, यहाँ ट्विस्ट है" (vary it).
- Then 3 facts introduced naturally with "पहला", "दूसरा", "लेकिन तीसरा सबसे खतरनाक/हैरान करने वाला है".
- Use real numbers as digits (100, 700 गुना). Make it vivid with one "सोचो..." / "इमैजिन करो..." line.
- Second last line: a satisfying payoff / why it matters.
- Last line: natural follow line, e.g. "ऐसे ही क्रेज़ी फैक्ट्स के लिए फॉलो कर लो।"
- Avoid AI tells: no "अद्भुत", "रोमांचक यात्रा", "आइए जानते हैं", "निष्कर्ष", "यह ध्यान देने योग्य है",
  no fancy shuddh Hindi, no emojis, no hashtags inside lines, no repeated sentence patterns.

FACTS
- Every fact must be TRUE and checkable. Use Google Search. Prefer NASA, ISRO, WHO, journals, big news sites.
- If a number is uncertain, say it simply ("लगभग", "कुछ रिपोर्ट्स के मुताबिक") instead of inventing.

FOR EACH LINE also give "visual": 2-4 English words of stock footage that literally shows that line
(e.g. "human hair closeup", "blood cells", "mars rover dust", "astronaut spacesuit").

OPTIONAL "fx" for a line (max 4 in the whole script, only where it really helps the viewer):
  "map: <English place, region>"   when the line is about a specific real place (city/state/country/sea)
  "label: <short English text>"   a date, time, name or number shown as a red tag (e.g. "30 October", "1:14 PM")
  "news: <short headline> | <source name>"   when the line cites a real report/study (source like NASA, WHO, BBC)
  "gola"   when the line points at something specific in the shot ("ye dekho", "yahi wo jagah")
Return ONLY this JSON (no other text):
{"title_hindi": ["short top line 1", "short top line 2"],
 "lines": [{"text": "...", "visual": "...", "fx": ""}],
 "yt_title": "Hindi title under 70 chars, curiosity, no clickbait lies",
 "yt_description": "3-4 natural Hindi lines about the video",
 "hashtags": ["#...", "#..."],
 "thumb_text": "2-4 word Hindi thumbnail text",
 "sources": ["source name – url", "..."]}
"""


def write_script(topic, key, out_path):
    """Returns dict (script data) or None. Also rewrites out_path (script.txt)."""
    if not key:
        log("   TOPIC ke liye Gemini key chahiye (api keys.txt me GEMINI=...)")
        return None
    log(f"0) Gemini script likh raha hai: {topic}")
    prompt = STYLE_GUIDE + f"\nTOPIC: {topic}\n"
    data = parse_json(ask(key, [prompt], search=True, temperature=0.8, timeout=120))
    if not (isinstance(data, dict) and data.get("lines")):
        log("   (Google search ke saath nahi hua, bina search try kar raha hoon)", show=False)
        data = parse_json(ask(key, [prompt], json_mode=True, temperature=0.8, timeout=120))
    if not (isinstance(data, dict) and data.get("lines")):
        log("   Gemini script nahi likh paya (limit/internet). Thodi der baad try karo.")
        return None
    lines = []
    for l in data["lines"]:
        t = (l.get("text") if isinstance(l, dict) else str(l)) or ""
        t = re.sub(r"\s+", " ", t).strip()
        if not t: continue
        v = (l.get("visual") if isinstance(l, dict) else "") or ""
        f_ = str((l.get("fx") if isinstance(l, dict) else "") or "").strip().strip("[]")
        if f_ and re.match(r"^(map|label|news|gola|bubble|list)\b", f_, re.I):
            t += f" [{f_}]"                              # v2.15: pro effect marker
        lines.append(t + (f" || {v.strip()}" if v.strip() else ""))
    title = data.get("title_hindi") or []
    if isinstance(title, str): title = [title]
    body = [f"# TOPIC (pehle): {topic}",
            f"# Gemini ne likha – {datetime.datetime.now():%d %b %Y %H:%M}. Kuch badalna ho to yahin badlo.",
            "# '||' ke baad wale English shabd = us line pe kya footage dikhe.", ""]
    if title:
        body.append("TITLE: " + " | ".join(x.strip() for x in title[:2] if x.strip()))
    body += lines
    srcs = data.get("sources") or []
    if srcs:
        body += ["", "# FACT CHECK – ye sources dekh lo:"] + [f"# - {s}" for s in srcs]
    out_path.write_text("\n".join(body) + "\n", encoding="utf-8")
    log(f"   script ready: {len(lines)} lines ✓  (script.txt me save)")
    data["_topic"] = topic
    return data


def read_topic(path):
    """script.txt me 'TOPIC:' line ho to topic lauta do."""
    try:
        for ln in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            s = ln.strip()
            if s.upper().startswith("TOPIC:"):
                return s.split(":", 1)[1].strip() or None
    except Exception:
        pass
    return None
