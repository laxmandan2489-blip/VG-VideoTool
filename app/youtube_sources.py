"""YouTube discovery provider for VG Video Tool.

Uses the official YouTube Data API v3 for public reference discovery and metadata only.
YouTube audiovisual content is not downloaded or stored by this API client. API metadata
is a discovery lead, not a legal guarantee; verify the original source and licence.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime, timezone
import requests
from common import TOOL, log

BASE = "https://www.googleapis.com/youtube/v3"

# ------------------------------------------------------------------ v3.13: quota + JSON safety (shared)
import os, sys, subprocess, threading, time
_JLOCK = threading.Lock()
QUOTA_FILE = TOOL / "temp" / "yt_quota_out.txt"
_QSTATE = {"out": None}


def _quota_day():
    """YouTube ki daily quota Pacific time aadhi raat reset hoti hai (~UTC-8)."""
    return datetime.fromtimestamp(time.time() - 8 * 3600, timezone.utc).strftime("%Y-%m-%d")


def quota_out() -> bool:
    """Aaj YouTube SEARCH ki limit khatam? (file me yaad rehta hai – har video pe 429 dobara nahi khaana)"""
    if _QSTATE["out"] is not None and _QSTATE["out"] == _quota_day():
        return True
    try:
        if QUOTA_FILE.exists() and QUOTA_FILE.read_text(encoding="utf-8").strip() == _quota_day():
            _QSTATE["out"] = _quota_day(); return True
    except Exception:
        pass
    return False


def mark_quota_out(why: str = "") -> None:
    if quota_out(): return
    _QSTATE["out"] = _quota_day()
    try:
        QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True); QUOTA_FILE.write_text(_quota_day(), encoding="utf-8")
    except Exception:
        pass
    log("   ⚠️ YouTube API search ki aaj ki limit khatam – aaj baaki search yt-dlp / Brave se hogi (API dobara nahi)")


def _is_quota(code, msg) -> bool:
    return code in (403, 429) and bool(re.search(r"quota", msg or "", re.I))


def load_json(path: Path, default):
    """Tooti JSON (do thread ek saath likhte the -> 'Extra data') -> .bad me rakh ke naya shuru."""
    with _JLOCK:
        if not path.exists(): return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            try: path.replace(path.with_suffix(".bad.json"))
            except Exception: pass
            log(f"  ({path.name} kharab tha ({str(e)[:60]}) – naya bana raha hoon)", show=False)
            return default


def save_json(path: Path, data) -> None:
    """Atomic + lock: pehle tmp file, phir replace (aadhi likhi file kabhi nahi)."""
    with _JLOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)


def update_json(path: Path, default, fn) -> None:
    """Padho -> badlo -> likho, sab ek hi lock me (do thread ek doosre ka data na mitaayein)."""
    with _JLOCK:
        data = default
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                try: path.replace(path.with_suffix(".bad.json"))
                except Exception: pass
                data = default
        data = fn(data) or data
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)


def ytdlp_search(query: str, n: int = 10) -> list[dict]:
    """v3.13: API quota ke BINA YouTube search (yt-dlp 'ytsearch'). Sirf metadata – download nahi.
    Return search_videos jaisa format."""
    if not query or not query.strip(): return []
    try:
        try:
            from yt_clips import js_args as _js
            jsa = _js()
        except Exception:
            jsa = []
        r = subprocess.run([sys.executable, "-m", "yt_dlp"] + jsa + ["--flat-playlist", "-J", "--no-warnings",
                            f"ytsearch{max(1, min(n, 20))}:{query[:150]}"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=18, stdin=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            log(f"  yt-dlp search fail: {r.stderr.strip()[-160:]}", show=False); return []
        j = json.loads(r.stdout or "{}")
    except Exception as e:
        log(f"  yt-dlp search error: {e}", show=False); return []
    out = []
    for x in j.get("entries") or []:
        vid = x.get("id")
        if not vid or len(str(vid)) != 11: continue
        th = x.get("thumbnails") or []
        thumb = (th[-1].get("url") if th else "") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        out.append({"provider": "yt-dlp search", "video_id": vid, "title": x.get("title") or "",
                    "description": (x.get("description") or "")[:600], "channel": x.get("channel") or x.get("uploader") or "",
                    "channel_id": x.get("channel_id") or "", "thumbnail": thumb,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "duration_seconds": float(x.get("duration") or 0), "view_count": int(x.get("view_count") or 0),
                    "channel_followers": int(x.get("channel_follower_count") or 0)})
    return out
TIMEOUT = 18
_QUERY_BUDGET = 24  # max search.list calls per generated video; protects daily quota
_queries_used = 0


def reset_query_budget() -> None:
    global _queries_used
    _queries_used = 0


def _duration_seconds(value: str) -> float:
    import re
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0) if m else 0



def purge_expired() -> None:
    """Delete non-authorized YouTube API metadata older than 30 calendar days."""
    path = TOOL / "temp" / "youtube_discovery.json"
    if not path.exists():
        return
    cutoff = datetime.now(timezone.utc).timestamp() - 30 * 24 * 60 * 60
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        kept = []
        for item in data.get("items", []):
            stamp = item.get("discovered_at") if isinstance(item, dict) else None
            try:
                dt = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt.timestamp() >= cutoff:
                    kept.append(item)
            except Exception:
                # Old records without a reliable timestamp are discarded conservatively.
                continue
        data["items"] = kept
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_json(path, data)
    except Exception as e:
        log(f"YouTube discovery expiry cleanup skip: {e}", show=False)

def search_videos(query: str, api_key: str, max_results: int = 5, order: str = "relevance") -> list[dict]:
    """Search public YouTube videos and enrich with duration/license metadata."""
    if not api_key or not query or not query.strip():
        return []
    if quota_out():                                   # v3.13: aaj ki limit khatam – 429 dobara mat khao
        return []
    try:
        # Reference research intentionally includes popular standard-license videos too.
        # Their metadata/thumbnails are analyzed only; audiovisual content is never fetched.
        r = requests.get(f"{BASE}/search", params={
            "part": "snippet", "q": query[:180], "type": "video",
            "maxResults": max(1, min(int(max_results), 10)), "order": order,
            "safeSearch": "moderate", "videoEmbeddable": "true", "key": api_key,
        }, timeout=TIMEOUT)
        if r.status_code != 200:
            try: detail = r.json().get("error", {}).get("message", r.text[:180])
            except Exception: detail = r.text[:180]
            log(f"  YouTube search {r.status_code}: {detail}", show=False)
            if _is_quota(r.status_code, detail): mark_quota_out(detail)
            return []
        items = r.json().get("items", [])
        ids = [x.get("id", {}).get("videoId") for x in items if x.get("id", {}).get("videoId")]
        details = {}
        if ids:
            d = requests.get(f"{BASE}/videos", params={
                "part": "contentDetails,status,statistics", "id": ",".join(ids), "key": api_key,
            }, timeout=TIMEOUT)
            if d.status_code == 200:
                details = {x.get("id"): x for x in d.json().get("items", [])}
        out = []
        for x in items:
            vid = (x.get("id") or {}).get("videoId")
            sn = x.get("snippet") or {}
            if not vid: continue
            det = details.get(vid, {})
            status = det.get("status") or {}
            out.append({
                "provider": "YouTube Data API v3",
                "video_id": vid,
                "title": sn.get("title", ""),
                "description": (sn.get("description") or "")[:1200],
                "channel": sn.get("channelTitle", ""),
                "channel_id": sn.get("channelId", ""),
                "published_at": sn.get("publishedAt", ""),
                "thumbnail": ((sn.get("thumbnails") or {}).get("high") or (sn.get("thumbnails") or {}).get("medium") or {}).get("url", ""),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "duration": (det.get("contentDetails") or {}).get("duration", ""),
                "duration_seconds": _duration_seconds((det.get("contentDetails") or {}).get("duration", "")),
                "youtube_license": status.get("license", "unknown"),
                "embeddable": status.get("embeddable"),
                "discovery_only": True,
                "downloaded": False,
                "reuse_permission_verified": False,
                "view_count": int((det.get("statistics") or {}).get("viewCount", 0) or 0),
                "like_count": int((det.get("statistics") or {}).get("likeCount", 0) or 0),
            })
        return out
    except Exception as e:
        log(f"  YouTube discovery error: {e}", show=False)
        return []


def record_scene(line_number: int, script_line: str, queries: list[str], api_key: str,
                 category: str = "", max_queries: int = 2) -> list[dict]:
    """Run bounded discovery and append auditable leads to temp/youtube_discovery.json."""
    if not api_key or quota_out():
        return []
    global _queries_used
    found, seen = [], set()
    # Bound total search.list calls for a single video, not just per scene.
    remaining = max(0, _QUERY_BUDGET - _queries_used)
    if remaining <= 0:
        log("  YouTube search budget for this video is complete; other providers continue.", show=False)
        return []
    # Recent news scenes prioritize latest uploads; other scenes prioritize relevance.
    order = "date" if "news" in str(category).lower() or "current" in str(category).lower() else "relevance"
    for qi, q in enumerate([x.strip() for x in queries if isinstance(x, str) and x.strip()][:min(max_queries, remaining)]):
        _queries_used += 1
        # Second query favors high-view reference videos, while first stays relevance/date focused.
        search_order = "viewCount" if qi == 1 and "news" not in str(category).lower() and "current" not in str(category).lower() else order
        for item in search_videos(q, api_key, max_results=5, order=search_order):
            item["search_order"] = search_order
            if item["video_id"] in seen: continue
            seen.add(item["video_id"])
            item.update({"line_number": line_number + 1, "script_line": script_line[:500], "search_query": q})
            found.append(item)
    if found:
        path = TOOL / "temp" / "youtube_discovery.json"
        def _merge(old):                              # v3.13 FIX: lock + atomic (pehle 4 thread ek saath likhte the)
            if not isinstance(old, dict): old = {"items": []}
            cutoff = datetime.now(timezone.utc).timestamp() - 30 * 24 * 60 * 60
            fresh = []
            for saved in old.get("items") or []:
                try:
                    dt = datetime.fromisoformat(str(saved.get("discovered_at", "")).replace("Z", "+00:00"))
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    if dt.timestamp() >= cutoff: fresh.append(saved)
                except Exception:
                    continue
            known = {(x.get("video_id"), x.get("line_number")) for x in fresh if isinstance(x, dict)}
            for item in found:
                item["discovered_at"] = datetime.now(timezone.utc).isoformat()
                marker = (item.get("video_id"), item.get("line_number"))
                if marker not in known:
                    fresh.append(item); known.add(marker)
            old["items"] = fresh[-2000:]
            old["updated_at"] = datetime.now(timezone.utc).isoformat()
            return old
        try:
            update_json(path, {"items": []}, _merge)
            log(f"  YouTube: line {line_number+1} ke liye {len(found)} discovery leads mile (download nahi kiye)", show=False)
        except Exception as e:
            log(f"  YouTube report save nahi hua: {e}", show=False)
    return found


def cc_images(query: str, api_key: str, n: int = 3) -> list[dict]:
    """v3.1: Sirf CREATIVE COMMONS (CC BY 3.0) YouTube videos ke thumbnail – entity ki photo jab Wikimedia pe na mile.

    Kyun sirf CC: standard licence wali video ka screenshot/thumbnail lagana copyright todta hai (channel strike).
    CC BY video ka creator reuse ki ijaazat deta hai, bas credit dena hota hai – credit apne-aap likha jaata hai.
    Video download NAHI hoti; sirf YouTube ka public thumbnail (i.ytimg.com) liya jaata hai.
    """
    if not api_key or not query or quota_out():
        return []
    try:
        r = requests.get(f"{BASE}/search", params={
            "part": "snippet", "q": query[:180], "type": "video", "maxResults": 10, "order": "relevance",
            "videoLicense": "creativeCommon", "safeSearch": "moderate", "key": api_key}, timeout=TIMEOUT)
        if r.status_code != 200:
            log(f"  YouTube CC search {r.status_code}", show=False)
            try: _m = r.json().get("error", {}).get("message", "")
            except Exception: _m = ""
            if _is_quota(r.status_code, _m or ("quota" if r.status_code == 429 else "")): mark_quota_out(_m)
            return []
        items = r.json().get("items", [])
        ids = [x["id"]["videoId"] for x in items if x.get("id", {}).get("videoId")]
        if not ids: return []
        d = requests.get(f"{BASE}/videos", params={"part": "status,snippet", "id": ",".join(ids), "key": api_key},
                         timeout=TIMEOUT)
        det = {x["id"]: x for x in (d.json().get("items", []) if d.status_code == 200 else [])}
        out = []
        toks = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
        for vid in ids:
            x = det.get(vid) or {}
            if (x.get("status") or {}).get("license") != "creativeCommon":
                continue                                          # dobara pakka kiya – sirf CC
            sn = x.get("snippet") or {}
            title = sn.get("title", "")
            if toks and not all(t in (title + " " + sn.get("channelTitle", "")).lower() for t in toks[:2]):
                continue                                          # title me naam hi nahi -> shayad kuch aur
            th = sn.get("thumbnails") or {}
            url = (th.get("maxres") or th.get("standard") or th.get("high") or {}).get("url")
            if not url: continue
            out.append({"kind": "image", "url": url, "src": "youtube cc", "channel": sn.get("channelTitle", ""),
                        "credit": f"Thumbnail of \"{title[:80]}\" by {sn.get('channelTitle','')} on YouTube "
                                  f"(https://youtu.be/{vid}), licensed CC BY 3.0"})
            if len(out) >= n: break
        return out
    except Exception as e:
        log(f"  YouTube CC image error: {e}", show=False)
        return []
