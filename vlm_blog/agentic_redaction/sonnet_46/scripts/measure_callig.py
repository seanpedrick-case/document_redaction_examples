"""Measure exact position of calligraphic Sister City Agreement title."""
import fitz
from pathlib import Path
from PIL import Image, ImageDraw

# Use final redacted PDF to see the actual black box position
pdfs = sorted(Path("output_final").glob("*_redacted.pdf"), key=lambda f: f.stat().st_mtime, reverse=True)
final_pdf = fitz.open(str(pdfs[0]))
print(f"Using: {pdfs[0].name}")

page = final_pdf[5]  # page 6 (0-indexed)
pix = page.get_pixmap(dpi=180)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
print(f"Page size: {pix.width}x{pix.height}")

# Draw fine grid lines every 5% 
draw = ImageDraw.Draw(img)
for pct in range(0, 100, 5):
    y = int(pct / 100 * pix.height)
    draw.line([(0, y), (50, y)], fill="red", width=1)
    draw.text((2, y), f"{pct}%", fill="red")

# Downscale
max_w = 1280
scale = max_w / pix.width
new_size = (max_w, int(pix.height * scale))
img = img.resize(new_size, Image.LANCZOS)
img.save("output/page6_final_grid.png")
print("Saved output/page6_final_grid.png")
