"""v3.2 SEMANTIC VISUAL VERIFICATION + PRE-RENDER VISUAL GATE + AUTO REPLACEMENT + REPORTS.

Kahan chalta hai: make_video.py me visuals milne ke BAAD aur shots render hone se PEHLE (aur QC round ke baad
dobara). Har line ke har chune gaye asset ko jaanchta hai:

  1. Identity (bharosa)  : aapki footage / Wikidata se pakki entity ki photo / map / naam card – source se pata
  2. CLIP (supporting)   : scene text, topic, mukhya naam vs lock ke FORBIDDEN cheezein + "doosre insaan ka chehra"
  3. Gemini Vision (context): poori kahani + lock + line + prev/next + frame -> verdict
       correct / weak / wrong_subject / unrelated / misleading / repeated  (+ subject_ok, action_ok, context_ok)
  Sirf CLIP par faisla nahi; Gemini mile to wahi context ka aakhri faisla.

Fail -> reject (url _used me, dobara nahi aayega) -> behtar query (lock: subject + action + context) se dobara
search -> mukhya entity ki doosri photo/clip -> lock-allowed Blender -> safe fallback (kinetic keyword card).
Chupchaap kuch accept nahi hota. Report: VISUAL_RELEVANCE_REPORT.json/.md, SCENE_VERIFICATION_REPORT.json.
"""
import io, json, re, subprocess, time
from pathlib import Path

from common import log

TH = {"pos": 0.215, "margin": 0.03, "face": 0.02, "gem_min": 7}   # v3.20: stricter documentary quality gate
TRUSTED = ("aapki footage", "aapka link", "chehra", "map", "news card")
SAFE = ("kinetic card", "name card")


# ------------------------------------------------------------------ frames
def frames(item, n=3):
    from PIL import Image
    p = Path(str(item.get("path", "")))
    if not p.exists(): return []
    try:
        if item.get("kind") == "image":
            return [Image.open(p).convert("RGB")]
        from common import duration
        d = duration(p) or 3
        out = []
        for f in ((0.5,) if n == 1 else (0.2, 0.5, 0.8)):
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{d * f:.2f}", "-i", str(p), "-frames:v", "1",
                                "-vf", "scale=360:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                               capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            if r.stdout: out.append(Image.open(io.BytesIO(r.stdout)).convert("RGB"))
        return out
    except Exception:
        return []


# ------------------------------------------------------------------ CLIP (supporting signal)
def clip_eval(ims, scene, lock):
    """{pos, topic, forb, forb_name, face} ya None (CLIP nahi)."""
    try:
        import aankh, numpy as np
        if not ims or not (aankh.STATE.get("ok") or aankh.ready()): return None
        main = lock.get("main_subject") or ""
        pos_t = [scene.get("show") or scene.get("subject") or "", lock.get("topic") or ""]
        if scene.get("uses_main") and main: pos_t.append(main + (" " + scene["action"] if scene.get("action") else ""))
        forb = list(lock.get("forbidden_subjects") or [])[:10]
        texts = [f"a photo of {t}" for t in pos_t + forb] + ["a close-up portrait photo of a person's face"]
        iv = aankh.image_vecs(ims); tv = aankh.text_vecs(texts)
        sim = (iv @ tv.T).mean(axis=0)                 # frames ka ausat
        k = len(pos_t)
        pos = float(sim[0]); top = float(sim[1]); subj = float(sim[2]) if k > 2 else pos
        f = sim[k:k + len(forb)]
        fi = int(np.argmax(f)) if len(f) else -1
        return {"pos": round(max(pos, subj), 4), "topic": round(top, 4),
                "forb": round(float(f[fi]), 4) if fi >= 0 else 0.0, "forb_name": forb[fi] if fi >= 0 else "",
                "face": round(float(sim[-1]), 4)}
    except Exception as e:
        log(f"   (CLIP verify skip: {str(e)[:80]})", show=False)
        return None


# ------------------------------------------------------------------ Gemini Vision (context verifier)
def gemini_eval(key, lock, scenes, assets):
    """assets: [(scene_i, k, PIL image, src)] -> {(i,k): {...}} ya {} (Gemini nahi)."""
    if not key or not assets: return {}
    try:
        from ai import ask_json
        parts = [("You are a strict documentary video editor verifying that every visual matches the narration.\n"
                  f"FULL STORY: {lock.get('story') or ''}\nMAIN SUBJECT: {lock.get('main_subject') or '-'} "
                  f"({lock.get('main_type')})\nTOPIC: {lock.get('topic')}\n"
                  f"ALLOWED: {', '.join(lock.get('allowed_subjects', [])[:14])}\n"
                  f"FORBIDDEN: {', '.join(lock.get('forbidden_subjects', [])[:12])}\n"
                  "For each numbered candidate frame decide: subject_ok (shows the intended subject – for a real "
                  "person, is it plausibly THAT person or their own content, not a different person), action_ok, "
                  "context_ok, verdict = correct | weak | wrong_subject | unrelated | misleading, score 0-10, why "
                  "(max 12 words). A beautiful but unrelated cinematic visual is 'unrelated'. "
                  "STRICT REJECT (verdict='misleading', score<=3) if the frame has: "
                  "(1) baked-in/cropped English or Hindi subtitles or news lower-third text banners, "
                  "(2) cute 3D cartoon toys or childish animations during a serious science/military/history topic, or "
                  "(3) generic empty park/grass/trees scenery when narration mentions people/soldiers/animals/objects, or (4) camera/microphone/studio gear on a desk unless the topic is filmmaking.\n"
                  'Return ONLY JSON: {"results": [{"n": number, "verdict": "..", "subject_ok": true, '
                  '"action_ok": true, "context_ok": true, "score": 0, "why": ".."}]}')]
        idx = []
        for n_, (i, k, im, src) in enumerate(assets[:16]):
            sc = scenes[i]
            b = io.BytesIO(); im.copy().convert("RGB").save(b, "JPEG", quality=72)
            parts += [f"Candidate {n_ + 1} | line {i + 1}: \"{sc['narration']}\" | intended: {sc['verify']} | "
                      f"previous line: {sc.get('prev', '')[:80]} | source: {src}", {"jpg": b.getvalue()}]
            idx.append((i, k))
        res = ask_json(key, parts, temperature=0.1, timeout=120)
        out = {}
        for r in (res or {}).get("results", []) if isinstance(res, dict) else []:
            try:
                n_ = int(r.get("n")) - 1
                if 0 <= n_ < len(idx): out[idx[n_]] = r
            except Exception:
                continue
        return out
    except Exception as e:
        log(f"   (Gemini visual verify skip: {str(e)[:80]})", show=False)
        return {}


# ------------------------------------------------------------------ decision
def decide(item, scene, lock, clip, gem, uses):
    """-> (status, score 0..1, reasons[])  status: correct/illustrative/safe_fallback/weak/wrong_subject/unrelated/
    misleading/repeated/unverified"""
    src = str(item.get("src", "")); r = []
    main = (lock.get("main_subject") or "").lower().replace(" ", "")
    if uses > 3 and not src.startswith(SAFE):
        return "repeated", 0.3, [f"same visual {uses} lines pe"]
    if src.startswith(TRUSTED) or item.get("face"):
        return "correct", 1.0, ["aapki / pakki source"]
    if src.startswith(SAFE):
        return "safe_fallback", 0.6, ["safe fallback (keyword card)"]
    if src.startswith("blender3d"):
        tpl = src.split(":", 1)[-1]
        from identity_lock import allows_template
        return (("illustrative", 0.75, [f"3D {tpl} – lock me allowed"]) if allows_template(lock, tpl, scene)
                else ("unrelated", 0.1, [f"3D {tpl} is kahani ka hissa nahi"]))
    ent = str(item.get("entity") or "").lower().replace(" ", "")
    identity = bool(ent) and (not main or ent == main or not scene.get("uses_main"))
    if gem:
        v = str(gem.get("verdict", "")).lower(); sc_ = float(gem.get("score") or 0) / 10
        r.append(f"Gemini: {v} {gem.get('score')}/10 – {gem.get('why', '')}")
        if v in ("unrelated", "misleading", "wrong_subject"):
            if identity and v == "wrong_subject":      # Wikidata pakki pehchaan > model ka andaza
                return "correct", 0.8, r + ["identity Wikidata se pakki"]
            return v, sc_, r
        if v == "weak" or sc_ * 10 < TH["gem_min"]:
            return ("correct" if identity else "weak"), max(sc_, 0.5 if identity else sc_), r
        return "correct", max(sc_, 0.7), r
    if identity:
        if clip and clip["forb"] > clip["pos"] + 0.03:
            return "weak", 0.5, [f"pakki entity, par CLIP: '{clip['forb_name']}' zyada dikh raha"]
        return "correct", 0.85, ["Wikidata/YouTube entity – pakki pehchaan" + (f", CLIP {clip['pos']}" if clip else "")]
    if not clip:
        return "unverified", 0.4, ["CLIP/Gemini dono nahi – jaanch nahi hui"]
    r.append(f"CLIP pos {clip['pos']} topic {clip['topic']} forbidden '{clip['forb_name']}' {clip['forb']} face {clip['face']}")
    if clip["forb"] > clip["pos"] + TH["margin"]:
        return "unrelated", clip["pos"], r + ["forbidden cheez zyada"]
    if lock.get("main_type") == "person" and scene.get("uses_main") and clip["face"] > clip["pos"] + TH["face"]:
        return "wrong_subject", clip["pos"], r + ["kisi aur insaan ka chehra"]
    if clip["pos"] < TH["pos"]:
        return "weak", clip["pos"], r + ["line se kamzor mel"]
    return "correct", min(1.0, clip["pos"] * 3.2), r


# ------------------------------------------------------------------ gate
def _evaluate(found, lock, key, only=None):
    """Har line ke har item ka verdict. Return {(i,k): result}."""
    scenes = lock["scenes"]; uses = {}
    def ukey(it):                       # v3.4: same photo ka alag crop = alag visual
        return f"{it.get('path')}#{it.get('crop_v', 0)}"
    for its, _ in found:
        for it in its:
            p = ukey(it); uses[p] = uses.get(p, 0) + 1
    res = {}; gem_assets = []; cache_frames = {}
    for i, (its, _k) in enumerate(found):
        if only is not None and i not in only: continue
        if i >= len(scenes): continue
        for k, it in enumerate(its):
            ims = frames(it)
            cache_frames[(i, k)] = ims
            res[(i, k)] = {"clip": clip_eval(ims, scenes[i], lock)}
            if ims and not str(it.get("src", "")).startswith(TRUSTED + SAFE) and not str(it.get("src", "")).startswith("blender3d"):
                gem_assets.append((i, k, ims[len(ims) // 2], str(it.get("src", ""))))
    gem = gemini_eval(key, lock, scenes, gem_assets) if gem_assets else {}
    for (i, k), r in res.items():
        it = found[i][0][k]
        st, sc, why = decide(it, scenes[i], lock, r["clip"], gem.get((i, k)), uses.get(ukey(it), 1))
        r.update(status=st, score=round(float(sc), 3), why=why, gemini=bool(gem.get((i, k))),
                 src=str(it.get("src", "")), path=str(it.get("path", "")), url=it.get("url"))
    return res


GOOD = ("correct", "illustrative", "safe_fallback")
KEEP = GOOD + ("unverified",)     # jaanch hi nahi ho payi (CLIP/Gemini nahi) -> rakho, par report me FAIL likho


def gate(found, sents, lock, keys, style, work, spans, W, H, fps=30, rounds=2, only=None, plan_scenes=None):
    """found ko IN-PLACE sudhaarta hai. Return report dict."""
    import sources
    key = keys.get("GEMINI") if str(style.get("visual_verify_gemini", "haan")).lower() in ("haan", "yes", "1") else None
    t0 = time.time()
    history = {i: [] for i in range(len(found))}
    weak_best = {}
    todo = set(range(len(found))) if only is None else set(only)
    for rnd in range(rounds + 1):
        res = _evaluate(found, lock, key, todo)
        bad_lines = set()
        for (i, k), r in res.items():
            history[i].append(dict(r, round=rnd, k=k))
        for i in sorted(todo):
            its = found[i][0]
            keep = [it for k, it in enumerate(its) if res.get((i, k), {}).get("status") in KEEP]
            rej = [it for k, it in enumerate(its) if res.get((i, k), {}).get("status") not in KEEP]
            for k, it in enumerate(its):              # sabse achha "weak" yaad rakho (kuch na mile to wahi, FAIL likh ke)
                r_ = res.get((i, k), {})
                if r_.get("status") == "weak" and r_.get("score", 0) > weak_best.get(i, (0, None))[0]:
                    weak_best[i] = (r_["score"], it)
            for it in rej:
                if it.get("url"):
                    with sources._lock: sources._used.add(it["url"])
            if rej:
                log(f"   🔍 line {i+1}: {len(rej)} visual reject – " +
                    "; ".join(res[(i, k)]["status"] + ": " + (res[(i, k)]["why"] or [""])[-1][:60]
                              for k in range(len(its)) if res.get((i, k), {}).get("status") not in GOOD)[:220])
            if keep or (i < len(lock["scenes"]) and lock["scenes"][i]["cta"] and not its):
                found[i] = (keep, found[i][1]); continue
            if not its and i < len(lock["scenes"]) and lock["scenes"][i]["cta"]:
                continue
            bad_lines.add(i)
            found[i] = ([], found[i][1])
        if not bad_lines or rnd == rounds:
            todo = bad_lines; break
        # ---- REPLACE: behtar query (lock) -> dobara search -> entity -> Blender -> safe fallback
        for i in sorted(bad_lines):
            sc = lock["scenes"][i]
            q1 = sc["query"]; q2 = " ".join(x for x in (sc["subject"], sc["action"], sc["context"]) if x)[:90]
            log(f"   🔁 line {i+1}: behtar visual dhoondh raha hoon – \"{q1}\"")
            if sc.get("uses_main") and lock.get("main_type") in ("person", "brand") and lock.get("main_subject"):
                try:                               # v3.4: pehle mukhya insaan ki hi nayi clip/photo (random search nahi)
                    import fallback_visuals
                    it_ = fallback_visuals.subject_footage(i, found, sents, keys, lock["main_subject"])
                    if it_:
                        found[i] = ([it_], found[i][1]); continue
                except Exception as e:
                    log(f"   (subject footage skip: {e})", show=False)
            try:                                   # v3.15 TOPIC LOCK: random search se pehle mukhya insaan/film ki apni video
                import visual_pick, subject_pool
                if visual_pick.TOPIC["lock"]:
                    pit = subject_pool.next_clip(i, "", sources.AVOID.get(i, ()))
                    if pit:
                        found[i] = ([pit], found[i][1]); continue
            except Exception as e:
                log(f"   (subject pool skip: {e})", show=False)
            try:
                r_ = sources.find_visuals(i, sc["show"] or q1, (lock.get("topic") or "").split()[:3],
                                          max(1, spans[i][2]), keys, extra_queries=[q1, q2],
                                          line=sents[i].get("script") or sents[i]["text"])
                try:                               # v3.15: naye search pe bhi kachra-filter (billi/baadal/anjaan log)
                    import visual_pick
                    if r_ and r_[0] and visual_pick.ON["on"]:
                        r_ = visual_pick.improve(i, r_, sc["show"] or q1, sents[i].get("script") or sents[i]["text"],
                                                 keys, max(1, spans[i][2]), lock)
                except Exception:
                    pass
                found[i] = r_ if r_ and r_[0] else found[i]
            except Exception as e:
                log(f"   (replace search skip: {e})", show=False)
        todo = bad_lines
    for i, (sc_, it) in weak_best.items():          # replacement nahi mila: kamzor par related wala wapas (report me weak)
        if not found[i][0] and not str(it.get("src", "")).startswith("blender3d"):
            found[i] = ([it], found[i][1])
    # ---- jo ab bhi khaali: lock-allowed Blender / safe fallback (fallback_visuals)
    still = [i for i in range(len(found)) if not found[i][0] and not lock["scenes"][i]["cta"]]
    if still:
        try:
            import fallback_visuals
            ps = plan_scenes or _scene_plan_like(lock)
            fallback_visuals.fill(found, sents, spans, [dict(s, blender_template=_lock_tpl(lock, s)) for s in ps],
                                  style, keys, work, W, H, fps, sources.KEYW,
                                  main=lock.get("main_subject") if lock.get("main_type") in ("person", "brand") else None)
        except Exception as e:
            log(f"   (safe fallback skip: {e})", show=False)
    final = _evaluate(found, lock, None)              # aakhri ginti (Gemini dobara nahi – limit bachao)
    for (i, k), r in final.items():
        prev = [h for h in history[i] if h["path"] == r["path"] and h.get("gemini")]
        if prev:                                       # pehle Gemini ne jaancha tha to wahi faisla
            r.update(status=prev[-1]["status"], score=prev[-1]["score"], why=prev[-1]["why"], gemini=True)
    return report(found, lock, final, history, work, time.time() - t0, bool(key))


def _scene_plan_like(lock):
    return [{"subject": s["subject"], "camera_move": None, "narration": s["narration"], "generation_prompt": s["gen_prompt"],
             "negative_prompt": s["negative"], "domain": ""} for s in lock["scenes"]]


def _lock_tpl(lock, s):
    from identity_lock import allows_template
    t = s.get("blender_template")
    return t if allows_template(lock, t, s) else None


def report(found, lock, final, history, work, secs, gem_used):
    scenes = []
    for i, sc in enumerate(lock["scenes"]):
        its = found[i][0] if i < len(found) else []
        rs = [final.get((i, k)) for k in range(len(its)) if final.get((i, k))]
        st = "cta" if sc["cta"] else ("missing" if not rs else min((r["status"] for r in rs),
                                                                   key=lambda s: ["unrelated", "misleading", "wrong_subject",
                                                                                  "repeated", "unverified", "weak",
                                                                                  "safe_fallback", "illustrative",
                                                                                  "correct"].index(s)
                                                                   if s in ("unrelated", "misleading", "wrong_subject",
                                                                            "repeated", "unverified", "weak",
                                                                            "safe_fallback", "illustrative",
                                                                            "correct") else 0))
        scenes.append({"line": i + 1, "narration": sc["narration"], "intended": sc["verify"], "uses_main": sc["uses_main"],
                       "status": st, "assets": rs, "rejected": [h for h in history.get(i, [])
                                                                  if h["status"] not in KEEP],
                       "score": round(min([r["score"] for r in rs] or [0]), 3)})
    body = [s for s in scenes if s["status"] != "cta"]
    n = max(1, len(body))
    rel = sum(1 for s in body if s["status"] in ("correct", "illustrative"))
    safe = sum(1 for s in body if s["status"] == "safe_fallback")
    bad = [s["line"] for s in body if s["status"] not in GOOD]
    rep = {"identity_lock": {k: lock[k] for k in ("main_subject", "main_type", "topic", "story", "allowed_subjects",
                                                   "forbidden_subjects", "source")},
           "scenes_total": len(body), "relevant": rel, "safe_fallback": safe, "failed_lines": bad,
           "relevance_pct": round(100 * rel / n, 1), "relevance_incl_safe_pct": round(100 * (rel + safe) / n, 1),
           "gemini_vision_used": any(h.get("gemini") for hs in history.values() for h in hs)
                                 or any(r.get("gemini") for s in scenes for r in s["assets"]),
           "seconds": round(secs, 1),
           "method": "identity(Wikidata/user) + CLIP similarity vs lock (supporting) + Gemini Vision context verdict"}
    try:
        Path(work, "SCENE_VERIFICATION_REPORT.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=2,
                                                                           default=str), encoding="utf-8")
        Path(work, "VISUAL_RELEVANCE_REPORT.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2,
                                                                         default=str), encoding="utf-8")
        Path(work, "VISUAL_RELEVANCE_REPORT.md").write_text(markdown(rep, scenes), encoding="utf-8")
    except Exception:
        pass
    rep["scenes"] = scenes
    return rep


def markdown(rep, scenes):
    L = rep["identity_lock"]
    out = [f"# VISUAL RELEVANCE REPORT", "",
           f"**Main subject:** {L['main_subject'] or '-'} ({L['main_type']}) · **Topic:** {L['topic']} · lock: {L['source']}",
           f"**Relevant (verified):** {rep['relevant']}/{rep['scenes_total']} = **{rep['relevance_pct']}%**  "
           f"· safe fallback: {rep['safe_fallback']} · incl. fallback {rep['relevance_incl_safe_pct']}%",
           f"**Failed lines:** {rep['failed_lines'] or 'none'} · Gemini Vision used: {rep['gemini_vision_used']}",
           "", f"Allowed: {', '.join(L['allowed_subjects'])}", "", f"Forbidden: {', '.join(L['forbidden_subjects'])}", "",
           "| Line | Status | Score | Source | Why |", "|---|---|---|---|---|"]
    for s in scenes:
        a = (s["assets"] or [{}])[0]
        out.append(f"| {s['line']} | {s['status']} | {s['score']} | {a.get('src', '-')} | "
                   f"{'; '.join(a.get('why') or [])[:90].replace('|', '/')} |")
    out += ["", "Rejected (har line):"]
    for s in scenes:
        for h in s["rejected"]:
            out.append(f"- line {s['line']} round {h['round']}: {h['status']} – {h['src']} – {'; '.join(h['why'])[:100]}")
    return "\n".join(out) + "\n"
