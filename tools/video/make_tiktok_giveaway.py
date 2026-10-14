"""Adapte la vidéo giveaway (carrée, pensée pour X) en TikTok vertical 1080x1920.

Usage : make_tiktok_giveaway.py <giveaway.mp4> <out.mp4>

- fond = la vidéo elle-même, floutée ; la vidéo carrée reste nette au centre-haut (zone sûre TikTok)
- accroche qui change à chaque scène + bandeau « watch till the end » + barre de progression (rétention)
- la fin « Retweet / link in the replies » (spécifique à X) est remplacée par une carte TikTok :
  Like. Comment. Follow. / @Haatmis / 4 DAYS ONLY / LINK IN BIO
"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

src, out = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
SQ_Y = 330            # position du carré (le bas de l'écran est mangé par l'interface TikTok)
CUT = 16.4            # début de la scène « To enter » d'origine, remplacée
TOTAL = 20.2
TMP = os.path.join(os.path.dirname(os.path.abspath(out)), "_tmp_giveaway")
os.makedirs(TMP, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
LAV, GREEN, DARK = (167, 139, 250), (74, 222, 128), (14, 10, 42)


def run(c):
    subprocess.run(c, check=True)


def text_png(lines, path, size, fill=((255, 255, 255), (196, 181, 253)), stroke=10, maxw=940, gap=1.05):
    meas = ImageDraw.Draw(Image.new("L", (10, 10)))
    while max(meas.textlength(l, font=ImageFont.truetype(FONT, size)) for l in lines) > maxw and size > 40:
        size -= 4
    f = ImageFont.truetype(FONT, size)
    lh = int(size * gap)
    w = int(max(meas.textlength(l, font=f) for l in lines)) + 2 * (stroke + 50)
    h = lh * len(lines) + 2 * (stroke + 50)
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i, l in enumerate(lines):
        d.text((w // 2, 50 + stroke + i * lh + lh // 2), l, font=f, fill=255, anchor="mm")
    grad = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        grad[:, :, c] = np.linspace(fill[0][c], fill[1][c], h)[:, None]
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow = Image.new("RGBA", (w, h), LAV + (0,))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, int(v * 0.9))))
    base.alpha_composite(glow)
    st = Image.new("RGBA", (w, h), DARK + (0,))
    st.putalpha(mask.filter(ImageFilter.MaxFilter(stroke * 2 + 1)))
    base.alpha_composite(st)
    txt = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
    txt.putalpha(mask)
    base.alpha_composite(txt)
    base.save(path)


def pill_png(label, path, size=46, bg=(88, 60, 200), fg=(255, 255, 255)):
    f = ImageFont.truetype(FONT, size)
    meas = ImageDraw.Draw(Image.new("L", (10, 10)))
    tw = int(meas.textlength(label, font=f))
    w, h = tw + 110, int(size * 2.0)
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    g = Image.new("RGBA", im.size, LAV + (0,))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((30, 30, 30 + w, 30 + h), h // 2, fill=170)
    g.putalpha(m.filter(ImageFilter.GaussianBlur(16)))
    im.alpha_composite(g)
    ImageDraw.Draw(im).rounded_rectangle((30, 30, 30 + w, 30 + h), h // 2, fill=bg + (255,), outline=LAV + (255,), width=3)
    ImageDraw.Draw(im).text((30 + w // 2, 30 + h // 2 + 2), label, font=f, fill=fg, anchor="mm")
    im.save(path)


def end_bg(path):
    y, x = np.mgrid[:H, :W].astype(np.float32)
    top = np.array([26, 18, 78], np.float32)
    bot = np.array([10, 7, 34], np.float32)
    t = (y / H)[:, :, None]
    img = top * (1 - t) + bot * t
    glow = np.exp(-(((x - W * 0.5) / 520) ** 2 + ((y - H * 0.55) / 620) ** 2))[:, :, None]
    img += glow * np.array([70, 46, 140], np.float32)
    rng = np.random.default_rng(3)
    img += rng.normal(0, 1.2, (H, W, 1))
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    L, m = 70, 60   # repères d'angle comme la vidéo d'origine
    for (cx, cy, sx, sy) in ((m, m + 40, 1, 1), (W - m, m + 40, -1, 1), (m, H - m - 40, 1, -1), (W - m, H - m - 40, -1, -1)):
        d.line((cx, cy, cx + sx * L, cy), fill=(120, 105, 200, 255), width=4)
        d.line((cx, cy, cx, cy + sy * L), fill=(120, 105, 200, 255), width=4)
    im.save(path)


def mono_png(label, path, size=40, col=(120, 225, 255), hint=None):
    f = ImageFont.truetype(MONO, size)
    meas = ImageDraw.Draw(Image.new("L", (10, 10)))
    w = int(meas.textlength(label, font=f)) + 40
    im = Image.new("RGBA", (w, size * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, size), label, font=f, fill=col + (255,), anchor="lm")
    im.save(path)


def tag_png(label, path, size=44):
    f = ImageFont.truetype(MONO, size)
    meas = ImageDraw.Draw(Image.new("L", (10, 10)))
    w = int(meas.textlength(label, font=f)) + 60
    im = Image.new("RGBA", (w, int(size * 1.9)), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((0, 0, w - 1, im.height - 1), fill=GREEN + (255,))
    ImageDraw.Draw(im).text((w // 2, im.height // 2), label, font=f, fill=(8, 38, 24), anchor="mm")
    im.save(path)


# ------------------------------------------------------------------ éléments
HOOKS = [  # (début, fin, lignes)
    (0.0, 3.0, ["FREE ROBLOX", "GIVEAWAY"]),
    (3.0, 10.0, ["WIN 2 LOW POLY", "ROBLOX PACKS"]),
    (10.0, CUT, ["3 WINNERS +", "5 FREE MODELS"]),
]
for i, (_, _, ls) in enumerate(HOOKS):
    text_png(ls, f"{TMP}/hook{i}.png", 104)
pill_png("WATCH TILL THE END TO ENTER", f"{TMP}/watch.png", 40)
pill_png("FOLLOW @HAATMIS", f"{TMP}/follow.png", 46, bg=(124, 58, 237))
end_bg(f"{TMP}/end_bg.png")
mono_png("// TO ENTER", f"{TMP}/e_label.png", 40)
text_png(["LIKE."], f"{TMP}/e_like.png", 190, stroke=12)
text_png(["COMMENT."], f"{TMP}/e_com.png", 190, stroke=12)
text_png(["FOLLOW."], f"{TMP}/e_fol.png", 190, stroke=12)
mono_png("@Haatmis", f"{TMP}/e_user.png", 64, col=(196, 181, 253))
tag_png("[ 4 DAYS ONLY ]", f"{TMP}/e_days.png", 42)
pill_png("LINK IN BIO", f"{TMP}/e_link.png", 64, bg=(124, 58, 237))
Image.new("RGBA", (W, 12), LAV + (255,)).save(f"{TMP}/bar.png")
Image.new("RGBA", (W, 12), (255, 255, 255, 50)).save(f"{TMP}/track.png")

# ------------------------------------------------------------------ montage
names = ["vid", "endbg", "label", "like", "com", "fol", "user", "days", "link", "watch", "follow", "bar", "track"] + [f"hook{i}" for i in range(len(HOOKS))]
paths = [src, f"{TMP}/end_bg.png", f"{TMP}/e_label.png", f"{TMP}/e_like.png", f"{TMP}/e_com.png", f"{TMP}/e_fol.png", f"{TMP}/e_user.png", f"{TMP}/e_days.png", f"{TMP}/e_link.png",
         f"{TMP}/watch.png", f"{TMP}/follow.png", f"{TMP}/bar.png", f"{TMP}/track.png"] + [f"{TMP}/hook{i}.png" for i in range(len(HOOKS))]
inp = []
for p in paths:
    if p.endswith(".png"):
        inp += ["-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL + 1:.2f}", "-i", p]
    else:
        inp += ["-i", p]
ix = {n: i for i, n in enumerate(names)}
fc = []
fc.append(f"[0:v]trim=0:{CUT + 0.6},setpts=PTS-STARTPTS,fps={FPS},split=2[a][b]")
fc.append(f"[a]scale=-2:{H},crop={W}:{H},gblur=sigma=34,eq=brightness=-0.12:saturation=1.1,fade=t=out:st={CUT - 0.1}:d=0.4,tpad=stop_mode=clone:stop_duration=6[bg]")
fc.append(f"[b]format=yuv420p,tpad=stop_mode=clone:stop_duration=6[sq]")
fc.append(f"[bg][sq]overlay=0:{SQ_Y}:eof_action=pass,format=yuv420p[v0]")
# barre de progression
bar_y = SQ_Y + 1080 + 28
fc.append(f"[v0][{ix['track']}:v]overlay=0:{bar_y}:eof_action=pass[v1]")
fc.append(f"[v1][{ix['bar']}:v]overlay=x='-{W}+{W}*min(1,t/{CUT})':y={bar_y}:eof_action=pass:enable='lt(t,{CUT})'[v2]")
cur = "v2"
# accroches (pop + flottement)
for i, (a, b, _) in enumerate(HOOKS):
    fc.append(f"[{ix[f'hook{i}']}:v]format=rgba,fade=t=in:st={a:.2f}:d=0.15:alpha=1,fade=t=out:st={b - 0.15:.2f}:d=0.15:alpha=1,"
              f"scale=w='iw*(1+0.35*exp(-10*max(0,t-{a:.2f})))':h=-1:eval=frame[hk{i}]")
    fc.append(f"[{cur}][hk{i}]overlay=x=(W-w)/2:y='{SQ_Y / 2 + 10}-h/2+8*sin(3*t)':eof_action=pass:enable='between(t,{a:.2f},{b:.2f})'[h{i}]")
    cur = f"h{i}"
# bandeaux du bas
fc.append(f"[{ix['watch']}:v]format=rgba,scale=w='iw*(1+0.04*sin(5*t))':h=-1:eval=frame[wp]")
fc.append(f"[{cur}][wp]overlay=x=(W-w)/2:y='{bar_y + 70}-h/2':eof_action=pass:enable='between(t,0.5,{CUT - 0.3})'[w1]")
# carte de fin
fc.append(f"[{ix['endbg']}:v]format=rgba,fade=t=in:st={CUT - 0.1}:d=0.3:alpha=1[eb]")
fc.append(f"[w1][eb]overlay=0:0:eof_action=pass:enable='gte(t,{CUT - 0.1})'[c0]")
cur = "c0"
items = [("label", 0.25, 0.40, "H*0.30"), ("like", 0.45, 0.45, "H*0.385"), ("com", 0.95, 0.45, "H*0.48"), ("fol", 1.45, 0.45, "H*0.575"),
         ("user", 2.0, 0.35, "H*0.66"), ("days", 2.3, 0.3, "H*0.72"), ("link", 2.6, 0.3, "H*0.79")]
for nm, dl, d, ypos in items:
    st = CUT + dl
    pop = 0.25 if nm in ("like", "com", "fol", "link") else 0.08
    extra = "+0.03*sin(6*t)" if nm == "link" else ""
    fc.append(f"[{ix[nm]}:v]format=rgba,fade=t=in:st={st:.2f}:d=0.18:alpha=1,scale=w='iw*(1+{pop}*exp(-9*max(0,t-{st:.2f})){extra})':h=-1:eval=frame[p_{nm}]")
    fc.append(f"[{cur}][p_{nm}]overlay=x=(W-w)/2:y='{ypos}-h/2':eof_action=pass:enable='gte(t,{st:.2f})'[o_{nm}]")
    cur = f"o_{nm}"
# flashs de coupe entre scènes (légers) pour le rythme
cuts = [3.0, 6.0, 10.0, 13.3, CUT]
pulse = "+".join(f"0.18*exp(-14*abs(t-{c}))" for c in cuts)
fc.append(f"[{cur}]eq=brightness='{pulse}':eval=frame,format=yuv420p[vout]")
fc.append(f"[0:a]apad=pad_dur=2,atrim=0:{TOTAL},afade=t=out:st={TOTAL - 0.8}:d=0.8[aout]")
run(["ffmpeg", "-y", "-loglevel", "error"] + inp + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{TOTAL}", "-c:v", "libx264", "-crf", "18",
                                                     "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
print("OK", out, os.path.getsize(out) // 1000, "ko")
