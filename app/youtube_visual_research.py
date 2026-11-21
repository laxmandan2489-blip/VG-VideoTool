"""YouTube visual-reference research (metadata + thumbnails, never video ripping).
Uses official YouTube Data API discovery and Gemini vision on public thumbnails to
turn popular/relevant references into sharper search queries for licensed sources.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path
import requests
from common import TOOL, log

THUMB_TIMEOUT = 15
MAX_THUMB_BYTES = 2_000_000


def _thumb(url: str) -> bytes | None:
    if not url or not url.startswith("https://"):
        return None
    try:
        r = requests.get(url, timeout=THUMB_TIMEOUT, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200 or len(r.content) > MAX_THUMB_BYTES:
            return None
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((640, 360))
        out = io.BytesIO(); im.save(out, "JPEG", quality=82)
        return out.getvalue()
    except Exception:
        return None


def _safe_score(x):
    try: return max(0, min(100, int(x)))
    except Exception: return 0


def analyze_scene(script_line: str, show: str, candidates: list[dict], gemini_key: str,
                  max_candidates: int = 3) -> dict:
    """Visually inspect candidate thumbnails and select the most scene-relevant reference.
    Returns analysis + query hints. Thumbnails are reference-only, not used in final video.
    """
    if not candidates:
        return {"status":"no_youtube_results", "query_hints":[]}
    pool = sorted(candidates, key=lambda x: (int(x.get("view_count",0) or 0), x.get("search_order") == "relevance"), reverse=True)[:max_candidates]
    parts = ["You are a strict visual researcher for a Hindi factual video. Compare the user's exact scene with these YouTube reference thumbnails. Thumbnails are ONLY visual references, never assets to reuse. Judge literal scene relevance, named subject, action, location/time period and misleading stock imagery. Return JSON: {best_index: 0-based or -1, relevance: 0-100, visible_subject: short, visual_pattern: short, query_hints: [3-6 precise English search phrases], reject_reason: short}. Do not infer details not visibly supported.\nSCRIPT LINE: "+script_line+"\nSCENE DIRECTOR TARGET: "+show]
    valid=[]
    for x in pool:
        b=_thumb(x.get("thumbnail",""))
        if b:
            valid.append(x); parts.append({"jpg":b}); parts.append("REFERENCE "+str(len(valid)-1)+" | title="+str(x.get("title",""))[:180]+" | channel="+str(x.get("channel",""))[:100]+" | views="+str(x.get("view_count",0)))
    if not valid:
        return {"status":"thumbnail_unavailable", "query_hints":[]}
    result=None
    if gemini_key:
        try:
            from ai import ask_json
            result=ask_json(gemini_key, parts, temperature=0.2, timeout=75, budget=90)
        except Exception as e:
            log(f"  YouTube thumbnail visual analysis skip: {str(e)[:100]}", show=False)
    if not isinstance(result,dict):
        # Metadata-only fallback: useful titles, but do not claim thumbnail understanding.
        hints=[]
        for x in valid[:2]:
            title=re.sub(r"[^\w\s-]", " ", str(x.get("title","")), flags=re.UNICODE)
            if title.strip(): hints.append(title.strip()[:90]+" footage")
        return {"status":"metadata_fallback", "query_hints":hints, "references":valid}
    bi=result.get("best_index",0)
    try: bi=int(bi)
    except Exception: bi=0
    bi=max(0,min(len(valid)-1,bi)) if bi>=0 else -1
    hints=result.get("query_hints") or []
    if isinstance(hints,str): hints=[hints]
    hints=[str(h).strip()[:100] for h in hints if str(h).strip()][:6]
    return {"status":"thumbnail_analyzed", "best_index":bi, "relevance":_safe_score(result.get("relevance")),
            "visible_subject":str(result.get("visible_subject",""))[:180],
            "visual_pattern":str(result.get("visual_pattern",""))[:220], "query_hints":hints,
            "reject_reason":str(result.get("reject_reason",""))[:160], "references":valid}


def save_report(line_number: int, script_line: str, analysis: dict) -> None:
    """v3.13 FIX: lock + atomic write (pehle threads ek saath likhte the -> tooti JSON)."""
    path=TOOL/"temp"/"youtube_visual_research.json"
    try:
        from youtube_sources import update_json
        refs=[]
        for x in analysis.get("references",[]):
            refs.append({k:x.get(k) for k in ("title","channel","url","thumbnail","view_count","published_at","search_query")})
        row={"line_number":line_number+1,"script_line":script_line[:500],"analysis":{k:v for k,v in analysis.items() if k!="references"},"references":refs,
             "researched_at":datetime.now(timezone.utc).isoformat()}
        def _m(old):
            if not isinstance(old, dict): old={"items":[]}
            rows=[r for r in old.get("items",[]) if not (r.get("line_number")==line_number+1 and r.get("script_line")==script_line[:500])]
            rows.append(row); old["items"]=rows[-1000:]; old["updated_at"]=datetime.now(timezone.utc).isoformat()
            return old
        update_json(path, {"items":[]}, _m)
    except Exception as e: log(f"  YouTube visual report save skip: {e}",show=False)
