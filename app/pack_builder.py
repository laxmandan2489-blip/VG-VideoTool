"""v3.36 ONE-CLICK LOCAL STAR & GREEN-SCREEN PACK BUILDER (runs on user's laptop with their internet).

Builds a permanent local library inside VideoTool so future videos load instantly with 100% accurate
faces/subjects and crisp green-screen overlays:
  1. my_cutouts/  : High-res official public/Wikimedia photos of top Indian & global figures
                    (Narendra Modi, APJ Abdul Kalam, Elon Musk, Ratan Tata, Virat Kohli, MS Dhoni,
                    Vikram Sarabhai, ISRO Rocket, India Map, etc.) — auto-removes background if rembg installed.
  2. mere_motion/ : Downloads clean green-screen / documentary motion clips using user's existing Pixabay key.
"""
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent
CUTOUTS_DIR = TOOL / "my_cutouts"
MOTION_DIR = TOOL / "mere_motion"

# Top Indian & Global figures / icons for fact & documentary Shorts (Wikimedia official titles)
STARS = {
    "narendra_modi": "Narendra Modi",
    "apj_abdul_kalam": "A. P. J. Abdul Kalam",
    "elon_musk": "Elon Musk",
    "ratan_tata": "Ratan Tata",
    "vikram_sarabhai": "Vikram Sarabhai",
    "virat_kohli": "Virat Kohli",
    "ms_dhoni": "MS Dhoni",
    "mukesh_ambani": "Mukesh Ambani",
    "vladimir_putin": "Vladimir Putin",
    "donald_trump": "Donald Trump",
    "isro_lvm3": "LVM3",
    "james_webb": "James Webb Space Telescope",
}

PIXABAY_GREEN_QUERIES = [
    ("green_fire_explosion", "fire explosion green screen"),
    ("green_smoke_overlay", "smoke overlay black background"),
    ("green_money_rain", "dollar money falling green screen"),
    ("green_glitch_fx", "glitch effect overlay"),
    ("green_lightning_fx", "lightning bolt black background"),
]


def _read_pixabay_key():
    for fname in ("api keys.txt", ".env"):
        p = TOOL / fname
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"PIXABAY[A-Z_]*\s*[:=]\s*([^\s'\"#]+)", txt, re.I)
            if m:
                return m.group(1).strip()
    return os.environ.get("PIXABAY_API_KEY", "").strip()


def _download_wiki_star(slug, wiki_title):
    import requests
    out_png = CUTOUTS_DIR / f"{slug}.png"
    out_jpg = CUTOUTS_DIR / f"{slug}.jpg"
    if out_png.exists() or out_jpg.exists():
        print(f"  [SKIP] {slug} pehle se maujood hai.")
        return
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(wiki_title)
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "VG-VideoTool/3.36"})
        if r.status_code != 200:
            return
        data = r.json()
        img_url = (data.get("originalimage") or data.get("thumbnail") or {}).get("source")
        if not img_url:
            return
        ir = requests.get(img_url, timeout=25, headers={"User-Agent": "VG-VideoTool/3.36"})
        if ir.status_code != 200 or len(ir.content) < 5000:
            return
        # Try automatic background removal with rembg if installed; else save crisp JPG
        try:
            import io
            from PIL import Image
            from rembg import remove
            im = Image.open(io.BytesIO(ir.content)).convert("RGBA")
            cut = remove(im)
            cut.save(out_png)
            print(f"  [OK PNG Cutout] {slug}.png")
        except Exception:
            out_jpg.write_bytes(ir.content)
            print(f"  [OK Photo] {slug}.jpg")
    except Exception as e:
        print(f"  [SKIP] {slug}: {str(e)[:60]}")


def _download_pixabay_fx(key):
    if not key:
        print("Pixabay key nahi mili — green-screen download skip.")
        return
    import requests
    MOTION_DIR.mkdir(parents=True, exist_ok=True)
    for slug, q in PIXABAY_GREEN_QUERIES:
        out_mp4 = MOTION_DIR / f"{slug}.mp4"
        if out_mp4.exists():
            print(f"  [SKIP] {out_mp4.name} pehle se hai.")
            continue
        try:
            r = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": key, "q": q, "per_page": 3},
                timeout=20,
            ).json()
            hits = r.get("hits") or []
            if not hits:
                continue
            vurl = (hits[0].get("videos") or {}).get("medium", {}).get("url")
            if not vurl:
                continue
            vr = requests.get(vurl, timeout=45)
            if vr.status_code == 200 and len(vr.content) > 20000:
                out_mp4.write_bytes(vr.content)
                print(f"  [OK FX] {out_mp4.name}")
        except Exception as e:
            print(f"  [SKIP FX] {slug}: {str(e)[:60]}")


def main():
    CUTOUTS_DIR.mkdir(parents=True, exist_ok=True)
    MOTION_DIR.mkdir(parents=True, exist_ok=True)
    print("=== 1) Leaders & Icons Local Library (my_cutouts/) ===")
    for slug, title in STARS.items():
        _download_wiki_star(slug, title)
    print("\n=== 2) Pixabay Motion & Green-Screen FX (mere_motion/) ===")
    _download_pixabay_fx(_read_pixabay_key())
    print("\n[DONE] Aapka local Star & FX Pack tayyar hai! (my_cutouts/ & mere_motion/)")


if __name__ == "__main__":
    main()
