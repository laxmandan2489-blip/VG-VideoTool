"""v3.1 LOCAL AI VIDEO MANAGER – FreeVideo (MiniMax H3 / VDN-H3, ComfyUI plugin) OPTIONAL backend.

Sach (FreeVideo README, 2026-10): kam se kam 8 GB NVIDIA VRAM + 16 GB RAM chahiye; Windows pe FreeVideo.exe
ComfyUI + models khud download karta hai. Model weights: MiniMax H3 Community License (code Apache-2.0).

Aapke laptop (8 GB RAM) pe ye LOCAL nahi chalega – ye module isko jaanchta hai, crash nahi karta, aur:
  * agar kisi doosre PC / cloud GPU pe ComfyUI+FreeVideo chal raha ho:  api keys.txt  ->  COMFYUI_URL=http://IP:8188
    to wahan se clip banwata hai (text->video, image->video / first frame, Blender frame se video).
  * workflow: ComfyUI me FreeVideo workflow kholo -> "Export (API)" -> VideoTool\\local_ai\\freevideo_workflow_api.json
    us JSON me in jagah placeholders likho: {{PROMPT}} {{NEGATIVE}} {{SEED}} {{SECONDS}} {{WIDTH}} {{HEIGHT}} {{IMAGE}}
  * koi model bina poochhe download NAHI hota.
"""
import json, os, random, shutil, time, uuid
from pathlib import Path
import requests

TOOL = Path(__file__).resolve().parent.parent
DIR = TOOL / "local_ai"
WF = DIR / "freevideo_workflow_api.json"
CACHE = TOOL / "temp" / "ai_video_cache"
STATE = {"checked": False, "ok": False, "why": "", "url": None}
MIN_VRAM, MIN_RAM, MIN_DISK = 8, 16, 60


def compat(rep=None):
    """(local_ok, reason) – asli hardware report se."""
    try:
        import hardware
        rep = rep or hardware.detect(write=False)
    except Exception as e:
        return False, f"hardware check nahi hua: {e}"
    vram = max([g.get("vram_gb") or 0 for g in rep.get("gpus", []) if g.get("cuda")] or [0])
    why = []
    if vram < MIN_VRAM: why.append(f"NVIDIA VRAM {vram} GB < {MIN_VRAM} GB")
    if (rep.get("ram_gb") or 0) < MIN_RAM: why.append(f"RAM {rep.get('ram_gb')} GB < {MIN_RAM} GB")
    if (rep.get("disk_free_gb") or 0) < MIN_DISK: why.append(f"disk {rep.get('disk_free_gb')} GB < {MIN_DISK} GB")
    return (not why), ("; ".join(why) or "OK")


def server(keys=None):
    """ComfyUI URL (local 127.0.0.1:8188 ya COMFYUI_URL) jo sach me jawab de raha ho."""
    if STATE["checked"]:
        return STATE["url"]
    STATE["checked"] = True
    urls = []
    k = (keys or {}).get("COMFYUI_URL") or (keys or {}).get("COMFYUI") or os.environ.get("COMFYUI_URL")
    if k: urls.append(k.rstrip("/"))
    urls.append("http://127.0.0.1:8188")
    for u in urls:
        try:
            r = requests.get(u + "/system_stats", timeout=4)
            if r.status_code == 200:
                STATE.update(ok=True, url=u, why="")
                return u
        except Exception:
            continue
    STATE["why"] = "ComfyUI server nahi mila (127.0.0.1:8188 / COMFYUI_URL)"
    return None


def available(keys=None):
    if not WF.exists():
        return False, f"workflow file nahi hai: {WF}"
    u = server(keys)
    return (u is not None), (u or STATE["why"])


def _fill(obj, rep):
    if isinstance(obj, dict): return {k: _fill(v, rep) for k, v in obj.items()}
    if isinstance(obj, list): return [_fill(v, rep) for v in obj]
    if isinstance(obj, str):
        for k, v in rep.items():
            if obj == "{{%s}}" % k: return v                     # number placeholder -> asli number
            obj = obj.replace("{{%s}}" % k, str(v))
    return obj


def _upload(u, image):
    with open(image, "rb") as f:
        r = requests.post(u + "/upload/image", files={"image": (Path(image).name, f, "image/png")},
                          data={"overwrite": "true"}, timeout=60)
    r.raise_for_status()
    return r.json().get("name") or Path(image).name


def generate(prompt, out, seconds=4.0, W=576, H=1024, image=None, negative="", keys=None, timeout=900,
             log=None, cancel=None, retries=1):
    """ComfyUI se video banwao. Return out path ya None. cancel(): True lautaye to /interrupt."""
    log = log or (lambda *a, **k: None)
    ok, why = available(keys)
    if not ok:
        log(f"   (local AI video band: {why})", show=False); return None
    u = STATE["url"]
    CACHE.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries + 1):
        try:
            rep = {"PROMPT": prompt, "NEGATIVE": negative or "text, watermark, deformed", "SEED": random.randint(1, 2**31),
                   "SECONDS": float(seconds), "WIDTH": int(W), "HEIGHT": int(H),
                   "IMAGE": _upload(u, image) if image else ""}
            wf = _fill(json.loads(WF.read_text(encoding="utf-8")), rep)
            cid = str(uuid.uuid4())
            r = requests.post(u + "/prompt", json={"prompt": wf, "client_id": cid}, timeout=60)
            r.raise_for_status(); pid = r.json()["prompt_id"]
            t0 = time.time(); last = -1
            while True:
                if cancel and cancel():
                    requests.post(u + "/interrupt", timeout=10); log("   AI video cancel kiya"); return None
                if time.time() - t0 > timeout:
                    requests.post(u + "/interrupt", timeout=10); raise TimeoutError(f"{timeout}s")
                h = requests.get(f"{u}/history/{pid}", timeout=30).json()
                if pid in h:
                    outs = h[pid].get("outputs", {})
                    for node in outs.values():
                        for key in ("gifs", "videos", "images"):
                            for f in node.get(key, []) or []:
                                fn = f.get("filename", "")
                                if fn.lower().endswith((".mp4", ".webm", ".mov")):
                                    v = requests.get(u + "/view", params={"filename": fn, "subfolder": f.get("subfolder", ""),
                                                                          "type": f.get("type", "output")}, timeout=300)
                                    Path(out).write_bytes(v.content)
                                    log(f"   🤖 AI video bana ({time.time()-t0:.0f}s)")
                                    return str(out)
                    raise RuntimeError("workflow ne video output nahi diya")
                el = int(time.time() - t0)
                if el // 30 != last:
                    last = el // 30; log(f"   🤖 AI video ban raha hai... {el}s", show=False)
                time.sleep(3)
        except Exception as e:
            log(f"   AI video koshish {attempt+1} fail: {str(e)[:120]}", show=False)
    return None


def storage_plan():
    """Install se pehle disk ka hisaab (FreeVideo README sizes nahi deta – isliye safe andaza)."""
    try:
        free = shutil.disk_usage(str(TOOL)).free / 1024 ** 3
    except Exception:
        free = 0
    need = {"ComfyUI + Python env": 8, "VDN-H3 video model (int8)": 25, "H3 text encoder": 10,
            "video/audio decoder + caches": 6, "kaam ke liye khaali jagah": 10}
    return {"free_gb": round(free, 1), "need_gb": need, "total_gb": sum(need.values()),
            "enough": free >= sum(need.values()),
            "note": "Sizes andaza hain (README me exact size nahi likha). Download se pehle FreeVideo launcher asli size dikhata hai."}


if __name__ == "__main__":
    ok, why = compat()
    print("FreeVideo LOCAL:", "HAAN" if ok else "NAHI", "-", why)
    print("Storage:", json.dumps(storage_plan(), indent=2))
    print("ComfyUI server:", server() or STATE["why"])
