"""
Montage TikTok vertical (1080x1920, 30 i/s) pour vendre le « ICE VFX pack » à partir de 3 vidéos de démonstration.

    python tools/video/make_tiktok.py <ult.mp4> <clip2.mp4> <clip3.mp4> <logo.png> <sortie.mp4>

Étapes : 7 plans (fond flou + plan recadré en carré avec zoom lent), textes animés, flashs sur les coupes, musique synthétique (kick / clap / basse / riser),
logo en filigrane (grand, très léger, au centre + petit qui change de coin toutes les 4 s), carte de fin « GET THE ICE VFX PACK — LINK IN BIO ».
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
src = sys.argv[1:4]
logo_path, out = sys.argv[4], sys.argv[5]
TMP = os.path.join(os.path.dirname(os.path.abspath(out)), "_tmp_tiktok")
os.makedirs(TMP, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_B = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"

# (index source, début, durée, texte, couleur)
SEGS = [
    (0, 0.9, 1.9, ["THIS ICE VFX"], "ice"),
    (2, 1.1, 2.1, ["IS INSANE"], "white"),
    (1, 1.0, 2.5, ["FREEZE", "EVERYTHING"], "ice"),
    (2, 10.0, 2.3, ["SHATTER", "IT ALL"], "white"),
    (0, 11.8, 2.6, ["HUGE ICE", "IMPACTS"], "ice"),
    (1, 15.8, 2.6, ["ICE SHARDS", "EVERYWHERE"], "white"),
    (2, 17.9, 2.4, ["FULL ICE", "VFX PACK"], "ice"),
]
END = 4.6
T = [0.0]
for s in SEGS:
    T.append(T[-1] + s[2])
TOTAL = T[-1] + END
print("durée totale", TOTAL)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:300]); print(r.stderr[-1500:]); raise SystemExit(1)


# ------------------------------------------------------------ plans : fond flou + carré zoomé
seg_files = []
for i, (si, st, du, _, _) in enumerate(SEGS):
    f = os.path.join(TMP, f"seg{i}.mp4")
    zoom = 0.10
    fc = (
        f"[0:v]trim=start={st}:duration={du},setpts=PTS-STARTPTS,fps={FPS},split=2[a][b];"
        f"[a]scale=-2:{H},crop={W}:{H},gblur=sigma=22,eq=brightness=-0.18:saturation=1.25[bg];"
        f"[b]crop=720:720:280:0,scale={W}:{W},scale=w='{W}*(1+{zoom}*t/{du})':h='{W}*(1+{zoom}*t/{du})':eval=frame,crop={W}:{W}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2-60,format=yuv420p[v];"
        f"[0:a]atrim=start={st}:duration={du},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={du-0.04}:d=0.04,volume=0.55[a]"
    )
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src[si], "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-c:a", "pcm_s16le", "-ar", "44100", f])
    seg_files.append(f)

# ------------------------------------------------------------ carte de fin (fond dégradé violet + clip flou assombri)
f = os.path.join(TMP, "end_bg.mp4")
fc = (f"[0:v]trim=start=24.2:duration={END},setpts=PTS-STARTPTS,fps={FPS},scale=-2:{H},crop={W}:{H},gblur=sigma=26,eq=brightness=-0.38:saturation=0.8,"
      f"colorchannelmixer=rr=0.7:gg=0.55:bb=1.0,format=yuv420p[v];[0:a]atrim=start=24.2:duration={END},asetpts=PTS-STARTPTS,volume=0.35,afade=t=out:st={END-0.6}:d=0.6[a]")
run(["ffmpeg", "-y", "-loglevel", "error", "-i", src[0], "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-c:a", "pcm_s16le", "-ar", "44100", f])
seg_files.append(f)

# ------------------------------------------------------------ logo : alpha dérivé de la luminosité (le fond sombre disparaît)
lg = Image.open(logo_path).convert("RGB")
arr = np.asarray(lg).astype(np.float32)
lum = arr.max(axis=2)
alpha = np.clip((lum - 120) / 110.0, 0, 1)
rgba = np.dstack([arr, alpha * 255]).astype(np.uint8)
logo = Image.fromarray(rgba, "RGBA")
logo_big = logo.resize((760, 760), Image.LANCZOS)
logo_sm = logo.resize((190, 190), Image.LANCZOS)
logo_big.save(os.path.join(TMP, "logo_big.png"))
logo_sm.save(os.path.join(TMP, "logo_small.png"))
glow = logo.resize((520, 520), Image.LANCZOS)
g2 = glow.filter(ImageFilter.GaussianBlur(26))
endlogo = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
endlogo.alpha_composite(g2, (90, 90))
endlogo.alpha_composite(glow, (90, 90))
endlogo.save(os.path.join(TMP, "logo_end.png"))


# ------------------------------------------------------------ textes (PNG avec contour + lueur)
def text_png(lines, path, size, color="white", extra_glow=True, stroke=14):
    meas = ImageDraw.Draw(Image.new("L", (1, 1)))
    while max(meas.textlength(l, font=ImageFont.truetype(FONT, size)) for l in lines) > 900 and size > 60:
        size -= 4
    fnt = ImageFont.truetype(FONT, size)
    lh = int(size * 1.08)
    wmax = max(int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(l, font=fnt)) for l in lines)
    img = Image.new("RGBA", (wmax + 120, lh * len(lines) + 90), (0, 0, 0, 0))
    col = {"white": (255, 255, 255), "ice": (180, 228, 255), "gold": (255, 226, 120), "violet": (200, 160, 255)}[color]
    gl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(gl)
    for k, l in enumerate(lines):
        tw = d.textlength(l, font=fnt)
        d.text(((img.width - tw) / 2, 30 + k * lh), l, font=fnt, fill=(90, 190, 255, 255), stroke_width=stroke + 6, stroke_fill=(90, 190, 255, 255))
    gl = gl.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(gl)
    d = ImageDraw.Draw(img)
    for k, l in enumerate(lines):
        tw = d.textlength(l, font=fnt)
        d.text(((img.width - tw) / 2 + 5, 30 + k * lh + 8), l, font=fnt, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        d.text(((img.width - tw) / 2, 30 + k * lh), l, font=fnt, fill=col + (255,), stroke_width=stroke, stroke_fill=(10, 20, 60, 255))
    img.save(path)
    return img.size


texts = []
for i, (_, _, _, lines, col) in enumerate(SEGS):
    size = 150 if len(lines) == 2 else 165
    p = os.path.join(TMP, f"txt{i}.png")
    text_png(lines, p, size, col)
    texts.append(p)
end_get = os.path.join(TMP, "end_get.png"); text_png(["GET THE"], end_get, 120, "white")
end_main = os.path.join(TMP, "end_main.png"); text_png(["ICE VFX", "PACK"], end_main, 215, "ice", stroke=18)
end_bio = os.path.join(TMP, "end_bio.png")
pill = Image.new("RGBA", (900, 200), (0, 0, 0, 0))
d = ImageDraw.Draw(pill)
d.rounded_rectangle((0, 0, 899, 199), 100, fill=(124, 77, 255, 255), outline=(220, 200, 255, 255), width=6)
fb = ImageFont.truetype(FONT, 100)
t = "LINK IN BIO"
d.text(((900 - d.textlength(t, font=fb)) / 2, 38), t, font=fb, fill=(255, 255, 255, 255))
pill.save(end_bio)
hook_tag = os.path.join(TMP, "tag.png")
tg = Image.new("RGBA", (860, 110), (0, 0, 0, 0))
d = ImageDraw.Draw(tg)
d.rounded_rectangle((0, 0, 859, 109), 55, fill=(10, 14, 40, 190), outline=(150, 210, 255, 255), width=4)
f2 = ImageFont.truetype(FONT_B, 46)
t = "ICE VFX PACK  •  FOR ROBLOX"
d.text(((860 - d.textlength(t, font=f2)) / 2, 30), t, font=f2, fill=(200, 235, 255, 255))
tg.save(hook_tag)

# ------------------------------------------------------------ musique synthétique (120 BPM)
SR = 44100
n = int(SR * (TOTAL + 0.5))
mus = np.zeros(n, dtype=np.float32)
rng = np.random.default_rng(3)


def add(buf, start, sig, gain=1.0):
    s = int(start * SR)
    e = min(len(buf), s + len(sig))
    if s < len(buf):
        buf[s:e] += sig[: e - s] * gain


def kick():
    t = np.arange(int(0.28 * SR)) / SR
    f = 120 * np.exp(-t * 22) + 42
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def clap():
    t = np.arange(int(0.2 * SR)) / SR
    return (rng.standard_normal(len(t)) * np.exp(-t * 28)).astype(np.float32) * 0.6


def hat():
    t = np.arange(int(0.05 * SR)) / SR
    x = rng.standard_normal(len(t)) * np.exp(-t * 90)
    return np.diff(x, prepend=0).astype(np.float32) * 0.5


def bass(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    saw = 2 * ((t * freq) % 1.0) - 1
    return (np.tanh(saw * 2.2) * 0.45 * np.exp(-t * 3.2)).astype(np.float32)


def riser(dur):
    t = np.arange(int(dur * SR)) / SR
    x = rng.standard_normal(len(t))
    k = np.exp(-(1 - t / dur) * 3.0)
    # filtre passe-haut croissant approximé par différences successives
    y = np.cumsum(x) * 0.0 + x
    for _ in range(int(2 + 4 * 0)):
        y = np.diff(y, prepend=0)
    return (y * (t / dur) ** 2.2 * 0.35).astype(np.float32)


def boom():
    t = np.arange(int(1.4 * SR)) / SR
    return (np.sin(2 * np.pi * (60 * np.exp(-t * 2.5) + 28) * t) * np.exp(-t * 2.8) * 1.1).astype(np.float32)


def whoosh(dur=0.5):
    t = np.arange(int(dur * SR)) / SR
    x = rng.standard_normal(len(t))
    y = np.convolve(x, np.ones(24) / 24, mode="same")
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (y * env * 0.9).astype(np.float32)


beat = 0.5
notes = [55.0, 55.0, 65.41, 49.0]     # La, La, Do, Sol (graves)
t0 = 0.0
b = 0
while t0 < TOTAL - 0.2:
    sect_end = T[-1]
    if t0 >= sect_end:          # carte de fin : kick plus léger
        g = 0.55
    else:
        g = 1.0
    add(mus, t0, kick(), 0.9 * g)
    if b % 2 == 1:
        add(mus, t0, clap(), 0.7 * g)
    add(mus, t0 + beat / 2, hat(), 0.5 * g)
    add(mus, t0 + beat / 4, hat(), 0.25 * g)
    add(mus, t0 + beat * 0.75, hat(), 0.25 * g)
    add(mus, t0, bass(notes[(b // 2) % 4], beat * 2), 0.8 * g)
    t0 += beat
    b += 1
add(mus, T[-1] - 1.6, riser(1.6), 1.0)
add(mus, T[-1], boom(), 1.0)
for c in T[1:-1]:
    add(mus, c - 0.18, whoosh(), 0.8)
add(mus, 0.0, boom(), 0.55)
mus = mus / (np.max(np.abs(mus)) + 1e-6) * 0.85
wav = os.path.join(TMP, "music.wav")
with wave.open(wav, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mus * 32767).astype(np.int16).tobytes())

# ------------------------------------------------------------ assemblage final
inputs = []
for f in seg_files:
    inputs += ["-i", f]
k0 = len(seg_files)
extra = [wav, os.path.join(TMP, "logo_big.png"), os.path.join(TMP, "logo_small.png"), os.path.join(TMP, "logo_end.png"), end_get, end_main, end_bio, hook_tag] + texts
for p in extra:
    inputs += ["-i", p]
idx = {name: k0 + i for i, name in enumerate(["wav", "lbig", "lsm", "lend", "get", "main", "bio", "tag"] + [f"t{i}" for i in range(len(texts))])}

fc = []
v = "".join(f"[{i}:v][{i}:a]" for i in range(len(seg_files)))
fc.append(f"{v}concat=n={len(seg_files)}:v=1:a=1[vc][ac]")
cur = "vc"
# flashs blancs de 4 images à chaque coupe
for ci, c in enumerate(T[1:-1] + [T[-1]]):
    fc.append(f"[{cur}]drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:enable='between(t,{c:.3f},{c + 0.10:.3f})'[f{ci}]")
    cur = f"f{ci}"
# vignette + tremblement léger : non (coût) ; textes
for i in range(len(SEGS)):
    a, b2 = T[i], T[i + 1]
    ty = f"(H*0.17)-60*max(0,1-(t-{a:.3f})/0.18)"
    fc.append(f"[{cur}][{idx[f't{i}']}:v]overlay=x=(W-w)/2:y='{ty}':enable='between(t,{a + 0.04:.3f},{b2 - 0.05:.3f})':format=auto[tx{i}]")
    cur = f"tx{i}"
# étiquette de produit au début
fc.append(f"[{cur}][{idx['tag']}:v]overlay=x=(W-w)/2:y=H*0.86:enable='between(t,0.4,{T[-1] - 0.3:.3f})'[tg]")
cur = "tg"
# carte de fin
e0 = T[-1]
fc.append(f"[{cur}][{idx['lend']}:v]overlay=x=(W-w)/2:y='H*0.06-70*max(0,1-(t-{e0:.3f})/0.35)':enable='gte(t,{e0 + 0.05:.3f})'[e1]")
fc.append(f"[e1][{idx['get']}:v]overlay=x=(W-w)/2:y=H*0.34:enable='gte(t,{e0 + 0.35:.3f})'[e2]")
fc.append(f"[e2][{idx['main']}:v]overlay=x=(W-w)/2:y='H*0.385+50*max(0,1-(t-{e0 + 0.55:.3f})/0.25)':enable='gte(t,{e0 + 0.55:.3f})'[e3]")
fc.append(f"[e3][{idx['bio']}:v]overlay=x=(W-w)/2:y=H*0.72:enable='gte(t,{e0 + 1.3:.3f})'[e4]")
cur = "e4"
# filigrane : grand très léger + petit qui change de coin
fc.append(f"[{idx['lbig']}:v]format=rgba,colorchannelmixer=aa=0.13[wm1]")
fc.append(f"[{cur}][wm1]overlay=x=(W-w)/2:y=(H-h)/2[w1]")
fc.append(f"[{idx['lsm']}:v]format=rgba,colorchannelmixer=aa=0.7[wm2]")
cx = "if(lt(mod(t,16),4),40,if(lt(mod(t,16),8),W-w-40,if(lt(mod(t,16),12),40,W-w-40)))"
cy = "if(lt(mod(t,16),4),170,if(lt(mod(t,16),8),170,if(lt(mod(t,16),12),H-h-330,H-h-330)))"
fc.append(f"[w1][wm2]overlay=x='{cx}':y='{cy}'[vout]")
fc.append(f"[{idx['wav']}:a]volume=0.75[m];[ac][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,afade=t=out:st={TOTAL - 0.5:.2f}:d=0.5[aout]")
cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", f"{TOTAL:.2f}",
                                                        "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
run(cmd)
print("OK", out, os.path.getsize(out) // 1000, "ko")
