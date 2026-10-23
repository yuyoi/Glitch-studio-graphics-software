"""GLITCH LAB - lo-fi glitch studio: algorithmic glitch brushes + whole-layer glitch filters.

    pythonw glitchlab.py [picture.png | picture.ora]

New effect = one .py file in effects/ (see gl/effects.py for the 10-line format), then RELOAD FX.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl.ui import main

if __name__ == '__main__':
    sys.exit(main(sys.argv))
