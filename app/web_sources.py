"""v2.22: Google ke ALAWA aur jagah se photo / video (Google ki image API naye logon ke liye band hai).

BINA KEY (free):
  coverr_videos    – Coverr HD stock videos (free, commercial use)
  archive_videos   – Internet Archive (Prelinger / purani public-domain films – itihaas, ghatnayein)
  loc_photos       – Library of Congress (purani asli photos – itihaas, log, jagah)
FREE KEY:
  pexels_photos    – PEXELS = ...      (wahi key jo Pexels video ki hai)
  unsplash_photos  – UNSPLASH = ...    (unsplash.com/developers – free)
  flickr_cc        – FLICKR = ...      (flickr.com/services/api – free; sirf CC / public-domain photos)
GOOGLE IMAGES JAISA (asli web photos – COPYRIGHT ho sakta hai, credits me "WEB PHOTO" likha aata hai):
  serper_images    – SERPER = ...      (serper.dev – Google Images ke result; 2500 free queries)
  (brave_images sources.py me hai – BRAVE = ...)
Har function list deta hai: [{kind, url, thumb, credit, tags?, web?}] – sources.download() seedha le leta hai.
"""
import re
from common import log

TIMEOUT = 20
FLICKR_OK = {"4": "CC BY 2.0", "5": "CC BY-SA 2.0", "7": "No known copyright", "8": "US Government Work",
             "9": "CC0", "10": "Public Domain Mark"}


def _S():
    import sources
    return sources.S


def _dom(u):
    return re.sub(r"^https?://(www\.)?", "", u or "").split("/")[0]


# ------------------------------------------------------------------ Google Images (Serper.dev)
def serper_images(q, key, n=10):
    if not key: return []
    try:
        r = _S().post("https://google.serper.dev/images", json={"q": q, "num": n},
                      headers={"X-API-KEY": key, "Content-Type": "application/json"}, timeout=TIMEOUT)
        if r.status_code != 200:
            log(f"  serper {r.status_code}: {r.text[:120]}", show=False); return []
        res = r.json().get("images", [])
    except Exception as e:
        log(f"  serper error: {e}", show=False); return []
    out = []
    for x in res:
        u = x.get("imageUrl")
        if not u or u.lower().split("?")[0].endswith((".svg", ".gif")): continue
        if max(x.get("imageWidth") or 0, x.get("imageHeight") or 0) and max(x.get("imageWidth") or 0, x.get("imageHeight") or 0) < 500:
            continue
        page = x.get("link") or ""
        out.append({"kind": "image", "url": u, "thumb": x.get("thumbnailUrl"), "tags": x.get("title", ""),
                    "credit": f"WEB PHOTO (Google Images) – {x.get('domain') or _dom(page)} ({page}) – copyright check karo",
                    "web": True})
    return out


# ------------------------------------------------------------------ free stock photos
def pexels_photos(q, key, n=12):
    if not key: return []
    try:
        r = _S().get("https://api.pexels.com/v1/search", params={"query": q, "per_page": n},
                     headers={"Authorization": key}, timeout=TIMEOUT)
        ph = r.json().get("photos", [])
    except Exception as e:
        log(f"  pexels photo error: {e}", show=False); return []
    out = []
    for p in ph:
        s = p.get("src") or {}
        u = s.get("large2x") or s.get("original")
        if not u: continue
        out.append({"kind": "image", "url": u, "thumb": s.get("medium"), "tags": p.get("alt", ""),
                    "credit": f"Pexels – {p.get('photographer','')} ({p.get('url','')})"})
    return out


def unsplash_photos(q, key, n=12):
    if not key: return []
    try:
        r = _S().get("https://api.unsplash.com/search/photos", params={"query": q, "per_page": n, "content_filter": "high"},
                     headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}, timeout=TIMEOUT)
        res = r.json().get("results", [])
    except Exception as e:
        log(f"  unsplash error: {e}", show=False); return []
    out = []
    for p in res:
        u = (p.get("urls") or {}).get("regular")
        if not u: continue
        user = (p.get("user") or {}).get("name", "")
        dl = (p.get("links") or {}).get("download_location")
        out.append({"kind": "image", "url": u, "thumb": (p.get("urls") or {}).get("small"),
                    "tags": " ".join(filter(None, [p.get("alt_description") or "", p.get("description") or ""])),
                    "credit": f"Unsplash – {user} ({(p.get('links') or {}).get('html','')})", "unsplash_dl": dl})
    return out


def unsplash_ping(item, key):
    """Unsplash ka niyam: photo use ho to download_location ko ek baar batao."""
    if key and item.get("unsplash_dl"):
        try:
            _S().get(item["unsplash_dl"], headers={"Authorization": f"Client-ID {key}"}, timeout=10)
        except Exception:
            pass


def flickr_cc(q, key, n=15):
    """Asli jagah / ghatna / log – sirf commercial-ok CC / public-domain photos."""
    if not key: return []
    try:
        r = _S().get("https://api.flickr.com/services/rest/", params={
            "method": "flickr.photos.search", "api_key": key, "text": q, "license": ",".join(FLICKR_OK),
            "sort": "relevance", "content_type": 1, "media": "photos", "safe_search": 1, "per_page": n,
            "extras": "url_l,url_c,url_m,owner_name,license,tags", "format": "json", "nojsoncallback": 1}, timeout=TIMEOUT)
        ph = (r.json().get("photos") or {}).get("photo", [])
    except Exception as e:
        log(f"  flickr error: {e}", show=False); return []
    out = []
    for p in ph:
        u = p.get("url_l") or p.get("url_c")
        if not u: continue
        lic = FLICKR_OK.get(str(p.get("license")), "")
        page = f"https://www.flickr.com/photos/{p.get('owner')}/{p.get('id')}"
        out.append({"kind": "image", "url": u, "thumb": p.get("url_m") or u, "tags": (p.get("title", "") + " " + p.get("tags", ""))[:200],
                    "credit": f"Flickr – {p.get('ownername','')} – {lic} ({page})"})
    return out


def loc_photos(q, n=20):
    """Library of Congress – purani asli photos. Sirf jahan rights me 'no known restrictions / public domain'."""
    try:
        r = _S().get("https://www.loc.gov/photos/", params={"q": q, "fo": "json", "c": n}, timeout=TIMEOUT,
                     headers={"Accept": "application/json"})
        res = r.json().get("results", [])
    except Exception as e:
        log(f"  loc error: {e}", show=False); return []
    out = []
    for it in res:
        rights = it.get("rights") or it.get("rights_information") or ""
        if isinstance(rights, list): rights = " ".join(x for x in rights if isinstance(x, str))
        rl = rights.lower()
        if not ("no known restrictions" in rl or "public domain" in rl or "no known copyright" in rl):
            continue
        ims = it.get("image_url") or []
        if isinstance(ims, str): ims = [ims]
        ims = [u if u.startswith("http") else "https:" + u for u in ims if isinstance(u, str) and u]
        if not ims: continue
        big = ims[-1]                                    # aakhri = sabse badi
        big = re.sub(r"#h=\d+&w=\d+", "", big)
        title = it.get("title", "") or ""
        out.append({"kind": "image", "url": big, "thumb": ims[0], "tags": title[:200],
                    "credit": f"Library of Congress – {title[:60]} – no known restrictions ({it.get('id','')})"})
    return out


# ------------------------------------------------------------------ free stock videos
def coverr_videos(q, n=12):
    try:
        r = _S().get("https://api.coverr.co/videos", params={"query": q, "page_size": n, "urls": "true"}, timeout=TIMEOUT)
        d = r.json()
        hits = d.get("hits") or d.get("videos") or []
    except Exception as e:
        log(f"  coverr error: {e}", show=False); return []
    out = []
    for v in hits:
        u = v.get("urls") or {}
        url = u.get("mp4_download") or u.get("mp4_1080") or u.get("mp4") or u.get("mp4_720")
        if not url: continue
        w, h = int(v.get("max_width") or v.get("width") or 1920), int(v.get("max_height") or v.get("height") or 1080)
        tags = v.get("tags") or ""
        if isinstance(tags, list): tags = " ".join(str(t) for t in tags)
        out.append({"kind": "video", "url": url, "portrait": h > w, "thumb": u.get("poster") or u.get("thumbnail") or v.get("poster"),
                    "tags": f"{v.get('title','')} {tags}"[:200],
                    "credit": f"Coverr – {v.get('title','')} (https://coverr.co/videos/{v.get('slug','')})"})
    return out


ARCHIVE_FORMATS = ("h.264", "MPEG4", "h.264 IA", "512Kb MPEG4")


def archive_videos(q, n=6):
    """Internet Archive – purani public-domain / CC films (itihaas, ghatnayein, purane shahar)."""
    toks = sorted({t for t in re.findall(r"[a-z]{3,}", q.lower())}, key=len, reverse=True)[:3]
    if not toks: return []
    queries = [f'"{" ".join(toks)}"~10', " AND ".join(toks[:2]), " OR ".join(toks)]
    docs = []
    for sq in queries:
        try:
            r = _S().get("https://archive.org/advancedsearch.php", params=[
                ("q", f"({sq}) AND mediatype:movies AND (collection:prelinger OR collection:opensource_movies OR "
                      f"licenseurl:*publicdomain* OR licenseurl:*creativecommons.org/licenses/by/*)"),
                ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "licenseurl"), ("fl[]", "collection"),
                ("rows", str(n)), ("output", "json")], timeout=TIMEOUT)
            docs = (r.json().get("response") or {}).get("docs", [])
        except Exception as e:
            log(f"  archive error: {e}", show=False); return []
        if docs: break
    out = []
    for d in docs[:n]:
        ident = d.get("identifier")
        if not ident: continue
        try:
            files = _S().get(f"https://archive.org/metadata/{ident}/files", timeout=TIMEOUT).json().get("result", [])
        except Exception:
            continue
        pick = None
        for fmt in ARCHIVE_FORMATS:
            c = [f for f in files if (f.get("format") or "") == fmt and f.get("name", "").lower().endswith(".mp4")
                 and int(f.get("size") or 0) < 400 * 1024 * 1024]
            if c:
                pick = min(c, key=lambda f: int(f.get("size") or 0)); break
        if not pick: continue
        lic = d.get("licenseurl") or ("Public domain (Prelinger)" if "prelinger" in str(d.get("collection")) else "CC")
        out.append({"kind": "video", "url": f"https://archive.org/download/{ident}/{pick['name']}", "portrait": False,
                    "thumb": f"https://archive.org/services/img/{ident}", "tags": str(d.get("title", ""))[:200],
                    "credit": f"Internet Archive – {str(d.get('title',''))[:60]} – {lic} (https://archive.org/details/{ident})"})
    return out
