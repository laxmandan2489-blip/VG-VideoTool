"""v3.1 ORIGINAL SOUND EFFECTS – math se bane (noise + sine), 100% apne, copyright-free.

Reels se kaate sounds (insaan ki awaaz / music ke tukde) ki jagah. Banao:
    python app/sfx_synth.py      -> assets/sfx/<category>/vg_*.wav
"""
import wave
import numpy as np
from pathlib import Path

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"


def _save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * 0.89, -1, 1)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def _t(d): return np.arange(int(d * SR)) / SR


def _lp(x, a):
    """one-pole low pass, a = 0..1 (time varying array allowed)"""
    y = np.empty_like(x); s = 0.0
    a = np.broadcast_to(a, x.shape)
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y


def _fade(x, a=0.005, b=0.03):
    n1, n2 = int(a * SR), int(b * SR)
    x[:n1] *= np.linspace(0, 1, n1); x[-n2:] *= np.linspace(1, 0, n2); return x


def whoosh(d=0.9, seed=0, up=True):
    rng = np.random.default_rng(seed); t = _t(d); n = rng.standard_normal(len(t))
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (1.6 if up else 2.2)
    sweep = 0.02 + 0.35 * (t / d if up else 1 - t / d)
    x = _lp(n, sweep) - _lp(n, sweep * 0.15)              # band-pass sweep
    return _fade(x * env)


def riser(d=2.0, seed=1):
    t = _t(d); rng = np.random.default_rng(seed)
    f = 120 * (2 ** (3 * t / d))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    noise = _lp(rng.standard_normal(len(t)), 0.05 + 0.3 * t / d)
    return _fade((0.5 * tone + 0.8 * noise) * (t / d) ** 2.2, 0.01, 0.02)


def boom(d=1.6, seed=2):
    t = _t(d); rng = np.random.default_rng(seed)
    f = 30 + 70 * np.exp(-t * 9)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.8)
    click = _lp(rng.standard_normal(len(t)), 0.25) * np.exp(-t * 40)
    return _fade(body + 0.5 * click, 0.001, 0.2)


def ding(d=1.4, f0=1318.5):
    t = _t(d)
    x = sum(a * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * k) for a, m, k in ((1, 1, 3.5), (0.4, 2.0, 5), (0.2, 3.01, 7)))
    return _fade(x, 0.002, 0.1)


def pop(d=0.12):
    t = _t(d); f = 900 * np.exp(-t * 30) + 200
    return _fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35), 0.001, 0.02)


def click(d=0.05, seed=3):
    t = _t(d); rng = np.random.default_rng(seed)
    return _fade(_lp(rng.standard_normal(len(t)), 0.6) * np.exp(-t * 160), 0.0005, 0.01)


def shimmer(d=1.2, seed=4):
    t = _t(d); rng = np.random.default_rng(seed); x = np.zeros_like(t)
    for f in rng.uniform(2000, 6000, 14):
        x += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-((t - rng.uniform(0.1, d * 0.7)) ** 2) / 0.02)
    return _fade(x * np.sin(np.pi * t / d))


def glitch(d=0.5, seed=5):
    t = _t(d); rng = np.random.default_rng(seed)
    sq = np.sign(np.sin(2 * np.pi * rng.choice([180, 360, 720], len(t)) * t))
    gate = (rng.random(int(d * 40)) > 0.4).repeat(int(SR / 40) + 1)[:len(t)]
    return _fade(0.4 * sq * gate + 0.3 * rng.standard_normal(len(t)) * gate)


def subdrop(d=1.5):
    t = _t(d); f = 90 * np.exp(-t * 1.6) + 28
    return _fade(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.2), 0.002, 0.2)


def make_all(out=OUT):
    out = Path(out); made = []
    # v3.1: whoosh/riser/glitch synth HATAYE – user ko "machine jaisi" lagi. Sirf naram pop/click/ding/boom.
    plan = {"boom": [boom(1.4, 2), boom(2.0, 3) + 0.6 * subdrop(2.0)],
            "ding": [ding(1.2), ding(1.4, 1567.98)], "pop": [pop(), pop(0.09)], "click": [click(), click(0.04, 9)]}
    for cat, xs in plan.items():
        for k, x in enumerate(xs):
            p = out / cat / f"vg_{cat}_{k+1}.wav"; _save(p, x.astype(np.float32)); made.append(p)
    return made


if __name__ == "__main__":
    for p in make_all(): print(p)
