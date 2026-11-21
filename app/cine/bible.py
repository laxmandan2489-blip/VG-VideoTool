"""STYLE BIBLE – har video ki EK pehchaan (rang, font, grade, motion, transition, sound).

Reference reel (Tomatoes / Smart Business) se seekha:
  * text kam, sirf 1 keyword ek baar me (POISON, REJECT, 30-35%)
  * numbers/headline: condensed bold (Bebas Neue), peela / accent rang
  * naam: Poppins ExtraBold (accent) + DM Serif Display (safed) – do font ka combo
  * typewriter / blur-reveal / tracking-in animation, halka glow
  * poori video ek garam, saturated grade – alag jagah ki photos bhi ek film jaisi
  * zyada tar seedhe cut, transition sirf baat badalne pe

Theme video ke topic se chuni jaati hai, video ke ANDAR nahi badalti.
"""
import json, re
from pathlib import Path

from . import CINE

ASSET_FONTS = CINE.parent.parent / "assets" / "fonts"

FONTS = {   # ASS family name, file
    "head": ("Bebas Neue", "BebasNeue-Regular.ttf"),
    "bold": ("Poppins ExtraBold", "Poppins-ExtraBold.ttf"),
    "semi": ("Poppins SemiBold", "Poppins-SemiBold.ttf"),
    "serif": ("DM Serif Display", "DMSerifDisplay-Regular.ttf"),
    "hindi": ("Mukta ExtraBold", "Mukta-ExtraBold.ttf"),
    "impact": ("Anton", "Anton-Regular.ttf"),
}

# rang: (R,G,B)
THEMES = {
    "warm": {        # khana, kheti, business, India, logon ki kahani (reference jaisa)
        "accent": (255, 214, 10), "accent2": (255, 92, 56), "text": (255, 255, 255),
        "bg1": (24, 16, 12), "bg2": (64, 30, 18), "map_land": (58, 44, 38), "map_line": (120, 96, 84),
        "grade": "eq=contrast=1.07:saturation=1.18:gamma=0.98,colorbalance=rs=0.04:gs=0.01:bs=-0.04:rm=0.02:bm=-0.02:rh=0.03:bh=-0.03",
        "mood": "warm golden-hour, natural sunlight, rich saturated reds and oranges",
    },
    "cosmic": {      # space, physics, tech, AI, future
        "accent": (64, 220, 255), "accent2": (255, 214, 10), "text": (255, 255, 255),
        "bg1": (6, 10, 24), "bg2": (18, 30, 70), "map_land": (24, 38, 70), "map_line": (70, 110, 170),
        "grade": "eq=contrast=1.09:saturation=1.08:gamma=0.97,colorbalance=rs=-0.03:gs=0.0:bs=0.05:rh=0.03:bh=-0.02",
        "mood": "cool cinematic teal-blue, deep shadows, soft rim light",
    },
    "nature": {      # jaanwar, samudra, jungle, sharir (biology)
        "accent": (120, 255, 140), "accent2": (255, 214, 10), "text": (255, 255, 255),
        "bg1": (8, 20, 14), "bg2": (18, 52, 36), "map_land": (30, 58, 44), "map_line": (80, 130, 100),
        "grade": "eq=contrast=1.06:saturation=1.14:gamma=0.98,colorbalance=rs=0.0:gs=0.02:bs=-0.01:rh=0.02:bh=-0.02",
        "mood": "lush natural documentary look, soft daylight, deep greens",
    },
    "dark": {        # khatra, rahasya, itihaas, crime, jung
        "accent": (255, 64, 64), "accent2": (255, 214, 10), "text": (255, 255, 255),
        "bg1": (10, 8, 10), "bg2": (44, 14, 16), "map_land": (46, 34, 36), "map_line": (110, 80, 84),
        "grade": "eq=contrast=1.12:saturation=0.96:gamma=0.95,colorbalance=rs=0.02:gs=-0.01:bs=-0.01:rh=0.02:bh=-0.03",
        "mood": "moody low-key light, high contrast, desaturated with red accents",
    },
}

THEME_WORDS = {
    "cosmic": "space planet nasa galaxy star sun moon mars orbit rocket universe black hole quantum atom physics "
              "electric electron computer ai robot chip gpu technology internet future satellite light speed laser",
    "nature": "animal bird fish shark whale ocean sea forest jungle tree plant insect snake tiger lion elephant "
              "body brain heart blood cell dna bacteria virus human river mountain",
    "dark": "danger deadly poison death kill war crime mystery secret ghost ancient history ruin bomb disaster "
            "prison army murder curse haunted",
    "warm": "food farmer tomato business company money india village market city startup leather crop "
            "factory product price",
}

THEME_HI = {
    "cosmic": "अंतरिक्ष ग्रह तारा सूरज चांद मंगल रॉकेट ब्रह्मांड परमाणु बिजली कंप्यूटर रोबोट",
    "nature": "जानवर पक्षी मछली शार्क व्हेल समुद्र जंगल पेड़ कीड़ा सांप शेर हाथी शरीर दिमाग दिल खून",
    "dark": "खतरनाक खतरा जहर ज़हर मौत रहस्य इतिहास युद्ध जंग अपराध भूत श्राप",
    "warm": "खाना किसान टमाटर बिजनेस कंपनी पैसा भारत गांव बाजार शहर फैक्ट्री",
}


def choose_theme(lines, eng, forced=None):
    if forced in THEMES:
        return forced
    txt_en = " ".join(eng).lower(); txt_hi = " ".join(lines)
    score = {}
    for k, ws in THEME_WORDS.items():
        score[k] = sum(len(re.findall(r"\b" + re.escape(w) + r"s?\b", txt_en)) for w in ws.split())
        score[k] += sum(txt_hi.count(w) for w in THEME_HI[k].split())
    best = max(score, key=lambda k: score[k])
    return best if score[best] > 0 else "warm"


def build(lines, eng, style, work=None):
    """Video ki Style Bible banao (dict). work diya ho to style_bible.json bhi likh do."""
    forced = (style.get("theme") or "").strip().lower()
    forced = {"garam": "warm", "space": "cosmic", "prakriti": "nature", "andhera": "dark", "auto": ""}.get(forced, forced)
    name = choose_theme(lines, eng, forced or None)
    t = dict(THEMES[name])
    b = {
        "theme": name,
        "palette": {k: t[k] for k in ("accent", "accent2", "text", "bg1", "bg2", "map_land", "map_line")},
        "grade": t["grade"],
        "mood": t["mood"],
        "fonts": {k: v[0] for k, v in FONTS.items()},
        "font_files": {k: v[1] for k, v in FONTS.items()},
        "typography": "1 keyword per moment; numbers=Bebas Neue accent; names=Poppins ExtraBold accent + DM Serif white; "
                      "animations: typewriter / blur-in / tracking-in / count-up; soft glow, no heavy outline",
        "motion": "slow push-in on photos, parallax depth, slide-in for new subject, NO random shake",
        "transitions": "mostly hard cuts; xfade (smooth push / zoom-in / blur / circle reveal) only when the story turns; "
                       "light-leak max 1 per video",
        "sound": "different whoosh every transition, soft riser before the reveal, NO forced boom / shutter 'bhat'",
        "ai_photo_suffix": f"photorealistic documentary photograph, {t['mood']}, natural skin and textures, "
                           f"shot on 35mm lens, shallow depth of field, no text, no watermark, not illustration, "
                           f"not 3d render, not cartoon",
    }
    if work:
        try:
            Path(work, "style_bible.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return b


def copy_fonts(dst_dir):
    """ASS (libass) ke liye fonts work/fonts me."""
    import shutil
    dst = Path(dst_dir); dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for _, f in FONTS.values():
        src = ASSET_FONTS / f
        if src.exists() and not (dst / f).exists():
            shutil.copy(src, dst / f); n += 1
    return n


def font_path(kind):
    return ASSET_FONTS / FONTS.get(kind, FONTS["bold"])[1]


def ass_col(rgb, alpha=0):
    r, g, b = rgb
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"
