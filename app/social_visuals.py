"""v3.46 MULTI-SOURCE SOCIAL & ARCHIVAL VISUAL HARVESTER.

Expands VideoTool beyond YouTube/Pixabay by discovering relevant:
  1) Pinterest high-res editorial/cinematic images (no login required)
  2) Public Twitter/X & Pinterest short 4.5s muted B-roll clips via yt-dlp (14s timeout)
  3) Internet Archive (archive.org) public documentary/historical MP4 footage
All candidates pass through VideoTool existing AI Aankh / Gemini relevance scoring!
"""
import re
import subprocess
import urllib.parse
from pathlib import Path
import requests
from common import log

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
_S = requests.Session()
_S.headers.update({"User-Agent": _UA})


def _ddg_links(query, limit=6):
    """Lightweight DuckDuckGo HTML search returning result URLs (zero API key)."""
    try:
        r = _S.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            timeout=8,
        )
        if not r.ok:
            return []
        urls = []
        for m in re.finditer(r"uddg=([^&\x22\x27]+)", r.text):
            u = urllib.parse.unquote(m.group(1))
            if u.startswith("http") and u not in urls:
                urls.append(u)
            if len(urls) >= limit:
                break
        return urls
    except Exception:
        return []


def archive_videos(q, limit=4):
    """Search Internet Archive (archive.org) for public documentary/historical MP4 clips."""
    out = []
    try:
        params = {
            "q": f"({q}) AND mediatype:movies AND format:MPEG4",
            "fl[]": ["identifier", "title"],
            "rows": str(limit),
            "page": "1",
            "output": "json",
        }
        r = _S.get("https://archive.org/advancedsearch.php", params=params, timeout=8)
        docs = (r.json().get("response") or {}).get("docs") or [] if r.ok else []
        for d in docs[:limit]:
            ident = d.get("identifier")
            if not ident:
                continue
            mr = _S.get(f"https://archive.org/metadata/{ident}/files", timeout=7)
            files = (mr.json().get("result") or []) if mr.ok else []
            mp4 = next(
                (f for f in files if str(f.get("name", "")).lower().endswith(".mp4")
                 and int(f.get("size") or 0) < 12_000_000),
                None,
            )
            if mp4:
                url = f"https://archive.org/download/{ident}/{urllib.parse.quote(mp4['name'])}"
                out.append({
                    "kind": "video",
                    "url": url,
                    "thumb": f"https://archive.org/services/img/{ident}",
                    "tags": str(d.get("title") or q)[:120],
                    "credit": f"Internet Archive – {ident}",
                })
    except Exception as e:
        log(f"  archive.org skip: {e}", show=False)
    return out


def pinterest_images(q, limit=6):
    """Discover high-res Pinterest images (i.pinimg.com) matching query."""
    out = []
    seen = set()
    try:
        # Step 1: find pin pages via DDG
        pin_urls = _ddg_links(f"site:pinterest.com {q}", limit=limit)
        for pu in pin_urls:
            if len(out) >= limit:
                break
            try:
                pr = _S.get(pu, timeout=6)
                if not pr.ok:
                    continue
                imgs = re.findall(r"https://i\.pinimg\.com/(?:originals|736x|564x)/[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp)", pr.text)
                for img in imgs:
                    if img in seen:
                        continue
                    seen.add(img)
                    # Upgrade 564x -> 736x when available
                    hi = img.replace("/564x/", "/736x/")
                    out.append({
                        "kind": "image",
                        "url": hi,
                        "thumb": img,
                        "tags": f"pinterest {q}",
                        "credit": "Pinterest",
                    })
                    break
            except Exception:
                continue
    except Exception as e:
        log(f"  pinterest image skip: {e}", show=False)
    return out


def _ytdlp_direct_video(page_url, timeout=8):
    """Resolve direct MP4 stream URL from X/Twitter, Pinterest, Facebook, Instagram via yt-dlp."""
    try:
        p = subprocess.run(
            ["yt-dlp", "-g", "-f", "best[ext=mp4][height<=1080]/best[ext=mp4]/best", "--no-playlist", "--no-warnings", page_url],
            capture_output=True, text=True, timeout=timeout,
        )
        if p.returncode == 0:
            for line in p.stdout.splitlines():
                line = line.strip()
                if line.startswith("http"):
                    return line
    except Exception:
        pass
    return None


def social_videos(q, limit=3):
    """Discover short relevant public video clips from Twitter/X & Pinterest via yt-dlp."""
    out = []
    seen = set()
    try:
        cand_pages = _ddg_links(f"(site:x.com/*/status OR site:twitter.com/*/status OR site:pinterest.com/pin) {q} video", limit=5)
        for page in cand_pages:
            if len(out) >= limit:
                break
            if page in seen:
                continue
            seen.add(page)
            direct = _ytdlp_direct_video(page, timeout=8)
            if direct:
                src_nm = "Twitter/X" if ("x.com" in page or "twitter.com" in page) else "Pinterest"
                out.append({
                    "kind": "video",
                    "url": direct,
                    "thumb": "",
                    "tags": f"{src_nm} {q}",
                    "credit": f"{src_nm} ({page[:60]})",
                    "max_secs": 5.0,
                })
    except Exception as e:
        log(f"  social video skip: {e}", show=False)
    return out
