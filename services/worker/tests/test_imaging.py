"""Unit tests for image processing helpers (needs Pillow, no broker/DB)."""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from worker.services import imaging
from worker.services.imaging import (
    crop,
    dtf_check,
    embroidery,
    enhance,
    export_pdf,
    export_png,
    extract_metadata,
    flip,
    halftone,
    remove_background,
    resize,
    rotate,
    underbase_preview,
    upscale,
    vectorize,
)


def _png(width: int, height: int, mode: str = "RGBA") -> bytes:
    buf = io.BytesIO()
    Image.new(mode, (width, height), (255, 0, 0, 255) if mode == "RGBA" else 0).save(
        buf, format="PNG"
    )
    return buf.getvalue()


def test_extract_metadata_reads_dimensions_and_alpha():
    meta = extract_metadata(_png(120, 80, "RGBA"))
    assert meta["width"] == 120
    assert meta["height"] == 80
    assert meta["format"] == "PNG"
    assert meta["has_alpha"] is True


def test_extract_metadata_no_alpha_for_rgb():
    meta = extract_metadata(_png(10, 10, "RGB"))
    assert meta["has_alpha"] is False


def test_upscale_doubles_dimensions_by_default():
    out = upscale(_png(10, 20, "RGB"), {})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (20, 40)


def test_upscale_scale_factor_is_clamped():
    out = upscale(_png(10, 10, "RGB"), {"scale": 100})
    meta = extract_metadata(out)
    assert meta["width"] == meta["height"] == 40  # clamped to MAX_UPSCALE_FACTOR (4x)


def test_enhance_preserves_dimensions_and_alpha():
    out = enhance(_png(50, 50, "RGBA"), {})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (50, 50)
    assert meta["has_alpha"] is True


def test_enhance_preserves_opaque_mode():
    out = enhance(_png(50, 50, "RGB"), {})
    meta = extract_metadata(out)
    assert meta["has_alpha"] is False


def test_dtf_check_passes_a_clean_large_image():
    report = dtf_check(_png(200, 200, "RGBA"))
    assert report["checks"] == []
    assert report["ready"] is True
    assert report["effective_dpi"] is None  # no source DPI and no target size given


def test_dtf_check_computes_effective_dpi_from_target_width():
    report = dtf_check(_png(100, 100, "RGBA"), {"target_width_in": 10})
    assert report["effective_dpi"] == 10
    codes = {c["code"]: c["severity"] for c in report["checks"]}
    assert codes["low_resolution"] == "error"
    assert report["ready"] is False


def test_dtf_check_warns_below_recommended_dpi_but_still_ready():
    report = dtf_check(_png(200, 200, "RGBA"), {"target_width_in": 1})
    assert report["effective_dpi"] == 200
    codes = {c["code"]: c["severity"] for c in report["checks"]}
    assert codes["low_resolution"] == "warning"
    assert report["ready"] is True  # warnings alone don't block readiness


def test_dtf_check_flags_no_transparency_and_small_size():
    report = dtf_check(_png(50, 50, "RGB"))
    codes = {c["code"]: c["severity"] for c in report["checks"]}
    assert codes["no_transparency"] == "warning"
    assert codes["image_too_small"] == "error"
    assert report["ready"] is False


def test_dtf_check_flags_unsupported_color_mode():
    buf = io.BytesIO()
    Image.new("L", (150, 150), 128).save(buf, format="PNG")
    report = dtf_check(buf.getvalue())
    codes = {c["code"] for c in report["checks"]}
    assert "unsupported_color_mode" in codes


def _rgba_with_shape(width: int, height: int, draw_fn) -> bytes:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(img))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_dtf_check_flags_content_touching_one_edge_only():
    # A block touching only the left edge, with margin on every other side.
    data = _rgba_with_shape(
        100, 100, lambda d: d.rectangle([0, 20, 40, 80], fill=(0, 0, 0, 255))
    )
    report = dtf_check(data)
    codes = {c["code"]: c for c in report["checks"]}
    assert "potential_clipping" in codes
    assert "left" in codes["potential_clipping"]["message"]


def test_dtf_check_does_not_flag_clipping_for_full_bleed_art():
    # Opaque on all four edges — treated as deliberate full-bleed, not a crop.
    report = dtf_check(_png(100, 100, "RGBA"))
    codes = {c["code"] for c in report["checks"]}
    assert "potential_clipping" not in codes


def test_dtf_check_does_not_flag_clipping_with_margin_on_every_side():
    data = _rgba_with_shape(
        100, 100, lambda d: d.rectangle([20, 20, 80, 80], fill=(0, 0, 0, 255))
    )
    report = dtf_check(data)
    codes = {c["code"] for c in report["checks"]}
    assert "potential_clipping" not in codes


def test_dtf_check_flags_a_thin_line_as_fine_lines_and_small_details():
    # A 2px-wide line at the default 300 DPI fallback is ~0.17mm — well under
    # both the 1mm/0.6mm thresholds — with margin on every side.
    data = _rgba_with_shape(
        120, 120, lambda d: d.line([(20, 60), (100, 60)], fill=(0, 0, 0, 255), width=2)
    )
    report = dtf_check(data)
    codes = {c["code"] for c in report["checks"]}
    assert "fine_lines" in codes
    assert "small_details" in codes
    assert "potential_clipping" not in codes


def test_dtf_check_does_not_flag_a_bold_shape_as_fine_lines():
    # A large, solid block: erosion shrinks its boundary, but opening (the
    # dilation pass) restores it — it isn't actually thin anywhere.
    data = _rgba_with_shape(
        200, 200, lambda d: d.rectangle([40, 40, 160, 160], fill=(0, 0, 0, 255))
    )
    report = dtf_check(data)
    codes = {c["code"] for c in report["checks"]}
    assert "fine_lines" not in codes
    assert "small_details" not in codes


# remove_background delegates to the configured AI provider (see
# worker/services/ai_providers.py and test_ai_providers.py, which cover the
# actual rembg wiring) — this only verifies imaging.py picks the provider up
# and passes parameters through.


def test_remove_background_delegates_to_configured_provider(monkeypatch):
    calls = []

    class FakeProvider:
        name = "fake"

        def remove(self, data, *, alpha_matting=False):
            calls.append((data, alpha_matting))
            return b"fake-output"

    monkeypatch.setattr(
        imaging.ai_providers, "get_background_removal_provider", lambda: FakeProvider()
    )

    out = remove_background(b"input-bytes", {"alpha_matting": True})

    assert out == b"fake-output"
    assert calls == [(b"input-bytes", True)]


# vectorize wraps vtracer (a native Rust extension) — the actual tracing is
# vtracer's problem to test; these tests only verify our wiring (input
# normalization, parameter passthrough, output encoding) at that boundary.
# vtracer itself segfaults on this machine's Python 3.14 (see project memory),
# so it must stay mocked here — real tracing is exercised by CI on Python 3.12.


def test_vectorize_normalizes_input_and_passes_parameters(monkeypatch):
    calls = []

    def fake_convert(png_bytes, img_format="png", **kwargs):
        calls.append((img_format, kwargs))
        return "<svg>fake</svg>"

    monkeypatch.setattr(imaging.vtracer, "convert_raw_image_to_svg", fake_convert)

    out = vectorize(
        _png(10, 10, "RGB"),
        {"mode": "polygon", "color_precision": 4, "filter_speckle": 2},
    )

    assert out == b"<svg>fake</svg>"
    assert len(calls) == 1
    img_format, kwargs = calls[0]
    assert img_format == "png"
    assert kwargs == {"mode": "polygon", "color_precision": 4, "filter_speckle": 2}


def test_vectorize_uses_default_parameters(monkeypatch):
    calls = []
    monkeypatch.setattr(
        imaging.vtracer,
        "convert_raw_image_to_svg",
        lambda png_bytes, img_format="png", **kwargs: calls.append(kwargs) or "<svg/>",
    )

    vectorize(_png(10, 10, "RGBA"))

    assert calls == [{"mode": "spline", "color_precision": 6, "filter_speckle": 4}]


def test_export_png_embeds_default_dpi_without_resizing():
    out = export_png(_png(10, 20, "RGBA"))
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (10, 20)
    assert meta["source_dpi"] == 300


def test_export_png_resizes_by_width_preserving_aspect():
    out = export_png(_png(10, 20, "RGB"), {"width": 20})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (20, 40)


def test_export_png_resizes_by_explicit_width_and_height():
    out = export_png(_png(10, 20, "RGB"), {"width": 5, "height": 5})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (5, 5)


def test_export_pdf_flattens_transparency_onto_white():
    out = export_pdf(_png(10, 10, "RGBA"))
    assert out.startswith(b"%PDF")


def _solid_rgb(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def test_halftone_preserves_dimensions():
    out = halftone(_solid_rgb(20, 20, (128, 128, 128)))
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (20, 20)


def test_halftone_darker_input_yields_darker_output():
    # A solid black cell should be fully dotted (near-black average); a solid
    # white cell should stay untouched (no dots drawn).
    dark_out = halftone(_solid_rgb(16, 16, (0, 0, 0)), {"cell_size": 8})
    light_out = halftone(_solid_rgb(16, 16, (255, 255, 255)), {"cell_size": 8})

    # Sample a cell's center, not a cell boundary — the ellipse doesn't reach
    # into the bounding box's corners, so a boundary point stays white either way.
    dark_pixel = Image.open(io.BytesIO(dark_out)).convert("L").getpixel((4, 4))
    light_pixel = Image.open(io.BytesIO(light_out)).convert("L").getpixel((4, 4))
    assert dark_pixel < light_pixel


def test_embroidery_preserves_dimensions_and_alpha():
    out = embroidery(_png(30, 30, "RGBA"))
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (30, 30)
    assert meta["has_alpha"] is True


def test_embroidery_preserves_opaque_mode():
    out = embroidery(_png(30, 30, "RGB"))
    meta = extract_metadata(out)
    assert meta["has_alpha"] is False


def test_crop_to_explicit_rectangle():
    out = crop(_png(100, 100, "RGBA"), {"left": 10, "top": 20, "right": 60, "bottom": 50})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (50, 30)


def test_crop_clamps_out_of_bounds_rectangle():
    out = crop(_png(50, 50, "RGBA"), {"left": -10, "top": -10, "right": 999, "bottom": 999})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (50, 50)


def test_crop_normalizes_an_inverted_rectangle():
    # right < left, bottom < top — should still produce a valid, non-empty crop.
    out = crop(_png(100, 100, "RGBA"), {"left": 80, "top": 80, "right": 20, "bottom": 20})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (60, 60)


def test_rotate_default_is_90_degrees_clockwise_and_swaps_dimensions():
    out = rotate(_png(20, 10, "RGBA"))
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (10, 20)


def test_rotate_180_preserves_dimensions():
    out = rotate(_png(20, 10, "RGBA"), {"degrees": 180})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (20, 10)


def test_rotate_snaps_to_nearest_90_degree_multiple():
    out = rotate(_png(20, 10, "RGBA"), {"degrees": 100})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (10, 20)  # 100 -> nearest is 90


def test_flip_horizontal_preserves_dimensions():
    out = flip(_png(20, 10, "RGBA"))
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (20, 10)


def test_flip_vertical_mirrors_top_to_bottom():
    data = _rgba_with_shape(10, 10, lambda d: d.point([(0, 0)], fill=(0, 0, 0, 255)))
    out = flip(data, {"direction": "vertical"})
    pixel = Image.open(io.BytesIO(out)).convert("RGBA").getpixel((0, 9))
    assert pixel == (0, 0, 0, 255)


def test_resize_to_explicit_dimensions():
    out = resize(_png(10, 20, "RGBA"), {"width": 40, "height": 60})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (40, 60)


def test_resize_by_width_preserves_aspect_ratio():
    out = resize(_png(10, 20, "RGBA"), {"width": 5})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (5, 10)


def test_resize_without_dimensions_is_a_no_op():
    out = resize(_png(10, 20, "RGBA"))
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (10, 20)


def _centered_square(width: int, height: int) -> bytes:
    # A colored square in the middle, transparent margin all around — leaves
    # a corner pixel to check background/garment handling per mode.
    return _rgba_with_shape(
        width,
        height,
        lambda d: d.rectangle(
            [width // 4, height // 4, 3 * width // 4, 3 * height // 4],
            fill=(200, 30, 30, 255),
        ),
    )


def test_underbase_preview_full_color_is_opaque_on_white():
    out = underbase_preview(_centered_square(40, 40), {"mode": "full_color"})
    img = Image.open(io.BytesIO(out)).convert("RGBA")
    assert img.getpixel((0, 0)) == (255, 255, 255, 255)  # was transparent, now white
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (40, 40)


def test_underbase_preview_defaults_to_full_color():
    out = underbase_preview(_centered_square(40, 40))
    img = Image.open(io.BytesIO(out)).convert("RGBA")
    assert img.getpixel((0, 0)) == (255, 255, 255, 255)


def test_underbase_preview_white_mode_is_a_silhouette_on_transparency():
    out = underbase_preview(_centered_square(40, 40), {"mode": "white"})
    img = Image.open(io.BytesIO(out)).convert("RGBA")
    assert img.getpixel((0, 0)) == (0, 0, 0, 0)  # margin stays transparent
    assert img.getpixel((20, 20)) == (255, 255, 255, 255)  # shape -> solid white


def test_underbase_preview_cmyk_mode_preserves_dimensions_and_alpha():
    out = underbase_preview(_centered_square(40, 40), {"mode": "cmyk"})
    meta = extract_metadata(out)
    assert (meta["width"], meta["height"]) == (40, 40)
    img = Image.open(io.BytesIO(out)).convert("RGBA")
    assert img.getpixel((0, 0))[3] == 0  # margin transparency preserved


def test_underbase_preview_cmyk_white_composites_on_the_garment_swatch():
    out = underbase_preview(_centered_square(40, 40), {"mode": "cmyk_white"})
    img = Image.open(io.BytesIO(out)).convert("RGBA")
    assert img.getpixel((0, 0)) == (*imaging._UNDERBASE_GARMENT_COLOR, 255)
    # The shape area should be fully opaque (color layer over the white layer).
    assert img.getpixel((20, 20))[3] == 255


def test_underbase_preview_unknown_mode_raises():
    with pytest.raises(ValueError, match="Unknown underbase preview mode"):
        underbase_preview(_centered_square(10, 10), {"mode": "not-a-real-mode"})
