"""v3.1 FALLBACK VISUALS – jab kisi line ki sahi (jaanchi hui) footage na mile.

Order (har line alag, kabhi doosri line ki clip shift nahi hoti):
  0. v3.4: video ka MUKHYA insaan/brand hai (jaise CarryMinati) -> USI ki nayi clip (official channel, naya hissa)
     ya usi ki photo (alag crop, padosi line pe nahi). Text card / 3D se pehle hamesha asli subject.
  1. local / remote AI video (FreeVideo via ComfyUI) – sirf agar server + workflow mile
  2. Blender procedural 3D scene – v3.4 se DEFAULT BAND (style.txt blender3d = haan karne pe hi)
  3. animated kinetic card (cine.cards – count-up / tracking-in keyword, chalte particles) – static photo NAHI
"""
import re
from pathlib import Path
from common import log, yes, num


HI_STOP = set("""है हैं था थी थे हो का की के को में मे से पर और या यह ये वह वो इस उस इसके उसके इसकी उसकी इसे उसे एक
कि जो जब तक भी ही तो ना नहीं न आप हम मैं तुम अपने अपनी अपना सब कुछ कोई किसी लिए साथ बाद पहले अब आज बहुत ऐसा ऐसी ऐसे
क्या क्यों कैसे कहाँ जाता जाती जाते होता होती होते करता करती करते रहा रही रहे गया गई गए बना बनी बने सकता सकती दिया
वाले वाली वाला अंदर बाहर ऊपर नीचे खास""".split())


def key_phrase(line):
    """Offline: line ka sabse 'bhaari' shabd (number > lamba naam/sangya), stopwords chhod ke – kinetic card ke liye."""
    import re as _re
    words = [w.strip("।,.!?\"'“”()") for w in line.split()]
    num = [w for w in words if _re.search(r"[0-9०-९]", w)]
    if num:
        k = words.index(num[0]); return " ".join(words[k:k + 2])
    cand = [w for w in words if w and w not in HI_STOP and len(w) >= 3]
    if not cand: return " ".join(words[:2])
    verb = ("ती", "ते", "ता", "ना", "ने", "गा", "गी", "या", "ये")       # kriya (verb) kam pasand – sangya behtar
    best = max(cand, key=lambda w: len(w) - (4 if w.endswith(verb) else 0) + (2 if cand.index(w) < 3 else 0))
    return best


def _need(found, i, nl, sents, last_follow_skip):
    its = found[i][0] if found[i] else []
    if its: return False
    if last_follow_skip and i == nl - 1 and re.search(r"(फॉलो|फोलो|सब्सक्राइब|subscribe|follow)",
                                                     (sents[i].get("script") or sents[i]["text"]).lower()):
        return False                       # aakhri follow line: pichhli clip + subscribe (jaan-boojh ke)
    return True


def _urls(found, j):
    if 0 <= j < len(found) and found[j]:
        return {str(it.get("url") or it.get("path")) for it in found[j][0]}
    return set()


def subject_footage(i, found, sents, keys, main):
    """v3.4: mukhya insaan/brand ki NAYI clip (official channel) ya uski photo (kam lagi hui, padosi line pe nahi)."""
    if not main:
        return None
    import sources
    try:
        import entity
        ent = entity.resolve(main) or {}
    except Exception:
        ent = {}
    label = ent.get("label") or main
    plan = sources.RAW_PLAN.get(i) or {}
    kw = [str(plan.get(k) or "") for k in ("query", "show", "meaning", "action") if plan.get(k)]
    yk = keys.get("YOUTUBE") or keys.get("YOUTUBEAPI") or keys.get("YOUTUBEAPIKEY")
    if yk:
        try:
            import yt_clips
            got = yt_clips.find(kw[0] if kw else label, yk, 1, "", (), prefer_channel=label, line_kw=kw,
                                channel_ids_=ent.get("yt") or ())
            if got:
                return dict(got[0], entity=label)
        except Exception as e:
            log(f"   (subject clip skip: {e})", show=False)
    if not ent or ent.get("type") not in ("person", "brand"):
        return None
    try:
        med = [c for c in entity.media(ent, 6) if c.get("kind") == "image"]
    except Exception:
        med = []
    near = _urls(found, i - 1) | _urls(found, i + 1)
    med = [c for c in med if c["url"] not in near]
    if not med:
        return None
    with sources._lock:
        c = min(med, key=lambda c: sources.ENT_COUNT.get(c["url"], 0))
        nuse = sources.ENT_COUNT.get(c["url"], 0)
        if nuse >= 4:
            return None                                       # ek photo 4 se zyada baar kabhi nahi
        sources.ENT_COUNT[c["url"]] = nuse + 1
    path = sources.download(c)
    if not path:
        return None
    return {"kind": "image", "path": path, "url": c["url"], "credit": c.get("credit", ""),
            "src": f"{ent['type']}: {label}", "hero": True, "entity": label, "etype": ent["type"], "role": c.get("role"),
            "desc": (ent.get("desc") or "")[:46], "crop_v": nuse + 1}


def fill(found, sents, spans, scenes, style, keys, work, W, H, fps=30, keyw=None, last_follow_skip=True, main=None):
    keyw = keyw or {}
    nl = len(sents); src = {}
    if main is None:
        try:
            import sources as _s0
            main = _s0.MAIN.get("name")
        except Exception:
            main = None
    mode = (style.get("blender3d") or "nahi").strip().lower()
    bmax = int(num(style, "blender_max", 0, 20)) if style.get("blender_max") else 4
    blender_ok = mode == "haan"                          # v3.4: 3D sirf jab user khud "haan" likhe
    eng = None
    if blender_ok:
        try:
            from cine import blender_engine as eng
            if not eng.find_blender() and not __import__("os").environ.get("VG_BPY_PYTHON"):
                log("   (Blender nahi mila – 3D fallback band. INSTALL_BLENDER_SUPPORT.bat chalao)", show=False)
                eng = None
        except Exception as e:
            log(f"   (Blender engine load nahi hua: {e})", show=False); eng = None
    ai_ok = False
    if yes(style.get("ai_video", "auto")) or style.get("ai_video", "auto") == "auto":
        try:
            import local_ai
            ai_ok, _why = local_ai.available(keys)
        except Exception:
            ai_ok = False
    pal_b = None
    try:
        from cine import bible
        pal_b = bible.build([s.get("script") or s["text"] for s in sents], [sc.get("subject", "") for sc in scenes or []],
                            style)["palette"]
    except Exception:
        pal_b = {"accent": (255, 214, 10), "accent2": (255, 92, 56), "text": (255, 255, 255),
                 "bg1": (24, 16, 12), "bg2": (64, 30, 18)}
    used_b = 0; n_cards = [0]
    for i in range(nl):
        if not _need(found, i, nl, sents, last_follow_skip):
            continue
        st, en, _k = spans[i]
        dur = max(1.0, en - st + 0.2)
        frames = max(2, int(round(dur * fps)))
        sc = scenes[i] if scenes and i < len(scenes) else {}
        out = Path(work) / "shots" / f"fb_{i:02d}.mp4"
        item = None
        if main and not re.search(r"(फॉलो|सब्सक्राइब|subscribe|follow)", (sents[i].get("script") or sents[i]["text"]).lower()):
            item = subject_footage(i, found, sents, keys, main)
            if item:
                log(f"   line {i+1}: {main} ki aur footage lagayi ({item['src']})", show=False)
        if item is None and ai_ok and sc:
            try:
                import local_ai
                r = local_ai.generate(sc.get("generation_prompt") or sc.get("subject", ""), out, dur, 576, 1024,
                                      negative=sc.get("negative_prompt", ""), keys=keys, log=log)
                if r:
                    item = {"kind": "video", "path": Path(r), "credit": "AI video (local FreeVideo/ComfyUI)",
                            "src": "ai video"}
            except Exception as e:
                log(f"   (AI video skip: {e})", show=False)
        try:                                            # v3.1: naam wala insaan/brand – free photo nahi mili -> NAME CARD
            import sources as _src
            ent = _src.NEED_NAMECARD.get(i)
        except Exception:
            ent = None
        if item is None and ent:
            try:
                import hero
                nout = Path(work) / "shots" / f"name_{i:02d}.mp4"
                it_ = {"namecard": True, "entity": ent["label"], "desc": (ent.get("desc") or "")[:46]}
                if hero.render(it_, dur, nout, W, H, style, fps):
                    item = {"kind": "video", "path": nout, "credit": "", "src": f"name card: {ent['label']}",
                            "whole": True, "ss": 0.0}
            except Exception as e:
                log(f"   (name card skip: {e})", show=False)
        tpl = sc.get("blender_template")
        if tpl == "abstract" and mode != "haan":
            tpl = None                    # v3.1: line ka asli 3D roop nahi -> abstract gola nahi, kinetic card behtar
        if item is None and eng and tpl and used_b < bmax and eng.STATE.get("timeouts", 0) == 0:
            log(f"   line {i+1}: sahi footage nahi mili – Blender 3D scene bana raha hoon ({tpl}, {sc.get('camera_move')})")
            try:
                from scene_plan import palette_for
                text = ""
                if tpl == "infographic":                       # 3D number: "2 CRORE", "90%" (Latin – Blender Hindi nahi likhta)
                    kp = key_phrase(sc.get("narration", ""))
                    try:
                        from translit import word as _hw
                        text = " ".join(w if re.search(r"[0-9%]", w) else _hw(w) for w in kp.split()).upper()
                    except Exception:
                        m = re.search(r"[0-9][0-9,.]*\s*%?", kp); text = m.group(0) if m else ""
                    text = re.sub(r"[०-९]", lambda m_: str("०१२३४५६७८९".index(m_.group(0))), text)[:12]
                r = eng.render(out, frames, W, H, tpl, sc.get("camera_move"), palette_for(sc), text=text, seed=7 + i,
                               log=log)
                if r:
                    used_b += 1
                    item = {"kind": "video", "path": Path(r), "credit": "", "src": f"blender3d:{tpl}",
                            "whole": True, "ss": 0.0}
            except Exception as e:
                log(f"   (Blender line {i+1} skip: {e})", show=False)
        if item is None and yes(style.get("topic_broll", "haan")):
            # v3.9: TEXT CARD SE PEHLE topic ka B-roll (film -> camera / film set / green screen ...).
            # 15 Nov Yash video: 7/9 line pe sirf text card aaya tha – user: "na video, na image".
            item = topic_broll(i, sents, keys, style, scenes)
            if item: log(f"   line {i+1}: topic B-roll lagaya ({item.get('src')})", show=False)
        if item is None and n_cards[0] >= int(num(style, "text_card_max", 0, 10) if style.get("text_card_max") else 1):
            item = _neighbour(found, i)                 # v3.9: text card max 1 – baaki pe paas wali line ki footage (alag hissa)
            if item: log(f"   line {i+1}: paas wali line ki footage (text card ki jagah)", show=False)
        if item is None:
            n_cards[0] += 1
            try:
                from cine import cards
                word = keyw.get(i) or key_phrase(sents[i].get("script") or sents[i]["text"])
                sub = ""                                    # v3.1: English subtitle nahi (viewer ke liye ajeeb)
                kout = Path(work) / "shots" / f"kcard_{i:02d}.mp4"
                numm = re.search(r"[0-9०-९][0-9०-९,.]*\s*(%|प्रतिशत|लाख|करोड़|हजार)?", sents[i].get("script") or sents[i]["text"])
                if numm:
                    cards.render_stat(numm.group(0), sub or word, dur, kout, W, H, style, pal_b, fps=fps)
                else:
                    cards.render_word(word, sub, dur, kout, W, H, style, pal_b, fps=fps)
                item = {"kind": "video", "path": kout, "credit": "", "src": "kinetic card", "whole": True, "ss": 0.0}
            except Exception as e:
                log(f"   (kinetic card skip line {i+1}: {e})", show=False)
        if item:
            found[i] = ([item], found[i][1] if found[i] else [])
            src[i] = item["src"]
            log(f"   line {i+1}: fallback visual = {item['src']}", show=False)
    return src



# ------------------------------------------------------------------ v3.9
def topic_broll(i, sents, keys, style, scenes=None):
    """Line ke topic (film / space / cricket ...) ka asli B-roll – Pixabay/Pexels/Wikimedia se, AI aankh jaanch ke saath."""
    try:
        import sources, identity_lock as IL
        txt = " ".join((s.get("script") or s["text"]) for s in sents)
        doms = IL._domains(txt + " " + (sents[i].get("script") or sents[i]["text"]))
        qs = []
        try:
            lk = sources.LOCK_REF.get("v") or {}
            sc = (lk.get("scenes") or [])[i] if i < len(lk.get("scenes") or []) else {}
            if sc.get("show"): qs.append(sc["show"])
        except Exception:
            pass
        for d in doms[:2]:
            qs += IL.DOMAIN_ALLOWED.get(d, [])[-5:]
        qs = [q for q in dict.fromkeys(qs) if q][:6]
        if not qs: return None
        r = sources.find_visuals(i, qs[0], [qs[0]], 1, keys, extra_queries=qs, line=sents[i].get("script") or sents[i]["text"])
        its = r[0] if isinstance(r, tuple) else r
        its = [x for x in (its or []) if x.get("kind") in ("video", "image")]
        return dict(its[0], src=f"topic B-roll: {its[0].get('src', '')}") if its else None
    except Exception as e:
        log(f"   (topic B-roll skip line {i+1}: {e})", show=False)
        return None


def _neighbour(found, i):
    for d in (1, -1, 2, -2, 3, -3):
        j = i + d
        if 0 <= j < len(found) and found[j] and found[j][0]:
            vids = [x for x in found[j][0] if x.get("kind") == "video" and "kinetic" not in str(x.get("src", ""))]
            if vids:
                return dict(vids[0], ss=None, src=f"{vids[0].get('src', '')} (paas wali line)")
    return None
