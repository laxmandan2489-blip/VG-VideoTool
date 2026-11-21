"""Opt-in downloader for YouTube videos the user owns or is licensed to reuse.
No DRM, private-video, or access-control bypass. Requires yt-dlp installed.
"""
from pathlib import Path
import re, shutil, subprocess

YOUTUBE_RE = re.compile(
    r"^https?://(?:(?:www|m|music)\\.)?(?:youtube\\.com/(?:watch(?:\\?|/)|shorts/|embed/|live/)|youtu\\.be/)[A-Za-z0-9_-]{6,}",
    re.I,
)

def is_watch_url(url: str) -> bool:
    return bool(YOUTUBE_RE.match((url or "").strip()))

def download_authorized(url: str, output_dir: Path, *, reuse_rights_confirmed=False, timeout=240):
    """Download only with explicit user confirmation of reuse rights."""
    if not reuse_rights_confirmed:
        raise PermissionError("Confirm that you own/have permission to reuse this video.")
    if not is_watch_url(url):
        raise ValueError("Expected a standard YouTube watch/share URL (not googlevideo CDN).")
    exe = shutil.which("yt-dlp")
    if not exe:
        raise RuntimeError("yt-dlp is not installed; install it first.")
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "%(id)s.%(ext)s"
    cmd = [exe, "--no-playlist", "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
           "--merge-output-format", "mp4", "--output", str(out), url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-1800:])
    files = sorted(output_dir.glob("*"), key=lambda p:p.stat().st_mtime, reverse=True)
    return files[0] if files else None
