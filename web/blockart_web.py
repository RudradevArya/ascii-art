"""Thin wrapper around blockart.py for use in Pyodide (browser).

This module provides functions that accept image bytes instead of file paths,
making it suitable for browser-based usage where images come from file inputs.
"""
import io
import sys
from types import SimpleNamespace

# Add parent directory to path so we can import blockart
sys.path.insert(0, '/home/pyodide')

from PIL import Image

# Import core functions from blockart.py
import blockart
from blockart import (
    CELL_ASPECT,
    render_text,
    mask_art,
    tone_art,
    to_html_lines,
    css_block,
)


def make_args(
    cols=100,
    mode='mask',
    crop='full',
    margin=0.15,
    fg=None,
    bg=None,
    texture=0.82,
    invert=False,
    gamma=1.0,
    dither=False,
    color=0,
    aspect=CELL_ASPECT,
    font_size=5,
    seed=7,
    label='Block art',
):
    """Create an args namespace compatible with blockart functions."""
    return SimpleNamespace(
        cols=cols,
        mode=mode,
        crop=crop,
        margin=margin,
        fg=fg if fg else None,
        bg=bg if bg else None,
        texture=texture,
        invert=invert,
        gamma=gamma,
        dither=dither,
        color=color,
        aspect=aspect,
        font_size=font_size,
        seed=seed,
        label=label,
    )


def load_image_from_bytes(image_bytes):
    """Load an image from bytes (from JS File API)."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        white = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(white, img)
    return img.convert("RGB")


def process_image(image_bytes, **kwargs):
    """Process image bytes and return art result.
    
    Args:
        image_bytes: Raw image bytes from JS File API
        **kwargs: Options passed to make_args()
    
    Returns:
        dict with keys: chars, html_lines, css, snippet_html, preview_html, 
                        art_txt, palette, bg, rows, cols
    """
    args = make_args(**kwargs)
    img = load_image_from_bytes(image_bytes)
    
    if args.mode == 'mask':
        chars, classes, palette, bg = mask_art(img, args)
    else:
        chars, classes, palette, bg = tone_art(img, args)
    
    html_lines = to_html_lines(chars, classes)
    return _build_result(chars, html_lines, palette, bg, args)


def process_text(text, **kwargs):
    """Process text and return art result.
    
    Args:
        text: Text to render (use \n for newlines)
        **kwargs: Options passed to make_args()
    
    Returns:
        dict with keys: chars, html_lines, css, snippet_html, preview_html,
                        art_txt, palette, bg, rows, cols
    """
    args = make_args(**kwargs)
    img = render_text(text.replace('\\n', '\n'))
    
    if args.mode == 'mask':
        chars, classes, palette, bg = mask_art(img, args)
    else:
        chars, classes, palette, bg = tone_art(img, args)
    
    html_lines = to_html_lines(chars, classes)
    return _build_result(chars, html_lines, palette, bg, args)


def _build_result(chars, html_lines, palette, bg, args):
    """Build the result dictionary with all output formats."""
    rows, cols = chars.shape
    
    css = css_block('.blockart', palette, bg, args.font_size)
    
    pre = f'<pre aria-label="{args.label}">' + '\n'.join(html_lines) + '</pre>'
    snippet_html = f'<style>\n{css}\n</style>\n<div class="blockart">{pre}</div>\n'
    
    preview_html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{args.label}</title>
<link href="https://fonts.cdnfonts.com/css/cascadia-code" rel="stylesheet">
<style>
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #1E1E1E; }}
{css}
</style></head>
<body><div class="blockart">{pre}</div></body></html>
'''
    
    art_txt = '\n'.join(''.join(r) for r in chars)
    
    return {
        'rows': rows,
        'cols': cols,
        'html_lines': html_lines,
        'css': css,
        'snippet_html': snippet_html,
        'preview_html': preview_html,
        'art_txt': art_txt,
        'palette': dict(palette),
        'bg': bg,
    }
