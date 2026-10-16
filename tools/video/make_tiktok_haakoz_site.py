"""
TikTok (1080x1920, 30 i/s) qui fait visiter TOUT le site Haakoz.com, aux couleurs du site : écran de lancement violet (logo HK qui goutte), fiche produit style site
(carte à coins arrondis, pastille de catégorie, étiquette de prix, nom + badge vérifié + « Haakoz »), onglets Modèles / Animations / VFX qui s'allument selon la catégorie,
puis carte de fin violette.

    python tools/video/make_tiktok_haakoz_site.py <pioches.mp4> <giveaway.mp4> <ult_ice.mp4> <capture_logo.png> <capture_animations.png> <sortie.mp4>
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
src, gsrc, isrc, logo_shot, anim_shot, out = sys.argv[1:7]
TMP = os.path.join(os.path.dirname(os.path.abspath(out)), "_tmp_hksite")
os.makedirs(TMP, exist_ok=True)
FB = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FX = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
FS = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
PURPLE, PURPLE_D, NAVY, LAV, PAGE = (110, 83, 246), (88, 65, 216), (27, 22, 54), (231, 222, 248), (251, 248, 253)
SITE = "haakoz.com"

OVT = 0.35                      # fondu entre produits (dans la fenêtre)
OV = 0.5                        # transition entre scènes
D0, D2 = 1.6, 3.6
# produits : (nom court, titre de la fiche, catégorie, prix affiché sur le site ou None, durée du clip dans la fenêtre)
PRODUCTS = [
    ("PICKAXES", "Realistic Pickaxes", "Models", "10\u20ac", 2.4),
    ("COZY HOUSE", "Cozy House", "Models", "15\u20ac", 1.9),
    ("NATURE PACK", "Nature Pack", "Models", "9\u20ac", 1.9),
    ("ICE VFX", "Ice VFX Pack", "VFX", None, 2.0),
    ("ANIMATIONS", "Roblox Animations", "Animations", "25\u20ac", 1.7),
    ("ANIMATIONS", "Roblox Animations", "Animations", "15\u20ac", 2.2),
]
CATS = ["All", "Models", "Animations", "VFX"]
L1 = sum(p[4] for p in PRODUCTS)
STARTS = [sum(p[4] for p in PRODUCTS[:i]) for i in range(len(PRODUCTS))]
D1 = L1 - OV                    # visible de la scène 1 (jusqu'au début du fondu vers la fin)
S1_0 = D0
S2_0 = D0 + D1
TOTAL = D0 + D1 + D2
WX, WY, WW, WH = 80, 470, 920, 840
GY0, GH = 290, 1200             # le groupe « carte » : y absolu de départ et hauteur (centre = centre de la fenêtre)
print("durée", TOTAL)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:600]); print(r.stderr[-2500:]); raise SystemExit(1)


def font(path, size):
    return ImageFont.truetype(path, size)


def textlen(txt, f):
    return ImageDraw.Draw(Image.new("L", (1, 1))).textlength(txt, font=f)


def rr_mask(w, h, r, ss=4):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def grad_img(w, h, c0, c1, horizontal=False):
    a = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        a[:, :, c] = (np.linspace(c0[c], c1[c], w)[None, :] if horizontal else np.linspace(c0[c], c1[c], h)[:, None])
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


def paste(base, im, x, y):
    x, y = int(x), int(y)
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(im.width, base.width - x), min(im.height, base.height - y)
    if cx1 > cx0 and cy1 > cy0:
        base.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def shadow(im, blur=26, dy=14, alpha=0.22, col=(110, 83, 246)):
    pad = blur * 3
    base = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = im.split()[3].point(lambda v: int(v * alpha))
    s = Image.new("RGBA", im.size, col + (0,))
    s.putalpha(a)
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh.paste(s, (pad, pad + dy))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(sh)
    base.alpha_composite(im, (pad, pad))
    return base


def pill(text, size, fg, bg=None, gradient=None, padx=1.0, pady=0.55, fontp=FB, outline=None, shad=False):
    f = font(fontp, size)
    tw = int(textlen(text, f))
    w, h = tw + int(size * 2 * padx), int(size * (1 + 2 * pady))
    m = rr_mask(w, h, h // 2)
    body = grad_img(w, h, *gradient) if gradient else Image.new("RGBA", (w, h), bg + (255,))
    body.putalpha(m)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.alpha_composite(body)
    if outline:
        ImageDraw.Draw(im).rounded_rectangle((1, 1, w - 2, h - 2), h // 2, outline=outline + (255,), width=3)
    ImageDraw.Draw(im).text((w / 2, h / 2 + size * 0.04), text, font=f, fill=fg + (255,), anchor="mm")
    return shadow(im) if shad else im


def text_im(lines, color_top, color_bot, size, fontp=FB, gap=1.05, glow=None, maxw=940):
    f = font(fontp, size)
    while max(textlen(l, f) for l in lines) > maxw and size > 30:
        size -= 4
        f = font(fontp, size)
    lh = int(size * gap)
    pad = 40
    w = int(max(textlen(l, f) for l in lines)) + 2 * pad
    h = lh * len(lines) + 2 * pad
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i, l in enumerate(lines):
        d.text((w / 2, pad + i * lh + lh / 2), l, font=f, fill=255, anchor="mm")
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if glow:
        g = Image.new("RGBA", (w, h), glow + (0,))
        g.putalpha(mask.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6)))
        im.alpha_composite(g)
    gi = grad_img(w, h, color_top, color_bot)
    gi.putalpha(mask)
    im.alpha_composite(gi)
    return im


# ============================================================ logo (extrait de la capture : clé de couleur sur le violet du site)
def make_logo():
    a = Image.open(logo_shot).convert("RGB")
    k = a.width / 923
    box = (int(300 * k), int(740 * k), int(670 * k), int(1140 * k))
    c = np.asarray(a.crop(box)).astype(np.float32)
    bg = np.array([110, 83, 246], np.float32)
    diff = np.maximum(c[:, :, 0] - bg[0], c[:, :, 1] - bg[1])
    al = np.clip((diff - 8) / 26.0, 0, 1)
    al3 = np.maximum(al, 1e-3)[:, :, None]
    fg = np.clip((c - bg * (1 - al3)) / al3, 0, 255)
    im = Image.fromarray(np.dstack([fg, al * 255]).astype(np.uint8), "RGBA")
    bb = im.getbbox()
    im = im.crop(bb)
    return im


# ============================================================ éléments graphiques
def tabs_png(active, path):
    """Rangée d'onglets du site : « Tous / Modèles / Animations / VFX », l'actif en violet."""
    f = font(FX, 40)
    gap, padx, h = 18, 34, 84
    widths = [int(textlen(c, f)) + 2 * padx for c in CATS]
    W_ = sum(widths) + gap * (len(CATS) - 1) + 40
    im = Image.new("RGBA", (W_ + 80, h + 80), (0, 0, 0, 0))
    bar = Image.new("RGBA", (W_, h + 24), (243, 241, 254, 255))
    bar.putalpha(rr_mask(W_, h + 24, (h + 24) // 2))
    base = Image.new("RGBA", im.size, (0, 0, 0, 0))
    base.paste(bar, (40, 28), bar)
    x = 40 + 20
    d = ImageDraw.Draw(base)
    for c, w in zip(CATS, widths):
        if c == active:
            g = grad_img(w, h, (126, 102, 246), (148, 127, 247))
            g.putalpha(rr_mask(w, h, h // 2))
            base.alpha_composite(g, (x, 40))
            d.text((x + w / 2, 40 + h / 2 + 2), c, font=f, fill=(255, 255, 255, 255), anchor="mm")
        else:
            d.text((x + w / 2, 40 + h / 2 + 2), c, font=f, fill=NAVY + (255,), anchor="mm")
        x += w + gap
    base.save(path)


def verified_star():
    star = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star)
    pts = []
    for i in range(24):
        r = 92 if i % 2 == 0 else 78
        pts.append((100 + r * math.cos(math.pi * i / 12), 100 + r * math.sin(math.pi * i / 12)))
    sd.polygon(pts, fill=(124, 100, 246, 255))
    sd.line([(58, 102), (88, 132), (144, 74)], fill=(255, 255, 255, 255), width=22, joint="curve")
    return star.resize((52, 52), Image.LANCZOS)


def make_assets():
    logo = make_logo()
    big = logo.resize((400, int(logo.height * 400 / logo.width)), Image.LANCZOS)
    big.save(f"{TMP}/logo_big.png")
    logo.resize((230, int(logo.height * 230 / logo.width)), Image.LANCZOS).save(f"{TMP}/logo_mid.png")
    # fonds
    y, x = np.mgrid[:H, :W].astype(np.float32)
    page = np.zeros((H, W, 3), np.float32)
    page[:] = np.array(PAGE, np.float32)
    g1 = np.exp(-(((x - 820) / 520) ** 2 + ((y - 120) / 380) ** 2))[:, :, None]
    g2 = np.exp(-(((x - 120) / 560) ** 2 + ((y - 1500) / 520) ** 2))[:, :, None]
    page = page * (1 - 0.55 * g1) + np.array([196, 180, 255], np.float32) * 0.55 * g1
    page = page * (1 - 0.35 * g2) + np.array([214, 202, 255], np.float32) * 0.35 * g2
    Image.fromarray(np.clip(page, 0, 255).astype(np.uint8)).save(f"{TMP}/bg_light.png")
    pu = np.zeros((H, W, 3), np.float32)
    pu[:] = np.array(PURPLE, np.float32)
    gl = np.exp(-(((x - W / 2) / 620) ** 2 + ((y - 760) / 760) ** 2))[:, :, None]
    pu = pu * (1 - 0.35 * gl) + np.array([150, 128, 255], np.float32) * 0.35 * gl
    vig = np.clip(((x - W / 2) ** 2 / (W * 0.9) ** 2 + (y - H / 2) ** 2 / (H * 0.8) ** 2), 0, 1)[:, :, None]
    pu = pu * (1 - 0.18 * vig)
    Image.fromarray(np.clip(pu, 0, 255).astype(np.uint8)).save(f"{TMP}/bg_purple.png")
    for i, (sz, col) in enumerate(((760, (190, 172, 255)), (620, (214, 200, 255)))):
        b = Image.new("RGBA", (sz + 200, sz + 200), (0, 0, 0, 0))
        ImageDraw.Draw(b).ellipse((100, 100, 100 + sz, 100 + sz), fill=col + (90,))
        b.filter(ImageFilter.GaussianBlur(60)).save(f"{TMP}/blob{i}.png")
    # carte (fond lavande + cadre blanc) ; la fenêtre vidéo arrondie se pose dessus
    rr_mask(WW, WH, 120).save(f"{TMP}/mask.png")
    grp = Image.new("RGBA", (W, GH), (0, 0, 0, 0))
    wy = WY - GY0
    bm = rr_mask(WW + 44, WH + 52, 140)
    bb = grad_img(WW + 44, WH + 52, (196, 180, 255), (176, 158, 255))
    bb.putalpha(bm)
    paste(grp, shadow(bb, 40, 26, 0.35), WX - 22 - 120, wy - 14 - 120)
    ring = Image.new("RGBA", (WW + 24, WH + 24), (255, 255, 255, 255))
    ring.putalpha(rr_mask(WW + 24, WH + 24, 130))
    grp.alpha_composite(ring, (WX - 12, wy - 12))
    grp.save(f"{TMP}/card.png")
    star = verified_star()
    av_logo = logo.resize((34, int(logo.height * 34 / logo.width)), Image.LANCZOS)
    for i, (short, title, cat, price, _d) in enumerate(PRODUCTS):
        ov = Image.new("RGBA", (W, GH), (0, 0, 0, 0))
        chip = pill({"Models": "3D Models", "Animations": "Animations", "VFX": "VFX"}[cat], 36, PURPLE_D, bg=(255, 255, 255), padx=0.7, pady=0.5, fontp=FX)
        ov.alpha_composite(chip, (WX + 34, wy + 34))
        ih = 150
        info = Image.new("RGBA", (WW - 40, ih), (0, 0, 0, 0))
        info.paste(Image.new("RGBA", info.size, (255, 255, 255, 255)), (0, 0), rr_mask(info.width, ih, 56))
        d = ImageDraw.Draw(info)
        d.text((44, 52), title, font=font(FB, 52), fill=NAVY + (255,), anchor="lm")
        info.alpha_composite(star, (44 + int(textlen(title, font(FB, 52))) + 24, 52 - 26))
        av = Image.new("RGBA", (56, 56), (0, 0, 0, 0))
        av.paste(Image.new("RGBA", (56, 56), (243, 240, 255, 255)), (0, 0), rr_mask(56, 56, 28))
        av.alpha_composite(av_logo, (11, 56 // 2 - av_logo.height // 2 - 1))
        info.alpha_composite(av, (40, 86))
        d.text((112, 114), "Haakoz", font=font(FX, 40), fill=NAVY + (255,), anchor="lm")
        paste(ov, shadow(info, 24, 14, 0.18), WX + 20 - 72, wy + WH + 26 - 72)
        ov.save(f"{TMP}/ov{i}.png")
        if price:
            tab = Image.new("RGBA", (200, 160), (0, 0, 0, 0))
            tw = Image.new("RGBA", (200, 160), (255, 255, 255, 255))
            tw.putalpha(rr_mask(200, 160, 40))
            tab.alpha_composite(tw)
            td = ImageDraw.Draw(tab)
            td.text((100, 42), "P R I C E", font=font(FX, 21), fill=(150, 142, 190, 255), anchor="mm")
            td.text((100, 104), price, font=font(FB, 84 if len(price) < 4 else 72), fill=NAVY + (255,), anchor="mm")
            shadow(tab, 22, 12, 0.3).save(f"{TMP}/price{i}.png")
        # titre : onglets du site + nom
        tabs_png(cat, f"{TMP}/tabs_{i}.png")
        tb = Image.open(f"{TMP}/tabs_{i}.png")
        tb = tb.resize((int(tb.width * 0.8), int(tb.height * 0.8)), Image.LANCZOS)
        nmi = text_im([short], (27, 22, 54), (88, 65, 216), 150, FB)
        im = Image.new("RGBA", (max(tb.width, nmi.width) + 20, tb.height + nmi.height - 40), (0, 0, 0, 0))
        im.alpha_composite(tb, ((im.width - tb.width) // 2, 0))
        im.alpha_composite(nmi, ((im.width - nmi.width) // 2, tb.height - 38))
        im.save(f"{TMP}/head{i}.png")
    # en-tête : logo + haakoz.com
    top = Image.new("RGBA", (460, 130), (0, 0, 0, 0))
    lg2 = logo.resize((82, int(logo.height * 82 / logo.width)), Image.LANCZOS)
    top.alpha_composite(lg2, (8, 65 - lg2.height // 2))
    ImageDraw.Draw(top).text((116, 60), SITE, font=font(FB, 56), fill=NAVY + (255,), anchor="lm")
    top.save(f"{TMP}/top.png")
    # scènes violettes
    text_im([SITE.upper()], (255, 255, 255), (232, 226, 255), 118, FB, glow=(255, 255, 255)).save(f"{TMP}/s0_word.png")
    pill("MODELS  \u2022  ANIMATIONS  \u2022  VFX", 40, (255, 255, 255), bg=(150, 128, 255), fontp=FX, padx=0.9, pady=0.55, outline=(220, 212, 255)).save(f"{TMP}/s0_tag.png")
    text_im(["EVERYTHING FOR"], (255, 255, 255), (232, 226, 255), 72, FB).save(f"{TMP}/e_get.png")
    text_im(["YOUR ROBLOX", "GAME"], (255, 255, 255), (222, 214, 255), 128, FB, glow=(255, 255, 255)).save(f"{TMP}/e_main.png")
    for j, c in enumerate(("3D MODELS", "ANIMATIONS", "VFX")):
        pill(c, 52, (255, 255, 255), bg=(150, 128, 255), fontp=FB, padx=0.9, pady=0.6, outline=(220, 212, 255)).save(f"{TMP}/e_c{j + 1}.png")
    pill(SITE, 66, NAVY, bg=(255, 255, 255), fontp=FB, padx=1.1, pady=0.6, shad=True).save(f"{TMP}/e_btn.png")
    text_im(["LINK IN BIO"], (255, 255, 255), (232, 226, 255), 64, FB).save(f"{TMP}/e_bio.png")
    text_im([SITE], (255, 255, 255), (255, 255, 255), 40, FB, glow=(60, 40, 150)).save(f"{TMP}/wm.png")


# ============================================================ poussière lumineuse (blanc sur noir ; sert en « screen » sur le violet et, inversée, en « multiply » sur le clair)
def make_dust(path):
    rng = np.random.default_rng(21)
    fl = []
    for i in range(150):
        depth = rng.random()
        fl.append(dict(x=rng.uniform(-60, W + 60), y=rng.uniform(-100, H + 100), v=25 + 110 * depth ** 1.2, r=2 + 8 * depth ** 1.5, sw=rng.uniform(15, 60), fr=rng.uniform(0.5, 1.6),
                       ph=rng.uniform(0, 6.28), a=0.3 + 0.7 * depth))

    def sprite(r):
        n = int(r * 4) | 1
        yy, xx = np.mgrid[:n, :n] - n // 2
        return np.clip(1.0 - np.hypot(xx, yy) / max(r, 0.5), 0, 1) ** 0.9
    cache = {}
    stars = [dict(x=rng.uniform(40, W - 40), y=rng.uniform(120, H - 360), t0=rng.uniform(0, TOTAL), dur=rng.uniform(0.6, 1.1), s=rng.uniform(14, 36)) for _ in range(34)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(int(TOTAL * FPS) + 2):
        t = fi / FPS
        img = np.zeros((H, W, 3), dtype=np.float32)
        for f in fl:
            y = (f["y"] - f["v"] * t) % (H + 200) - 100
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
            s = (sp[ya - y0:yb - y0, xa - x0:xb - x0] * f["a"])[:, :, None]
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
                        img[py, px] = np.maximum(img[py, px], (a, a, a))
        pr.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    pr.stdin.close()
    pr.wait()


# ============================================================ fenêtre produit (vidéo des pioches recadrée, fondus enchaînés)
def make_window():
    specs = [
        # (source, filtre d'entrée, durée)
        (src, "trim=start=0:duration=2.0,setpts=1.45*(PTS-STARTPTS),fps={fps},trim=duration={L},delogo=x=410:y=50:w=230:h=110,crop=790:720:420:0", False),
        (gsrc, "trim=start=6.9:duration={L},setpts=PTS-STARTPTS,fps={fps},crop=685:624:200:456", False),
        (gsrc, "trim=start=3.6:duration={L},setpts=PTS-STARTPTS,fps={fps},crop=631:576:260:40", False),
        (isrc, "trim=start=12.0:duration={L},setpts=PTS-STARTPTS,fps={fps},crop=788:720:246:0", False),
        (anim_shot, "fps={fps},crop=327:300:98:880", True),
        (anim_shot, "fps={fps},crop=327:300:98:1560", True),
    ]
    files = []
    for i, ((path, flt, still), prod) in enumerate(zip(specs, PRODUCTS)):
        L = prod[4] + OVT
        flt = flt.format(fps=FPS, L=L)
        if still:
            im = Image.open(anim_shot).convert("RGB")
            k = im.width / 923
            # recadrage en pixels réels de la capture (coordonnées de la capture 923 px de large)
            w0, h0, x0, y0 = [int(float(v) * k) for v in flt.split("crop=")[1].split(":")]
            pre = ["-loop", "1", "-framerate", str(FPS), "-t", f"{L:.2f}", "-i", path]
            head = f"[0:v]fps={FPS},crop={w0}:{h0}:{x0}:{y0},scale=1840:-1:flags=lanczos"
        else:
            pre = ["-i", path]
            head = f"[0:v]{flt}"
        dd = f"{'-' if i % 2 else ''}40"
        fc = (f"{head},scale={WW}:{WH},scale=w='{WW}*(1+0.14*t/{L}+0.05*exp(-9*t))':h='{WH}*(1+0.14*t/{L}+0.05*exp(-9*t))':eval=frame,"
              f"crop={WW}:{WH}:x='(iw-{WW})/2+{dd}*(t/{L}-0.5)':y='(ih-{WH})/2+10*sin(5*t)',unsharp=5:5:0.7,eq=brightness=0.04:contrast=1.08:saturation=1.15:gamma=0.97,format=yuv420p[v]")
        f = f"{TMP}/tile{i}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error"] + pre + ["-filter_complex", fc, "-map", "[v]", "-an", "-t", f"{L:.2f}", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", f])
        files.append(f)
    trans = ["smoothleft", "zoomin", "smoothup", "circleopen", "smoothright", "radial"]
    inp, fc, last = [], [], "0:v"
    for f in files:
        inp += ["-i", f]
    length = PRODUCTS[0][4] + OVT
    for k in range(1, len(files)):
        off = length - OVT
        fc.append(f"[{last}][{k}:v]xfade=transition={trans[(k - 1) % len(trans)]}:duration={OVT}:offset={off:.3f}[v{k}]")
        length += PRODUCTS[k][4]
        last = f"v{k}"
    p = f"{TMP}/window.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", str(FPS), p])
    return p


# ============================================================ scènes
class G:
    """Petit constructeur de graphe ffmpeg : entrées en boucle + calques à apparition « pop »."""

    def __init__(self, dur):
        self.inp, self.fc, self.n, self.cur, self.dur = [], [], 0, None, dur

    def png(self, path):
        self.inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{self.dur + 0.5:.2f}", "-i", path]
        self.n += 1
        return self.n - 1

    def vid(self, path):
        self.inp += ["-i", path]
        self.n += 1
        return self.n - 1

    def pop(self, path, a, cx, cy, b2=None, mode="stamp", amp=0.4, k=9, bob=6, extra=""):
        i = self.png(path)
        nm = f"p{i}"
        fo = f",fade=t=out:st={b2 - 0.15:.3f}:d=0.15:alpha=1" if b2 else ""
        if mode == "elastic":
            sc = f"(1-0.7*exp(-8*max(0,t-{a:.3f}))*cos(14*max(0,t-{a:.3f})))"
        else:
            sc = f"(1+{amp}*exp(-{k}*max(0,t-{a:.3f})){extra})"
        self.fc.append(f"[{i}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.16:alpha=1{fo},scale=w='max(2,iw*{sc})':h=-1:eval=frame[{nm}]")
        nx = f"o{i}"
        en = f":enable='between(t,{a:.3f},{b2:.3f})'" if b2 else f":enable='gte(t,{a:.3f})'"
        self.fc.append(f"[{self.cur}][{nm}]overlay=x='{cx}-w/2':y='{cy}-h/2+{bob}*sin(2.2*t)':eof_action=pass{en}[{nx}]")
        self.cur = nx

    def run(self, out_path, extra_in=None):
        run(["ffmpeg", "-y", "-loglevel", "error"] + self.inp + ["-filter_complex", ";".join(self.fc), "-map", f"[{self.cur}]", "-t", f"{self.dur:.3f}", "-an", "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                                                                 "-pix_fmt", "yuv420p", "-r", str(FPS), out_path])


def dust_blend(g, dust_idx, mode, opacity):
    if mode == "screen":
        g.fc.append(f"[{g.cur}]format=gbrp[bgr];[{dust_idx}:v]format=gbrp[dr];[bgr][dr]blend=all_mode=screen:all_opacity={opacity},format=rgba[dx]")
    else:
        g.fc.append(f"[{g.cur}]format=gbrp[bgr];[{dust_idx}:v]negate,curves=r='0/0.55 1/1':g='0/0.42 1/1':b='0/0.96 1/1',format=gbrp[dr];[bgr][dr]blend=all_mode=multiply:all_opacity={opacity},format=rgba[dx]")
    g.cur = "dx"


def scene0(dust):
    g = G(D0 + OV)
    b = g.png(f"{TMP}/bg_purple.png")
    d = g.vid(dust)
    g.fc.append(f"[{b}:v]format=rgba[b0]")
    g.cur = "b0"
    dust_blend(g, d, "screen", 0.8)
    g.pop(f"{TMP}/logo_big.png", 0.1, "540", "780", mode="elastic", bob=10)
    g.pop(f"{TMP}/s0_word.png", 0.55, "540", "1130", amp=0.35)
    g.pop(f"{TMP}/s0_tag.png", 0.85, "540", "1285", amp=0.25, bob=3)
    g.run(f"{TMP}/s0.mp4")


def scene1(dust, window):
    g = G(L1)
    b = g.png(f"{TMP}/bg_light.png")
    b0 = g.png(f"{TMP}/blob0.png")
    b1 = g.png(f"{TMP}/blob1.png")
    d = g.vid(dust)
    wv = g.vid(window)
    mk = g.png(f"{TMP}/mask.png")
    g.fc.append(f"[{b}:v]format=rgba[bg]")
    g.fc.append(f"[bg][{b0}:v]overlay=x='640+60*sin(0.9*t)':y='-250+40*cos(0.7*t)':eof_action=pass[x1]")
    g.fc.append(f"[x1][{b1}:v]overlay=x='-330+50*cos(0.8*t)':y='1250+50*sin(0.6*t)':eof_action=pass[x2]")
    top = g.png(f"{TMP}/top.png")
    g.fc.append(f"[{top}:v]format=rgba,fade=t=in:st=0.3:d=0.4:alpha=1[tp]")
    g.fc.append(f"[x2][tp]overlay=x=(W-w)/2:y=105:eof_action=pass[x3]")
    a = 0.35
    cy = WY + WH // 2
    sc = f"(1-0.7*exp(-8*max(0,t-{a}))*cos(14*max(0,t-{a})))"
    cg = g.png(f"{TMP}/card.png")
    g.fc.append(f"[{cg}:v]format=rgba,fade=t=in:st={a}:d=0.16:alpha=1,scale=w='max(2,iw*{sc})':h=-1:eval=frame[cgs]")
    g.fc.append(f"[{wv}:v]format=yuv420p[wv0]")
    g.fc.append(f"[wv0][{mk}:v]alphamerge,format=rgba,fade=t=in:st={a}:d=0.16:alpha=1,scale=w='max(2,iw*{sc})':h=-1:eval=frame[wvs]")
    g.fc.append(f"[x3][cgs]overlay=x='540-w/2':y='{GY0 + GH // 2}-h/2+8*sin(2*t)':eof_action=pass[x4]")
    g.fc.append(f"[x4][wvs]overlay=x='540-w/2':y='{cy}-h/2+8*sin(2*t)':eof_action=pass[x5]")
    g.cur = "x5"
    n = len(PRODUCTS)
    for i, (short, title, cat, price, du) in enumerate(PRODUCTS):
        t0 = 0.55 if i == 0 else STARTS[i] + 0.2
        t1 = (STARTS[i + 1] + 0.2) if i + 1 < n else None
        # pastille + bandeau d'infos (suivent le pop de la carte seulement au premier produit ; ensuite simple fondu)
        g.pop(f"{TMP}/ov{i}.png", t0, "540", str(GY0 + GH // 2), b2=t1, amp=0.0, bob=8)
        if price:
            g.pop(f"{TMP}/price{i}.png", t0 + 0.25, WX + WW - 105, WY + 38, b2=t1, mode="elastic", bob=5)
        g.pop(f"{TMP}/head{i}.png", t0, "540", "345", b2=t1, amp=0.35, bob=4)
    dust_blend(g, d, "multiply", 0.75)
    g.run(f"{TMP}/s1.mp4")


def scene2(dust):
    g = G(D2)
    b = g.png(f"{TMP}/bg_purple.png")
    d = g.vid(dust)
    g.fc.append(f"[{b}:v]format=rgba[b0]")
    g.cur = "b0"
    dust_blend(g, d, "screen", 0.8)
    g.pop(f"{TMP}/logo_mid.png", 0.55, "540", "300", mode="elastic", bob=8)
    g.pop(f"{TMP}/e_get.png", 0.8, "540", "520", amp=0.3, bob=0)
    g.pop(f"{TMP}/e_main.png", 0.95, "540", "700", amp=0.35, bob=0)
    g.pop(f"{TMP}/e_c1.png", 1.3, "540", "960", amp=0.3, bob=2)
    g.pop(f"{TMP}/e_c2.png", 1.45, "540", "1070", amp=0.3, bob=2)
    g.pop(f"{TMP}/e_c3.png", 1.6, "540", "1180", amp=0.3, bob=2)
    g.pop(f"{TMP}/e_btn.png", 1.95, "540", "1320", amp=0.3, bob=0, extra="+0.03*sin(6*t)")
    g.pop(f"{TMP}/e_bio.png", 2.25, "540", "1440", amp=0.2, bob=0)
    g.run(f"{TMP}/s2.mp4")


# ============================================================ son (sans musique)
def bloop(dur=0.4, f0=1000, f1=260):
    t = np.arange(int(dur * SR)) / SR
    fr = f1 + (f0 - f1) * np.exp(-t * 16)
    return (np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 9) * (1 - np.exp(-t * 600))).astype(np.float32)


def make_audio():
    n = int(SR * (TOTAL + 0.6))
    fx = np.zeros(n, np.float32)
    add(fx, 0.14, bloop(), 0.55)
    add(fx, S1_0 - 0.45, whoosh(0.55, up=False), 0.2)
    notes = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]
    for i, (short, title, cat, price, du) in enumerate(PRODUCTS):
        t0 = S1_0 + (0.55 if i == 0 else STARTS[i] + 0.2)
        add(fx, t0 + 0.05, bell(notes[i], 1.3), 0.5)
        if price:
            for j, f in enumerate((1760, 2349)):
                add(fx, t0 + 0.28 + 0.07 * j, ping(f, 0.6, 8), 0.35)
        if i in (1, 3, 5):
            add(fx, S1_0 + STARTS[i] - 0.2, whoosh(0.45, up=(i % 2 == 1)), 0.18)
    add(fx, S2_0 - 0.9, riser(1.1), 0.28)
    add(fx, S2_0 + 0.1, boom(), 0.22)
    add(fx, S2_0 + 0.6, bloop(), 0.5)
    for j, f in enumerate((783.99, 987.77, 1174.66)):
        add(fx, S2_0 + 1.0 + 0.12 * j, bell(f, 1.1), 0.45)
    for j, f in enumerate((1760, 2349, 3136)):
        add(fx, S2_0 + 1.9 + 0.07 * j, ping(f, 0.7, 8), 0.4)
    fx = reverb(fx, wet=0.2)
    mix = fx / (np.max(np.abs(fx)) + 1e-6) * 0.7
    p = f"{TMP}/sfx.wav"
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return p


def final(s0, s1, s2, sfx):
    wm = f"{TMP}/wm.png"
    fc = (f"[0:v][1:v]xfade=transition=circleopen:duration={OV}:offset={D0:.3f}[a];"
          f"[a][2:v]xfade=transition=smoothup:duration={OV}:offset={D0 + L1 - OV:.3f}[b];"
          f"[b]format=rgba[b1];[4:v]format=rgba,colorchannelmixer=aa=0.5[wm];"
          f"[b1][wm]overlay=x='if(lt(mod(t,12),4),40,if(lt(mod(t,12),8),W-w-40,40))':y=1500:eof_action=pass:enable='gte(t,{S1_0 + 0.8})',format=yuv420p[v];"
          f"[3:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=2.0,alimiter=limit=0.9,afade=t=out:st={TOTAL - 0.5:.2f}:d=0.5[aout]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", s0, "-i", s1, "-i", s2, "-i", sfx, "-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL + 1:.2f}", "-i", wm, "-filter_complex", fc,
         "-map", "[v]", "-map", "[aout]", "-t", f"{TOTAL:.2f}", "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", out])


if __name__ == "__main__":
    make_assets()
    dust = f"{TMP}/dust.mp4"
    if not os.path.exists(dust):
        make_dust(dust)
    win = make_window()
    scene0(dust)
    scene1(dust, win)
    scene2(dust)
    final(f"{TMP}/s0.mp4", f"{TMP}/s1.mp4", f"{TMP}/s2.mp4", make_audio())
    print("OK", out, os.path.getsize(out) // 1000, "ko")
