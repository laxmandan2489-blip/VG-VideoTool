"""FootageFlow-inspired media search/link-download adapter for VG Video Tool.

This is an integration layer, not a bundled copy of the FootageFlow desktop app.
It reuses VG's existing licensed providers and adds a bounded yt-dlp adapter for
public URLs only when a reusable licence or explicit rights-holder permission is
recorded. No cookies, login bypass, DRM bypass, private media, or paywall bypass.
"""
from __future__ import annotations
import json
import re
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SUPPORTED_HOSTS = {
    "vimeo.com", "www.vimeo.com", "player.vimeo.com",
    "dailymotion.com", "www.dailymotion.com", "dai.ly",
    "x.com", "www.x.com", "twitter.com", "www.twitter.com",
}
BLOCKED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be",
                 "youtube-nocookie.com", "www.youtube-nocookie.com", "googlevideo.com", "www.googlevideo.com",
                 "ytimg.com", "www.ytimg.com", "youtubeusercontent.com", "www.youtubeusercontent.com",
                 "instagram.com", "www.instagram.com", "facebook.com", "www.facebook.com", "tiktok.com", "www.tiktok.com"}


def parse_time(value: str | None) -> float | None:
    if not value:
        return None
    s = str(value).strip()
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", s):
            return float(s)
        parts = s.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except (TypeError, ValueError):
        return None
    return None


def parse_link_hint(hint: str) -> dict:
    """Parse optional URL metadata in a script line's || hint."""
    text = hint or ""
    rights = re.search(r"\bRIGHTS\s*=\s*(CC[-_ ]?BY|CC0|PUBLIC[-_ ]?DOMAIN|PERMISSION)\b", text, re.I)
    start = re.search(r"\bSTART\s*=\s*([0-9:.]+)", text, re.I)
    end = re.search(r"\bEND\s*=\s*([0-9:.]+)", text, re.I)
    return {
        "rights": re.sub(r"[ _]", "-", rights.group(1)).upper() if rights else "",
        "start": parse_time(start.group(1)) if start else None,
        "end": parse_time(end.group(1)) if end else None,
    }


def host_allowed(url: str) -> tuple[bool, str]:
    try:
        p = urlparse(url)
        if p.scheme != "https" or not p.hostname:
            return False, "sirf HTTPS public media URLs allowed hain"
        host = p.hostname.lower()
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}:
            return False, "YouTube download is disabled for API/Terms compliance; use the official player or a creator-hosted authorized source file"
        if host in BLOCKED_HOSTS:
            return False, "Instagram/Facebook/TikTok direct download is adapter mein supported nahi; official source kholen"
        if host not in SUPPORTED_HOSTS:
            return False, "ye public link supported provider domain se nahi hai"
        return True, ""
    except Exception:
        return False, "invalid media URL"


def _rights_ok(rights: str, explicit_permission: bool = False) -> bool:
    r = (rights or "").upper().replace("_", "-").replace(" ", "-")
    return explicit_permission or r in {"CC-BY", "CCBY", "CC0", "PUBLIC-DOMAIN"}


def _sidecar(path: Path, meta: dict) -> None:
    payload = dict(meta)
    payload["downloaded_at"] = datetime.now(timezone.utc).isoformat()
    payload["local_file"] = path.name
    try:
        path.with_suffix(path.suffix + ".source.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [f"Title: {payload.get('title','')}", f"Creator/channel: {payload.get('creator','')}",
                 f"Source: {payload.get('source_url','')}", f"Rights: {payload.get('rights_status','unknown')}",
                 f"Clip: {payload.get('clip_start','')} - {payload.get('clip_end','')}",
                 "Verify the original source and licence before publishing."]
        path.with_suffix(path.suffix + ".source.txt").write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def _yt_dlp_download(url: str, output_dir: Path, start: float | None, end: float | None,
                     meta: dict) -> Path | None:
    try:
        import yt_dlp
        from yt_dlp.utils import download_range_func
    except Exception:
        try:
            from common import log
            log("  FootageFlow Link Downloader: yt-dlp install nahi hai; 1_SETUP dobara chalao.", show=False)
        except Exception:
            pass
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", str(meta.get("video_id") or ""))[:80] or hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]
    outtmpl = str(output_dir / f"ff_{safe_id}.%(ext)s")
    opts = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "merge_output_format": "mp4", "outtmpl": outtmpl,
        "noplaylist": True, "ignoreconfig": True, "quiet": True, "no_warnings": True,
        "retries": 2, "fragment_retries": 2, "socket_timeout": 25,
        "max_filesize": 500 * 1024 * 1024, "overwrites": False,
        "nocheckcertificate": False, "cachedir": False,
    }
    if start is not None and end is not None and end > start:
        opts["download_ranges"] = download_range_func(None, [(start, end)])
        opts["force_keyframes_at_cuts"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        try:
            from common import log
            log(f"  FootageFlow download fail: {str(e)[:180]}", show=False)
        except Exception:
            pass
        return None
    candidates = sorted(output_dir.glob(f"ff_{safe_id}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in candidates:
        if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".m4v"} and p.stat().st_size > 20000:
            _sidecar(p, meta)
            return p
    return None


def download_authorized_link(item: dict, output_dir: Path) -> Path | None:
    """Download only a supported public URL with verified CC/PD or explicit permission."""
    url = str(item.get("url") or "")
    ok, why = host_allowed(url)
    if not ok:
        from common import log
        log(f"  FootageFlow: {why}", show=False)
        return None
    rights = str(item.get("rights_status") or "")
    permission = bool(item.get("explicit_permission"))
    if not _rights_ok(rights, permission):
        from common import log
        log("  FootageFlow: rights unknown – download/render block. Hint mein RIGHTS=CC-BY / CC0 / PUBLIC-DOMAIN ya RIGHTS=PERMISSION likhein.", show=False)
        return None
    start, end = item.get("start"), item.get("end")
    if (start is None) != (end is None) or (start is not None and (end <= start or end - start > 90)):
        from common import log
        log("  FootageFlow: START/END range invalid (max 90 sec).", show=False)
        return None
    return _yt_dlp_download(url, output_dir, start, end, {
        "provider": "FootageFlow-compatible yt-dlp adapter", "title": item.get("title", ""),
        "creator": item.get("creator", ""), "source_url": url, "rights_status": rights,
        "rights_basis": "explicit user confirmation" if permission else "declared reusable licence; verify original page",
        "clip_start": start, "clip_end": end,
    })


