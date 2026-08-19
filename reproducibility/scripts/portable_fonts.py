"""Portable Pillow font loading through Matplotlib's bundled font registry."""

from __future__ import annotations

from matplotlib import font_manager
from PIL import ImageFont


def load_pillow_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Return Matplotlib's bundled DejaVu Sans without a platform font path."""
    properties = font_manager.FontProperties(
        family="DejaVu Sans",
        weight="bold" if bold else "normal",
    )
    path = font_manager.findfont(properties, fallback_to_default=True)
    return ImageFont.truetype(path, size=size)
