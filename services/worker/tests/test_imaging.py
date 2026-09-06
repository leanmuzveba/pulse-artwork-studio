"""Unit tests for image processing helpers (needs Pillow, no broker/DB)."""

from __future__ import annotations

import io

from PIL import Image

from worker.services import imaging
from worker.services.imaging import (
    dtf_check,
    embroidery,
    enhance,
    export_pdf,
    export_png,
    extract_metadata,
    halftone,
    remove_background,
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


# remove_background wraps rembg (a real ONNX model) — the actual segmentation is
# rembg's problem to test; these tests only verify our wiring (session reuse,
# parameter passthrough) at that boundary, so no model download is needed here.


def test_remove_background_passes_input_and_parameters_through(monkeypatch):
    imaging._background_removal_session.cache_clear()
    monkeypatch.setattr(imaging.rembg, "new_session", lambda name: f"session:{name}")
    calls = []

    def fake_remove(data, session=None, alpha_matting=False):
        calls.append((data, session, alpha_matting))
        return b"fake-output"

    monkeypatch.setattr(imaging.rembg, "remove", fake_remove)

    out = remove_background(b"input-bytes", {"alpha_matting": True})

    assert out == b"fake-output"
    assert calls == [(b"input-bytes", "session:u2net", True)]


def test_remove_background_reuses_cached_session(monkeypatch):
    imaging._background_removal_session.cache_clear()
    session_calls = []
    monkeypatch.setattr(
        imaging.rembg, "new_session", lambda name: session_calls.append(name) or "sess"
    )
    monkeypatch.setattr(
        imaging.rembg, "remove", lambda data, session=None, alpha_matting=False: b"x"
    )

    remove_background(b"a")
    remove_background(b"b")

    assert len(session_calls) == 1


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
