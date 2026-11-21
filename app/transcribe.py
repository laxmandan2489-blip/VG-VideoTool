"""v2.8: Recording sunke script likho (bot confirm karwata hai).  python transcribe.py <recording> <out.txt>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path
from common import log, read_style, TOOL, WORK


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    style = read_style(TOOL / "style.txt")
    import align, voice
    WORK.mkdir(parents=True, exist_ok=True)
    wav = WORK / "transcribe_tmp.wav"
    voice.save_wav(wav, voice.load_wav(src))
    words, segs = align.transcribe(wav, style.get("whisper_model_meri", "small"), "hi")
    if not words:
        print("TRANSCRIBE_FAIL"); sys.exit(2)
    lines = []; cur = [words[0]]
    for a, b in zip(words, words[1:]):
        if b["start"] - a["end"] > 0.55 or len(cur) >= 14:
            lines.append(" ".join(w["w"] for w in cur)); cur = []
        cur.append(b)
    lines.append(" ".join(w["w"] for w in cur))
    out.write_text("\n".join(l.strip() for l in lines if l.strip()) + "\n", encoding="utf-8")
    print("TRANSCRIBE_OK")


if __name__ == "__main__":
    main()
