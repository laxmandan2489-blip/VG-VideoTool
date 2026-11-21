"""v3.16 AI APP BRIDGE – bina API ke ChatGPT / Claude / Gemini APP (aapka subscription) se visual + editing plan.

Kyun: aapke paas ChatGPT Go, Claude Pro, Gemini Pro APP hain, API nahi. App ko background me "robot" se chalana
(browser automation) bharosemand nahi hai – login, captcha, UI badalna, aur kuch apps ki sharton ke khilaaf bhi.
Isliye SAAF aur pakka tareeka: COPY-PASTE (30 second ka kaam):

  1. Telegram:  /prompt  likho aur usi message me (agli lines me) apni script daalo.
     (Laptop pe: AI_PLAN_BANAO.bat – script.txt se prompt bana ke clipboard me copy kar deta hai.)
  2. Bot ek lamba PROMPT bhejega. Use copy karke ChatGPT / Claude / Gemini app me paste karo.
  3. App jo JSON jawab de ({"vg_plan": ...}) – use copy karke Telegram bot ko bhej do
     (laptop pe: ai_plan.txt me paste karke save).
  4. Ab wahi script bot ko bhejo – tool har line ke liye AAPKE AI ke bataye search shabd, "kya dikhna chahiye",
     kya NAHI dikhna chahiye, effect aur transition use karega. Plan 3 din tak, usi script ke liye.

Plan na ho to tool pehle jaisa (Gemini key / Groq / offline) chalta hai – kuch rukta nahi.
"""
import json, re, time
from pathlib import Path
from common import TOOL, log

PLAN_FILE = TOOL / "temp" / "ai_plan.json"
PASTE_FILE = TOOL / "ai_plan.txt"
MAX_AGE = 3 * 86400

EFFECTS = ("none", "slow_zoom_in", "slow_zoom_out", "pan", "punch_zoom", "3d_photo", "glow", "shake")
TRANSITIONS = ("cut", "whoosh", "flash", "dissolve", "zoom", "whip")
SFX = ("none", "whoosh", "impact", "riser", "ding", "boom")


def script_lines(text):
    """Script -> lines (make_video.read_script jaisa: khaali, #, TITLE:, LONG/SHORT chhod ke, '||' hint hata ke)."""
    out = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"): continue
        up = s.upper().strip(" .:!")
        if up in ("LONG", "LAMBI", "SHORT", "SHORTS") or up.startswith(("TITLE:", "KEYWORDS:", "TOPIC:", "/PROMPT")):
            continue
        s = s.split("||", 1)[0].strip()
        s = re.sub(r"\[[^\]]{0,80}\]", "", s).strip()           # [map: ..] jaise tag
        if s: out.append(s)
    return out


def build_prompt(lines, title=""):
    """ChatGPT / Claude / Gemini app me paste karne wala prompt."""
    numbered = "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines))
    return (
        "You are the VISUAL DIRECTOR and SENIOR EDITOR for a viral Hindi YouTube Shorts channel (documentary / facts "
        "style, like top Indian explainer reels). Below is a Hindi voice-over script, one numbered line per scene.\n\n"
        "For EVERY line decide exactly what the viewer must SEE on screen so the visual proves what the narrator says "
        "(the right person, the right company, the right place, the right event, the right object, the right action). "
        "My tool will search YouTube, Pixabay, Pexels, Wikimedia and Internet Archive with your search phrases, so:\n"
        "- write search phrases in ENGLISH, 2-6 words, concrete and filmable (e.g. 'Jensen Huang keynote stage', "
        "'NVIDIA H100 GPU close up', 'Patna ghat Chhath devotees sunset'), most specific first, then 1-2 broader backups;\n"
        "- name real people / companies / places exactly (correct spelling) in 'entity';\n"
        "- list what must NOT appear in 'avoid' (wrong person, rival company, unrelated religion/film, cartoons...);\n"
        "- 'visual' = video (real footage, preferred) | photo (only if footage unlikely) | map (place/route) | "
        "text (big number/year/headline);\n"
        f"- 'effect' one of {list(EFFECTS)} – use sparingly, calm/emotional lines get none or slow zoom;\n"
        f"- 'transition' INTO this line, one of {list(TRANSITIONS)} – mostly 'cut', special ones only on topic change "
        "or big reveal;\n"
        f"- 'sfx' one of {list(SFX)} – only where it adds impact, never on every line;\n"
        "- 'text_on_screen' = 0-3 words to show big (a year, number or key word) or empty.\n\n"
        "Also choose 'genre' for the whole video: history | festival | tech | science | news | mystery | person | general.\n\n"
        + (f"Video title: {title}\n\n" if title else "")
        + "SCRIPT:\n" + numbered + "\n\n"
        "Reply with ONLY this JSON (no explanation, no markdown), one object per line, same count and order:\n"
        '{"vg_plan": 1, "genre": "...", "lines": [{"line": 1, "text": "<first 6 words of the Hindi line>", '
        '"show": "<what the viewer sees, 1 sentence>", "entity": "", "visual": "video", '
        '"queries": ["...", "...", "..."], "avoid": ["..."], "effect": "none", "transition": "cut", "sfx": "none", '
        '"text_on_screen": ""}]}'
    )


def _extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t.strip(), flags=re.I).strip()
    t = re.sub(r"```$", "", t).strip()
    a = t.find("{"); b = t.rfind("}")
    if a < 0 or b <= a: return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        try:                                                     # aam galti: aakhri comma
            return json.loads(re.sub(r",\s*([}\]])", r"\1", t[a:b + 1]))
        except Exception:
            return None


def parse(text):
    """Return (plan dict, error str)."""
    j = _extract_json(text or "")
    if not isinstance(j, dict) or not isinstance(j.get("lines"), list) or not j["lines"]:
        return None, "JSON samajh nahi aaya (poora jawab copy karo – { se } tak)"
    out = []
    for k, x in enumerate(j["lines"]):
        if not isinstance(x, dict): continue
        q = [str(s).strip() for s in (x.get("queries") or []) if str(s).strip()][:5]
        out.append({"line": int(x.get("line") or k + 1) if str(x.get("line", "")).isdigit() else k + 1,
                    "text": str(x.get("text") or "")[:120],
                    "show": str(x.get("show") or "")[:200],
                    "entity": str(x.get("entity") or "")[:80],
                    "visual": str(x.get("visual") or "video").lower()[:10],
                    "queries": q,
                    "avoid": [str(s).strip() for s in (x.get("avoid") or []) if str(s).strip()][:5],
                    "effect": str(x.get("effect") or "none").lower(),
                    "transition": str(x.get("transition") or "cut").lower(),
                    "sfx": str(x.get("sfx") or "none").lower(),
                    "text_on_screen": str(x.get("text_on_screen") or "")[:30]})
    if not out:
        return None, "lines khaali"
    return {"genre": str(j.get("genre") or "").lower(), "lines": out, "t": time.time()}, ""


def save(text):
    plan, err = parse(text)
    if not plan: return None, err
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return plan, ""


def _norm(s):
    return re.sub(r"[^\w]+", "", (s or "").lower())


def load_for(sents, work=None):
    """make_video ke liye: {line_index: {...}}. Plan purana / alag script ka ho to {}."""
    try:                                                     # laptop wala tareeka: ai_plan.txt me paste kiya
        if PASTE_FILE.exists() and PASTE_FILE.stat().st_size > 20 and \
                (not PLAN_FILE.exists() or PASTE_FILE.stat().st_mtime > PLAN_FILE.stat().st_mtime):
            p_, e_ = save(PASTE_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            if not p_: log(f"   (ai_plan.txt: {e_})", show=False)
    except Exception:
        pass
    if not PLAN_FILE.exists(): return {}
    try:
        plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if time.time() - float(plan.get("t") or 0) > MAX_AGE:
        return {}
    L = plan.get("lines") or []
    texts = [(s.get("script") or s.get("text") or "") for s in sents]
    out = {}
    # 1) text se milaan (AI ne line ke pehle shabd lautaaye)
    hits = 0
    for x in L:
        nx = _norm(x.get("text"))[:18]
        if len(nx) < 6: continue
        for i, t in enumerate(texts):
            if nx and nx in _norm(t):
                out[i] = x; hits += 1; break
    # 2) ginti barabar ho to kram se
    if hits < max(1, len(texts) // 2):
        if len(L) != len(texts):
            log(f"   (AI plan: {len(L)} lines, script me {len(texts)} – alag script ka lagta hai, chhod diya)", show=False)
            return {}
        out = {i: x for i, x in enumerate(L)}
    if work:
        try:
            (Path(work) / "ai_plan_used.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass
    if plan.get("genre"):
        for x in out.values(): x["_genre"] = plan["genre"]
    return out


if __name__ == "__main__":                       # AI_PLAN_BANAO.bat: script.txt -> prompt (clipboard)
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else TOOL / "script.txt"
    lines = script_lines(src.read_text(encoding="utf-8-sig", errors="replace")) if src.exists() else []
    if len(lines) < 2:
        print("  script.txt me kam se kam 2 lines chahiye."); sys.exit(1)
    pr = build_prompt(lines)
    (TOOL / "ai_prompt.txt").write_text(pr, encoding="utf-8")
    try:
        import subprocess
        subprocess.run(["clip"], input=pr.encode("utf-16-le"), check=False)
        print(f"  ✅ {len(lines)} lines ka prompt CLIPBOARD me copy ho gaya (ai_prompt.txt me bhi).")
    except Exception:
        print("  ✅ prompt ai_prompt.txt me hai – kholo aur copy karo.")
    print("  1) ChatGPT / Claude / Gemini app me Ctrl+V karke bhejo.")
    print("  2) Jo JSON jawab aaye, use ai_plan.txt me paste karke SAVE karo (Notepad abhi khul raha hai).")
    print("  3) Phir video banao – tool khud plan uthayega.")
    if not PASTE_FILE.exists(): PASTE_FILE.write_text("", encoding="utf-8")
    try:
        import os; os.startfile(str(PASTE_FILE))
    except Exception:
        pass
