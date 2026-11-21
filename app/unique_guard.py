"""v3.21 STRICT NO-REPEATED-FOOTAGE GUARD (CPU-lightweight, <2MB RAM).

Prevents the same source video or visually identical clip/frame from appearing twice
in a single generated video by tracking:
  1. Normalized source URL / asset ID
  2. File SHA-256 content hash (catches renamed duplicates)
  3. 64-bit perceptual dHash on middle frame (catches re-encoded / cropped duplicates)
"""
import hashlib
import io
import subprocess
from pathlib import Path
from PIL import Image


def _sha256_fast(path, max_bytes=2 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(max_bytes))
    return h.hexdigest()


def _dhash(im, size=8):
    g = im.convert("L").resize((size + 1, size), Image.Resampling.BILINEAR)
    px = list(g.getdata())
    bits = 0
    for row in range(size):
        off = row * (size + 1)
        for col in range(size):
            bits = (bits << 1) | (1 if px[off + col] > px[off + col + 1] else 0)
    return bits


def _hamming(a, b):
    return (a ^ b).bit_count()


def _mid_frame(path, kind="video"):
    p = Path(path)
    if not p.exists():
        return None
    try:
        if kind == "image" or p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            return Image.open(p).convert("RGB")
        r = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-ss", "1.0", "-i", str(p),
             "-frames:v", "1", "-vf", "scale=160:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
            capture_output=True, timeout=15, stdin=subprocess.DEVNULL,
        )
        if r.stdout:
            return Image.open(io.BytesIO(r.stdout)).convert("RGB")
    except Exception:
        pass
    return None


class UniqueAssetGuard:
    """Session-scoped registry ensuring zero repeated footage in one video."""

    def __init__(self, dhash_threshold=8):
        self.urls = set()
        self.hashes = set()
        self.dhashes = []
        self.threshold = dhash_threshold

    def _norm_url(self, u):
        return str(u or "").strip().lower().split("#")[0]

    def is_duplicate(self, item):
        if not isinstance(item, dict):
            return False
        url = self._norm_url(item.get("url") or item.get("src_url") or "")
        if url and url in self.urls:
            return True
        p = item.get("path")
        if p and Path(str(p)).exists():
            try:
                sha = _sha256_fast(p)
                if sha in self.hashes:
                    return True
                im = _mid_frame(p, item.get("kind", "video"))
                if im is not None:
                    dh = _dhash(im)
                    if any(_hamming(dh, prev) <= self.threshold for prev in self.dhashes):
                        return True
            except Exception:
                pass
        return False

    def register(self, item):
        if not isinstance(item, dict):
            return
        url = self._norm_url(item.get("url") or item.get("src_url") or "")
        if url:
            self.urls.add(url)
        p = item.get("path")
        if p and Path(str(p)).exists():
            try:
                self.hashes.add(_sha256_fast(p))
                im = _mid_frame(p, item.get("kind", "video"))
                if im is not None:
                    self.dhashes.append(_dhash(im))
            except Exception:
                pass
