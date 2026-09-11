"""Image analysis and transform helpers. Pure functions — no Celery/DB imports,
easy to test in isolation."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import vtracer
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat

from worker.services import ai_providers

# Upscale is capped to avoid a single job exhausting worker memory/CPU.
MAX_UPSCALE_FACTOR = 4.0
MAX_UPSCALE_DIMENSION = 8000

# Halftone dot-cell size (px), clamped to keep it a deliberate stylistic choice.
MIN_HALFTONE_CELL = 2
MAX_HALFTONE_CELL = 40

# DTF print-readiness thresholds.
DTF_RECOMMENDED_DPI = 300
DTF_MIN_ACCEPTABLE_DPI = 150
DTF_MIN_DIMENSION_PX = 100

# Real-world stroke/detail width below which DTF printing risks dropout or
# blur — used by the fine-lines / small-details checks below.
DTF_MIN_LINE_WIDTH_MM = 1.0
DTF_MIN_DETAIL_WIDTH_MM = 0.6
_MM_PER_INCH = 25.4


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _alpha_mask(img: Image.Image) -> Image.Image:
    """Return an "L" mask of non-transparent pixels (255 opaque, 0 transparent).

    Images with no real alpha channel are treated as fully opaque.
    """
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    if not has_alpha:
        return Image.new("L", img.size, 255)
    alpha = img.convert("RGBA").getchannel("A")
    return alpha.point(lambda a: 255 if a > 16 else 0)


def _opaque_pixel_count(mask: Image.Image) -> float:
    # Stat.sum on an "L" mask of only {0, 255} values is a fast (C-side) way
    # to count opaque pixels without a Python-level loop over every pixel.
    return ImageStat.Stat(mask).sum[0] / 255.0


def _touching_edges(mask: Image.Image) -> set[str]:
    """Which canvas edges the opaque content's bounding box reaches."""
    bbox = mask.getbbox()
    if bbox is None:
        return set()
    left, top, right, bottom = bbox
    width, height = mask.size
    edges = set()
    if left <= 0:
        edges.add("left")
    if top <= 0:
        edges.add("top")
    if right >= width:
        edges.add("right")
    if bottom >= height:
        edges.add("bottom")
    return edges


def _detail_loss_ratio(mask: Image.Image, kernel_px: int) -> float:
    """Fraction of opaque pixels lost to a morphological *opening* (erode then
    dilate) at `kernel_px` — the standard technique for finding features
    narrower than a given width without also flagging bulky shapes.

    Erosion alone shrinks every shape's boundary regardless of its size, which
    would flag any modestly-sized solid shape as "thin". Opening's dilation
    pass grows a shape back out afterward, so a bulky shape (wider than the
    kernel) is restored to ~its original size while a thin one (narrower than
    the kernel), having been eroded away to nothing, stays gone. PIL's rank
    filters extend the canvas edge by replication, so this measures loss
    against the artwork's *internal* transparent boundaries only, not the
    canvas edge (that's `_touching_edges`'s job instead).
    """
    if kernel_px < 3:
        return 0.0
    if kernel_px % 2 == 0:
        kernel_px += 1
    before = _opaque_pixel_count(mask)
    if before == 0:
        return 0.0
    opened = mask.filter(ImageFilter.MinFilter(kernel_px)).filter(
        ImageFilter.MaxFilter(kernel_px)
    )
    after = _opaque_pixel_count(opened)
    return max(0.0, (before - after) / before)


def _mm_to_px(mm: float, dpi: int) -> int:
    return max(1, round(mm / _MM_PER_INCH * dpi))


def extract_metadata(data: bytes) -> dict[str, Any]:
    """Read basic image metadata from raw bytes.

    Returns width/height in pixels, the format and mode, whether the image has
    an alpha channel (transparency), and the embedded DPI if present.
    """
    with Image.open(BytesIO(data)) as img:
        dpi = img.info.get("dpi")
        source_dpi = round(dpi[0]) if dpi else None
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "has_alpha": bool(has_alpha),
            "source_dpi": source_dpi,
        }


def dtf_check(data: bytes, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analyze an artwork for DTF print-readiness (the "AI Inspector").

    Analysis only — no image is produced. Optional `parameters.target_width_in`
    / `target_height_in` (inches) let the effective print DPI be computed from
    the intended print size; otherwise the file's embedded DPI is used.

    Returns the base metadata plus `effective_dpi`, a `checks` list of
    `{code, severity, message}` (severity "warning" or "error"), and an overall
    `ready` flag (false if any check is an "error"). Also runs print-specific
    checks — `potential_clipping` (content reaching the canvas edge),
    `fine_lines` and `small_details` (content thinner than DTF can reliably
    reproduce, estimated at the effective DPI). The line/detail checks are a
    heuristic (erosion-based detail-loss proxy), not real OCR or vector
    analysis — advisory, like every other check here.
    """
    parameters = parameters or {}
    meta = extract_metadata(data)

    effective_dpi = meta["source_dpi"]
    target_width_in = parameters.get("target_width_in")
    target_height_in = parameters.get("target_height_in")
    if target_width_in:
        effective_dpi = round(meta["width"] / float(target_width_in))
    elif target_height_in:
        effective_dpi = round(meta["height"] / float(target_height_in))

    checks: list[dict[str, str]] = []

    if effective_dpi is not None and effective_dpi < DTF_MIN_ACCEPTABLE_DPI:
        checks.append(
            {
                "code": "low_resolution",
                "severity": "error",
                "message": f"Effective resolution is {effective_dpi} DPI; "
                f"DTF printing needs at least {DTF_MIN_ACCEPTABLE_DPI} DPI.",
            }
        )
    elif effective_dpi is not None and effective_dpi < DTF_RECOMMENDED_DPI:
        checks.append(
            {
                "code": "low_resolution",
                "severity": "warning",
                "message": f"Effective resolution is {effective_dpi} DPI; "
                f"{DTF_RECOMMENDED_DPI} DPI is recommended for crisp DTF prints.",
            }
        )

    if not meta["has_alpha"]:
        checks.append(
            {
                "code": "no_transparency",
                "severity": "warning",
                "message": "No transparency detected — run background removal "
                "before printing, unless a full-bleed background is intended.",
            }
        )

    if meta["mode"] not in ("RGB", "RGBA"):
        checks.append(
            {
                "code": "unsupported_color_mode",
                "severity": "warning",
                "message": f"Image is in {meta['mode']} mode; convert to RGB/RGBA.",
            }
        )

    if meta["width"] < DTF_MIN_DIMENSION_PX or meta["height"] < DTF_MIN_DIMENSION_PX:
        checks.append(
            {
                "code": "image_too_small",
                "severity": "error",
                "message": f"Image is {meta['width']}x{meta['height']}px; "
                f"at least {DTF_MIN_DIMENSION_PX}x{DTF_MIN_DIMENSION_PX}px is needed.",
            }
        )

    with Image.open(BytesIO(data)) as img:
        img.load()
        mask = _alpha_mask(img)

    touching = _touching_edges(mask)
    if touching and len(touching) < 4:
        checks.append(
            {
                "code": "potential_clipping",
                "severity": "warning",
                "message": f"Artwork content reaches the {', '.join(sorted(touching))} "
                "edge of the canvas and may be clipped when printed — add a small "
                "transparent margin around the design.",
            }
        )

    # Only meaningful when the canvas has a genuine mix of opaque/transparent
    # pixels — a fully solid or fully empty canvas has no internal detail for
    # erosion to measure, and would otherwise report a spurious 0% loss.
    opaque_count = _opaque_pixel_count(mask)
    if 0 < opaque_count < mask.width * mask.height:
        dpi_for_detail = effective_dpi or DTF_RECOMMENDED_DPI

        fine_line_kernel = _mm_to_px(DTF_MIN_LINE_WIDTH_MM, dpi_for_detail)
        if _detail_loss_ratio(mask, fine_line_kernel) > 0.10:
            checks.append(
                {
                    "code": "fine_lines",
                    "severity": "warning",
                    "message": f"Some strokes appear thinner than the "
                    f"~{DTF_MIN_LINE_WIDTH_MM:.1f}mm DTF can reliably print at "
                    f"{dpi_for_detail} DPI; thin lines may drop out or blur.",
                }
            )

        detail_kernel = _mm_to_px(DTF_MIN_DETAIL_WIDTH_MM, dpi_for_detail)
        if _detail_loss_ratio(mask, detail_kernel) > 0.03:
            checks.append(
                {
                    "code": "small_details",
                    "severity": "warning",
                    "message": "Small text or fine details thinner than "
                    f"~{DTF_MIN_DETAIL_WIDTH_MM:.1f}mm were detected; they may not "
                    "print cleanly. Consider enlarging small text before printing.",
                }
            )

    ready = not any(c["severity"] == "error" for c in checks)
    return {**meta, "effective_dpi": effective_dpi, "checks": checks, "ready": ready}


def enhance(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Auto-enhance an image: contrast stretch plus a mild sharpen/contrast/color
    boost. Transparency (if any) is preserved untouched — only RGB is adjusted.

    Optional `parameters`: `sharpness`, `contrast`, `color` — multipliers around
    1.0, each clamped to [0.5, 2.0].
    """
    parameters = parameters or {}
    sharpness = _clamp(float(parameters.get("sharpness", 1.3)), 0.5, 2.0)
    contrast = _clamp(float(parameters.get("contrast", 1.1)), 0.5, 2.0)
    color = _clamp(float(parameters.get("color", 1.05)), 0.5, 2.0)

    with Image.open(BytesIO(data)) as img:
        img.load()
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        rgba = img.convert("RGBA")
        rgb = rgba.convert("RGB")
        alpha = rgba.getchannel("A")

        rgb = ImageOps.autocontrast(rgb, cutoff=1)
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
        rgb = ImageEnhance.Color(rgb).enhance(color)
        rgb = ImageEnhance.Sharpness(rgb).enhance(sharpness)

        out = BytesIO()
        if has_alpha:
            result = rgb.convert("RGBA")
            result.putalpha(alpha)
            result.save(out, format="PNG")
        else:
            rgb.save(out, format="PNG")
        return out.getvalue()


def upscale(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Upscale an image with high-quality (Lanczos) resampling.

    Optional `parameters.scale` (default 2.0) multiplies both dimensions,
    clamped to [1.0, `MAX_UPSCALE_FACTOR`]; the output is additionally capped at
    `MAX_UPSCALE_DIMENSION` px per side regardless of the requested scale.
    """
    parameters = parameters or {}
    scale = _clamp(float(parameters.get("scale", 2.0)), 1.0, MAX_UPSCALE_FACTOR)

    with Image.open(BytesIO(data)) as img:
        img.load()
        target_w = min(round(img.width * scale), MAX_UPSCALE_DIMENSION)
        target_h = min(round(img.height * scale), MAX_UPSCALE_DIMENSION)
        resized = img.resize((max(target_w, 1), max(target_h, 1)), Image.LANCZOS)

        out = BytesIO()
        resized.save(out, format="PNG")
        return out.getvalue()


def crop(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Crop to a pixel rectangle.

    Optional `parameters`: `left`, `top`, `right`, `bottom` (px; default to
    the image's own edges). Values are clamped to the image bounds and
    normalized so the rectangle is never inverted or empty.
    """
    parameters = parameters or {}
    with Image.open(BytesIO(data)) as img:
        img.load()
        width, height = img.size
        left = int(_clamp(float(parameters.get("left", 0)), 0, width))
        top = int(_clamp(float(parameters.get("top", 0)), 0, height))
        right = int(_clamp(float(parameters.get("right", width)), 0, width))
        bottom = int(_clamp(float(parameters.get("bottom", height)), 0, height))
        left, right = sorted((left, right))
        top, bottom = sorted((top, bottom))
        if right - left < 1:
            right = left + 1
        if bottom - top < 1:
            bottom = top + 1
        cropped = img.crop((left, top, right, bottom))

        out = BytesIO()
        cropped.save(out, format="PNG")
        return out.getvalue()


def rotate(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Rotate clockwise by a multiple of 90 degrees (default 90).

    Optional `parameters.degrees` is rounded to the nearest multiple of 90.
    The canvas expands to fit the rotated image, so nothing is cropped off.
    """
    parameters = parameters or {}
    degrees = round(float(parameters.get("degrees", 90)) / 90.0) * 90 % 360

    with Image.open(BytesIO(data)) as img:
        img.load()
        # PIL's Image.rotate() turns counter-clockwise for a positive angle;
        # the editor's "rotate" convention is clockwise, hence the negation.
        rotated = img.rotate(-degrees, expand=True) if degrees else img.copy()

        out = BytesIO()
        rotated.save(out, format="PNG")
        return out.getvalue()


def flip(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Mirror the image.

    Optional `parameters.direction`: "horizontal" (default, left-right
    mirror) or "vertical" (top-bottom mirror).
    """
    parameters = parameters or {}
    direction = parameters.get("direction", "horizontal")

    with Image.open(BytesIO(data)) as img:
        img.load()
        flipped = (
            img.transpose(Image.FLIP_TOP_BOTTOM)
            if direction == "vertical"
            else img.transpose(Image.FLIP_LEFT_RIGHT)
        )

        out = BytesIO()
        flipped.save(out, format="PNG")
        return out.getvalue()


def resize(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Resize to explicit pixel dimensions.

    Unlike `upscale`, this isn't scale-based or capped to
    `MAX_UPSCALE_FACTOR` — it's a direct editor resize (up or down). Optional
    `parameters`: `width`/`height` (px; if only one is given, the other is
    scaled to preserve aspect ratio). With neither given, the image is
    returned unchanged.
    """
    parameters = parameters or {}
    target_w = parameters.get("width")
    target_h = parameters.get("height")

    with Image.open(BytesIO(data)) as img:
        img.load()
        if target_w or target_h:
            orig_w, orig_h = img.width, img.height
            if target_w and not target_h:
                target_h = round(orig_h * (float(target_w) / orig_w))
            elif target_h and not target_w:
                target_w = round(orig_w * (float(target_h) / orig_h))
            img = img.resize((max(int(target_w), 1), max(int(target_h), 1)), Image.LANCZOS)

        out = BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()


def remove_background(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Remove the background, producing a transparent PNG.

    Delegates to the configured background-removal AI provider (see
    `worker/services/ai_providers.py`) — defaults to rembg/U^2-Net, running
    locally with no external API call. Optional `parameters.alpha_matting`
    (bool, default False) trades speed for softer edges on foreground objects
    with fine detail (hair, fur).
    """
    parameters = parameters or {}
    alpha_matting = bool(parameters.get("alpha_matting", False))
    provider = ai_providers.get_background_removal_provider()
    return provider.remove(data, alpha_matting=alpha_matting)


def vectorize(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Trace a raster image into a real path-based SVG (via vtracer).

    The input is normalized to RGBA PNG first (vtracer needs a raw pixel
    format it understands), then traced. Optional `parameters`: `mode`
    ("spline", "polygon", or "none"; default "spline"), `color_precision`
    (default 6), `filter_speckle` (default 4, suppresses tiny noise regions).

    Returns UTF-8-encoded SVG markup, not a raster image.
    """
    parameters = parameters or {}
    mode = parameters.get("mode", "spline")
    color_precision = int(parameters.get("color_precision", 6))
    filter_speckle = int(parameters.get("filter_speckle", 4))

    with Image.open(BytesIO(data)) as img:
        img.load()
        png_buf = BytesIO()
        img.convert("RGBA").save(png_buf, format="PNG")
        png_bytes = png_buf.getvalue()

    svg = vtracer.convert_raw_image_to_svg(
        png_bytes,
        img_format="png",
        mode=mode,
        color_precision=color_precision,
        filter_speckle=filter_speckle,
    )
    return svg.encode("utf-8")


def export_png(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Re-encode an image as PNG for export, optionally resizing and embedding DPI.

    Optional `parameters`: `width`/`height` (px; resize with the other
    dimension scaled to preserve aspect ratio if only one is given), `dpi`
    (embedded resolution metadata, default 300).
    """
    parameters = parameters or {}
    dpi = int(parameters.get("dpi", 300))
    target_w = parameters.get("width")
    target_h = parameters.get("height")

    with Image.open(BytesIO(data)) as img:
        img.load()
        if target_w or target_h:
            orig_w, orig_h = img.width, img.height
            if target_w and not target_h:
                target_h = round(orig_h * (float(target_w) / orig_w))
            elif target_h and not target_w:
                target_w = round(orig_w * (float(target_h) / orig_h))
            img = img.resize((max(int(target_w), 1), max(int(target_h), 1)), Image.LANCZOS)

        out = BytesIO()
        img.save(out, format="PNG", dpi=(dpi, dpi))
        return out.getvalue()


def export_pdf(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Convert an image to a single-page PDF for export.

    Transparency is flattened onto a white background, since PDF has no alpha
    channel. Optional `parameters.dpi` (default 300) sets the embedded
    resolution.
    """
    parameters = parameters or {}
    dpi = int(parameters.get("dpi", 300))

    with Image.open(BytesIO(data)) as img:
        img.load()
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))

        out = BytesIO()
        background.save(out, format="PDF", resolution=dpi)
        return out.getvalue()



# Neutral dark backdrop standing in for a garment, so a "printed on dark
# fabric" preview has something to show the white underbase layer against.
_UNDERBASE_GARMENT_COLOR = (60, 60, 64)


def _composite_on_white(rgba: Image.Image) -> Image.Image:
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    background.alpha_composite(rgba)
    return background


def _posterized_cmyk(rgb: Image.Image, step: int = 32) -> Image.Image:
    """Quantize each CMYK ink channel to coarse steps. 4-color process
    printing can't render a full continuous-tone gradient the way an RGB
    screen can, so this gives a rough "printed ink" look, not a color-managed
    conversion."""
    cmyk = rgb.convert("CMYK")
    bands = [b.point(lambda v: min(255, round(v / step) * step)) for b in cmyk.split()]
    return Image.merge("CMYK", bands).convert("RGB")


def _simulate_cmyk(rgba: Image.Image) -> Image.Image:
    """The artwork with a CMYK-process ink look, its original alpha intact."""
    posterized = _posterized_cmyk(_composite_on_white(rgba).convert("RGB"))
    result = posterized.convert("RGBA")
    result.putalpha(rgba.getchannel("A"))
    return result


def _white_underbase_layer(alpha: Image.Image) -> Image.Image:
    """The alpha channel rendered as a solid white silhouette — what a DTF
    printer's white-ink layer looks like underneath the color layer."""
    mask = alpha.point(lambda a: 255 if a > 16 else 0)
    white = Image.new("RGBA", alpha.size, (255, 255, 255, 255))
    empty = Image.new("RGBA", alpha.size, (0, 0, 0, 0))
    return Image.composite(white, empty, mask)


def underbase_preview(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Render a DTF print-layer preview.

    A visual simulation only — not a RIP replacement or a color-accurate
    proof. Optional `parameters.mode`: "full_color" (default, on a white
    background), "cmyk" (posterized ink-channel approximation), "white" (the
    white-ink underbase layer alone, as a silhouette on transparency), or
    "cmyk_white" (both layers composited over a dark garment swatch,
    simulating a print on dark fabric).
    """
    parameters = parameters or {}
    mode = parameters.get("mode", "full_color")
    if mode not in ("full_color", "cmyk", "white", "cmyk_white"):
        raise ValueError(f"Unknown underbase preview mode: {mode!r}")

    with Image.open(BytesIO(data)) as img:
        img.load()
        rgba = img.convert("RGBA")

        if mode == "full_color":
            result = _composite_on_white(rgba)
        elif mode == "cmyk":
            result = _simulate_cmyk(rgba)
        elif mode == "white":
            result = _white_underbase_layer(rgba.getchannel("A"))
        else:  # cmyk_white
            garment = Image.new("RGBA", rgba.size, (*_UNDERBASE_GARMENT_COLOR, 255))
            garment.alpha_composite(_white_underbase_layer(rgba.getchannel("A")))
            garment.alpha_composite(_simulate_cmyk(rgba))
            result = garment

        out = BytesIO()
        result.save(out, format="PNG")
        return out.getvalue()


def halftone(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Apply a classic dot-screen halftone effect (black dots on white).

    Grayscale only — screen-printing-style halftones are single-color layers,
    so any transparency is flattened away. Optional `parameters.cell_size`
    (px per dot cell, default 8, clamped to
    [`MIN_HALFTONE_CELL`, `MAX_HALFTONE_CELL`]) sets dot density: smaller
    cells mean finer, more detailed dots.
    """
    parameters = parameters or {}
    cell_size = int(_clamp(float(parameters.get("cell_size", 8)), MIN_HALFTONE_CELL, MAX_HALFTONE_CELL))

    with Image.open(BytesIO(data)) as img:
        img.load()
        gray = img.convert("L")
        width, height = gray.size

        canvas = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(canvas)

        for y in range(0, height, cell_size):
            for x in range(0, width, cell_size):
                cell = gray.crop((x, y, min(x + cell_size, width), min(y + cell_size, height)))
                brightness = ImageStat.Stat(cell).mean[0] / 255.0
                radius = (1.0 - brightness) * (cell_size / 2.0)
                if radius > 0.5:
                    cx, cy = x + cell_size / 2, y + cell_size / 2
                    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=0)

        out = BytesIO()
        canvas.convert("RGB").save(out, format="PNG")
        return out.getvalue()


def embroidery(data: bytes, parameters: dict[str, Any] | None = None) -> bytes:
    """Apply a stylized embroidery-look visual effect.

    Preview only — this does not generate real machine stitch/digitizing
    data. Posterizes the color palette (simulating a limited thread-color
    count) and blends in a subtle emboss texture to suggest raised stitching.
    Transparency is preserved. Optional `parameters.color_levels` (bits kept
    per channel, default 4, clamped to [2, 8]) controls how aggressively
    colors are posterized — lower means fewer, flatter "thread" colors.
    """
    parameters = parameters or {}
    color_levels = int(_clamp(float(parameters.get("color_levels", 4)), 2, 8))

    with Image.open(BytesIO(data)) as img:
        img.load()
        has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        rgba = img.convert("RGBA")
        rgb = rgba.convert("RGB")
        alpha = rgba.getchannel("A")

        posterized = ImageOps.posterize(rgb, color_levels)
        emboss = rgb.filter(ImageFilter.EMBOSS).convert("RGB")
        stitched = Image.blend(posterized, emboss, alpha=0.25)

        out = BytesIO()
        if has_alpha:
            result = stitched.convert("RGBA")
            result.putalpha(alpha)
            result.save(out, format="PNG")
        else:
            stitched.save(out, format="PNG")
        return out.getvalue()
