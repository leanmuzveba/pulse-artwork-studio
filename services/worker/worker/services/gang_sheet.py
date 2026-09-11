"""Gang sheet composition — auto-nest multiple artworks onto one print sheet.

A separate module from imaging.py because its functions operate on a *list*
of images rather than transforming one, which doesn't fit imaging.py's
one-image-in-one-image-out shape.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image


def compose_gang_sheet(
    tiles: list[tuple[str, bytes, int]],
    *,
    sheet_width_px: int,
    spacing_px: int,
) -> tuple[bytes, list[dict[str, Any]], int]:
    """Shelf-pack a list of tiles onto one sheet of fixed width.

    `tiles` is `(artwork_id, image_bytes, rotate_degrees)` — the same
    artwork appears once per requested copy, already expanded by the caller.
    Rotation is normalized to the nearest 90-degree turn.

    Uses a simple shelf/row packer: tiles are placed left-to-right, wrapping
    to a new row when the next tile would exceed `sheet_width_px`; each row's
    height is its tallest tile. Not bin-packing-optimal, but deterministic,
    fast, and reads naturally top-to-bottom on a printed sheet.

    Returns the composited PNG bytes, each tile's placement (in px, in the
    same order as `tiles`), and the sheet height actually used.
    """
    prepared: list[tuple[str, Image.Image, int]] = []
    for artwork_id, data, rotate_deg in tiles:
        with Image.open(BytesIO(data)) as img:
            img.load()
            tile = img.convert("RGBA")
            normalized = round(rotate_deg / 90.0) * 90 % 360
            if normalized:
                tile = tile.rotate(-normalized, expand=True)
            prepared.append((artwork_id, tile, normalized))

    placements: list[dict[str, Any]] = []
    x = spacing_px
    y = spacing_px
    row_height = 0
    sheet_height = spacing_px

    for artwork_id, tile, rotate_deg in prepared:
        width, height = tile.size
        if x + width + spacing_px > sheet_width_px and x > spacing_px:
            x = spacing_px
            y += row_height + spacing_px
            row_height = 0

        placements.append(
            {
                "artwork_id": artwork_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "rotate_deg": rotate_deg,
            }
        )
        x += width + spacing_px
        row_height = max(row_height, height)
        sheet_height = max(sheet_height, y + row_height + spacing_px)

    canvas = Image.new("RGBA", (sheet_width_px, sheet_height), (0, 0, 0, 0))
    for (_artwork_id, tile, _rotate_deg), placement in zip(prepared, placements, strict=True):
        canvas.alpha_composite(tile, (placement["x"], placement["y"]))

    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue(), placements, sheet_height
