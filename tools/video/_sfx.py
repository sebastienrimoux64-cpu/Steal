"""Synthèse sonore partagée (whoosh, ping, cloche, riser, boom, réverb) — extraite de make_tiktok_v2.py."""
import numpy as np

SR = 44100
rng = np.random.default_rng(5)


def add(buf, start, sig, gain=1.0):
    s = int(start * SR)
    if s < 0:
        sig = sig[-s:]
        s = 0
    e = min(len(buf), s + len(sig))
    if s < len(buf) and e > s:
        buf[s:e] += sig[: e - s] * gain


def lp_sweep(x, f0, f1):
    """Passe-bas à une pôle avec fréquence de coupure glissante f0 -> f1."""
    n = len(x)
    out = np.zeros(n, np.float32)
    y = 0.0
    fs = np.geomspace(f0, f1, n)
    al = 1 - np.exp(-2 * np.pi * fs / SR)
    for i in range(n):
        y += al[i] * (x[i] - y)
        out[i] = y
    return out


def whoosh(dur=0.7, up=True):
    t = np.arange(int(dur * SR)) / SR
    x = rng.standard_normal(len(t)).astype(np.float32)
    y = lp_sweep(x, 250, 7000) if up else lp_sweep(x, 7000, 250)
    y = y - lp_sweep(y, 80, 80)          # retire le grave
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    return (y * env * 2.6).astype(np.float32)


def ping(freq, dur=0.25, decay=18):
    t = np.arange(int(dur * SR)) / SR
    return (np.sin(2 * np.pi * freq * t) * np.exp(-t * decay) * (1 - np.exp(-t * 900))).astype(np.float32)


def ice_crack(pings=9, spread=0.28):
    n = int(0.9 * SR)
    sig = np.zeros(n, np.float32)
    t = np.arange(n) / SR
    burst = rng.standard_normal(n).astype(np.float32)
    burst = burst - lp_sweep(burst, 1500, 1500)
    add(sig, 0, burst[: int(0.12 * SR)] * np.exp(-np.arange(int(0.12 * SR)) / SR * 38), 1.1)
    for k in range(pings):
        add(sig, rng.uniform(0, spread), ping(rng.uniform(2400, 9500), 0.18, rng.uniform(30, 70)), rng.uniform(0.25, 0.6))
    thump = np.sin(2 * np.pi * (95 * np.exp(-t * 14) + 38) * t) * np.exp(-t * 9)
    sig += thump.astype(np.float32) * 0.9
    return sig


def shatter():
    n = int(1.3 * SR)
    sig = np.zeros(n, np.float32)
    for k in range(34):
        add(sig, rng.uniform(0, 0.55) ** 1.4, ping(rng.uniform(1800, 11000), 0.2, rng.uniform(25, 80)), rng.uniform(0.15, 0.55))
    nz = rng.standard_normal(int(0.4 * SR)).astype(np.float32)
    nz = nz - lp_sweep(nz, 2500, 2500)
    add(sig, 0, nz * np.exp(-np.arange(len(nz)) / SR * 14), 0.9)
    return sig


def pop_tick():
    return (ping(1250, 0.12, 55) * 0.5 + np.pad(ping(2500, 0.08, 80), (0, int(0.04 * SR))) * 0.3).astype(np.float32)


def bell(freq, dur=1.6):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2.76 * t) + 0.25 * np.sin(2 * np.pi * freq * 5.4 * t)
    return (s * np.exp(-t * 2.6) * (1 - np.exp(-t * 600)) * 0.35).astype(np.float32)


def riser(dur=1.5):
    t = np.arange(int(dur * SR)) / SR
    x = rng.standard_normal(len(t)).astype(np.float32)
    y = lp_sweep(x, 300, 9000)
    return (y * (t / dur) ** 2 * 2.6).astype(np.float32)


def boom():
    t = np.arange(int(1.6 * SR)) / SR
    return (np.sin(2 * np.pi * (70 * np.exp(-t * 2.2) + 30) * t) * np.exp(-t * 2.5) * 1.2).astype(np.float32)


def reverb(x, t60=1.1, wet=0.28):
    n = int(t60 * SR)
    ir = rng.standard_normal(n).astype(np.float32) * np.exp(-np.arange(n) / SR * (6.9 / t60))
    ir[0] = 0
    L = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[: len(x)].astype(np.float32)
    return x + wet * y / (np.max(np.abs(y)) + 1e-6) * np.max(np.abs(x))
