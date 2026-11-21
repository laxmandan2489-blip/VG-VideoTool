"""v3.1 SCENE PLANNER – har narration line ka poora, validate kiya hua scene plan (structured JSON).

Gemini (jo pehle se search shabd ke liye ek call karta hai, usi call me) line ka matlab, subject, action,
jagah, samay, mood, camera deta hai. Gemini na mile to offline heuristic (Hindi + English shabd) se plan banta hai.
Plan se tay hota hai:
  * kya search karna hai + kya NAHI dikhna chahiye (avoid) -> galat clip reject
  * visual method ki priority (footage / AI photo / Blender 3D template / infographic / kinetic card)
  * camera move, transition, SFX, music intensity, verification criteria
Output: work/scene_plan.json  (har video ke saath, debugging ke liye bhi)
"""
import json, re
from pathlib import Path

FIELDS = ["scene_id", "narration", "semantic", "subject", "secondary", "action", "environment", "time_period",
          "domain", "emotion", "background", "foreground", "camera_angle", "camera_move", "lighting", "palette",
          "depth_layers", "vfx", "motion_graphics", "animation", "transition", "sfx", "music_intensity",
          "caption_timing", "asset_priority", "blender_template", "queries", "generation_prompt",
          "negative_prompt", "avoid", "verify", "start", "end"]

DOMAINS = {
    "space": ("अंतरिक्ष ग्रह तारा तारे सूरज सूर्य चांद चाँद चंद्रमा मंगल बृहस्पति शनि आकाशगंगा ब्रह्मांड नासा रॉकेट उपग्रह ब्लैक "
              "space planet star sun moon mars jupiter saturn galaxy universe nasa rocket satellite orbit astronaut nebula comet asteroid"),
    "ocean": "समुद्र महासागर गहराई मछली व्हेल शार्क जीव पानी ocean sea deep underwater fish whale shark coral jellyfish",
    "biology": ("कोशिका डीएनए जीन शरीर दिमाग दिल खून बैक्टीरिया वायरस कोशिकाएं cell dna gene body brain heart blood "
                "bacteria virus organ neuron"),
    "science": ("वैज्ञानिक विज्ञान परमाणु अणु ऊर्जा प्रयोग भौतिकी रसायन scientist science atom molecule energy experiment "
                "physics chemistry quantum laser electric"),
    "technology": ("कंप्यूटर मोबाइल फोन चिप रोबोट इंटरनेट एआई तकनीक सॉफ्टवेयर computer phone chip robot internet ai "
                   "technology software gadget processor youtube"),
    "history": ("इतिहास इमरजेंसी आपातकाल आजादी स्वतंत्रता अंग्रेजों प्रधानमंत्री चुनाव साल पहले राजा रानी साम्राज्य किला महल युद्ध प्राचीन मुगल अंग्रेज history ancient king queen empire "
                "fort palace war century dynasty medieval"),
    "geography": "देश पहाड़ नदी रेगिस्तान महाद्वीप नक्शा शहर country mountain river desert continent map city volcano",
    "mystery": "रहस्य रहस्यमय राज़ अजीब डरावना भूत गायब mystery secret strange haunted ghost disappeared unknown",
    "money": "पैसा करोड़ लाख रुपये कंपनी बिजनेस अमीर money crore lakh rupees company business rich profit",
    "nature": "जंगल पेड़ जानवर शेर हाथी पक्षी forest tree animal lion elephant bird nature",
    "biography": ("यूट्यूबर एक्टर खिलाड़ी क्रिकेटर नेता चैनल वीडियो youtuber actor player cricketer leader channel "
                  "video creator star"),
}
TEMPLATE_FOR = {"space": "space", "ocean": "underwater", "biology": "cell", "science": "molecule",
                "technology": "technology", "history": "history", "geography": "globe", "mystery": "mystery",
                "money": "infographic", "nature": "abstract", "biography": None, "general": "abstract"}
SUB_TEMPLATES = [("infographic", "सब्सक्राइबर subscribers subscriber व्यूज views मिलियन million बिलियन billion करोड़ लाख "
                                 "प्रतिशत percent % growth ग्रोथ कमाई revenue"),
                 ("technology", "गेमिंग gaming कंप्यूटर computer यूट्यूब youtube स्ट्रीमिंग streaming चिप chip एआई ai "
                                "रोबोट robot सॉफ्टवेयर software इंटरनेट internet"),
                 ("dna", "डीएनए dna gene जीन helix"), ("solar_system", "सौर मंडल solar system planets ग्रहों"),
                 ("planet", "ग्रह planet mars मंगल jupiter बृहस्पति"), ("globe", "पृथ्वी धरती earth globe नक्शा"),
                 ("energy", "ऊर्जा energy power बिजली lightning laser"), ("molecule", "अणु molecule परमाणु atom")]
EMOTIONS = [("shock", "चौंक हैरान यकीन shocking unbelievable shock सच में चौंकाने"),
            ("mystery", "रहस्य राज़ अजीब कोई नहीं जानता mystery secret strange unknown"),
            ("danger", "खतरनाक खतरा मौत जहर ज़हर deadly danger death poison"),
            ("hype", "बूम तेजी अचानक करोड़ों लाखों viral fast boom suddenly million"),
            ("wonder", "अद्भुत सुंदर चमक amazing beautiful glow incredible wonder"),
            ("sad", "दुख अकेला हार sad lonely lost"),
            ("cta", "फॉलो सब्सक्राइब लाइक follow subscribe like")]
CAMERA_FOR = {"space": "orbit", "ocean": "push_in", "biology": "macro_reveal", "science": "macro_reveal",
              "technology": "orbit", "history": "crane_up", "geography": "orbit", "mystery": "push_in",
              "money": "reveal", "nature": "tracking", "biography": "push_in", "general": "push_in"}
TRANSITION_FOR = {"shock": "flash", "mystery": "fade", "danger": "glitch", "hype": "whip", "wonder": "light_leak",
                  "sad": "fade", "cta": "cut", "info": "cut"}
SFX_FOR = {"shock": "boom", "mystery": "riser", "danger": "boom", "hype": "whoosh", "wonder": "shimmer",
           "sad": None, "cta": "pop", "info": None}
MUSIC_FOR = {"shock": 0.8, "mystery": 0.5, "danger": 0.75, "hype": 0.9, "wonder": 0.6, "sad": 0.35, "cta": 0.6,
             "info": 0.5}
LIGHT_FOR = {"space": "hard sun key + blue rim, deep black", "ocean": "volumetric god rays from surface, teal",
             "biology": "soft translucent backlight", "science": "clean studio key + accent rim",
             "technology": "neon rim, emissive grid", "history": "warm golden-hour side light, dust",
             "geography": "daylight from upper left", "mystery": "single spotlight, heavy fog, low key",
             "money": "bright studio, accent glow", "nature": "natural soft daylight",
             "biography": "soft key on subject", "general": "cinematic key + rim"}


def _score(text, words):
    t = text.lower()
    n = 0
    for w in words.split():
        if not w: continue
        if re.match(r"[a-z]", w.lower()):        # English: poora shabd ("cell" != "cancelled")
            n += bool(re.search(r"\b" + re.escape(w.lower()) + r"s?\b", t))
        else:
            n += w in t
    return n


def detect_domain(hi, en):
    txt = f"{hi} {en}"
    sc = {d: _score(txt, w) for d, w in DOMAINS.items()}
    if re.search(r"\b1[6-9]\d\d\b|\b20[0-1]\d\b", txt):
        sc["history"] += 2                       # purana saal -> itihaas (B&W archive look)
    best = max(sc, key=sc.get)
    return best if sc[best] > 0 else "general"


def detect_emotion(hi, en, idx, n):
    txt = f"{hi} {en}"
    if idx == n - 1 and _score(txt, EMOTIONS[-1][1]):
        return "cta"
    for name, words in EMOTIONS:
        if _score(txt, words): return name
    return "shock" if idx == 0 else "info"


def pick_template(domain, hi, en):
    txt = f"{hi} {en}".lower()
    has_num = bool(re.search(r"[0-9०-९]", hi))
    for t, words in SUB_TEMPLATES:
        if t == "infographic" and not has_num:
            continue                                   # 3D chart sirf jab line me sach me number ho
        if any(w.lower() in txt for w in words.split()):
            return t
    if re.search(r"[0-9०-९]", hi) and domain in ("money", "general", "biography"):
        return "infographic"
    return TEMPLATE_FOR.get(domain)


def _priority(domain, has_who):
    if has_who or domain == "biography":
        return ["user_footage", "licensed_photo_of_subject", "licensed_footage", "ai_image_parallax",
                "kinetic_card", "blender_3d"]
    if domain in ("space", "ocean", "biology", "science", "technology", "geography"):
        return ["licensed_footage", "blender_3d", "ai_image_parallax", "local_ai_video", "infographic", "kinetic_card"]
    return ["licensed_footage", "ai_image_parallax", "blender_3d", "local_ai_video", "kinetic_card"]


def heuristic_scene(i, n, hi, en, raw=None, who=None):
    raw = raw if isinstance(raw, dict) else {}
    domain = (raw.get("domain") or "").lower().strip() or detect_domain(hi, en)
    if domain not in DOMAINS and domain != "general": domain = detect_domain(hi, en)
    emotion = (raw.get("emotion") or "").lower().strip() or detect_emotion(hi, en, i, n)
    if emotion not in TRANSITION_FOR: emotion = detect_emotion(hi, en, i, n)
    subj = (raw.get("subject") or raw.get("show") or en or "").strip()
    tpl = raw.get("template") if raw.get("template") else pick_template(domain, hi, en)
    cam = raw.get("camera") or CAMERA_FOR.get(domain, "push_in")
    if emotion == "mystery": cam = "push_in"
    q = [x for x in (raw.get("q") or []) if isinstance(x, str) and x.strip()]
    avoid = [x for x in (raw.get("avoid") or []) if isinstance(x, str) and x.strip()]
    if domain in ("space", "ocean", "biology", "science"):
        avoid += ["cartoon", "text overlay", "unrelated people"]
    return {
        "scene_id": i + 1, "narration": hi, "semantic": raw.get("meaning") or en,
        "subject": subj, "secondary": raw.get("secondary") or [], "action": raw.get("action") or "",
        "environment": raw.get("environment") or "", "time_period": raw.get("time") or "present",
        "domain": domain, "emotion": emotion,
        "background": raw.get("environment") or LIGHT_FOR.get(domain, ""), "foreground": subj,
        "camera_angle": "low hero angle" if emotion in ("shock", "hype") else "eye level",
        "camera_move": cam, "lighting": LIGHT_FOR.get(domain, LIGHT_FOR["general"]),
        "palette": domain, "depth_layers": ["background", "subject", "foreground particles"],
        "vfx": {"mystery": ["fog", "dust"], "danger": ["sparks"], "wonder": ["glow", "particles"],
                "shock": ["zoom punch"], "hype": ["motion streaks"]}.get(emotion, []),
        "motion_graphics": ["number count-up"] if re.search(r"[0-9०-९]", hi) else [],
        "animation": tpl or "footage", "transition": TRANSITION_FOR.get(emotion, "cut"),
        "sfx": SFX_FOR.get(emotion), "music_intensity": MUSIC_FOR.get(emotion, 0.5),
        "caption_timing": "word-level (Whisper / pauses)",
        "asset_priority": _priority(domain, bool(who)),
        "blender_template": tpl, "queries": q[:6],
        "generation_prompt": (f"cinematic documentary shot of {subj}, {raw.get('environment') or ''}, "
                              f"{LIGHT_FOR.get(domain, '')}, realistic, accurate, 9:16, no text").replace(" ,", ","),
        "negative_prompt": "text, watermark, logo, cartoon, deformed, extra limbs, wrong subject, blurry",
        "avoid": sorted(set(avoid))[:8],
        "verify": f"frame must clearly show: {subj}" + (f"; must NOT show: {', '.join(avoid[:4])}" if avoid else ""),
        "who": who or "",
    }


def validate(scene):
    """Saare fields hon, sahi type ke hon. Galat ho to theek karke lautao."""
    s = dict(scene)
    for f in FIELDS:
        if f not in s:
            s[f] = [] if f in ("secondary", "depth_layers", "vfx", "motion_graphics", "asset_priority", "queries",
                               "avoid") else ("" if f not in ("music_intensity", "start", "end") else 0.0)
    for f in ("secondary", "depth_layers", "vfx", "motion_graphics", "asset_priority", "queries", "avoid"):
        if not isinstance(s[f], list): s[f] = [str(s[f])] if s[f] else []
    try: s["music_intensity"] = max(0.0, min(1.0, float(s["music_intensity"])))
    except Exception: s["music_intensity"] = 0.5
    if s["camera_move"] not in ("push_in", "pull_out", "orbit", "crane_up", "reveal", "fly_through", "tracking",
                                "macro_reveal"):
        s["camera_move"] = "push_in"
    return s


def build(lines, eng, sents=None, raw=None, who=None, work=None):
    """lines (Hindi), eng (English 'kya dikhe'), raw: Gemini ka per-line dict. Return list of validated scenes."""
    raw = raw or {}; who = who or {}
    n = len(lines); out = []
    for i, hi in enumerate(lines):
        sc = heuristic_scene(i, n, hi, eng[i] if i < len(eng) else "", raw.get(i), who.get(i))
        if sents and i < len(sents):
            sc["start"] = round(float(sents[i].get("start", 0)), 3)
            sc["end"] = round(float(sents[i + 1]["start"] if i + 1 < len(sents) else sents[i].get("end", 0)), 3)
        out.append(validate(sc))
    _avoid_repeats(out)
    if work:
        try:
            Path(work, "scene_plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return out


def _avoid_repeats(scenes):
    """Lagaataar same camera / transition nahi (repetitive editing)."""
    alt_cam = {"push_in": "reveal", "orbit": "crane_up", "reveal": "push_in", "crane_up": "orbit",
               "macro_reveal": "orbit", "tracking": "push_in", "pull_out": "push_in", "fly_through": "orbit"}
    alt_tr = {"flash": "whip", "whip": "light_leak", "light_leak": "fade", "fade": "cut", "glitch": "flash", "cut": "cut"}
    for k in range(1, len(scenes)):
        if scenes[k]["camera_move"] == scenes[k - 1]["camera_move"]:
            scenes[k]["camera_move"] = alt_cam.get(scenes[k]["camera_move"], "push_in")
        if scenes[k]["transition"] == scenes[k - 1]["transition"] and scenes[k]["transition"] != "cut":
            scenes[k]["transition"] = alt_tr.get(scenes[k]["transition"], "cut")


def palette_for(scene, bible_pal=None):
    base = {"space": ([64, 200, 255], [255, 200, 90], [4, 6, 16]), "ocean": ([40, 255, 220], [80, 160, 255], [2, 16, 34]),
            "biology": ([255, 90, 140], [120, 220, 255], [16, 8, 20]), "science": ([64, 220, 255], [255, 214, 10], [6, 10, 24]),
            "technology": ([40, 230, 255], [160, 90, 255], [4, 8, 16]), "history": ([255, 180, 90], [255, 230, 180], [30, 18, 10]),
            "geography": ([90, 200, 120], [255, 214, 10], [6, 12, 20]), "mystery": ([255, 60, 60], [255, 214, 10], [6, 6, 10]),
            "money": ([255, 214, 10], [80, 255, 140], [10, 10, 14])}.get(scene.get("domain"),
                                                                           ([64, 220, 255], [255, 214, 10], [6, 10, 24]))
    return {"accent": base[0], "accent2": base[1], "bg": base[2]}


def summary(scenes):
    return ", ".join(f"{s['scene_id']}:{s['domain']}/{s['emotion']}/{s['blender_template'] or '-'}" for s in scenes)
