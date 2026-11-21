"""v2.8: "Footage kharab hai, sahi karo" jaisi baat ko pakke badlaavon me badalna."""
import re
from ai import ask_json

STYLE_KEYS = {
    "caption_size": "number 90-160", "caption_jagah": "upar/beech/neeche", "caption_rang": "peela/hara/laal/neela/safed",
    "caption_shabd": "1/2/3", "captions": "haan/nahi", "transition": "haan/nahi", "flash_har_clip": "haan/nahi",
    "visual_badle_har": "seconds 1.5-4", "music_awaaz": "0-40", "sfx_awaaz": "0-100", "awaaz_bhaari": "0-12",
    "ai_speed": "-20..30", "layer": "haan/nahi", "layer_taakat": "0-100", "motion": "haan/nahi",
    "video_fit": "4:5/poora/bhar", "subscribe_size": "1-1.5", "hook_text": "haan/nahi", "zoom": "haan/nahi",
}
VOICE_KEYS = {"ai_speed", "awaaz_bhaari"}


def parse(key, lines, text):
    """Returns dict: bad_lines [idx], all_footage bool, style {k:v}, text_fixes {idx: text}, note str."""
    fb = {"bad_lines": [], "all_footage": False, "style": {}, "text_fixes": {}, "note": text}
    t = text.lower()
    if key:
        res = ask_json(key, [
            "A creator gives feedback on a Hindi YouTube Short made by an automatic tool. Turn it into concrete "
            "edits. Lines are numbered below. If they mention a time (e.g. '12 second pe'), use the line times.\n"
            f"Feedback: {text}\n\nLines:\n" + "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines)) +
            "\n\nStyle settings you may change (name: allowed values): "
            + "; ".join(f"{k}: {v}" for k, v in STYLE_KEYS.items()) +
            "\nReturn ONLY JSON: {\"bad_lines\": [line numbers whose footage must change], "
            "\"all_footage\": true if they complain about footage/clips in general, "
            "\"style\": {setting: value}, \"text_fixes\": [{\"line\": n, \"text\": \"new Hindi line\"}], "
            "\"summary_hindi\": \"one short Hinglish sentence of what you will change\"}"],
            temperature=0.1, timeout=60)
        if isinstance(res, dict):
            for n in res.get("bad_lines") or []:
                try:
                    i = int(n) - 1
                    if 0 <= i < len(lines): fb["bad_lines"].append(i)
                except Exception:
                    pass
            fb["all_footage"] = bool(res.get("all_footage"))
            for k, v in (res.get("style") or {}).items():
                if k in STYLE_KEYS: fb["style"][k] = str(v).lower()
            for x in res.get("text_fixes") or []:
                try:
                    i = int(x["line"]) - 1
                    if 0 <= i < len(lines) and str(x.get("text", "")).strip(): fb["text_fixes"][i] = str(x["text"]).strip()
                except Exception:
                    pass
            fb["note"] = res.get("summary_hindi") or text
            return fb
    # bina Gemini: seedhe shabd pakdo
    for m in re.findall(r"line\s*(\d+)", t):
        i = int(m) - 1
        if 0 <= i < len(lines): fb["bad_lines"].append(i)
    if any(w in t for w in ("footage", "clip", "video kharab", "visual", "fotage")) and not fb["bad_lines"]:
        fb["all_footage"] = True
    if "caption" in t and ("bada" in t or "bade" in t): fb["style"]["caption_size"] = "150"
    if "caption" in t and ("chhota" in t or "chote" in t): fb["style"]["caption_size"] = "110"
    if "flash" in t and ("kam" in t or "band" in t): fb["style"]["flash_har_clip"] = "nahi"
    return fb
