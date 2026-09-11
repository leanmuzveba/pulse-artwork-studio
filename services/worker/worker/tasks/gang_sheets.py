"""Gang sheet composition tasks.

Mirrors exports.py's design: the worker is stateless — it downloads each
source artwork, auto-nests them, composites the result, uploads it, and
returns its location plus the placement of every tile. The API reconciles
that into the gang_sheets row on poll.
"""

from __future__ import annotations

from typing import Any

from worker.celery_app import celery_app
from worker.config import get_settings
from worker.services import gang_sheet, storage


@celery_app.task(name="gang_sheets.run", bind=True)
def run(
    self,
    gang_sheet_id: str,
    project_id: str,
    sheet_width_px: int,
    spacing_px: int,
    dpi: int,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Download each item's artwork, auto-nest, and composite one gang sheet.

    `items`: `[{artwork_id, bucket, key, copies, rotate_deg}, ...]`.
    """
    self.update_state(state="STARTED", meta={"gang_sheet_id": gang_sheet_id})

    tiles: list[tuple[str, bytes, int]] = []
    for item in items:
        data = storage.download_bytes(item["bucket"], item["key"])
        copies = max(1, int(item.get("copies", 1)))
        rotate_deg = int(item.get("rotate_deg", 0))
        tiles.extend((item["artwork_id"], data, rotate_deg) for _ in range(copies))

    output, placements, sheet_height_px = gang_sheet.compose_gang_sheet(
        tiles, sheet_width_px=sheet_width_px, spacing_px=spacing_px
    )

    settings = get_settings()
    out_bucket = settings.s3_bucket_exports
    out_key = f"projects/{project_id}/gang-sheets/{gang_sheet_id}.png"
    storage.upload_bytes(out_bucket, out_key, output, "image/png")

    return {
        "bucket": out_bucket,
        "key": out_key,
        "mime_type": "image/png",
        "size_bytes": len(output),
        "sheet_width_px": sheet_width_px,
        "sheet_height_px": sheet_height_px,
        "dpi": dpi,
        "placements": placements,
    }
