<p align="center"><img src="assets/logo.png" width="420" alt="Glitch Lab"></p>

# Glitch Lab

> *"Every hitch gets turned into a shortcut when I persist."*

**A lo-fi glitch studio for painters.** Glitch Lab is a small editor that does one thing: break pictures
beautifully. Pen-pressure **glitch brushes** paint square-pixel dot lines, random speckle, TV static and
broken video blocks exactly where you draw, and whole-layer **glitch filters** do the rest: colour-plate rips,
VHS tape, dead-channel snow, test-card bars, JPEG/DCT rot, pixel sorting, and filters built on maths people
find beautiful (1/f fractal noise, quasicrystals, Turing patterns). Every effect is one small Python file,
so adding the next glitch you find is a 10-line job.

> **Made by JunkSmithWizard (JSW) together with Claude (Anthropic's AI).** It started as an accident: a
> half-broken layer recovery of one of JSW's drawings came out torn and speckled in a way that looked better
> than the original. JSW wanted that look on purpose, plus brushes Krita can't do. Claude wrote the code;
> JSW judged every effect by eye and steered what came next.

<p align="center"><img src="assets/screenshot.png" width="860" alt="Glitch Lab window: brushes and colour modes on the left, canvas in the middle, filters and layers on the right"></p>

## What's in it

**Brushes** (pen pressure, the pen's eraser end erases, ERASE mode turns any brush into a hole-puncher)

| Brush | What it does |
|---|---|
| **Dot Line** | square pixel dots laid along your stroke, in the direction you draw; rows, gaps, jitter, dropout |
| **Speckle** | a fresh random scatter of square specks on every dab (never smears); scatter = random, **blue noise**, **sunflower** (golden angle), clumps |
| **Static** | paints TV snow (circle, square or scan band) |
| **Block Brush** | paints broken digital video: DCT-crushed blocks, wrong-place copies, drag-down smears |
| **Row Slip** | slides thin bands of the picture sideways (pick one channel for an RGB tear) |
| **Pixel Pen** | plain hard pixel pen / eraser for cleanup |

**Colour modes** for every brush: pick, palette (5 swatches), random, pure RGB, **bust** (the drawing's own colours,
torn off a nearby spot and hue-spun), **golden** (golden-ratio hue steps: the most evenly spread colours),
**drift** (hue wanders with 1/f pink noise). Tick *every pixel its own colour* for per-pixel chaos.

<p align="center"><img src="assets/brushes.png" width="860" alt="Brush presets painted over the test picture"></p>

**Filters** (whole layer, live preview while you move the sliders, APPLY keeps it, Ctrl+Z drops it)

| Filter | What it does |
|---|---|
| **Colour Rip** | k-means splits the picture into colour plates, then prints each like a screenprint: off-register, torn where colours meet, speckled |
| **Dropout** | worn-print alpha dropout (clumps + grain, protects lines) |
| **Fractal Colour** | 1/f^β noise made in the Fourier domain (the fractal statistics of clouds and of the Pollock paintings people rate most beautiful), with domain warp: hue bust, palette, thermal bands |
| **Quasicrystal** | N plane waves added together: never-repeating Penrose-like moiré; palette, hue bust, lace cut, chroma moiré |
| **Turing** | Gray-Scott reaction-diffusion (coral, spots, maze, mitosis, worms, bubbles) grown out of *your* line art |
| **TV Snow** | dead-channel static with scan streaks and a rolling bar; over, behind the drawing, or weak-signal ghost |
| **VHS / Cable** | 1/f line wobble, colour bleed, tracking bands, head-switch tear, interlace comb, tape fade |
| **Colour Bars** | SMPTE / EBU / RGB ramp test cards: behind, over, or torn in as slices |
| **Block Rot** | real JPEG maths: 8×8 DCT quantisation (colour crushed harder) + broken macroblocks |
| **Pixel Sort**, **RGB Shift**, **Scanlines**, **Dither** (Bayer, Game Boy), **JPEG Crush**, **Slice Shift** | the classics |

<p align="center"><img src="assets/filters.png" width="860" alt="Filter presets applied to the test picture"></p>

57 presets ship in `presets.json`; **SAVE CURRENT AS PRESET** adds yours.

## Install and run

Windows, Python 3.10+:

```
pip install -r requirements.txt
python glitchlab.py            (or double-click "Glitch Lab.bat", or drag a PNG onto it)
```

- Opens PNG / JPG / **ORA** (layers kept). Saves layered **.ora**, which Krita opens with every layer intact.
  **Export PNG** writes a flat copy. It never overwrites the file you opened, and autosaves every 3 minutes.
- Pen: Windows Ink tablets (pressure + eraser end). Mouse works too. Fingers pan, two fingers pinch-zoom.
- Keys: **E** paint/erase, **[ ]** brush size, **+ / -** zoom, wheel zoom, space-drag pan, **F** fit, **1** 100%,
  **Ctrl+Z / Ctrl+Y** undo/redo, **Ctrl+Enter** apply filter, **Ctrl+S** save.

`glitch_tex.py` / `glitch.bat` is the original command-line dropout texture: drag PNG layers onto the .bat.

## Add your own glitch

Drop a file in `effects/` and press **RELOAD FX** (restart for a new button). Sliders and presets come for free.

```python
"""My filter: shows as a tooltip."""
import numpy as np

NAME = 'Invert Bands'
KIND = 'filter'
PARAMS = [P('every', 'EVERY N px', 2, 200, 40)]          # key, label, min, max, default

def apply(img, p, rng):                                   # img: HxWx4 uint8, return a new one
    out = img.copy()
    rows = (np.arange(img.shape[0]) // p['every']) % 2 == 1
    out[rows, :, :3] = 255 - out[rows, :, :3]
    return out
```

A brush gives `spacing(p, pressure)` and `dab(ctx, x, y, pressure, angle)` instead and stamps with
`ctx.square(x, y, size)`, which already handles erase mode and all the colour modes. See `gl/effects.py`.

## License

MIT. See [LICENSE](LICENSE). The test picture in `assets/` is generated (shapes and a gradient), not artwork.
