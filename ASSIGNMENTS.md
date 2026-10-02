# Learn block art by building it

Nine small assignments, each building on the one before. By the end you'll have rebuilt the core of `blockart.py` yourself.

**How to use this:** read the task, try it for 15–30 minutes, and only then open the answer. Each answer is the simplest version that works, not the cleverest.

**Setup:** `pip install pillow numpy`, then work in this folder. Put any photo here as `photo.jpg`; the logo is at `../../kuku logo.png`. Windows' console needs one line to print block characters, so every printing answer starts with `sys.stdout.reconfigure(encoding="utf-8")`.

---

## 1. Your first ASCII picture: a brightness ramp

**Task:** Load `photo.jpg`, turn it grey, shrink it to 80 columns, and print it using the characters `" .:-=+*#%@"`, where space means black and `@` means white.

**Concepts:** grayscale, image resizing, mapping a range (0–255) onto a list index.

**Read:**
- [Pillow `Image` reference](https://pillow.readthedocs.io/en/stable/reference/Image.html): `open`, `convert("L")`, `resize`, `getpixel`.
- [Paul Bourke: Character representation of greyscale images](https://paulbourke.net/dataformats/asciiart/): the classic character ramps.

<details><summary>Answer</summary>

```python
import sys
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
RAMP = " .:-=+*#%@"

img = Image.open("photo.jpg").convert("L")      # "L" = one brightness value per pixel, 0..255
cols = 80
rows = int(img.height * cols / img.width)
small = img.resize((cols, rows))

for y in range(rows):
    line = ""
    for x in range(cols):
        brightness = small.getpixel((x, y))
        line += RAMP[brightness * (len(RAMP) - 1) // 255]
    print(line)
```

`brightness * 9 // 255` turns 0..255 into an index 0..9. On a dark terminal, bright pixels become `@`, which has the most ink.

</details>

---

## 2. Fix the stretch: character aspect ratio

**Task:** Your picture from assignment 1 looks too tall. Work out why, and fix it with one change to how `rows` is calculated.

**Concepts:** a character cell is not square. In most monospace fonts it's roughly 0.5–0.6 times as wide as it is tall, so treating each character as a square pixel stretches the image vertically.

**Bonus:** measure your font's real ratio in the browser. Make a `<span>` holding 100 `█` characters in your font at `font-size: 100px`, and read its width in DevTools: `ratio = width / 100 / 100`. Cascadia Code gives 0.576.

<details><summary>Answer</summary>

Each character covers `cell_w` image pixels across and `cell_h = cell_w / aspect` pixels down, so:

```python
ASPECT = 0.576                                   # Cascadia Code; about 0.5 for most terminals
rows = round(img.height * cols * ASPECT / img.width)
```

Everything else stays the same. The picture now has the right proportions.

</details>

---

## 3. Swap letters for blocks, and show it in a browser

**Task:** Replace the ramp with the five block shades `" ░▒▓█"`, and write the result into `a3.html` inside a `<pre>`, light grey on black. Open it in a browser. Then change `line-height` to `1.3` and see what happens.

**Concepts:** Unicode block elements fill a fixed share of the character cell (0%, 25%, 50%, 75%, 100%), so neighbouring cells merge into solid areas. `line-height: 1` makes rows touch. Resizing with `Image.BOX` averages every pixel a cell covers instead of picking one.

**Read:**
- [Wikipedia: Block Elements](https://en.wikipedia.org/wiki/Block_Elements) and the [Unicode chart (PDF)](https://www.unicode.org/charts/PDF/U2580.pdf).
- [MDN: `line-height`](https://developer.mozilla.org/en-US/docs/Web/CSS/line-height).

<details><summary>Answer</summary>

```python
from PIL import Image

SHADES = " ░▒▓█"
ASPECT = 0.576

img = Image.open("photo.jpg").convert("L")
cols = 100
rows = round(img.height * cols * ASPECT / img.width)
small = img.resize((cols, rows), Image.BOX)

lines = []
for y in range(rows):
    lines.append("".join(SHADES[small.getpixel((x, y)) * 4 // 255] for x in range(cols)))

art = "\n".join(lines)
html = f"""<!DOCTYPE html><meta charset="utf-8">
<body style="background:#0C0C0C; color:#CCCCCC">
<pre style="font: 6px/1 Consolas, monospace; letter-spacing: 0">{art}</pre>
"""
with open("a3.html", "w", encoding="utf-8") as f:
    f.write(html)
```

`font: 6px/1` means 6px text with `line-height: 1`. At `1.3` you get dark stripes between rows: the blocks no longer touch, and the picture turns back into "text".

</details>

---

## 4. Logos: separate the subject from the background

**Task:** Load `../../kuku logo.png` and make a true/false *mask* that is `True` on the dark symbol and `False` on the red. Print it at 80 columns using `█` for True and a space for False.

**Hint:** print a background pixel and a symbol pixel with `img.getpixel((x, y))`, and look for the channel where they differ most.

**Bonus:** instead of hard-coding the cut-off, compute it automatically with Otsu's method.

**Concepts:** thresholding (splitting an image into two groups with one cut-off value), colour channels, Otsu's method.

**Read:**
- [Wikipedia: Thresholding](https://en.wikipedia.org/wiki/Thresholding_(image_processing)).
- [Wikipedia: Otsu's method](https://en.wikipedia.org/wiki/Otsu%27s_method).
- [NumPy: absolute basics](https://numpy.org/doc/stable/user/absolute_beginners.html), for working with `img[..., 0]` and boolean arrays.

<details><summary>Answer</summary>

```python
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

img = np.asarray(Image.open("../../kuku logo.png").convert("RGB")).astype(float)
mask = img[..., 0] < 100          # red channel: background ≈ 161, symbol ≈ 45

cols, aspect = 80, 0.576
h, w = mask.shape
rows = round(h * cols * aspect / w)
small = Image.fromarray(mask.astype(np.uint8) * 255).resize((cols, rows), Image.NEAREST)

for row in np.asarray(small):
    print("".join("█" if v else " " for v in row))
```

Bonus: Otsu tries every possible cut-off and keeps the one that makes the two groups most different from each other:

```python
def otsu(values):
    hist, edges = np.histogram(values, bins=256)
    p = hist / hist.sum()
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(p)                       # share of pixels below each cut
    w1 = 1 - w0
    m0 = np.cumsum(p * centers)
    between = (m0[-1] * w0 - m0) ** 2 / np.maximum(w0 * w1, 1e-12)
    return centers[np.argmax(between)]

mask = img[..., 0] < otsu(img[..., 0])
```

</details>

---

## 5. Smooth edges: coverage instead of yes/no

**Task:** In assignment 4 the curves are jagged, and thin parts flicker in and out. Instead of asking "is this cell's centre on the symbol?", measure *how much* of each cell the symbol covers (0.0–1.0), then pick `█` above 0.60, `▓` above 0.35, `▒` above 0.12, and a space otherwise.

**Concepts:** `Image.NEAREST` samples a single pixel per cell, which causes jagged edges and lost detail (*aliasing*). `Image.BOX` averages every pixel in the cell (*area averaging*), and partial shades on edge cells act as *anti-aliasing*.

**Read:**
- [Wikipedia: Image scaling](https://en.wikipedia.org/wiki/Image_scaling): nearest-neighbour vs box sampling.
- [Wikipedia: Spatial anti-aliasing](https://en.wikipedia.org/wiki/Spatial_anti-aliasing).

<details><summary>Answer</summary>

```python
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

img = np.asarray(Image.open("../../kuku logo.png").convert("RGB")).astype(float)
mask = img[..., 0] < 100

cols, aspect = 80, 0.576
h, w = mask.shape
rows = round(h * cols * aspect / w)
coverage = np.asarray(Image.fromarray(mask.astype(np.float32)).resize((cols, rows), Image.BOX))

def shade(c):
    if c > 0.60: return "█"
    if c > 0.35: return "▓"
    if c > 0.12: return "▒"
    return " "

for row in coverage:
    print("".join(shade(c) for c in row))
```

A float32 array becomes a mode `"F"` image, so `BOX` returns the average of the 0/1 mask, which is the coverage.

</details>

---

## 6. Give the background some texture

**Task:** Background cells are plain spaces right now. Fill most of them with `░` and a few with spaces, chosen at random, so the background has grain like vin.gg. Running the script twice must give *exactly* the same picture.

**Concepts:** random noise as texture; a *seed* makes random numbers repeatable.

**Read:** [NumPy random `Generator`](https://numpy.org/doc/stable/reference/random/generator.html).

<details><summary>Answer</summary>

Add this to assignment 5's answer:

```python
rng = np.random.default_rng(7)          # same seed -> same "random" numbers every run
noise = rng.random((rows, cols))        # one number in 0..1 per cell

def shade(c, n):
    if c > 0.60: return "█"
    if c > 0.35: return "▓"
    if c > 0.12: return "▒"
    return "░" if n > 0.18 else " "     # about 82% of background cells get ░

for y in range(rows):
    print("".join(shade(coverage[y, x], noise[y, x]) for x in range(cols)))
```

</details>

---

## 7. Real colours in HTML

**Task:** Output the logo from assignment 6 as HTML where the symbol is the logo's dark colour, the `░` texture is a slightly darker red, and the box background is the logo's red. Find the colours from the image, don't guess them. Keep the HTML small: one `<span>` per *run* of same-coloured characters, not one per character.

**Concepts:** colour sampling with the median (robust against stray edge pixels), CSS classes, run-length encoding.

**Read:** [Wikipedia: Run-length encoding](https://en.wikipedia.org/wiki/Run-length_encoding).

<details><summary>Answer</summary>

```python
import numpy as np
from PIL import Image

img = np.asarray(Image.open("../../kuku logo.png").convert("RGB")).astype(float)
mask = img[..., 0] < 100
fg = np.median(img[mask], axis=0)       # symbol colour
bg = np.median(img[~mask], axis=0)      # background colour
tx = bg + (fg - bg) * 0.3               # texture: 30% of the way from bg towards fg
hexc = lambda c: "#%02X%02X%02X" % tuple(int(v) for v in c)

cols, aspect = 110, 0.576
h, w = mask.shape
rows = round(h * cols * aspect / w)
coverage = np.asarray(Image.fromarray(mask.astype(np.float32)).resize((cols, rows), Image.BOX))
noise = np.random.default_rng(7).random((rows, cols))

def cell(c, n):
    if c > 0.60: return "█", "s"
    if c > 0.35: return "▓", "s"
    if c > 0.12: return "▒", "s"
    return ("░", "t") if n > 0.18 else (" ", None)

lines = []
for y in range(rows):
    out, run, run_cls = [], "", None
    for x in range(cols):
        ch, cls = cell(coverage[y, x], noise[y, x])
        if cls != run_cls and run:
            out.append(f'<span class="{run_cls}">{run}</span>' if run_cls else run)
            run = ""
        run_cls, run = cls, run + ch
    out.append(f'<span class="{run_cls}">{run}</span>' if run_cls else run)
    lines.append("".join(out))

html = f"""<!DOCTYPE html><meta charset="utf-8">
<style>
  pre {{ background: {hexc(bg)}; font: 5px/1 Consolas, monospace; letter-spacing: 0; display: inline-block; margin: 0; }}
  .s {{ color: {hexc(fg)}; }}
  .t {{ color: {hexc(tx)}; }}
</style>
<pre>{chr(10).join(lines)}</pre>
"""
with open("a7.html", "w", encoding="utf-8") as f:
    f.write(html)
```

This is essentially the logo on your portfolio.

</details>

---

## 8. Dithering: smooth gradients with only five shades

**Task:** Make a left-to-right gradient (black to white) 100 columns × 12 rows, and print it twice with `" ░▒▓█"`: once by plain rounding, once with Floyd–Steinberg dithering. Compare the two.

**Concepts:** quantization (rounding to a few levels) creates visible *banding*. Error diffusion passes each cell's rounding error on to its neighbours, so the *average* over an area stays correct.

**Read:**
- [Wikipedia: Floyd–Steinberg dithering](https://en.wikipedia.org/wiki/Floyd%E2%80%93Steinberg_dithering).
- [Wikipedia: Dither](https://en.wikipedia.org/wiki/Dither), covering ordered (Bayer) dithering too.

<details><summary>Answer</summary>

```python
import sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
SHADES = " ░▒▓█"

def quantize(values, dither):
    v = values.copy() * 4                     # 0..1 -> 0..4 (five shades)
    rows, cols = v.shape
    out = np.zeros((rows, cols), dtype=int)
    for y in range(rows):
        for x in range(cols):
            q = int(np.clip(round(v[y, x]), 0, 4))
            out[y, x] = q
            if dither:
                err = v[y, x] - q             # what rounding threw away...
                if x + 1 < cols: v[y, x + 1] += err * 7 / 16      # ...is handed to the neighbours
                if y + 1 < rows:
                    if x > 0: v[y + 1, x - 1] += err * 3 / 16
                    v[y + 1, x] += err * 5 / 16
                    if x + 1 < cols: v[y + 1, x + 1] += err * 1 / 16
    return out

gradient = np.tile(np.linspace(0, 1, 100), (12, 1))
for dither in (False, True):
    print("dithered:" if dither else "rounded:")
    for row in quantize(gradient, dither):
        print("".join(SHADES[i] for i in row))
    print()
```

Rounding gives five hard stripes; dithering mixes neighbouring shades, so the gradient looks continuous. This is what `--dither` does in `blockart.py`.

</details>

---

## 9. Bonus: double the resolution with half blocks

**Task:** Use the *upper half block* `▀`. Its text colour paints the top half of the cell and the background colour paints the bottom half, so each character shows **two** pixels stacked. Render `photo.jpg` in full colour this way into `a9.html`.

**Concepts:** foreground/background colour per cell; each half cell is twice as wide as it is tall (with aspect 0.576 it's about 1.15:1), so the image needs twice as many pixel rows as character rows.

**Read:**
- [Chafa](https://hpjansson.org/chafa/), a terminal image viewer that uses this trick and many more.
- [Wikipedia: ANSI escape codes, 24-bit colour](https://en.wikipedia.org/wiki/ANSI_escape_code#24-bit), if you want to print it in a terminal instead.

<details><summary>Answer</summary>

```python
from PIL import Image

img = Image.open("photo.jpg").convert("RGB")
cols, aspect = 120, 0.576
rows = round(img.height * cols * aspect / img.width)
small = img.resize((cols, rows * 2), Image.BOX)      # two pixel rows per character row
hexc = lambda c: "#%02X%02X%02X" % c

lines = []
for y in range(rows):
    cells = []
    for x in range(cols):
        top = small.getpixel((x, 2 * y))
        bottom = small.getpixel((x, 2 * y + 1))
        cells.append(f'<span style="color:{hexc(top)};background:{hexc(bottom)}">▀</span>')
    lines.append("".join(cells))

html = f"""<!DOCTYPE html><meta charset="utf-8">
<body style="background:#111">
<pre style="font: 6px/1 Consolas, monospace; letter-spacing: 0">{chr(10).join(lines)}</pre>
"""
with open("a9.html", "w", encoding="utf-8") as f:
    f.write(html)
```

This file is large (one `<span>` per character). Grouping equal neighbours, as in assignment 7, would shrink it.

</details>

---

## Final challenge

Without looking, rebuild `blockart.py`'s mask mode in one file: auto-detect the background from the border pixels, threshold with Otsu, compute coverage with `BOX`, add seeded texture, sample colours with the median, and write HTML with run-grouped spans. Then compare your output with `python blockart.py "../../kuku logo.png" --cols 110`.

## Where to go next

- **Shape matching:** pick characters by the *shape* of the image patch, not just its brightness (`/` for rising edges, `_` for floors). Search "structure-based ASCII art".
- **Colour quantization:** how `--color 16` picks a 16-colour palette. See [Wikipedia: Color quantization](https://en.wikipedia.org/wiki/Color_quantization) and median cut.
- **Gamma and perceived brightness:** why 50% grey doesn't look half as bright. See [Wikipedia: Gamma correction](https://en.wikipedia.org/wiki/Gamma_correction).
- **Shaders:** the same ideas run per pixel on the GPU to turn live 3D games into ASCII. Search "ASCII shader".
