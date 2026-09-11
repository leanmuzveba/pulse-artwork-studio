"""Unit tests for the gang sheet auto-nest/composite helper (needs Pillow, no
broker/DB)."""

from __future__ import annotations

import io

from PIL import Image

from worker.services.gang_sheet import compose_gang_sheet


def _png(width: int, height: int, color=(200, 30, 30, 255)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def test_places_single_tile_inset_by_the_spacing_margin():
    data, placements, sheet_height = compose_gang_sheet(
        [("a1", _png(20, 10), 0)], sheet_width_px=200, spacing_px=5
    )
    assert placements == [
        {"artwork_id": "a1", "x": 5, "y": 5, "width": 20, "height": 10, "rotate_deg": 0}
    ]
    assert sheet_height == 5 + 10 + 5
    meta_img = Image.open(io.BytesIO(data))
    assert meta_img.size == (200, sheet_height)


def test_tiles_pack_left_to_right_on_one_row_when_they_fit():
    _data, placements, _h = compose_gang_sheet(
        [("a1", _png(20, 10), 0), ("a2", _png(20, 10), 0)],
        sheet_width_px=200,
        spacing_px=5,
    )
    assert [p["artwork_id"] for p in placements] == ["a1", "a2"]
    assert placements[0]["y"] == placements[1]["y"] == 5
    assert placements[1]["x"] == 5 + 20 + 5  # right after the first tile + spacing


def test_wraps_to_a_new_row_when_exceeding_sheet_width():
    _data, placements, sheet_height = compose_gang_sheet(
        [("a1", _png(60, 10), 0), ("a2", _png(60, 10), 0)],
        sheet_width_px=100,  # only one 60px tile fits per row with 5px margins
        spacing_px=5,
    )
    assert placements[0]["y"] == 5
    assert placements[1]["y"] == 5 + 10 + 5  # second row, below the first
    assert placements[1]["x"] == 5
    assert sheet_height == placements[1]["y"] + 10 + 5


def test_rotate_90_swaps_placed_dimensions():
    _data, placements, _h = compose_gang_sheet(
        [("a1", _png(30, 10), 90)], sheet_width_px=200, spacing_px=0
    )
    assert (placements[0]["width"], placements[0]["height"]) == (10, 30)
    assert placements[0]["rotate_deg"] == 90


def test_rotate_degrees_snap_to_nearest_90():
    _data, placements, _h = compose_gang_sheet(
        [("a1", _png(30, 10), 100)], sheet_width_px=200, spacing_px=0
    )
    assert placements[0]["rotate_deg"] == 90


def test_repeated_copies_of_the_same_artwork_each_get_a_placement():
    _data, placements, _h = compose_gang_sheet(
        [("a1", _png(10, 10), 0), ("a1", _png(10, 10), 0), ("a1", _png(10, 10), 0)],
        sheet_width_px=200,
        spacing_px=0,
    )
    assert len(placements) == 3
    assert all(p["artwork_id"] == "a1" for p in placements)
    assert [p["x"] for p in placements] == [0, 10, 20]


def test_output_is_a_valid_transparent_png():
    data, _placements, _h = compose_gang_sheet(
        [("a1", _png(10, 10), 0)], sheet_width_px=50, spacing_px=5
    )
    img = Image.open(io.BytesIO(data))
    assert img.format == "PNG"
    assert img.mode == "RGBA"
    # A corner outside every placed tile should stay transparent.
    assert img.getpixel((0, 0))[3] == 0
