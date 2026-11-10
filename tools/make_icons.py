"""Genera los íconos de EC-Cam (PWA + Windows). Uso: python tools/make_icons.py"""
from pathlib import Path
from PIL import Image, ImageDraw
OUT = Path(__file__).resolve().parent.parent / "src" / "web" / "img"
BG, ORANGE, RING, LENS = (18, 22, 20), (240, 124, 30), (44, 52, 48), (10, 12, 11)
def icon(size, maskable=False):
    s = 4 * size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if maskable:
        d.rectangle([0, 0, s, s], fill=BG); k = 0.62
    else:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=BG); k = 0.84
    c = s / 2; r = s * k / 2
    # cuerpo de la cámara (círculo naranja) + aro + lente + brillo
    d.ellipse([c - r, c - r, c + r, c + r], fill=ORANGE)
    r2 = r * 0.70; d.ellipse([c - r2, c - r2, c + r2, c + r2], fill=RING)
    r3 = r * 0.50; d.ellipse([c - r3, c - r3, c + r3, c + r3], fill=LENS)
    r4 = r * 0.16; ox, oy = c - r * 0.18, c - r * 0.18
    d.ellipse([ox - r4, oy - r4, ox + r4, oy + r4], fill=(255, 255, 255, 230))
    # punto de grabación
    r5 = r * 0.09; px, py = c + r * 0.58, c - r * 0.58
    d.ellipse([px - r5, py - r5, px + r5, py + r5], fill=(255, 255, 255))
    return im.resize((size, size), Image.LANCZOS)
OUT.mkdir(parents=True, exist_ok=True)
for n in (192, 512):
    icon(n).save(OUT / f"pwa-{n}.png"); icon(n, True).save(OUT / f"pwa-maskable-{n}.png")
icon(64).save(OUT / "favicon.png")
icon(256).save(OUT / "eccam.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("Íconos en", OUT)
