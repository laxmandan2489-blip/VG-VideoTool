"""v2.18b: KOKORO (laptop pe chalne wali free, unlimited AI awaaz) ka DEMO – sirf sunne ke liye.
Pasand aaye to agle update me Gemini ka backup banega.

Chalana: python kokoro_demo.py <out.json> [hindi line]
Pehli baar: kokoro-onnx install (~50 MB) + model download (~330 MB) – ek hi baar.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
from common import TOOL

DIR = TOOL / "ai_aankh" / "kokoro"
FILES = {"kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
         "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"}
VOICES = ["hm_omega", "hm_psi", "hf_alpha", "hf_beta"]       # hm = aadmi, hf = aurat


def main():
    out = Path(sys.argv[1])
    line = sys.argv[2] if len(sys.argv) > 2 else "समुद्र की सबसे गहरी जगह इतनी गहरी है कि उसमें माउंट एवरेस्ट भी डूब जाए।"
    res = {"ok": False, "files": [], "err": ""}
    try:
        try:
            import kokoro_onnx  # noqa
        except Exception:
            print("1) (pehli baar) Kokoro install ho raha hai...", flush=True)
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "kokoro-onnx", "soundfile"],
                               capture_output=True, text=True, timeout=1500, stdin=subprocess.DEVNULL)
            if r.returncode != 0:
                raise RuntimeError("install nahi hua: " + r.stderr[-300:])
        import requests
        DIR.mkdir(parents=True, exist_ok=True)
        for name, url in FILES.items():
            fp = DIR / name
            if fp.exists() and fp.stat().st_size > 1_000_000: continue
            print(f"2) (pehli baar) model download: {name} ...", flush=True)
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = fp.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for ch in r.iter_content(1 << 20): f.write(ch)
                tmp.replace(fp)
        print("3) Kokoro awaaz bana raha hoon...", flush=True)
        from kokoro_onnx import Kokoro
        import soundfile as sf
        k = Kokoro(str(DIR / "kokoro-v1.0.onnx"), str(DIR / "voices-v1.0.bin"))
        for v in VOICES:
            try:
                samples, sr = k.create(line, voice=v, speed=1.0, lang="hi")
                wav = out.with_name(f"kokoro_{v}.wav"); sf.write(str(wav), samples, sr)
                ogg = wav.with_suffix(".ogg")
                subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(wav), "-c:a", "libopus", "-b:a", "48k",
                                str(ogg)], capture_output=True, timeout=60)
                res["files"].append({"voice": v, "file": str(ogg if ogg.exists() else wav)})
                print(f"   {v} ✓", flush=True)
            except Exception as e:
                print(f"   {v}: {e}", flush=True)
        res["ok"] = bool(res["files"])
        if not res["ok"]: res["err"] = "koi awaaz nahi bani (Hindi support / model)"
    except Exception as e:
        res["err"] = str(e)[:300]
        print("   Kokoro nahi chala: " + res["err"], flush=True)
    out.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
