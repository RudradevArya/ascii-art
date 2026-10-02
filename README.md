# blockart.py

Turns any image or text into Unicode block art (`░ ▒ ▓ █`) that you can paste into a web page. It generated the Kuru logo in the portfolio header.

## Live

Try the web UI without installing anything:

- **Production:** https://ascii.projects.xrudra.dev
- **Cloudflare Pages:** https://ascii-art-asi.pages.dev

## Web UI

A browser-based interface is deployed on Cloudflare Pages:

| Environment | URL |
|---|---|
| Production (custom domain) | https://ascii.projects.xrudra.dev |
| Cloudflare Pages | https://ascii-art-asi.pages.dev |

## Setup

You need Python 3.9+ and two libraries:

```bash
pip install pillow numpy
```

Run every command below from this folder (`tools/ascii-art`).

## Quick start

```bash
# The portfolio logo (this is how the header art was made)
python blockart.py "../../kuku logo.png" --cols 110

# Open the result in a browser
start out/kuku-logo/preview.html        # Windows
open  out/kuku-logo/preview.html        # macOS
```

Each run writes three files to `out/<name>/`:

| File | What it is |
|---|---|
| `preview.html` | Standalone page to check how the art looks |
| `snippet.html` | `<style>` + `<div class="blockart"><pre>…</pre></div>` to paste into any site |
| `art.txt` | Plain characters, no colours (handy for terminals, READMEs, Discord) |

`out/` is git-ignored, so experiment freely.

## Two modes: pick the one that matches your picture

**`--mode mask` (default): logos, icons, text, anything with a solid subject on a plain background.**
The script finds the background colour from the image border, separates the subject from it, and draws the subject with `█ ▓ ▒` (shaded edges keep curves smooth) on a lightly textured `░` background. Colours are sampled from the image automatically.

**`--mode tone`: photos and anything with gradients.**
Each character is picked by brightness: bright pixels get dense blocks, dark pixels get light ones or spaces (this is the vin.gg look). Use `--invert` if the art goes on a light page.

## Recipes

```bash
# Logo, cropped tight around the subject instead of keeping the whole picture
python blockart.py logo.png --crop fit --cols 90

# Logo with a plain background (no ░ texture)
python blockart.py logo.png --texture 0

# Logo recoloured: cream symbol on a black box
python blockart.py logo.png --fg "#F2E6D8" --bg "#0C0C0C"

# Text (uses Arial Bold; pass --font for another .ttf)
python blockart.py --text "RUDRA" --cols 90 --fg "#F2E6D8" --bg "#0C0C0C"
python blockart.py --text "HELLO\nWORLD" --cols 80 --texture 0

# Photo in grey on a dark page, smoother gradients with dithering
python blockart.py me.jpg --mode tone --cols 120 --dither

# Photo in colour (16-colour palette)
python blockart.py me.jpg --mode tone --cols 120 --color 16

# Photo for a light page, with punchier mid-tones
python blockart.py me.jpg --mode tone --invert --gamma 1.4

# Print to the terminal instead of opening a browser
python blockart.py logo.png --cols 70 --print
```

## Putting art on the portfolio

**Replace the header logo automatically** (mask mode only). This swaps the art inside `.kuru-dynasty-art` in `index.html` and updates its background and symbol colours:

```bash
python blockart.py "new logo.png" --cols 110 --inject ../../index.html
```

Check the page, then commit. If you don't like it, `git checkout index.html` brings back the old one.

**Anywhere else:** copy the contents of `out/<name>/snippet.html` into the page. Rename `.blockart` if it clashes with something.

## Size and detail

The on-screen size depends on the column count, the row count and the CSS font size:

```
width  ≈ cols × font-size × 0.576
height ≈ rows × font-size
```

The header logo is 110 columns × 42 rows at `font-size: 5px`, so about 317 × 210 px. For more detail at the same width, raise `--cols` and lower `--font-size` together (for example 160 columns at 3.5px). Very small sizes can break on browsers where the user has set a minimum font size, so check on your phone too.

## Options

Run `python blockart.py -h` for the full list. The ones you'll use most:

| Option | Default | Meaning |
|---|---|---|
| `--cols N` | 100 | Characters per row; more = more detail |
| `--mode mask/tone` | mask | Solid-subject art or brightness art |
| `--crop full/fit` | full | Keep the whole picture, or crop around the subject |
| `--fg`, `--bg` | from image | Override the subject / background colour |
| `--texture 0..1` | 0.82 | Mask mode: how much of the background gets `░` |
| `--dither` | off | Tone mode: Floyd–Steinberg dithering |
| `--color N` | off | Tone mode: colour cells with an N-colour palette |
| `--invert` | off | Tone mode: dark pixels get dense blocks |
| `--gamma` | 1.0 | Tone mode: >1 darkens mid-tones, <1 brightens them |
| `--font-size` | 5 | CSS px size written into the snippet |
| `--aspect` | 0.576 | Width / height of one character in your font |
| `--seed` | 7 | Change for a different random background texture |

## Troubleshooting

- **Art looks stretched or squashed.** Your font isn't Cascadia Code. Measure its ratio (see assignment 2 in `ASSIGNMENTS.md`) and pass `--aspect`.
- **Thin lines between rows.** The `<pre>` needs `line-height: 1`, and the font must have full-height block glyphs (Cascadia Code, Consolas, Menlo and DejaVu Sans Mono do).
- **Subject and background are swapped, or details missing in mask mode.** The background is detected from the image border, so the subject must not touch all four edges. Try `--crop fit`, or use `--mode tone`.
- **Characters print as `?` in the terminal.** Use Windows Terminal or VS Code's terminal, which support UTF-8.

---

## Web UI (Browser Version)

A browser-based version is available in the `web/` folder. It runs entirely in the browser using [Pyodide](https://pyodide.org) (Python compiled to WebAssembly) — no server required.

### Features

- Upload images or enter text directly in the browser
- All the same options as the CLI (mode, columns, colors, dither, etc.)
- Live preview of generated art
- Copy to clipboard or download as HTML snippet / plain text

### Try Locally

```bash
# From the repository root:
npx serve .
# Then open http://localhost:3000/web/
```

Or use Python's built-in server:

```bash
python -m http.server 8000
# Then open http://localhost:8000/web/
```

### Deploy to Cloudflare Pages

The web UI is hosted at [ascii.projects.xrudra.dev](https://ascii.projects.xrudra.dev).

To deploy your own instance:

1. Connect your repository to Cloudflare Pages
2. Configure build settings:
   - **Build command:** `cp blockart.py web/`
   - **Build output directory:** `web`
3. Deploy!

The build command copies `blockart.py` into the `web/` folder so the Python module is available alongside the web assets. The site is then served from the root URL (e.g. `your-project.pages.dev/`).

To use a custom domain, add it in the Cloudflare Pages dashboard under **Custom domains**.

The `_headers` file configures the required CORS headers for Pyodide to work correctly.

### How It Works

The web UI loads `blockart.py` directly via Pyodide, so the core algorithm is identical to the CLI. A thin wrapper (`web/blockart_web.py`) adapts the file-based API to accept image bytes from JavaScript's File API.
