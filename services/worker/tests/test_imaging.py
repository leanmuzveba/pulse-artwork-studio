"""Unit tests for image processing helpers (needs Pillow, no broker/DB)."""

from __future__ import annotations

import io

from PIL import Image

from worker.services import imaging
from worker.services.imaging import enhance, extract_metadata, remove_background, upscale


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
