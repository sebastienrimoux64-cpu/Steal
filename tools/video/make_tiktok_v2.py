"""
Montage TikTok v2 (1080x1920, 30 i/s) du « ICE VFX pack » : transitions fluides (xfade), étalonnage glacé lumineux (bloom, teintes froides),
flocons et éclats qui tombent, givre sur les bords de l'écran, texte à apparition élastique, beaucoup de sound design (whooshs, craquements de glace,
tintements, riser) + musique synthétique, filigrane logo, carte de fin.

    python tools/video/make_tiktok_v2.py <ult.mp4> <clip2.mp4> <clip3.mp4> <logo.png> <sortie.mp4>
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
src = sys.argv[1:4]
logo_path, out = sys.argv[4], sys.argv[5]
TMP = os.path.join(os.path.dirname(os.path.abspath(out)), "_tmp_tiktok2")
os.makedirs(TMP, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
OV = 0.4          # durée des transitions

SEGS = [  # (source, début, durée visible, lignes de texte, transition vers le plan suivant)
    (0, 0.9, 1.9, ["THIS ICE VFX"], "zoomin"),
    (2, 1.1, 2.1, ["IS INSANE"], "smoothleft"),
    (1, 1.0, 2.5, ["FREEZE", "EVERYTHING"], "fadewhite"),
    (2, 10.0, 2.3, ["SHATTER", "IT ALL"], "circleopen"),
    (0, 11.8, 2.6, ["HUGE ICE", "IMPACTS"], "smoothup"),
    (1, 15.8, 2.6, ["ICE SHARDS", "EVERYWHERE"], "radial"),
    (2, 17.9, 2.4, ["FULL ICE", "VFX PACK"], "fadewhite"),
]
END = 4.6
T = [0.0]
for s in SEGS:
    T.append(T[-1] + s[2])
TOTAL = T[-1] + END
print("durée", TOTAL)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:400]); print(r.stderr[-2500:]); raise SystemExit(1)


# ============================================================ flocons + paillettes (vidéo noire, mélange « screen »)
def make_snow(path):
    rng = np.random.default_rng(7)
    N = 230
    fl = []
    for i in range(N):
        depth = rng.random()
        fl.append(dict(x=rng.uniform(-60, W + 60), y=rng.uniform(-100, H + 100), v=60 + 260 * depth ** 1.2, r=1.5 + 9 * depth ** 1.5, sw=rng.uniform(15, 70), fr=rng.uniform(0.6, 2.2),
                       ph=rng.uniform(0, 6.28), a=0.35 + 0.65 * depth, big=depth > 0.82))
    # sprites doux
    def sprite(r):
        n = int(r * 4) | 1
        y, x = np.mgrid[:n, :n] - n // 2
        d = np.hypot(x, y) / max(r, 0.5)
        return np.clip(1.0 - d, 0, 1) ** 0.8
    cache = {}
    stars = [dict(x=rng.uniform(40, W - 40), y=rng.uniform(100, H - 100), t0=rng.uniform(0, TOTAL), dur=rng.uniform(0.5, 1.1), s=rng.uniform(14, 40)) for _ in range(46)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n_frames = int(TOTAL * FPS) + 2
    YY, XX = np.mgrid[:H, :W].astype(np.float32)
    for fi in range(n_frames):
        t = fi / FPS
        img = np.zeros((H, W, 3), dtype=np.float32)
        for f in fl:
            y = (f["y"] + f["v"] * t) % (H + 200) - 100
            x = f["x"] + f["sw"] * math.sin(t * f["fr"] + f["ph"])
            r = f["r"]
            key = int(r * 2)
            if key not in cache:
                cache[key] = sprite(max(1.0, key / 2))
            sp = cache[key]
            h2 = sp.shape[0] // 2
            xi, yi = int(x), int(y)
            x0, y0 = xi - h2, yi - h2
            xa, ya = max(0, x0), max(0, y0)
            xb, yb = min(W, x0 + sp.shape[1]), min(H, y0 + sp.shape[0])
            if xb <= xa or yb <= ya:
                continue
            s = sp[ya - y0:yb - y0, xa - x0:xb - x0] * f["a"] * (0.55 if f["big"] else 1.0)
            img[ya:yb, xa:xb, 0] = np.maximum(img[ya:yb, xa:xb, 0], s * 0.92)
            img[ya:yb, xa:xb, 1] = np.maximum(img[ya:yb, xa:xb, 1], s * 0.97)
            img[ya:yb, xa:xb, 2] = np.maximum(img[ya:yb, xa:xb, 2], s)
        # paillettes en croix
        for st in stars:
            u = (t - st["t0"]) % (TOTAL + 0.01)
            if u > st["dur"]:
                continue
            k = math.sin(math.pi * u / st["dur"]) ** 2
            L = int(st["s"] * k)
            if L < 2:
                continue
            xi, yi = int(st["x"]), int(st["y"])
            for d in range(-L, L + 1):
                a = (1 - abs(d) / L) ** 1.5 * k
                for (px, py) in ((xi + d, yi), (xi, yi + d)):
                    if 0 <= px < W and 0 <= py < H:
                        img[py, px] = np.maximum(img[py, px], (0.8 * a, 0.95 * a, a))
        for k, c in enumerate(T[1:-1] + [T[-1]]):
            u = (t - (c - 0.15)) / 0.8
            if 0 <= u <= 1:
                pos = (-300 + 1700 * u) * (1 if k % 2 == 0 else 1)
                dgrid = (XX * (0.6 if k % 2 == 0 else -0.6) + YY * 0.8 + (0 if k % 2 == 0 else 650)) - pos
                band = (np.exp(-(dgrid / 90.0) ** 2) * 0.55 + np.exp(-(dgrid / 22.0) ** 2) * 0.4)[:, :, None]
                img = np.maximum(img, band * np.array([0.8, 0.95, 1.0], np.float32))
        pr.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    pr.stdin.close()
    pr.wait()


# ============================================================ givre sur les bords
def make_frost(path):
    rng = np.random.default_rng(11)

    def fbm(h, w, octs=5):
        acc = np.zeros((h, w), np.float32)
        amp, tot = 1.0, 0.0
        for o in range(octs):
            g = rng.random((2 + 3 * 2 ** o, 2 + 2 * 2 ** o)).astype(np.float32)
            im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
            acc += np.asarray(im, np.float32) / 255 * amp
            tot += amp
            amp *= 0.55
        return acc / tot
    n = fbm(H, W)
    yy, xx = np.mgrid[:H, :W]
    d = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy]).astype(np.float32)
    edge = np.clip(1.0 - d / (W * 0.14), 0, 1) ** 1.2
    a = np.clip((edge * 1.25 + (n - 0.5) * 0.9 * edge) , 0, 1)
    a = np.clip((a - 0.12) / 0.5, 0, 1) ** 0.9
    col = np.zeros((H, W, 4), np.float32)
    col[..., 0] = 0.80 + 0.2 * n
    col[..., 1] = 0.93 + 0.07 * n
    col[..., 2] = 1.0
    col[..., 3] = a * 0.92
    img = Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8), "RGBA")
    # cristaux ramifiés dans les coins
    dr = ImageDraw.Draw(img)

    def branch(x, y, ang, ln, depth, w):
        if depth == 0 or ln < 6:
            return
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        dr.line((x, y, x2, y2), fill=(235, 248, 255, 215), width=w)
        for da in (-0.62, 0.62):
            branch(x2 - math.cos(ang) * ln * 0.3, y2 - math.sin(ang) * ln * 0.3, ang + da, ln * 0.55, depth - 1, max(1, w - 1))
        branch(x2, y2, ang + rng.uniform(-0.15, 0.15), ln * 0.7, depth - 1, max(1, w - 1))
    for (cx, cy, base) in ((0, 0, 0.8), (W, 0, 2.3), (0, H, -0.8), (W, H, -2.3)):
        for k in range(7):
            branch(cx, cy, base + rng.uniform(-0.55, 0.55), rng.uniform(150, 320), 4, 5)
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    glow = img.filter(ImageFilter.GaussianBlur(14))
    out_ = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out_.alpha_composite(glow)
    out_.alpha_composite(img)
    out_.save(path)


# ============================================================ logo / textes
def make_assets():
    lg = Image.open(logo_path).convert("RGB")
    arr = np.asarray(lg).astype(np.float32)
    alpha = np.clip((arr.max(axis=2) - 120) / 110.0, 0, 1)
    logo = Image.fromarray(np.dstack([arr, alpha * 255]).astype(np.uint8), "RGBA")
    logo.resize((760, 760), Image.LANCZOS).save(f"{TMP}/logo_big.png")
    logo.resize((190, 190), Image.LANCZOS).save(f"{TMP}/logo_small.png")
    glow = logo.resize((520, 520), Image.LANCZOS)
    e = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    e.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)), (90, 90))
    e.alpha_composite(glow, (90, 90))
    e.save(f"{TMP}/logo_end.png")


def text_png(lines, path, size, grad=((255, 255, 255), (150, 216, 255)), stroke=14):
    meas = ImageDraw.Draw(Image.new("L", (1, 1)))
    while max(meas.textlength(l, font=ImageFont.truetype(FONT, size)) for l in lines) > 900 and size > 60:
        size -= 4
    fnt = ImageFont.truetype(FONT, size)
    lh = int(size * 1.08)
    wmax = int(max(meas.textlength(l, font=fnt) for l in lines))
    img = Image.new("RGBA", (wmax + 140, lh * len(lines) + 100), (0, 0, 0, 0))
    gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(gl)
    for k, l in enumerate(lines):
        tw = d.textlength(l, font=fnt)
        d.text(((img.width - tw) / 2, 35 + k * lh), l, font=fnt, fill=(120, 215, 255, 255), stroke_width=stroke + 8, stroke_fill=(120, 215, 255, 255))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(img)
    mask = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(mask)
    for k, l in enumerate(lines):
        tw = d.textlength(l, font=fnt)
        d.text(((img.width - tw) / 2 + 6, 35 + k * lh + 9), l, font=fnt, fill=(0, 20, 70, 170), stroke_width=stroke, stroke_fill=(0, 20, 70, 170))
        d.text(((img.width - tw) / 2, 35 + k * lh), l, font=fnt, fill=(12, 40, 110, 255), stroke_width=stroke, stroke_fill=(12, 40, 110, 255))
        md.text(((img.width - tw) / 2, 35 + k * lh), l, font=fnt, fill=255)
    g = Image.new("RGBA", img.size)
    gp = g.load()
    for y in range(img.height):
        t = min(1.0, max(0.0, (y - 30) / max(1, lh * len(lines))))
        c = tuple(int(grad[0][i] * (1 - t) + grad[1][i] * t) for i in range(3)) + (255,)
        for x in range(img.width):
            gp[x, y] = c
    img.paste(g, (0, 0), mask)
    img.save(path)


def make_texts():
    for i, s in enumerate(SEGS):
        text_png(s[3], f"{TMP}/txt{i}.png", 150 if len(s[3]) == 2 else 165)
    text_png(["GET THE"], f"{TMP}/end_get.png", 120)
    text_png(["ICE VFX", "PACK"], f"{TMP}/end_main.png", 215, grad=((255, 255, 255), (120, 200, 255)), stroke=18)
    pill = Image.new("RGBA", (900, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(pill)
    d.rounded_rectangle((0, 0, 899, 199), 100, fill=(124, 77, 255, 255), outline=(235, 245, 255, 255), width=7)
    fb = ImageFont.truetype(FONT, 100)
    t = "LINK IN BIO"
    d.text(((900 - d.textlength(t, font=fb)) / 2, 38), t, font=fb, fill=(255, 255, 255, 255))
    gl = pill.filter(ImageFilter.GaussianBlur(18))
    o = Image.new("RGBA", (960, 260), (0, 0, 0, 0))
    o.alpha_composite(gl, (30, 30))
    o.alpha_composite(pill, (30, 30))
    o.save(f"{TMP}/end_bio.png")
    tg = Image.new("RGBA", (860, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(tg)
    d.rounded_rectangle((0, 0, 859, 109), 55, fill=(10, 30, 70, 175), outline=(190, 235, 255, 255), width=4)
    f2 = ImageFont.truetype(FONT_B, 46)
    t = "ICE VFX PACK  •  FOR ROBLOX"
    d.text(((860 - d.textlength(t, font=f2)) / 2, 30), t, font=f2, fill=(220, 242, 255, 255))
    tg.save(f"{TMP}/tag.png")


# ============================================================ sound design
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


def make_audio():
    n = int(SR * (TOTAL + 0.6))
    sfx = np.zeros(n, np.float32)
    mus = np.zeros(n, np.float32)
    # un son différent par transition, peu nombreux
    for k in range(1, len(SEGS)):
        c = T[k]
        if k == 1:
            add(sfx, c - 0.35, whoosh(0.6, up=True), 0.8)
        elif k == 2:
            add(sfx, c - 0.3, whoosh(0.55, up=False), 0.7)
        elif k == 3:
            add(sfx, c - 0.5, riser(0.7), 0.6)
            add(sfx, c + 0.1, bell(1568.0, 1.2), 0.5)
        elif k == 4:
            add(sfx, c - 0.05, ice_crack(4, 0.15), 0.8)
        elif k == 5:
            add(sfx, c - 0.35, whoosh(0.6, up=True), 0.7)
            add(sfx, c + 0.0, boom(), 0.35)
        elif k == 6:
            add(sfx, c - 0.05, shatter(), 0.75)
    # intro : un seul tintement
    add(sfx, 0.0, bell(1318.5, 1.2), 0.5)
    e = T[-1]
    add(sfx, e - 1.2, riser(1.2), 0.8)
    add(sfx, e, boom(), 0.9)
    for j, f in enumerate((783.99, 1046.5, 1318.5)):
        add(sfx, e + 0.1 + 0.16 * j, bell(f), 0.7)
    add(sfx, e + 1.3, pop_tick(), 0.6)
    for _ in range(8):
        add(sfx, rng.uniform(0.5, TOTAL - 0.5), ping(rng.uniform(3000, 5600), 0.5, 7), rng.uniform(0.04, 0.08))
    sfx = reverb(sfx)
    # musique légère (120 BPM)
    def kick():
        t = np.arange(int(0.28 * SR)) / SR
        return (np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 22) + 42) / SR) * np.exp(-t * 11)).astype(np.float32)

    def clap():
        t = np.arange(int(0.2 * SR)) / SR
        return (rng.standard_normal(len(t)) * np.exp(-t * 28)).astype(np.float32) * 0.5

    def bass(freq, dur):
        t = np.arange(int(dur * SR)) / SR
        saw = 2 * ((t * freq) % 1.0) - 1
        return (np.tanh(saw * 2.0) * 0.4 * np.exp(-t * 3.0)).astype(np.float32)

    beat = 0.5
    notes = [55.0, 55.0, 65.41, 49.0]
    t0, b = 0.0, 0
    while t0 < TOTAL - 0.2:
        g = 0.55 if t0 >= T[-1] else 1.0
        add(mus, t0, kick(), 0.75 * g)
        if b % 2 == 1:
            add(mus, t0, clap(), 0.55 * g)
        add(mus, t0 + beat / 2, ping(7000, 0.04, 120) * 0.0 + (rng.standard_normal(int(0.04 * SR)).astype(np.float32) * np.exp(-np.arange(int(0.04 * SR)) / SR * 90) * 0.35), 0.5 * g)
        add(mus, t0, bass(notes[(b // 2) % 4], beat * 2), 0.65 * g)
        t0 += beat
        b += 1
    mix = sfx * 1.0 + mus * 0.55
    mix = mix / (np.max(np.abs(mix)) + 1e-6) * 0.9
    p = f"{TMP}/sfx.wav"
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return p


# ============================================================ plans
def make_segments():
    files = []
    for i, (si, st, du, _, _) in enumerate(SEGS):
        L = du + (OV if i < len(SEGS) else 0)
        zoom = 0.24
        fc = (
            f"[0:v]trim=start={st}:duration={L},setpts=PTS-STARTPTS,fps={FPS},split=2[a][b];"
            f"[a]scale=-2:{H},crop={W}:{H},gblur=sigma=20,eq=brightness=0.16:saturation=1.0,colorbalance=rs=-0.12:gs=0.02:bs=0.22:rm=-0.1:gm=0.04:bm=0.2,"
            f"colorchannelmixer=rr=0.8:gg=0.95:bb=1.0:rb=0.05:gb=0.1[bg];"
            f"[b]crop=720:720:280:0,scale={W}:{W},scale=w='{W}*(1+{zoom}*t/{L}+0.10*exp(-9*t))':h='{W}*(1+{zoom}*t/{L}+0.10*exp(-9*t))':eval=frame,crop={W}:{W}:x='(iw-{W})/2+{'-' if i % 2 else ''}60*(t/{L}-0.5)':y='(ih-{W})/2+16*sin(5*t)',"
            f"eq=brightness=0.07:contrast=1.14:saturation=1.35:gamma=0.95,colorbalance=rm=-0.06:bm=0.1:rh=-0.05:bh=0.12,split=2[f1][f2];"
            f"[f2]gblur=sigma=30,eq=brightness=0.05[f3];[f1]format=gbrp[f1r];[f3]format=gbrp[f3r];[f1r][f3r]blend=all_mode=screen:all_opacity=0.40,format=yuva420p,"
            f"geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='255*min(1,min(Y,{W - 1}-Y)/170)'[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2-60+14*sin(2.2*t),format=yuv420p[v];"
            f"[0:a]atrim=start={st}:duration={L},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={L - 0.06}:d=0.06,volume=0.5,aformat=sample_rates=44100:channel_layouts=stereo[a]"
        )
        f = f"{TMP}/seg{i}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src[si], "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "pcm_s16le", f])
        files.append(f)
    # carte de fin : fond glacé flou
    fc = (f"[0:v]trim=start=24.2:duration={END},setpts=PTS-STARTPTS,fps={FPS},scale=-2:{H},crop={W}:{H},gblur=sigma=28,eq=brightness=-0.18:saturation=0.9,"
          f"colorchannelmixer=rr=0.55:gg=0.6:bb=1.0:rb=0.15:gb=0.12,format=yuv420p[v];"
          f"[0:a]atrim=start=24.2:duration={END},asetpts=PTS-STARTPTS,volume=0.3,afade=t=out:st={END - 0.6}:d=0.6,aformat=sample_rates=44100:channel_layouts=stereo[a]")
    f = f"{TMP}/end_bg.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src[0], "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "pcm_s16le", f])
    files.append(f)
    return files


def make_base(files):
    inp = []
    for f in files:
        inp += ["-i", f]
    fc, last_v, last_a = [], "0:v", "0:a"
    length = SEGS[0][2] + OV
    for k in range(1, len(files)):
        off = length - OV
        fc.append(f"[{last_v}][{k}:v]xfade=transition={SEGS[k - 1][4]}:duration={OV}:offset={off:.3f}[v{k}]")
        fc.append(f"[{last_a}][{k}:a]acrossfade=d={OV}:c1=tri:c2=tri[a{k}]")
        seg_len = (SEGS[k][2] + OV) if k < len(SEGS) else END
        length = length + seg_len - OV
        last_v, last_a = f"v{k}", f"a{k}"
    p = f"{TMP}/base.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", f"[{last_v}]", "-map", f"[{last_a}]", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", p])
    return p


def final(base, snow, frost, sfx):
    names = ["base", "snow", "frost", "lbig", "lsm", "lend", "get", "main", "bio", "tag", "sfx"] + [f"t{i}" for i in range(len(SEGS))]
    paths = [base, snow, frost, f"{TMP}/logo_big.png", f"{TMP}/logo_small.png", f"{TMP}/logo_end.png", f"{TMP}/end_get.png", f"{TMP}/end_main.png", f"{TMP}/end_bio.png", f"{TMP}/tag.png", sfx] + \
            [f"{TMP}/txt{i}.png" for i in range(len(SEGS))]
    inp = []
    for n, p in zip(names, paths):
        if p.endswith(".png"):
            inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL + 1:.2f}", "-i", p]
        else:
            inp += ["-i", p]
    ix = {n: i for i, n in enumerate(names)}
    fc = []
    # lueur d'impact + éclaircie générale
    pulses = "+".join(f"0.26*exp(-9*abs(t-{c:.3f}))" for c in T[1:])
    fc.append(f"[0:v]eq=brightness='0.03+{pulses}':saturation=1.12:contrast=1.04:eval=frame[g0]")
    fc.append(f"[g0]format=gbrp[g0r];[{ix['snow']}:v]format=gbrp[snr];[g0r][snr]blend=all_mode=screen:all_opacity=0.92[sn]")
    fc.append(f"[{ix['frost']}:v]format=rgba,fade=t=in:st=0:d=1.3:alpha=1[fr]")
    fc.append(f"[sn][fr]overlay=0:0[c0]")
    cur = "c0"
    for i in range(len(SEGS)):
        a, b2 = T[i] + OV * 0.55, T[i + 1] + OV * 0.4
        fc.append(f"[{ix[f't{i}']}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.14:alpha=1,fade=t=out:st={b2 - 0.12:.3f}:d=0.12:alpha=1,"
                  f"scale=w='iw*(1+0.45*exp(-9*max(0,t-{a:.3f})))':h=-1:eval=frame[tp{i}]")
        fc.append(f"[{cur}][tp{i}]overlay=x=(W-w)/2:y='H*0.2-h/2+10*sin(3.2*t)':eof_action=pass:enable='between(t,{a:.3f},{b2:.3f})'[x{i}]")
        cur = f"x{i}"
    fc.append(f"[{ix['tag']}:v]format=rgba,fade=t=in:st=0.5:d=0.4:alpha=1,fade=t=out:st={T[-1] - 0.2:.3f}:d=0.3:alpha=1[tgp]")
    fc.append(f"[{cur}][tgp]overlay=x=(W-w)/2:y=H*0.86:eof_action=pass[tg]")
    e0 = T[-1] + OV * 0.5
    fc.append(f"[{ix['lend']}:v]format=rgba,fade=t=in:st={e0:.3f}:d=0.4:alpha=1,scale=w='iw*(1+0.12*sin(2*t))':h=-1:eval=frame[le]")
    fc.append(f"[tg][le]overlay=x=(W-w)/2:y='H*0.05-h*0.0':eof_action=pass[e1]")
    for nm, y0, dl in (("get", 0.34, 0.35), ("main", 0.385, 0.6), ("bio", 0.70, 1.3)):
        st = e0 + dl
        fc.append(f"[{ix[nm]}:v]format=rgba,fade=t=in:st={st:.3f}:d=0.25:alpha=1,scale=w='iw*(1+0.18*exp(-8*max(0,t-{st:.3f}))+0.02*sin(5*t))':h=-1:eval=frame[{nm}p]")
    fc.append(f"[e1][getp]overlay=x=(W-w)/2:y='H*0.325-h/2':eof_action=pass[e2]")
    fc.append(f"[e2][mainp]overlay=x=(W-w)/2:y='H*0.515-h/2':eof_action=pass[e3]")
    fc.append(f"[e3][biop]overlay=x=(W-w)/2:y='H*0.73-h/2':eof_action=pass[e4]")
    cur = "e4"
    fc.append(f"[{ix['lbig']}:v]format=rgba,colorchannelmixer=aa=0.13[wm1]")
    fc.append(f"[{cur}][wm1]overlay=x=(W-w)/2:y=(H-h)/2:eof_action=pass[w1]")
    fc.append(f"[{ix['lsm']}:v]format=rgba,colorchannelmixer=aa=0.7[wm2]")
    cx = "if(lt(mod(t,16),4),40,if(lt(mod(t,16),8),W-w-40,if(lt(mod(t,16),12),40,W-w-40)))"
    cy = "if(lt(mod(t,16),4),170,if(lt(mod(t,16),8),170,if(lt(mod(t,16),12),H-h-330,H-h-330)))"
    fc.append(f"[w1][wm2]overlay=x='{cx}':y='{cy}':eof_action=pass,format=yuv420p[vout]")
    fc.append(f"[0:a]volume=0.8[oa];[{ix['sfx']}:a]volume=1.0,aformat=sample_rates=44100:channel_layouts=stereo[sf];[oa][sf]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,afade=t=out:st={TOTAL - 0.5:.2f}:d=0.5[aout]")
    run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{TOTAL:.2f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                                                       "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])


if __name__ == "__main__":
    make_assets()
    make_texts()
    if not os.path.exists(f"{TMP}/frost.png"):
        make_frost(f"{TMP}/frost.png")
    if not os.path.exists(f"{TMP}/snow.mp4"):
        make_snow(f"{TMP}/snow.mp4")
    sfx = make_audio()
    files = make_segments()
    base = make_base(files)
    final(base, f"{TMP}/snow.mp4", f"{TMP}/frost.png", sfx)
    print("OK", out, os.path.getsize(out) // 1000, "ko")
