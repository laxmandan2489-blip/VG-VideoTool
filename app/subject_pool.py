"""v3.15 SUBJECT POOL – "kuch nahi mila to YASH ki hi koi aur video lagao, random stock nahi" (user, 15 Nov).

Video ka mukhya insaan / film (identity lock + film) ke OFFICIAL YouTube videos ka ek pool banta hai (yt-dlp search,
free – API quota nahi; Brave key ho to Brave video bhi):
    "<film> official teaser", "<film> glimpse", "<naam> <film>", "<naam> official trailer", "<naam> interview" ...
Sirf wo video jinke title me naam/film ho, reaction/edit/fan/status na ho, aur 5 lakh+ views ho.
Jis line ke liye sahi footage nahi mili, uspe isi pool ki video ka ALAG hissa (har baar naya video / naya second)
lagta hai. Kabhi same hissa dobara nahi.
"""
import random, re, threading, time
from common import log, CACHE

POOL = {"key": None, "vids": [], "next": 0, "main": ""}
_LOCK = threading.Lock()
BAD = re.compile(r"(reaction|react|review|explained|spoof|parody|roast|fan ?made|status|whatsapp|#shorts|meme|"
                 r"\bedit\b|lyrical|ai generated|trolls?|vs\b|ranking|top 10|facts about)", re.I)
GOOD = re.compile(r"(official|trailer|teaser|glimpse|first look|introduction|title reveal|promo|song|making|"
                  r"behind the scenes|bts|interview|press meet|event|promotion|launch|scene|look)", re.I)


def _c(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


# v3.18 ('MOTE' brain implant jaisa naam -> 'Mote Mote Nain' gaana ka khatra): film na ho to ye titles nahi
NOFILM_BAD = re.compile(r"(\bsong\b|\bsongs\b|gaana|lyrics?|music video|official audio|video song|remix|jukebox|"
                        r"trailer|teaser|web ?series|episode|\bmovie\b)", re.I)


def build(main="", film="", keys=None, context=""):
    """Pool ek baar per video. Return list of {video_id,title,channel,duration_seconds,view_count,url,thumb}."""
    k = _c(main) + "|" + _c(film)
    with _LOCK:
        if POOL["key"] == k: return POOL["vids"]
    base = re.split(r"[:(]", film or "")[0].strip()
    qs = []
    if base:
        qs += [f"{film} official teaser", f"{base} glimpse", f"{base} {main} first look".strip()]
    if main:
        qs += [f"{main} {base}".strip(), f"{main} official trailer", f"{main} interview"]
    seen, vids = set(), []
    try:
        import youtube_sources as ys
        rows = []
        for q in list(dict.fromkeys(qs))[:6]:
            rows += [dict(x, _q=q) for x in ys.ytdlp_search(q, 12)]
        try:
            import sources
            if sources.BRAVE_KEYS:
                for q in qs[:2]:
                    for x in sources.brave_videos(q, n=10):
                        if x.get("yt"):
                            rows.append({"video_id": x["yt"], "title": x.get("title", ""), "channel": x.get("channel", ""),
                                         "duration_seconds": x.get("duration_seconds", 0), "view_count": x.get("view_count", 0),
                                         "thumbnail": x.get("thumb"), "url": x.get("url"), "_q": q})
        except Exception:
            pass
        names = [_c(n) for n in (main, base) if n]
        for x in rows:
            vid = x.get("video_id"); t = x.get("title") or ""
            if not vid or vid in seen: continue
            if BAD.search(t) or not GOOD.search(t): continue
            if not base and NOFILM_BAD.search(t): continue     # v3.18: topic film nahi -> gaana / trailer nahi
            if names and not any(n and n in _c(t) for n in names): continue
            d = float(x.get("duration_seconds") or 0)
            if d and not (15 <= d <= 1800): continue
            if max(int(x.get("view_count") or 0), int(x.get("channel_followers") or 0)) < 500_000: continue
            seen.add(vid)
            film_hit = bool(base) and _c(base) in _c(t)
            vids.append({"video_id": vid, "title": t, "channel": x.get("channel", ""), "duration_seconds": d or 120.0,
                         "view_count": int(x.get("view_count") or 0), "url": f"https://www.youtube.com/watch?v={vid}",
                         "thumb": x.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "film": film_hit})
        vids.sort(key=lambda v: (not v["film"], -v["view_count"]))
    except Exception as e:
        log(f"   (subject pool skip: {str(e)[:100]})", show=False)
    vids = vids[:10]
    with _LOCK:
        POOL.update(key=k, vids=vids, next=0, main=main or film)
    log(f"   🎞 '{main or film}' ki apni official videos (random footage ki jagah): {len(vids)}"
        + (f" – jaise: {vids[0]['title'][:60]}" if vids else " – nahi mili (internet / yt-dlp?)"))
    return vids


def next_clip(line_idx, verify_text="", avoid=(), secs=3.5):
    """Pool ki AGLI video ka naya hissa. Return item dict ya None."""
    import yt_clips, sources
    with _LOCK:
        vids = list(POOL["vids"]); start_i = POOL["next"]
    if not vids or not yt_clips._ytdlp_ok():
        return None
    order = [vids[(start_i + k) % len(vids)] for k in range(len(vids))]
    lim = lambda v: max(3, int(v.get("duration_seconds") or 60) // 12)
    # pehle wo video jinka kam use hua; sab apni seema pe ho to bhi (naya second) – text card / random se behtar
    order = [v for v in order if yt_clips.USED_VIDS.get(v["video_id"], 0) < lim(v)] + \
            [v for v in order if yt_clips.USED_VIDS.get(v["video_id"], 0) >= lim(v)]
    for k, v in enumerate(order):
        dur = float(v.get("duration_seconds") or 120)
        fr = [0.06, 0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82, 0.9]; random.shuffle(fr)
        for f in fr[:5]:
            st = round(max(0.5, min(dur - secs - 0.5, dur * f)), 1)
            key = (v["video_id"], int(st // 3))
            with yt_clips._LOCK:
                if key in yt_clips.USED: continue
                yt_clips.USED.add(key)
            d = CACHE / "ytclips"; d.mkdir(parents=True, exist_ok=True)
            _sp_risk = yt_clips.is_copyright_risk(v.get("channel", ""), v.get("title", ""), license_str=v.get("license", ""))
            if _sp_risk:
                p = yt_clips._extract_screenshot(v["video_id"], st, d / f"{v['video_id']}_{int(st)}_ss")
                _sp_kind = "image"
            else:
                p = yt_clips._cut(v["video_id"], st, secs + 0.5, d / f"{v['video_id']}_{int(st)}")
                _sp_kind = "video"
            if not p: break
            try:
                import visual_quality_gate as _vqg
                _qok, _qwhy = _vqg.check(p, _sp_kind)
                if not _qok:
                    continue
            except Exception:
                pass
            if verify_text and sources.verify(p, _sp_kind, verify_text, (), avoid, line_idx) is False:
                continue
            with _LOCK: POOL["next"] = (vids.index(v) + 1) % len(vids)
            with yt_clips._LOCK:
                yt_clips._N["n"] += 1; yt_clips.USED_VIDS[v["video_id"]] = yt_clips.USED_VIDS.get(v["video_id"], 0) + 1
            url = f"{v['url']}&t={int(st)}"
            _src_lbl = "subject pool screenshot (copyright-safe)" if _sp_risk else "subject pool (youtube)"
            log(f"   {'📸' if _sp_risk else '🎞'} line {line_idx+1}: '{v['title'][:50]}' ({int(st)}s, {_src_lbl})")
            return {"kind": _sp_kind, "path": p, "url": url, "src": _src_lbl, "pool": True,
                    "entity": POOL.get("main") or "",
                    "credit": f"YouTube: \"{v['title'][:70]}\" – {v.get('channel','')} ({url})"}
    return None
