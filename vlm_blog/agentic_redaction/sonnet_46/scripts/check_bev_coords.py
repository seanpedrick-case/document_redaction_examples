"""Measure exact position of Beverly D'Neill signature on page 6 of original PDF."""
import fitz
from pathlib import Path
from PIL import Image, ImageDraw

orig_pdf = fitz.open("Partnership-Agreement-Toolkit_0_0.pdf")
page = orig_pdf[5]  # page index 5 = page 6 (0-based)

# Render at high resolution for accurate measurement
pix = page.get_pixmap(dpi=180)
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

print(f"Page 6 dimensions: {pix.width}x{pix.height} pixels at 180dpi")

# Draw grid lines at key y positions
draw = ImageDraw.Draw(img)

# Mark the positions based on current boxes
boxes = [
    ("Beverly sig (current)", 0.380, 0.605, 0.705, 0.645, "red"),
    ("Jorge sig (current)", 0.390, 0.775, 0.720, 0.820, "blue"),
    ("Jorge name", 0.561569, 0.825455, 0.70902, 0.839091, "green"),
]

for name, xmin, ymin, xmax, ymax, color in boxes:
    x0 = xmin * pix.width
    y0 = ymin * pix.height
    x1 = xmax * pix.width
    y1 = ymax * pix.height
    draw.rectangle([x0, y0, x1, y1], outline=color, width=4)
    draw.text((x0, max(0, y0-15)), name, fill=color)

# Also draw reference lines at 10% intervals
for pct in range(0, 100, 10):
    y = int(pct / 100 * pix.height)
    draw.line([(0, y), (30, y)], fill="gray", width=2)
    draw.text((2, y), f"{pct}%", fill="gray")

# Downscale for display
max_w = 1280
if img.width > max_w:
    scale = max_w / img.width
    new_size = (max_w, int(img.height * scale))
    img = img.resize(new_size, Image.LANCZOS)

img.save("output/page6_coords_check.png")
print(f"Saved to output/page6_coords_check.png")
