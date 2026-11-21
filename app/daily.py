"""v2.18: ROZ KA PLAN – ▶️ Aaj shuru karo: 5 video ka target, ChatGPT/Gemini ke liye prompt (5 science scripts),
5 scripts ek message me -> 5 videos, report. + Bot roz seekhne ke liye 2-3 reels maangta hai. + Guide.
"""
import re, json, datetime, random
from pathlib import Path
from common import TOOL, read_style, num

MEM = TOOL / "seekha"
PLAN = TOOL / "temp" / "roz_plan.json"
TOPICS = MEM / "topics_history.json"

AREAS = ["space aur grah", "samundar ki gehraai", "insaan ka sharir aur dimaag", "ajeeb jaanwar", "dinosaur aur purana zamana",
         "dharti ki taaqat (jwalamukhi, toofan, bhookamp)", "kudrat ke ajoobe (pahaad, gufa, registan)",
         "science ki khojein aur technology", "keede-makode aur chhote jeev", "mausam aur aasmaan"]


def today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def target():
    try:
        st = read_style(TOOL / "style.txt")
        return int(num(st, "roz_target", 1, 20)) if st.get("roz_target") else 5
    except Exception:
        return 5


def load_plan():
    try:
        d = json.loads(PLAN.read_text(encoding="utf-8"))
        if d.get("date") == today(): return d
    except Exception:
        pass
    return {"date": today(), "done": 0, "gate": 0, "fail": 0, "asked_learn": False}


def save_plan(d):
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    PLAN.write_text(json.dumps(d), encoding="utf-8")


def mark(kind):
    d = load_plan(); d[kind] = d.get(kind, 0) + 1; save_plan(d); return d


def topics_used(n=40):
    try:
        return json.loads(TOPICS.read_text(encoding="utf-8"))[-n:]
    except Exception:
        return []


def add_topic(script_text):
    t = ""
    for ln in script_text.splitlines():
        s = ln.strip()
        if s.upper().startswith("TITLE:"):
            t = s.split(":", 1)[1].replace("|", " ").strip(); break
    if not t:
        first = [l for l in script_text.splitlines() if l.strip() and not l.strip().startswith(("#", "TITLE"))]
        t = re.sub(r"\[.*?\]|\|\|.*", "", first[0]).strip()[:60] if first else ""
    if not t: return
    lst = topics_used(200); lst.append(t)
    MEM.mkdir(parents=True, exist_ok=True)
    TOPICS.write_text(json.dumps(lst[-200:], ensure_ascii=False), encoding="utf-8")


def prompt_text(n=5, long_mode=False):
    """v3.58: VideoTool-calibrated Master Prompt (Shorts 5-pack ya Long News+Fact Documentary).
    ChatGPT / Gemini me paste karo -> pinpoint '||' stock & '|| AI:' visual hints ke saath ready scripts milengi."""
    if long_mode:
        return MASTER_PROMPT_LONG
    return MASTER_PROMPT.replace("{N}", str(max(1, int(n or 5))))


MASTER_PROMPT = """MERA TOPIC (1 se 5 topic likho, ya "AUTO" likho to khud 5 viral trending topics chuno):
<<< yahan apna topic likho (ya AUTO rehne do) >>>

You are India's #1 viral Hindi YouTube Shorts scriptwriter for my channel "The Viral Gyaan" (science, space, deep ocean, mystery, world news facts, history, technology).
My automated VideoTool reads every Hindi line, speaks it with AI voice, and picks visuals STRICTLY from the English visual hint after "||".
Write {N} complete, high-retention Hindi Shorts scripts (if topics are listed above, write 1 per topic; if "AUTO", pick {N} mind-blowing, 100% true, verifiable trending fact topics).

STRICT SCRIPT RULES (40-55 sec, 14-18 SHORT micro-beat lines per script, 5-9 words per line — ONE single visual idea/emotion per line!):
0. MICRO-BEAT RULE (CRITICAL FOR ANY TOPIC): NEVER combine two contrasting ideas in one line! Split them into two short lines so EACH emotion/object gets its OWN exact visual (e.g., Line A: "इसके पीछे पैसे की कमी नहीं है।" || stacks of cash money closeup  ->  Line B: "बल्कि प्रकृति की अजीब ताकत है।" || violent storm waves crashing ocean).
1. HOOK (Line 1): Shocking/curious hook in first 2 seconds. NEVER start with "दोस्तों", "क्या आप जानते हैं", "आज हम बात करेंगे".
2. CONTEXT (Lines 2-3): Clear who / what / where with a concrete visual.
3. STAT / NUMBER LINE (at least 1 line): Include a real big number with unit (e.g. "2688 किलोमीटर", "90%", "500 करोड़") — my tool turns this into an animated Stat Counter Card!
4. YEAR / PROOF LINE (at least 1 line): Include a real year (e.g. "साल 1992 में") or official report/study — my tool turns this into a yellow-highlighted News/Archive Card!
5. TWIST / OPEN LOOP (Line 5 or 6): Start with "लेकिन चौंकाने वाली बात यह है..." or "पर असली राज़..." — my tool triggers a dramatic 0.9s music silence drop + reaction!
6. CLIMAX & PAYOFF (Lines 7-11): Escalating facts, strongest reveal near the end.
7. CTA (Last line): "ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।" (NO "||" on this last line!)

LANGUAGE: Natural spoken Hindi in Devanagari (friendly, punchy, conversational). Common English words can stay in Devanagari or simple English (NASA, Point Nemo, AI). NO emojis, NO hashtags, NO markdown bolding (**), NO numbering (1., 2.), NO "FACT CHECK:" footer.

VISUAL HINT RULES (MOST IMPORTANT — FOLLOW 100%):
After EVERY spoken line (except the last CTA line), add " || " followed by an English visual hint using ONE of these two exact formats:

A) REAL STOCK VIDEO (use for 70-80% of lines):
   Format: || <3 to 5 concrete filmable English words>
   - Describe ONLY physical things a real camera can film: [subject] + [action/place] + [shot type].
   - GOOD: "deep ocean waves aerial view", "satellite orbiting earth space", "volcano lava erupting night", "scientist laboratory microscope closeup", "fighter jet flying clouds", "snowy mountain peak drone shot"
   - BAD (NEVER write these): abstract words ("shocking secret", "amazing fact", "mystery", "impossible"), long sentences, text/logos, "random", or unknown people when the line is not about a person.
   - If the line is about a specific famous real person, write their exact full name + setting (e.g. "Albert Einstein blackboard portrait", "Elon Musk rocket launch stage").

B) CUSTOM AI CINEMATIC SCENE (use for 2-4 lines per script where real stock footage DOES NOT EXIST — e.g. sunken spaceship underwater, dinosaur asteroid impact, inside a black hole, futuristic city, microscopic battle):
   Format: || AI: <8 to 14 vivid visual English words, cinematic realistic documentary style>
   - GOOD: "AI: sunken rusted satellite resting on dark deep ocean floor dramatic underwater light rays"
   - GOOD: "AI: glowing asteroid crashing into prehistoric earth ocean dramatic fiery shockwave"

OPTIONAL TAGS (put at END of Hindi line, right BEFORE "||"):
- [map: Place Name, Country] -> use on max 1 geography line per script for an animated 3D map zoom!

OUTPUT FORMAT (STRICT — copy-paste ready for my Telegram Bot, NOTHING extra before or after):
Separate multiple scripts with a single line containing only ====

TITLE: <2-4 crisp Hindi/Hinglish words> | <2-4 hook words>
<line 1> || <3-5 concrete stock words OR AI: vivid scene>
<line 2> [map: Place, Country] || <3-5 concrete stock words>
...
ऐसे ही चौंकाने वाले फैक्ट्स के लिए अभी सब्सक्राइब करें और अगली वीडियो देखना मत भूलना।
====
TITLE: <Script 2 title> | <hook>
...
"""


MASTER_PROMPT_LONG = """MERA TOPIC (Long News + Fact Documentary Video):
<<< yahan apna topic ya breaking news + fact likho >>>

You are India's #1 Hindi Long-Form News & Fact Documentary scriptwriter (Dhruv Rathee / Nitish Rajput / Mohak Mangal style) for "The Viral Gyaan".
My automated VideoTool renders 16:9 documentary videos in calm 5-second pacing with chapters, yellow-marker News/Report cards, Stat Counter cards, and pinpoint visuals from your "||" hints.

STRUCTURE (3-6 minutes, 28-45 lines, 12-18 words per line, divided into 3-5 chapters using "## Chapter Name"):
- ## शुरुआत (Strong curiosity hook + why this news/fact matters today, 5-6 lines)
- ## असली कहानी (Timeline, background, real dates/years & official reports/court/government facts)
- ## चौंकाने वाले आंकड़े (Key numbers, %, ₹/crore/km stats — triggers Stat Counter Cards!)
- ## बड़ा असर और निष्कर्ष (What it means for common people + calm takeaway + clean subscribe CTA)

VISUAL HINT RULES (CRITICAL — EVERY LINE EXCEPT LAST CTA LINE MUST HAVE "||"):
- REAL STOCK FOOTAGE (75% lines): || <3-5 concrete filmable English words> (e.g. "indian parliament building exterior", "stock market screen red graph", "cargo ship ocean aerial", "supreme court building architecture").
- IMPOSSIBLE / EXPLAINER / RECONSTRUCTION SCENES (25% lines): || AI: <8-14 vivid realistic documentary words> (e.g. "AI: dark submarine cable glowing on deep ocean floor cinematic documentary").
- Put [map: City or Country] at the end of 1-2 geography lines (before "||") for animated maps.
- Include real years (e.g. 2024, 1991) and words like "रिपोर्ट", "सर्वे", "सरकार", "अदालत", "रिसर्च" on proof lines so my tool auto-triggers yellow-highlighter News Brief cards!
- NO emojis, NO hashtags, NO markdown bold (**), NO numbering, NO extra commentary outside the script.

OUTPUT EXACTLY THIS:
TITLE: <crisp documentary title> | <hook subtitle>
## शुरुआत
<line 1> || <visual hint>
...
## असली कहानी
<line> || <visual hint>
...
ऐसे ही गहरे रिसर्च वाले न्यूज़ और फैक्ट वीडियो के लिए चैनल को सब्सक्राइब ज़रूर करें।
"""

def split_scripts(text):
    """ChatGPT ka jawab -> alag scripts. ==== / ---- / "Script 2" se todta hai. [] agar ek hi script."""
    t = text.replace("\r", "")
    t = re.sub(r"\*\*|__|```[a-z]*", "", t)
    parts = re.split(r"\n\s*(?:={3,}|-{4,}|#{0,3}\s*(?:script|स्क्रिप्ट|video)\s*\d+\s*[:.)-]?)\s*\n", "\n" + t + "\n",
                     flags=re.I)
    out = []
    for p in parts:
        lines = []
        for ln in p.splitlines():
            s = ln.strip()
            if not s: continue
            if re.match(r"^(?:script|स्क्रिप्ट|video)\s*\d+\s*[:.)-]?\s*$", s, re.I): continue
            lines.append(s)
        spoken = [l for l in lines if re.search(r"[\u0900-\u097f]{3}", l) and not l.upper().startswith(("TITLE", "- "))]
        if len(spoken) >= 5:
            out.append("\n".join(lines))
    return out if len(out) >= 2 else []


LEARN_ASK = [
    ("transitions", "jinme ACHHE TRANSITIONS hon (ek shot se doosre me jaana – whoosh, zoom, swipe)"),
    ("motion", "jinme MOTION / 3D effects hon (ghoomti photo, 3D text, camera move)"),
    ("captions", "jinke CAPTIONS (bolte shabd) bahut achhe dikhte hon"),
    ("sound", "jinka SOUND DESIGN tagda ho (whoosh, boom, ding sahi jagah)"),
    ("effects", "jinme koi NAYA EFFECT ho jo aapne pehle nahi dekha"),
    ("tutorial", "koi EDITING TUTORIAL (CapCut / Premiere / After Effects) ka chhota hissa"),
    ("hook", "jinka SHURUAAT (pehle 3 sec) bahut pakad wali ho"),
]


def learn_message():
    k = datetime.datetime.now().timetuple().tm_yday % len(LEARN_ASK)
    cat, desc = LEARN_ASK[k]
    week = 0
    try:
        mem = json.loads((MEM / "style_yaad.json").read_text(encoding="utf-8"))
        cut = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        week = sum(1 for m in mem if str(m.get("time", "")) >= cut)
    except Exception:
        pass
    newe = 0
    try:
        newe = len([l for l in (MEM / "naye_effects.txt").read_text(encoding="utf-8").splitlines() if l.strip()])
    except Exception:
        pass
    return (f"🧠 Aaj seekhne ke liye mujhe 2-3 reels bhejo {desc}.\n"
            "Har reel ke caption me likho:  seekho\n"
            f"(Is hafte {week} reels seekhi ✅" + (f" • {newe} naye effects ki list bani – Claude ko bhejni hai" if newe else "") +
            ")\nAaj nahi? Koi baat nahi – kal phir poochhunga.")


GUIDE = """📖 VG BOT – GUIDE

▶️ ROZ KA KAAM (10-15 min aapka):
1. Neeche "▶️ Aaj shuru karo" dabao
2. Bot jo PROMPT bheje use poora copy karo -> ChatGPT ya Gemini me paste
3. ChatGPT ka POORA jawab copy karke bot ko EK message me bhejo (5 scripts, ==== se alag)
4. Bot 5 videos ek-ek karke banayega aur bhejega (Drive me bhi) – laptop charger pe + chalu rakho
5. Best 3 upload karo. Bot aakhir me report deta hai (kitni bani / kitni ruki)

🧠 BOT KO SIKHANA:
• Koi achhi reel -> bot ko bhejo, caption: seekho  (sirf sound: sound nikalo)
• Naya effect dikhe to bot demo bhejega -> ✅ Rakho / ❌ Hatao
• /style – kya seekha   /effects – motion effects   /style_bhool – bhool jao

✏️ VIDEO SUDHAAR: video ke neeche buttons (Footage sahi karo / Naya thumbnail) ya likho "line 3 ki clip badlo"

⚙️ SETTING: "setting: captions bade karo"  ya seedha  "setting: transition_sound whoosh"
   /settings – abhi ki settings   /wapas_setting – ulta karo

⛔ QUALITY GATE: kharab video nahi bhejta – 🔁 Dobara try / 📤 Phir bhi bhejo
🎙️ Gemini awaaz na mile: bot poochhta hai – baad me / Microsoft awaaz

💾 BACKUP: apne-aap (har update + roz) -> G:\\My Drive\\VG Backup.  /backup  /backup_status
🔄 UPDATE: Claude ki ZIP bot ko bhejo (caption: update).  /purana = pichhla version
🩺 Dikkat: /health  /log (Claude ko bhejo)  /rok (video roko)"""
