"""
TikTok (1080x1920, 30 i/s) pour le pack « 8 pioches réalistes » (Haatkeoz.fr) à partir de la vidéo de présentation.

    python tools/video/make_tiktok_pickaxes.py <pioches.mp4> <sortie.mp4>

Une pioche par plan (bois → lapis-lazuli) avec son nom et sa couleur de lueur, transitions xfade, poussière dorée + éclats qui montent,
reflets lumineux à chaque coupe, texte à apparition élastique, bandeau de prix permanent, carte de fin avec le prix en dollars.
Les textes français et le « haatmis.fr » de la vidéo d'origine sont recadrés / floutés : tout est en anglais.
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _sfx as sx  # noqa: E402
from _sfx import SR, add, bell, boom, ping, reverb, riser, whoosh  # noqa: E402

W, H, FPS = 1080, 1920, 30
src, out = sys.argv[1], sys.argv[2]
TMP = os.path.join(os.path.dirname(os.path.abspath(out)), "_tmp_pickaxes")
os.makedirs(TMP, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
OV = 0.4
SQ_Y = 330                      # la pioche (recadrage vertical) occupe 330 → 1718 ; le bas est de toute façon mangé par l'interface TikTok
FH = 1388                       # hauteur du recadrage 560x720 mis à la largeur 1080
PRICE_EUR = 10
PRICE = "$11.50"                # 10 € ≈ 11,5 $ (taux ≈ 1,15) — à ajuster si besoin
SITE = "HAATKEOZ.FR"

# nom, couleur de la lueur, dégradé du texte (haut, bas)
TIERS = [
    ("WOOD", (255, 160, 80), ((255, 235, 200), (230, 150, 80))),
    ("COPPER", (255, 135, 90), ((255, 230, 210), (240, 130, 85))),
    ("IRON", (190, 215, 245), ((255, 255, 255), (170, 200, 235))),
    ("GOLD", (255, 205, 60), ((255, 250, 200), (255, 195, 40))),
    ("DIAMOND", (70, 220, 255), ((235, 255, 255), (60, 205, 250))),
    ("URANIUM", (140, 255, 80), ((240, 255, 215), (120, 240, 60))),
    ("RUBY", (255, 60, 90), ((255, 220, 225), (255, 70, 95))),
    ("LAPIS", (70, 110, 255), ((225, 235, 255), (80, 125, 255))),
]
DUR, INTRO, END = 1.8, 1.6, 4.4
TRANS = ["fadewhite", "smoothleft", "smoothup", "circleopen", "smoothright", "radial", "smoothdown", "zoomin", "fadewhite"]
# segments : (début source, durée visible, type)
SEGS = [(0.0, INTRO, "intro")] + [(2.0 + 4 * k + 1.1, DUR, "pick") for k in range(8)]
T = [0.0]
for s in SEGS:
    T.append(T[-1] + s[1])
TOTAL = T[-1] + END
print("durée", TOTAL)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:500]); print(r.stderr[-2500:]); raise SystemExit(1)


# ============================================================ poussière dorée + éclats + reflets (vidéo noire, mélange « screen »)
def make_dust(path):
    rng = np.random.default_rng(9)
    fl = []
    for i in range(190):
        depth = rng.random()
        fl.append(dict(x=rng.uniform(-60, W + 60), y=rng.uniform(-100, H + 100), v=30 + 150 * depth ** 1.2, r=1.5 + 7 * depth ** 1.5, sw=rng.uniform(15, 60), fr=rng.uniform(0.5, 1.8),
                       ph=rng.uniform(0, 6.28), a=0.3 + 0.7 * depth))

    def sprite(r):
        n = int(r * 4) | 1
        y, x = np.mgrid[:n, :n] - n // 2
        return np.clip(1.0 - np.hypot(x, y) / max(r, 0.5), 0, 1) ** 0.9
    cache = {}
    stars = [dict(x=rng.uniform(40, W - 40), y=rng.uniform(120, H - 360), t0=rng.uniform(0, TOTAL), dur=rng.uniform(0.5, 1.0), s=rng.uniform(14, 38)) for _ in range(40)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    YY, XX = np.mgrid[:H, :W].astype(np.float32)
    warm = np.array([1.0, 0.86, 0.55], np.float32)
    for fi in range(int(TOTAL * FPS) + 2):
        t = fi / FPS
        img = np.zeros((H, W, 3), dtype=np.float32)
        for f in fl:
            y = (f["y"] - f["v"] * t) % (H + 200) - 100          # ça monte
            x = f["x"] + f["sw"] * math.sin(t * f["fr"] + f["ph"])
            key = int(f["r"] * 2)
            if key not in cache:
                cache[key] = sprite(max(1.0, key / 2))
            sp = cache[key]
            h2 = sp.shape[0] // 2
            x0, y0 = int(x) - h2, int(y) - h2
            xa, ya = max(0, x0), max(0, y0)
            xb, yb = min(W, x0 + sp.shape[1]), min(H, y0 + sp.shape[0])
            if xb <= xa or yb <= ya:
                continue
            s = (sp[ya - y0:yb - y0, xa - x0:xb - x0] * f["a"])[:, :, None] * warm
            img[ya:yb, xa:xb] = np.maximum(img[ya:yb, xa:xb], s)
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
                        img[py, px] = np.maximum(img[py, px], (a, 0.92 * a, 0.7 * a))
        for k, c in enumerate(T[1:len(SEGS) + 1]):
            u = (t - (c - 0.15)) / 0.8
            if 0 <= u <= 1:
                pos = -300 + 1700 * u
                dgrid = (XX * (0.6 if k % 2 == 0 else -0.6) + YY * 0.8 + (0 if k % 2 == 0 else 650)) - pos
                band = (np.exp(-(dgrid / 90.0) ** 2) * 0.5 + np.exp(-(dgrid / 22.0) ** 2) * 0.4)[:, :, None]
                img = np.maximum(img, band * np.array([1.0, 0.93, 0.75], np.float32))
        pr.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    pr.stdin.close()
    pr.wait()


# ============================================================ éléments graphiques
def text_png(parts, path, grad=((255, 255, 255), (255, 214, 120)), glow=(255, 190, 70), stroke=13, maxw=930, gap=1.06):
    """parts : liste de (texte, taille). Dégradé vertical, contour sombre, halo coloré."""
    meas = ImageDraw.Draw(Image.new("L", (1, 1)))
    fitted = []
    for tx, sz in parts:
        while meas.textlength(tx, font=ImageFont.truetype(FONT, sz)) > maxw and sz > 30:
            sz -= 4
        fitted.append((tx, sz))
    pad = 70
    wmax = int(max(meas.textlength(tx, font=ImageFont.truetype(FONT, sz)) for tx, sz in fitted))
    hs = [int(sz * gap) for _, sz in fitted]
    w, h = wmax + 2 * pad + 2 * stroke, sum(hs) + 2 * pad
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    y = pad
    for (tx, sz), lh in zip(fitted, hs):
        md.text((w / 2, y + lh / 2), tx, font=ImageFont.truetype(FONT, sz), fill=255, anchor="mm")
        y += lh
    shadow = mask.filter(ImageFilter.MaxFilter(stroke * 2 + 1))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gl = Image.new("RGBA", (w, h), glow + (0,))
    gl.putalpha(shadow.filter(ImageFilter.GaussianBlur(18)).point(lambda v: min(255, int(v * 1.1))))
    img.alpha_composite(gl)
    dk = Image.new("RGBA", (w, h), (28, 14, 6, 0))
    dk.putalpha(shadow)
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh.paste(dk, (6, 9))
    img.alpha_composite(sh)
    img.alpha_composite(dk)
    g = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        g[:, :, c] = np.linspace(grad[0][c], grad[1][c], h)[:, None]
    gi = Image.fromarray(g.astype(np.uint8)).convert("RGBA")
    gi.putalpha(mask)
    img.alpha_composite(gi)
    img.save(path)


def pill_png(label, path, size=44, bg=(24, 14, 6, 205), outline=(255, 200, 80), fg=(255, 236, 190), glow=(255, 180, 60), sub=None):
    f = ImageFont.truetype(FONT, size)
    meas = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = int(meas.textlength(label, font=f))
    w, h = tw + int(size * 2.4), int(size * 2.1)
    pad = 40
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad, pad + w, pad + h), h // 2, fill=190)
    g = Image.new("RGBA", im.size, glow + (0,))
    g.putalpha(m.filter(ImageFilter.GaussianBlur(16)))
    im.alpha_composite(g)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), h // 2, fill=bg, outline=outline + (255,), width=4)
    d.text((pad + w / 2, pad + h / 2 + 2), label, font=f, fill=fg, anchor="mm")
    im.save(path)


def glow_png(col, path, cy=0.43):
    y, x = np.mgrid[:H, :W].astype(np.float32)
    g = np.exp(-(((x - W / 2) / 520) ** 2 + ((y - H * cy) / 700) ** 2))
    img = (g[:, :, None] * np.array(col, np.float32) / 255.0 * 255.0)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)


def make_assets():
    for i, (nm, col, grad) in enumerate(TIERS):
        text_png([(f"PICKAXE {i + 1}/8", 54), (nm, 190)], f"{TMP}/name{i}.png", grad=grad, glow=col)
        glow_png(col, f"{TMP}/glow{i + 1}.png")
    glow_png((255, 210, 120), f"{TMP}/glow0.png")
    text_png([("8 REALISTIC", 124), ("PICKAXES", 150)], f"{TMP}/hook.png", glow=(255, 190, 70))
    text_png([("8 REALISTIC", 120), ("PICKAXES", 150)], f"{TMP}/e_title.png")
    text_png([("ONLY", 70), (PRICE, 330)], f"{TMP}/e_price.png", grad=((255, 255, 255), (120, 255, 150)), glow=(70, 255, 130), stroke=16)
    text_png([("PBR TEXTURES  •  FBX FILES", 50), ("READY FOR ROBLOX STUDIO", 50)], f"{TMP}/e_feat.png", grad=((255, 245, 215), (255, 215, 140)), glow=(255, 170, 50), stroke=7, gap=1.25)
    text_png([("USE THEM IN YOUR OWN GAMES", 56)], f"{TMP}/e_use.png", grad=((255, 255, 255), (255, 226, 160)), glow=(255, 170, 50), stroke=8)
    pill_png("LINK IN BIO", f"{TMP}/e_link.png", 86, bg=(255, 170, 30, 255), outline=(255, 245, 210), fg=(40, 20, 4), glow=(255, 190, 70))
    text_png([(SITE, 76)], f"{TMP}/e_site.png", grad=((255, 255, 255), (255, 214, 120)), glow=(255, 190, 70), stroke=9)
    pill_png(f"8 PICKAXES  •  ONLY {PRICE}", f"{TMP}/price_pill.png", 44)
    text_png([(SITE, 42)], f"{TMP}/wm.png", grad=((255, 255, 255), (255, 235, 190)), glow=(0, 0, 0), stroke=5)


# ============================================================ sound design
def make_audio():
    rng = sx.rng
    n = int(SR * (TOTAL + 0.6))
    fx = np.zeros(n, np.float32)
    mus = np.zeros(n, np.float32)
    notes = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.7, 1318.5]       # gamme pentatonique montante, une note par pioche
    for i in range(8):
        k = i + 1
        pop = T[k] + OV * 0.55
        add(fx, pop, bell(notes[i], 1.4), 0.55)
        if i in (0, 2, 4, 6):                                                      # un whoosh une coupe sur deux
            add(fx, T[k] - 0.3, whoosh(0.55, up=(i % 4 == 0)), 0.2)
    add(fx, 0.05, boom(), 0.12)
    e = T[-1]
    add(fx, e - 1.0, riser(1.2), 0.3)
    add(fx, e + 0.05, boom(), 0.4)
    for j, f in enumerate((783.99, 987.77, 1174.66)):
        add(fx, e + 0.1 + 0.12 * j, bell(f, 1.2), 0.5)
    pr = e + 1.05                                                                    # « ka-ching » quand le prix apparaît
    add(fx, pr, ping(1760, 0.5, 9), 0.7)
    add(fx, pr + 0.07, ping(2349, 0.7, 8), 0.7)
    add(fx, pr + 0.14, ping(3136, 0.9, 7), 0.5)
    fx = reverb(fx, wet=0.22)

    def kick():
        t = np.arange(int(0.28 * SR)) / SR
        return (np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 22) + 42) / SR) * np.exp(-t * 11)).astype(np.float32)

    def clap():
        t = np.arange(int(0.2 * SR)) / SR
        return (rng.standard_normal(len(t)) * np.exp(-t * 28)).astype(np.float32) * 0.45

    def bass(freq, dur):
        t = np.arange(int(dur * SR)) / SR
        return (np.tanh((2 * ((t * freq) % 1.0) - 1) * 2.0) * 0.35 * np.exp(-t * 3.0)).astype(np.float32)

    def pluck(freq):
        t = np.arange(int(0.35 * SR)) / SR
        return (np.sin(2 * np.pi * freq * t) * np.exp(-t * 11) * 0.35).astype(np.float32)
    beat, t0, b = 0.5, 0.0, 0
    bn = [55.0, 55.0, 65.41, 49.0]
    arp = [261.63, 329.63, 392.0, 523.25, 392.0, 329.63, 440.0, 523.25]
    while t0 < TOTAL - 0.2:
        g = 0.6 if t0 >= T[-1] else 1.0
        add(mus, t0, kick(), 0.7 * g)
        if b % 2 == 1:
            add(mus, t0, clap(), 0.5 * g)
        add(mus, t0, bass(bn[(b // 2) % 4], beat * 2), 0.6 * g)
        add(mus, t0, pluck(arp[b % 8]), 0.5 * g)
        add(mus, t0 + beat / 2, pluck(arp[(b + 3) % 8] * 2), 0.28 * g)
        t0 += beat
        b += 1
    mix = fx * 1.0 + mus * 0.5
    mix = mix / (np.max(np.abs(mix)) + 1e-6) * 0.9
    p = f"{TMP}/sfx.wav"
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return p


# ============================================================ plans
def make_segments():
    files = []
    for i, (st, du, kind) in enumerate(SEGS):
        L = du + OV
        if kind == "intro":
            crop = "delogo=x=598:y=50:w=40:h=70,crop=560:720:600:0"
        else:
            crop = "crop=560:720:600:0"
        d = f"{'-' if i % 2 else ''}60"
        fc = (
            f"[0:v]trim=start={st}:duration={L},setpts=PTS-STARTPTS,fps={FPS},split=2[a][b];"
            f"[a]scale=-2:{H},crop={W}:{H},gblur=sigma=26,eq=brightness=0.05:saturation=1.15,format=gbrp[bgr];"
            f"[1:v]format=gbrp[gr];[bgr][gr]blend=all_mode=screen:all_opacity=0.6,format=yuv420p[bg];"
            f"[b]{crop},scale={W}:{FH},scale=w='{W}*(1+0.12*t/{L}+0.06*exp(-9*t))':h='{FH}*(1+0.12*t/{L}+0.06*exp(-9*t))':eval=frame,"
            f"crop={W}:{FH}:x='(iw-{W})/2+{d}*(t/{L}-0.5)':y='(ih-{FH})/2+14*sin(5*t)',"
            f"unsharp=5:5:0.8,eq=brightness=0.06:contrast=1.12:saturation=1.3:gamma=0.95,split=2[f1][f2];"
            f"[f2]gblur=sigma=30,eq=brightness=0.05[f3];[f1]format=gbrp[f1r];[f3]format=gbrp[f3r];[f1r][f3r]blend=all_mode=screen:all_opacity=0.40,format=yuva420p,"
            f"geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='255*min(1,min(Y,{FH - 1}-Y)/150)'[fg];"
            f"[bg][fg]overlay=(W-w)/2:{SQ_Y}+14*sin(2.2*t),format=yuv420p[v]"
        )
        f = f"{TMP}/seg{i}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-loop", "1", "-framerate", str(FPS), "-t", f"{L:.2f}", "-i", f"{TMP}/glow{i}.png", "-filter_complex", fc,
             "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", f])
        files.append(f)
    # carte de fin : fond flou de la scène finale, assombri, avec lueur dorée
    fc = (f"[0:v]trim=start=34.8:duration=3.2,delogo=x=20:y=50:w=640:h=110,setpts=PTS-STARTPTS,fps={FPS},tpad=stop_mode=clone:stop_duration=3,trim=duration={END},scale=-2:{H},crop={W}:{H},gblur=sigma=30,"
          f"eq=brightness=-0.12:saturation=1.1,format=gbrp[bgr];[1:v]format=gbrp[gr];[bgr][gr]blend=all_mode=screen:all_opacity=0.5,format=yuv420p[v]")
    f = f"{TMP}/end_bg.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-loop", "1", "-framerate", str(FPS), "-t", f"{END:.2f}", "-i", f"{TMP}/glow0.png", "-filter_complex", fc,
         "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", f])
    files.append(f)
    return files


def make_base(files):
    inp = []
    for f in files:
        inp += ["-i", f]
    fc, last = [], "0:v"
    length = SEGS[0][1] + OV
    for k in range(1, len(files)):
        off = length - OV
        fc.append(f"[{last}][{k}:v]xfade=transition={TRANS[k - 1]}:duration={OV}:offset={off:.3f}[v{k}]")
        seg_len = (SEGS[k][1] + OV) if k < len(SEGS) else END
        length += seg_len - OV
        last = f"v{k}"
    p = f"{TMP}/base.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", str(FPS), p])
    return p


def final(base, dust, sfx):
    names = ["base", "dust", "hook", "pill", "wm", "title", "price", "feat", "use", "link", "site", "sfx"] + [f"n{i}" for i in range(8)]
    paths = [base, dust, f"{TMP}/hook.png", f"{TMP}/price_pill.png", f"{TMP}/wm.png", f"{TMP}/e_title.png", f"{TMP}/e_price.png", f"{TMP}/e_feat.png", f"{TMP}/e_use.png",
             f"{TMP}/e_link.png", f"{TMP}/e_site.png", sfx] + [f"{TMP}/name{i}.png" for i in range(8)]
    inp = []
    for p in paths:
        if p.endswith(".png"):
            inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL + 1:.2f}", "-i", p]
        else:
            inp += ["-i", p]
    ix = {n: i for i, n in enumerate(names)}
    fc = []
    pulses = "+".join(f"0.22*exp(-9*abs(t-{c:.3f}))" for c in T[1:len(SEGS) + 1])
    fc.append(f"[0:v]eq=brightness='0.02+{pulses}':saturation=1.1:contrast=1.04:eval=frame,format=gbrp[g0r]")
    fc.append(f"[{ix['dust']}:v]format=gbrp[dr];[g0r][dr]blend=all_mode=screen:all_opacity=0.9,format=rgba[c0]")
    cur = "c0"
    e0 = T[-1] + OV * 0.5

    def pop(nm, a, b2, ypos, amp=0.4, k=9, extra="", fade_out=True):
        fo = f",fade=t=out:st={b2 - 0.12:.3f}:d=0.12:alpha=1" if fade_out else ""
        fc.append(f"[{ix[nm]}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.14:alpha=1{fo},scale=w='iw*(1+{amp}*exp(-{k}*max(0,t-{a:.3f})){extra})':h=-1:eval=frame[p_{nm}]")

    def put(nm, a, b2, ypos, **kw):
        nonlocal cur
        pop(nm, a, b2, ypos, **kw)
        nxt = f"o_{nm}"
        end_en = f",{b2:.3f}" if b2 is not None else ",999"
        fc.append(f"[{cur}][p_{nm}]overlay=x=(W-w)/2:y='{ypos}-h/2+8*sin(3*t)':eof_action=pass:enable='between(t,{a:.3f}{end_en})'[{nxt}]")
        cur = nxt

    put("hook", 0.05, T[1] + OV * 0.5, "175")
    for i in range(8):
        a, b2 = T[i + 1] + OV * 0.55, T[i + 2] + OV * 0.4
        put(f"n{i}", a, b2, "190", amp=0.45)
    # bandeau de prix permanent (pendant les pioches)
    fc.append(f"[{ix['pill']}:v]format=rgba,fade=t=in:st=1.2:d=0.3:alpha=1,fade=t=out:st={e0 - 0.2:.3f}:d=0.2:alpha=1,scale=w='iw*(1+0.035*sin(5*t))':h=-1:eval=frame[pp]")
    fc.append(f"[{cur}][pp]overlay=x=(W-w)/2:y='372-h/2':eof_action=pass:enable='between(t,1.2,{e0:.3f})'[pl]")
    cur = "pl"
    # carte de fin
    put("title", e0 + 0.10, 999, "H*0.19", amp=0.35)
    put("price", e0 + 0.85, 999, "H*0.395", amp=0.6, k=7, extra="+0.03*sin(6*t)")
    put("feat", e0 + 1.35, 999, "H*0.56", amp=0.15)
    put("use", e0 + 1.65, 999, "H*0.612", amp=0.15)
    put("link", e0 + 2.0, 999, "H*0.6875", amp=0.3, extra="+0.03*sin(6*t)")
    put("site", e0 + 2.3, 999, "H*0.752", amp=0.15)
    # filigrane qui tourne dans les coins
    fc.append(f"[{ix['wm']}:v]format=rgba,colorchannelmixer=aa=0.6[wmk]")
    cx = "if(lt(mod(t,16),4),40,if(lt(mod(t,16),8),W-w-40,if(lt(mod(t,16),12),40,W-w-40)))"
    cy = "if(lt(mod(t,16),4),620,if(lt(mod(t,16),8),1000,if(lt(mod(t,16),12),1130,720)))"
    fc.append(f"[{cur}][wmk]overlay=x='{cx}':y='{cy}':eof_action=pass:enable='lt(t,{e0:.3f})',format=yuv420p[vout]")
    fc.append(f"[{ix['sfx']}:a]aformat=sample_rates=44100:channel_layouts=stereo,loudnorm=I=-16:TP=-2:LRA=5,afade=t=out:st={TOTAL - 0.5:.2f}:d=0.5[aout]")
    run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{TOTAL:.2f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                                                       "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])


if __name__ == "__main__":
    make_assets()
    dust = f"{TMP}/dust.mp4"
    if not os.path.exists(dust):
        make_dust(dust)
    sfx = make_audio()
    base = make_base(make_segments())
    final(base, dust, sfx)
    print("OK", out, os.path.getsize(out) // 1000, "ko")
