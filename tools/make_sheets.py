"""Planches contact par catégorie : python tools/make_sheets.py <dossier_thumbs> <dossier_sortie> [colonnes]"""
import glob, os, sys
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
os.makedirs(out, exist_ok=True)
cats = {}
for f in sorted(glob.glob(src + "/*.png")):
    cat, name = os.path.basename(f)[:-4].split("__")
    cats.setdefault(cat, []).append((name, f))
T = 300
for cat, items in cats.items():
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * T, rows * (T + 22)), (245, 245, 243))
    d = ImageDraw.Draw(sheet)
    for i, (name, f) in enumerate(items):
        im = Image.open(f).convert("RGB").resize((T, T))
        x, y = (i % cols) * T, (i // cols) * (T + 22)
        sheet.paste(im, (x, y))
        d.text((x + 6, y + T + 4), name, fill=(40, 40, 40))
    sheet.save(f"{out}/{cat}.png")
    print(cat, len(items))
