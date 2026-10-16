"""
TikTok (1080x1920, 30 i/s) de présentation de la boutique Haakoz.com : un coup d'œil rapide sur les packs (VFX glace, pioches, arbres voxel,
nature réaliste, feu de camp animé, katanas), transitions xfade, poussière dorée, texte élastique, effets sonores sans musique, carte de fin « HAAKOZ.COM ».

    python tools/video/make_tiktok_haakoz.py <sortie.mp4>
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
UP = "/root/.claude/uploads/0aa101b7-0592-57c3-b839-49cfb9fcce70/"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
out = sys.argv[1]
TMP = os.path.join(os.path.dirname(os.path.abspath(out)), "_tmp_haakoz")
os.makedirs(TMP, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
OV = 0.4
SQ_Y = 330
FH = 1288                       # tuile 1080x1288 (ratio 0,838) : y 330 -> 1618
SITE = "HAAKOZ.COM"
ASPECT = "604:720"              # recadrage vidéo 1280x720 au ratio de la tuile
CY, CG, CD = (70, 220, 255), (255, 205, 60), (110, 235, 120)
# (petit titre, titre, couleur, dégradé, type, fichier, début, recadrage/chaîne)
SEGS = [
    ("YOUR ROBLOX GAME", "NEEDS THIS", (255, 190, 70), ((255, 255, 255), (255, 214, 120)), "vid", UP + "b9f57ad6-ULT.mp4", 12.0, "crop=604:720:338:0"),
    ("EPIC EFFECTS", "ICE VFX", CY, ((235, 255, 255), (60, 205, 250)), "vid", UP + "7e5ac0f7-702addbc62fe2cc28987df72e592695d.mp4", 1.1, "crop=604:720:338:0"),
    ("8 REALISTIC TOOLS", "PICKAXES", CG, ((255, 250, 200), (255, 195, 40)), "vid", UP + "fb78ac0e-669f0144f7dc87d11d5d41b36c41f8f8.mp4", 15.1, "delogo=x=470:y=285:w=130:h=65,crop=604:720:503:0"),
    ("6 CUTE TREES", "VOXEL TREES", CD, ((240, 255, 215), (110, 235, 100)), "img", ROOT + "/TreesVoxel/Apercus/arbre-jungle.png", 0, "crop=800:954:200:106"),
    ("31 REALISTIC ASSETS", "NATURE PACK", (190, 140, 255), ((245, 235, 255), (170, 120, 255)), "img", ROOT + "/NaturePackRealiste/Apercus/rocher-cristaux.png", 0, "crop=880:1050:325:0"),
    ("ANIMATED", "CAMPFIRE", (255, 140, 50), ((255, 240, 200), (255, 130, 40)), "vid", ROOT + "/NaturePackRealiste/Apercus/feu-de-camp.mp4", 1.0, "crop=453:540:43:0"),
    ("4 BLADES", "KATANAS", (255, 90, 100), ((255, 235, 235), (255, 80, 95)), "img", ROOT + "/KatanasRealistic/Previews/Lineup.png", 0, "crop=838:1000:581:0"),
]
DUR, END = 2.0, 4.4
TRANS = ["fadewhite", "smoothleft", "smoothup", "circleopen", "smoothright", "radial", "zoomin"]
T = [0.0]
for _ in SEGS:
    T.append(T[-1] + (1.7 if len(T) == 1 else DUR))
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
        for k, c in enumerate(T[1:]):
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
    for i, (sub, title, col, grad, *_r) in enumerate(SEGS):
        if i == 0:
            text_png([("YOUR ROBLOX GAME", 74), ("NEEDS THIS", 190)], f"{TMP}/name{i}.png", grad=grad, glow=col)
        else:
            text_png([(sub, 54), (title, 170)], f"{TMP}/name{i}.png", grad=grad, glow=col)
        glow_png(col, f"{TMP}/glow{i}.png")
    glow_png((255, 210, 120), f"{TMP}/glow_end.png")
    text_png([("GET IT ALL ON", 70), (SITE, 168)], f"{TMP}/e_title.png", glow=(255, 190, 70), stroke=14)
    text_png([("ASSETS  •  VFX  •  PACKS", 54), ("FOR YOUR ROBLOX GAMES", 54)], f"{TMP}/e_feat.png", grad=((255, 245, 215), (255, 215, 140)), glow=(255, 170, 50), stroke=7, gap=1.3)
    pill_png("LINK IN BIO", f"{TMP}/e_link.png", 96, bg=(255, 170, 30, 255), outline=(255, 245, 210), fg=(40, 20, 4), glow=(255, 190, 70))
    pill_png(f"ROBLOX ASSETS  •  {SITE}", f"{TMP}/pill.png", 42)
    text_png([(SITE, 42)], f"{TMP}/wm.png", grad=((255, 255, 255), (255, 235, 190)), glow=(0, 0, 0), stroke=5)


# ============================================================ sound design (pas de musique : effets seulement)
def make_audio():
    rng = sx.rng
    n = int(SR * (TOTAL + 0.6))
    fx = np.zeros(n, np.float32)
    notes = [392.0, 523.25, 587.33, 659.25, 783.99, 880.0, 1046.5]
    for i in range(len(SEGS)):
        pop = T[i] + (OV * 0.55 if i else 0.15)
        add(fx, pop, bell(notes[i], 1.4), 0.55)
        if i and i % 2 == 1:
            add(fx, T[i] - 0.3, whoosh(0.55, up=(i % 4 == 1)), 0.2)
    add(fx, 0.05, boom(), 0.12)
    e = T[-1]
    add(fx, e - 1.0, riser(1.2), 0.3)
    add(fx, e + 0.05, boom(), 0.25)
    for j, f in enumerate((783.99, 987.77, 1174.66)):
        add(fx, e + 0.1 + 0.12 * j, bell(f, 1.2), 0.5)
    pr = e + 0.9
    add(fx, pr, ping(1760, 0.5, 9), 0.6)
    add(fx, pr + 0.07, ping(2349, 0.7, 8), 0.6)
    add(fx, pr + 0.14, ping(3136, 0.9, 7), 0.45)
    fx = reverb(fx, wet=0.22)
    mix = fx / (np.max(np.abs(fx)) + 1e-6) * 0.7
    p = f"{TMP}/sfx.wav"
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return p


# ============================================================ plans
def seg_len(i):
    return (1.7 if i == 0 else DUR)


def make_segments():
    files = []
    for i, (_, _, col, _, kind, path, st, crop) in enumerate(SEGS):
        L = seg_len(i) + OV
        d = f"{'-' if i % 2 else ''}50"
        if kind == "vid":
            pre = f"-i {path}".split()
            head = f"[0:v]trim=start={st}:duration={L},setpts=PTS-STARTPTS,fps={FPS},{crop},scale={W}:{FH}"
        else:
            pre = ["-loop", "1", "-framerate", str(FPS), "-t", f"{L:.2f}", "-i", path]
            head = f"[0:v]fps={FPS},{crop},scale={W}:{FH}"
        fc = (
            f"{head},split=3[t0][a][b];"
            f"[a]scale=-2:{H},crop={W}:{H},gblur=sigma=26,eq=brightness=0.05:saturation=1.15,format=gbrp[bgr];"
            f"[1:v]format=gbrp[gr];[bgr][gr]blend=all_mode=screen:all_opacity=0.6,format=yuv420p[bg];"
            f"[b]scale=w='{W}*(1+0.14*t/{L}+0.06*exp(-9*t))':h='{FH}*(1+0.14*t/{L}+0.06*exp(-9*t))':eval=frame,"
            f"crop={W}:{FH}:x='(iw-{W})/2+{d}*(t/{L}-0.5)':y='(ih-{FH})/2+14*sin(5*t)',"
            f"unsharp=5:5:0.8,eq=brightness=0.05:contrast=1.1:saturation=1.25:gamma=0.95,split=2[f1][f2];"
            f"[f2]gblur=sigma=30,eq=brightness=0.05[f3];[f1]format=gbrp[f1r];[f3]format=gbrp[f3r];[f1r][f3r]blend=all_mode=screen:all_opacity=0.40,format=yuva420p,"
            f"geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='255*min(1,min(Y,{FH - 1}-Y)/150)'[fg];"
            f"[bg][fg]overlay=(W-w)/2:{SQ_Y}+14*sin(2.2*t),format=yuv420p[v];[t0]nullsink"
        )
        fc = fc.replace(";[t0]nullsink", "")
        fc = fc.replace("split=3[t0][a][b]", "split=2[a][b]")
        f = f"{TMP}/seg{i}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error"] + pre + ["-loop", "1", "-framerate", str(FPS), "-t", f"{L:.2f}", "-i", f"{TMP}/glow{i}.png", "-filter_complex", fc,
             "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", f])
        files.append(f)
    # carte de fin : fond doré sombre
    fc = (f"color=c=0x120a04:s={W}x{H}:r={FPS}:d={END},format=gbrp[bgr];[0:v]format=gbrp[gr];[bgr][gr]blend=all_mode=screen:all_opacity=0.55,format=yuv420p[v]")
    f = f"{TMP}/end_bg.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-t", f"{END:.2f}", "-i", f"{TMP}/glow_end.png", "-filter_complex", fc,
         "-map", "[v]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", f])
    files.append(f)
    return files


def make_base(files):
    inp = []
    for f in files:
        inp += ["-i", f]
    fc, last = [], "0:v"
    length = seg_len(0) + OV
    for k in range(1, len(files)):
        off = length - OV
        fc.append(f"[{last}][{k}:v]xfade=transition={TRANS[k - 1]}:duration={OV}:offset={off:.3f}[v{k}]")
        length += ((seg_len(k) + OV) if k < len(SEGS) else END) - OV
        last = f"v{k}"
    p = f"{TMP}/base.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-r", str(FPS), p])
    return p


def final(base, dust, sfx):
    names = ["base", "dust", "pill", "wm", "title", "feat", "link", "sfx"] + [f"n{i}" for i in range(len(SEGS))]
    paths = [base, dust, f"{TMP}/pill.png", f"{TMP}/wm.png", f"{TMP}/e_title.png", f"{TMP}/e_feat.png", f"{TMP}/e_link.png", sfx] + [f"{TMP}/name{i}.png" for i in range(len(SEGS))]
    inp = []
    for p in paths:
        if p.endswith(".png"):
            inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL + 1:.2f}", "-i", p]
        else:
            inp += ["-i", p]
    ix = {n: i for i, n in enumerate(names)}
    fc = []
    pulses = "+".join(f"0.22*exp(-9*abs(t-{c:.3f}))" for c in T[1:])
    fc.append(f"[0:v]eq=brightness='0.02+{pulses}':saturation=1.1:contrast=1.04:eval=frame,format=gbrp[g0r]")
    fc.append(f"[{ix['dust']}:v]format=gbrp[dr];[g0r][dr]blend=all_mode=screen:all_opacity=0.9,format=rgba[c0]")
    cur = "c0"
    e0 = T[-1] + OV * 0.5

    def put(nm, a, b2, ypos, amp=0.4, k=9, extra=""):
        nonlocal cur
        fo = f",fade=t=out:st={b2 - 0.12:.3f}:d=0.12:alpha=1"
        fc.append(f"[{ix[nm]}:v]format=rgba,fade=t=in:st={a:.3f}:d=0.14:alpha=1{fo},scale=w='iw*(1+{amp}*exp(-{k}*max(0,t-{a:.3f})){extra})':h=-1:eval=frame[p_{nm}]")
        fc.append(f"[{cur}][p_{nm}]overlay=x=(W-w)/2:y='{ypos}-h/2+8*sin(3*t)':eof_action=pass:enable='between(t,{a:.3f},{b2:.3f})'[o_{nm}]")
        cur = f"o_{nm}"

    for i in range(len(SEGS)):
        a = (T[i] + OV * 0.55) if i else 0.05
        b2 = (T[i + 1] + OV * 0.4) if i + 1 < len(T) else 999
        put(f"n{i}", a, b2, "190", amp=0.45)
    fc.append(f"[{ix['pill']}:v]format=rgba,fade=t=in:st=1.4:d=0.3:alpha=1,fade=t=out:st={e0 - 0.2:.3f}:d=0.2:alpha=1,scale=w='iw*(1+0.035*sin(5*t))':h=-1:eval=frame[pp]")
    fc.append(f"[{cur}][pp]overlay=x=(W-w)/2:y='372-h/2':eof_action=pass:enable='between(t,1.4,{e0:.3f})'[pl]")
    cur = "pl"
    put("title", e0 + 0.10, 999, "H*0.33", amp=0.35)
    put("feat", e0 + 0.9, 999, "H*0.50", amp=0.15)
    put("link", e0 + 1.4, 999, "H*0.62", amp=0.3, extra="+0.03*sin(6*t)")
    fc.append(f"[{ix['wm']}:v]format=rgba,colorchannelmixer=aa=0.6[wmk]")
    cx = "if(lt(mod(t,16),4),40,if(lt(mod(t,16),8),W-w-40,if(lt(mod(t,16),12),40,W-w-40)))"
    cy = "if(lt(mod(t,16),4),620,if(lt(mod(t,16),8),1000,if(lt(mod(t,16),12),1130,720)))"
    fc.append(f"[{cur}][wmk]overlay=x='{cx}':y='{cy}':eof_action=pass:enable='lt(t,{e0:.3f})',format=yuv420p[vout]")
    fc.append(f"[{ix['sfx']}:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=2.0,alimiter=limit=0.9,afade=t=out:st={TOTAL - 0.5:.2f}:d=0.5[aout]")
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
