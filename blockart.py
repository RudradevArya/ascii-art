"""Turn an image or a piece of text into Unicode block art (░ ▒ ▓ █) for a web page.

Examples:
    python blockart.py "../../kuku logo.png" --cols 110
    python blockart.py photo.jpg --mode tone --cols 120 --dither
    python blockart.py photo.jpg --mode tone --color 16
    python blockart.py --text "RUDRA" --cols 90 --fg "#F2E6D8" --bg "#0C0C0C"
    python blockart.py "../../kuku logo.png" --cols 110 --inject ../../index.html

Run `python blockart.py -h` for every option.
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SHADES = " ░▒▓█"
# Width of one Cascadia Code glyph divided by the font size; with `line-height: 1`
# each character cell is therefore 0.576 times as wide as it is tall.
CELL_ASPECT = 0.576
HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- input

def load_image(path):
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(white, img)
    return img.convert("RGB")


def load_font(font_path, size):
    candidates = [font_path] if font_path else []
    candidates += [
        "arialbd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def render_text(text, font_path=None, size=200, pad=40):
    font = load_font(font_path, size)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = probe.multiline_textbbox((0, 0), text, font=font, align="center")
    img = Image.new("RGB", (right - left + 2 * pad, bottom - top + 2 * pad), "white")
    ImageDraw.Draw(img).multiline_text((pad - left, pad - top), text, font=font, fill="black", align="center")
    return img


# ---------------------------------------------------------------- image helpers

def otsu_threshold(values):
    """Pick the cut that best separates `values` into two groups (Otsu's method)."""
    hist, edges = np.histogram(values, bins=256)
    p = hist / hist.sum()
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(p)
    w1 = 1 - w0
    mean0 = np.cumsum(p * centers)
    between = (mean0[-1] * w0 - mean0) ** 2 / np.maximum(w0 * w1, 1e-12)
    return centers[np.argmax(between)]


def split_subject(img):
    """Return (mask, fg_rgb, bg_rgb): background is whatever colour fills the image border."""
    arr = np.asarray(img, dtype=np.float32)
    border = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.linalg.norm(arr - bg, axis=2)
    mask = dist > otsu_threshold(dist)
    fg = np.median(arr[mask], axis=0) if mask.any() else 255 - bg
    return mask, fg, bg


def crop_to_subject(img, mask, margin):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return img, mask
    h, w = mask.shape
    pad_y = int((ys.max() - ys.min()) * margin)
    pad_x = int((xs.max() - xs.min()) * margin)
    y0, y1 = max(0, ys.min() - pad_y), min(h, ys.max() + pad_y + 1)
    x0, x1 = max(0, xs.min() - pad_x), min(w, xs.max() + pad_x + 1)
    return img.crop((x0, y0, x1, y1)), mask[y0:y1, x0:x1]


def grid_size(width, height, cols, aspect):
    cell_w = width / cols
    cell_h = cell_w / aspect
    return cols, max(1, round(height / cell_h))


def area_average(values, cols, rows):
    """Shrink a 2-D float array to (rows, cols), each cell = mean of the pixels it covers."""
    small = Image.fromarray(values.astype(np.float32), mode="F").resize((cols, rows), Image.BOX)
    return np.asarray(small)


def quantize(values, levels, dither):
    """Round 0..1 values to 0..levels; optionally spread the rounding error (Floyd–Steinberg)."""
    v = np.clip(values, 0, 1) * levels
    out = np.zeros(v.shape, dtype=int)
    rows, cols = v.shape
    for y in range(rows):
        for x in range(cols):
            q = int(np.clip(round(v[y, x]), 0, levels))
            out[y, x] = q
            if not dither:
                continue
            err = v[y, x] - q
            if x + 1 < cols:
                v[y, x + 1] += err * 7 / 16
            if y + 1 < rows:
                if x > 0:
                    v[y + 1, x - 1] += err * 3 / 16
                v[y + 1, x] += err * 5 / 16
                if x + 1 < cols:
                    v[y + 1, x + 1] += err * 1 / 16
    return out


def to_hex(rgb):
    r, g, b = (int(round(c)) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def parse_hex(value):
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


# ---------------------------------------------------------------- the two art styles

def mask_art(img, args):
    """Two-colour art: a solid subject on a lightly textured background (logos, icons, text)."""
    mask, fg, bg = split_subject(img)
    if args.crop == "fit":
        img, mask = crop_to_subject(img, mask, args.margin)
    if args.fg:
        fg = parse_hex(args.fg)
    if args.bg:
        bg = parse_hex(args.bg)

    h, w = mask.shape
    cols, rows = grid_size(w, h, args.cols, args.aspect)
    coverage = area_average(mask, cols, rows)
    noise = np.random.default_rng(args.seed).random((rows, cols))
    sparkle = 0.05 if args.texture > 0 else 0

    chars = np.full((rows, cols), " ", dtype="<U1")
    classes = np.full((rows, cols), "", dtype="<U3")
    for y in range(rows):
        for x in range(cols):
            cov, n = coverage[y, x], noise[y, x]
            if cov > 0.60:
                chars[y, x], classes[y, x] = "█", "ks"
            elif cov > 0.35:
                chars[y, x], classes[y, x] = "▓", "ks"
            elif cov > 0.12:
                chars[y, x], classes[y, x] = "▒", "ks"
            elif n < sparkle:
                chars[y, x], classes[y, x] = "▒", "kb"
            elif n >= 1 - args.texture:
                chars[y, x], classes[y, x] = "░", "kb"

    texture = bg + (fg - bg) * 0.3
    palette = {"ks": to_hex(fg), "kb": to_hex(texture)}
    return chars, classes, palette, to_hex(bg)


def tone_art(img, args):
    """Brightness art for photos: brighter pixel -> denser block (flip with --invert)."""
    if args.crop == "fit":
        mask, _, _ = split_subject(img)
        img, _ = crop_to_subject(img, mask, args.margin)

    cols, rows = grid_size(img.width, img.height, args.cols, args.aspect)
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255
    ink = area_average(gray, cols, rows)
    if args.invert:
        ink = 1 - ink
    ink = ink ** args.gamma
    levels = quantize(ink, len(SHADES) - 1, args.dither)
    chars = np.array(list(SHADES))[levels]

    bg = args.bg or ("#FFFFFF" if args.invert else "#0C0C0C")
    if args.color:
        small = img.resize((cols, rows), Image.BOX)
        indexed = small.quantize(colors=args.color, method=Image.Quantize.MEDIANCUT)
        flat = indexed.getpalette()[: args.color * 3]
        palette = {f"c{i}": to_hex(flat[i * 3:i * 3 + 3]) for i in range(args.color)}
        classes = np.vectorize(lambda i: f"c{i}")(np.asarray(indexed))
    else:
        fg = args.fg or ("#1A1A1A" if args.invert else "#CCCCCC")
        palette = {"kt": fg}
        classes = np.full((rows, cols), "kt", dtype="<U3")
    classes[chars == " "] = ""
    return chars, classes, palette, bg


# ---------------------------------------------------------------- output

def to_html_lines(chars, classes):
    """Group runs of same-coloured characters into one <span> each, to keep the HTML small."""
    lines = []
    for row_chars, row_classes in zip(chars, classes):
        parts, run, run_class = [], "", None
        for ch, cls in zip(row_chars, row_classes):
            if cls != run_class and run:
                parts.append(f'<span class="{run_class}">{run}</span>' if run_class else run)
                run = ""
            run_class = cls
            run += ch
        if run:
            parts.append(f'<span class="{run_class}">{run}</span>' if run_class else run)
        lines.append("".join(parts))
    return lines


def css_block(scope, palette, bg, font_size):
    colors = "\n".join(f"{scope} .{name} {{ color: {hexcode}; }}" for name, hexcode in palette.items())
    return f"""{scope} {{
    display: inline-block;
    background: {bg};
    border-radius: 6px;
    overflow: hidden;
}}
{scope} pre {{
    margin: 0;
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: {font_size}px;
    line-height: 1;
    letter-spacing: 0;
    white-space: pre;
    font-variant-ligatures: none;
    -webkit-text-size-adjust: none;
    text-size-adjust: none;
}}
{colors}"""


def write_outputs(out_dir, chars, html_lines, palette, bg, font_size, label):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "art.txt").write_text("\n".join("".join(r) for r in chars), encoding="utf-8")

    pre = f'<pre aria-label="{label}">' + "\n".join(html_lines) + "</pre>"
    css = css_block(".blockart", palette, bg, font_size)
    snippet = f"<style>\n{css}\n</style>\n<div class=\"blockart\">{pre}</div>\n"
    (out_dir / "snippet.html").write_text(snippet, encoding="utf-8")

    preview = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{label}</title>
<link href="https://fonts.cdnfonts.com/css/cascadia-code" rel="stylesheet">
<style>
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #1E1E1E; }}
{css}
</style></head>
<body><div class="blockart">{pre}</div></body></html>
"""
    (out_dir / "preview.html").write_text(preview, encoding="utf-8")


def inject(index_path, html_lines, palette, bg, label):
    """Replace the logo art in the portfolio's index.html and update its colours."""
    src = index_path.read_text(encoding="utf-8")
    pre_re = re.compile(r'(<div class="kuru-dynasty-art">\s*<pre)[^>]*>.*?</pre>', re.S)
    if len(pre_re.findall(src)) != 1:
        sys.exit(f"Could not find exactly one .kuru-dynasty-art <pre> in {index_path}")
    body = "\n".join(html_lines)
    src = pre_re.sub(lambda m: f'{m.group(1)} aria-label="{label}">{body}</pre>', src)

    for name, hexcode in palette.items():
        src, found = re.subn(rf"(\.kuru-dynasty-art \.{name} \{{ color: )#[0-9A-Fa-f]{{6}}", rf"\g<1>{hexcode}", src)
        if not found:
            print(f"note: add `.kuru-dynasty-art .{name} {{ color: {hexcode}; }}` to the CSS in {index_path.name}")
    src = re.sub(r'((?:\[data-theme="dark"\] )?\.kuru-dynasty-art \{\s*background: )#[0-9A-Fa-f]{6}', rf"\g<1>{bg}", src)
    index_path.write_text(src, encoding="utf-8", newline="")


# ---------------------------------------------------------------- CLI

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", nargs="?", help="path to a .png/.jpg/.webp (omit when using --text)")
    parser.add_argument("--text", help="render this text instead of an image (use \\n for new lines)")
    parser.add_argument("--font", help="TTF/OTF font file for --text (default: Arial Bold)")
    parser.add_argument("--mode", choices=["mask", "tone"], default="mask",
                        help="mask = solid subject on a background (logos, text); tone = brightness shading (photos)")
    parser.add_argument("--cols", type=int, default=100, help="characters per row (more = more detail)")
    parser.add_argument("--crop", choices=["full", "fit"], default="full",
                        help="full = keep the whole picture; fit = crop around the subject")
    parser.add_argument("--margin", type=float, default=0.15, help="space kept around the subject with --crop fit")
    parser.add_argument("--fg", help="override the subject colour, e.g. '#F2E6D8'")
    parser.add_argument("--bg", help="override the background colour, e.g. '#0C0C0C'")
    parser.add_argument("--texture", type=float, default=0.82,
                        help="mask mode: share of background cells drawn as ░ (0 = plain background)")
    parser.add_argument("--invert", action="store_true", help="tone mode: dark pixels get dense blocks (for light pages)")
    parser.add_argument("--gamma", type=float, default=1.0, help="tone mode: >1 darkens mid-tones, <1 brightens them")
    parser.add_argument("--dither", action="store_true", help="tone mode: Floyd–Steinberg dithering for smoother gradients")
    parser.add_argument("--color", type=int, default=0, metavar="N", help="tone mode: colour each cell using N palette colours")
    parser.add_argument("--aspect", type=float, default=CELL_ASPECT, help="character width / height of your font")
    parser.add_argument("--font-size", type=float, default=5, help="CSS font size in px for the generated snippet")
    parser.add_argument("--seed", type=int, default=7, help="random seed for the background texture")
    parser.add_argument("--out", help="output folder (default: out/<name> next to this script)")
    parser.add_argument("--inject", metavar="INDEX_HTML", help="also replace the logo art inside this index.html")
    parser.add_argument("--label", default="Kuru dynasty symbol", help="aria-label for screen readers")
    parser.add_argument("--print", action="store_true", help="print the art to the terminal")
    args = parser.parse_args()

    if bool(args.image) == bool(args.text):
        parser.error("give either an image path or --text, not both")

    if args.text:
        img = render_text(args.text.replace("\\n", "\n"), args.font)
        name = re.sub(r"[^a-z0-9]+", "-", args.text.lower()).strip("-") or "text"
    else:
        img = load_image(args.image)
        name = re.sub(r"[^a-z0-9]+", "-", Path(args.image).stem.lower()).strip("-") or "image"

    chars, classes, palette, bg = (mask_art if args.mode == "mask" else tone_art)(img, args)
    html_lines = to_html_lines(chars, classes)

    out_dir = Path(args.out) if args.out else HERE / "out" / name
    write_outputs(out_dir, chars, html_lines, palette, bg, args.font_size, args.label)
    rows, cols = chars.shape
    print(f"{cols} x {rows} characters -> {out_dir}")
    print(f"background {bg}, colours {palette}")

    if args.inject:
        inject(Path(args.inject), html_lines, palette, bg, args.label)
        print(f"updated {args.inject}")

    if args.print:
        print("\n".join("".join(r) for r in chars))


if __name__ == "__main__":
    main()
