"""v3.95 Official YouTube Data API v3 Resumable Uploader (Unlisted Default + Browser UA + 3x Retry + Telegram file_id Backup)."""
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse
import requests

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

CATEGORY_MAP = {
    "science": "28",
    "technology": "28",
    "tech": "28",
    "news": "25",
    "sports": "17",
    "history": "27",
    "business": "27",
    "army": "27",
    "mystery": "27",
    "influencer": "24",
    "general": "27",
}


def tg_send(token, chat_id, text):
    if not (token and chat_id):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": str(text)[:4000], "disable_web_page_preview": False},
            timeout=30,
        )
    except Exception as e:
        print("TG notify skip:", e)


def parse_video_source(raw_url):
    """Split optional '#vg_tg=<file_id>' or 'tgfile://<file_id>' backup tag from PUB_VIDEO_URL."""
    s = (raw_url or "").strip()
    if s.startswith("tgfile://"):
        return "", s[len("tgfile://"):].strip()
    if "#vg_tg=" in s:
        base, fid = s.split("#vg_tg=", 1)
        return base.strip(), fid.strip()
    return s, ""


def _is_valid_mp4(path):
    p = Path(path)
    if not p.exists() or p.stat().st_size < 20000:
        return False, f"size={p.stat().st_size if p.exists() else 0}B"
    try:
        with open(p, "rb") as f:
            head = f.read(64)
        low = head.lstrip().lower()
        if low.startswith((b"<!doctype", b"<html", b"<head", b"<?xml", b"{")):
            return False, "HTML/text error page instead of MP4"
        if b"ftyp" in head[:32] or head[:4] == b"\x1a\x45\xdf\xa3":
            return True, f"valid MP4 ({p.stat().st_size / (1024*1024):.1f} MB)"
        # Allow valid binary media if size > 100 KB and not HTML
        if p.stat().st_size > 100000:
            return True, f"binary video ({p.stat().st_size / (1024*1024):.1f} MB)"
        return False, f"unrecognized small header ({p.stat().st_size}B)"
    except Exception as e:
        return False, str(e)


def _download_from_url(url, dst_path, retries=3):
    clean_url = url.strip()
    if clean_url.startswith("http://tmpfiles.org/"):
        clean_url = "https://" + clean_url[len("http://"):]
    host = urlparse(clean_url).netloc or clean_url[:40]
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            with requests.get(
                clean_url,
                stream=True,
                timeout=180,
                allow_redirects=True,
                headers={"User-Agent": BROWSER_UA, "Accept": "video/mp4,application/octet-stream,*/*"},
            ) as r:
                ctype = (r.headers.get("Content-Type") or "").lower()
                if not r.ok:
                    last_err = f"{host} HTTP {r.status_code}"
                elif "text/html" in ctype:
                    last_err = f"{host} returned HTML page (expired/blocked)"
                else:
                    with open(dst_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    ok, note = _is_valid_mp4(dst_path)
                    if ok:
                        return True, f"{host} ({note})"
                    last_err = f"{host} invalid file ({note}, ctype={ctype or 'none'})"
        except Exception as e:
            last_err = f"{host} error: {str(e)[:80]}"
        if attempt < retries:
            time.sleep(2 * attempt)
    return False, last_err


def _download_from_telegram(tg_token, file_id, dst_path, retries=3):
    if not (tg_token and file_id):
        return False, "tg_file_id/token missing"
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{tg_token}/getFile",
                params={"file_id": file_id},
                timeout=30,
            )
            if not r.ok:
                last_err = f"TG getFile HTTP {r.status_code}"
            else:
                j = r.json() or {}
                fpath = ((j.get("result") or {}).get("file_path") or "").strip()
                if not fpath:
                    last_err = f"TG getFile no file_path: {str(j.get('description') or '')[:80]}"
                else:
                    dl_url = f"https://api.telegram.org/file/bot{tg_token}/{fpath}"
                    with requests.get(dl_url, stream=True, timeout=180) as dr:
                        if not dr.ok:
                            last_err = f"TG file download HTTP {dr.status_code}"
                        else:
                            with open(dst_path, "wb") as f:
                                for chunk in dr.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        f.write(chunk)
                            ok, note = _is_valid_mp4(dst_path)
                            if ok:
                                return True, f"Telegram backup ({note})"
                            last_err = f"TG invalid file ({note})"
        except Exception as e:
            last_err = f"TG backup error: {str(e)[:80]}"
        if attempt < retries:
            time.sleep(2 * attempt)
    return False, last_err


def get_access_token(client_id, client_secret, refresh_token):
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"YouTube OAuth token refresh failed ({r.status_code}): {r.text[:240]}")
    tok = (r.json() or {}).get("access_token")
    if not tok:
        raise RuntimeError("No access_token returned from Google OAuth")
    return tok


def download_video(video_url, dst_path, tg_token="", tg_file_id=""):
    clean_url, parsed_fid = parse_video_source(video_url)
    fid = (tg_file_id or parsed_fid or "").strip()
    errs = []

    if clean_url:
        ok, info = _download_from_url(clean_url, dst_path, retries=3)
        if ok:
            print("Downloaded video via direct link:", info)
            return dst_path
        errs.append(info)
        print("Direct video download failed:", info)

    if fid and tg_token:
        print("Trying Telegram permanent file_id backup...")
        ok2, info2 = _download_from_telegram(tg_token, fid, dst_path, retries=3)
        if ok2:
            print("Downloaded video via Telegram backup:", info2)
            return dst_path
        errs.append(info2)
        print("Telegram backup failed:", info2)

    raise RuntimeError("Video download fail (" + " | ".join(e for e in errs if e) + ")")


def build_snippet(title, description, tags_raw, mode="SHORT", category="general", privacy="unlisted"):
    clean_title = (title or "The Viral Gyaan").strip()
    if mode.upper() == "SHORT" and "#shorts" not in clean_title.lower() and len(clean_title) <= 91:
        clean_title = f"{clean_title} #Shorts"
    clean_title = clean_title[:100]

    clean_desc = (description or clean_title).strip()
    if mode.upper() == "SHORT" and "#shorts" not in clean_desc.lower():
        clean_desc += "\n\n#Shorts #TheViralGyaan"

    tags = []
    if isinstance(tags_raw, str):
        tags = [t.strip().lstrip("#") for t in tags_raw.replace("\n", ",").split(",") if t.strip()]
    elif isinstance(tags_raw, (list, tuple)):
        tags = [str(t).strip().lstrip("#") for t in tags_raw if str(t).strip()]
    tags = [t for t in dict.fromkeys(tags) if len(t) <= 30][:25]

    cat_id = CATEGORY_MAP.get((category or "general").strip().lower(), "27")
    priv = (privacy or "unlisted").strip().lower()
    if priv not in ("unlisted", "private", "public"):
        priv = "unlisted"

    return {
        "snippet": {
            "title": clean_title,
            "description": clean_desc[:4900],
            "tags": tags,
            "categoryId": cat_id,
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": priv,
            "selfDeclaredMadeForKids": False,
        },
    }


def upload_to_youtube(video_path, metadata, access_token):
    video_path = Path(video_path)
    file_size = video_path.stat().st_size

    init_r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": "video/mp4",
        },
        data=json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
        timeout=60,
    )
    if not init_r.ok:
        raise RuntimeError(f"YouTube upload init failed ({init_r.status_code}): {init_r.text[:260]}")

    upload_url = init_r.headers.get("Location")
    if not upload_url:
        raise RuntimeError("YouTube resumable upload Location header missing")

    with open(video_path, "rb") as f:
        up_r = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Length": str(file_size),
                "Content-Type": "video/mp4",
            },
            data=f,
            timeout=300,
        )
    if not up_r.ok:
        raise RuntimeError(f"YouTube video upload failed ({up_r.status_code}): {up_r.text[:260]}")

    data = up_r.json() or {}
    vid_id = data.get("id")
    if not vid_id:
        raise RuntimeError(f"YouTube upload response missing video id: {str(data)[:200]}")
    return vid_id


def main():
    tg_token = (os.environ.get("TG_TOKEN") or "").strip()
    tg_chat = (os.environ.get("TG_CHAT_ID") or "").strip()
    cid = (os.environ.get("YT_CLIENT_ID") or "").strip()
    csec = (os.environ.get("YT_CLIENT_SECRET") or "").strip()
    rtok = (os.environ.get("YT_REFRESH_TOKEN") or "").strip()

    video_url = (os.environ.get("PUB_VIDEO_URL") or "").strip()
    tg_file_id = (os.environ.get("PUB_TG_FILE_ID") or "").strip()
    title = (os.environ.get("PUB_TITLE") or "The Viral Gyaan").strip()
    desc = (os.environ.get("PUB_DESCRIPTION") or "").strip()
    tags = (os.environ.get("PUB_TAGS") or "").strip()
    mode = (os.environ.get("PUB_MODE") or "SHORT").strip().upper()
    category = (os.environ.get("PUB_CATEGORY") or "general").strip().lower()
    privacy = (os.environ.get("YT_PRIVACY") or "unlisted").strip().lower()

    if not (cid and csec and rtok):
        msg = "❌ YouTube Upload skipped: GitHub Secrets me YT_CLIENT_ID, YT_CLIENT_SECRET, aur YT_REFRESH_TOKEN add karein."
        print(msg)
        tg_send(tg_token, tg_chat, msg)
        sys.exit(1)

    if not (video_url or tg_file_id):
        msg = "❌ YouTube Upload fail: Video download URL aur Telegram backup dono khali hain."
        print(msg)
        tg_send(tg_token, tg_chat, msg)
        sys.exit(1)

    try:
        with tempfile.TemporaryDirectory(prefix="vg_yt_") as td:
            vpath = Path(td) / "upload.mp4"
            print("Downloading video from:", video_url.split("#")[0][:80] or "Telegram backup")
            download_video(video_url, vpath, tg_token=tg_token, tg_file_id=tg_file_id)
            print(f"Downloaded {vpath.stat().st_size / (1024*1024):.1f} MB -> getting OAuth token...")
            token = get_access_token(cid, csec, rtok)
            meta = build_snippet(title, desc, tags, mode=mode, category=category, privacy=privacy)
            vid_id = upload_to_youtube(vpath, meta, token)
            yt_link = f"https://youtu.be/{vid_id}"
            studio_link = f"https://studio.youtube.com/video/{vid_id}/edit"
            print("Uploaded successfully:", yt_link)
            tg_send(
                tg_token,
                tg_chat,
                f"✅ YouTube Upload Done ({privacy.upper()})!\n\n"
                f"🎬 {meta['snippet']['title']}\n"
                f"🔗 Preview: {yt_link}\n"
                f"⚙️ YT Studio: {studio_link}\n\n"
                f"👉 Phone me YouTube Studio khol kar 5 sec me copyright check + 'Altered/Synthetic Content' tick karke Public kar do!",
            )
    except Exception as e:
        err = f"❌ YouTube Upload fail: {str(e)[:340]}"
        print(err)
        tg_send(tg_token, tg_chat, err)
        sys.exit(1)


if __name__ == "__main__":
    main()
