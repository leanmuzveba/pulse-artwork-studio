"""AI provider adapters.

A stable interface between processing operations (worker/services/imaging.py)
and the underlying AI models/services that implement them, so a provider can
be swapped or a new one added without touching the operation's calling code.
All provider configuration — including any future remote API keys — is read
server-side only, from worker/config.py; it never reaches the Flutter client.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import rembg

from worker.config import get_settings


class BackgroundRemovalProvider(Protocol):
    """Removes an image's background, returning a transparent PNG."""

    name: str

    def remove(self, data: bytes, *, alpha_matting: bool = False) -> bytes: ...


@lru_cache(maxsize=1)
def _rembg_session():
    """Load the U^2-Net model once per worker process and reuse it across jobs."""
    return rembg.new_session("u2net")


class RembgBackgroundRemovalProvider:
    """Local, on-CPU background removal via rembg's U^2-Net model.

    No network call and no API key — this is the default provider.
    """

    name = "rembg_local"

    def remove(self, data: bytes, *, alpha_matting: bool = False) -> bytes:
        return rembg.remove(data, session=_rembg_session(), alpha_matting=alpha_matting)


_BACKGROUND_REMOVAL_PROVIDERS: dict[str, BackgroundRemovalProvider] = {
    "rembg_local": RembgBackgroundRemovalProvider(),
}


def get_background_removal_provider(name: str | None = None) -> BackgroundRemovalProvider:
    """Look up the configured background-removal provider.

    Defaults to `settings.ai_background_removal_provider`. Raises `ValueError`
    for an unregistered name rather than silently falling back to the default.
    """
    name = name or get_settings().ai_background_removal_provider
    try:
        return _BACKGROUND_REMOVAL_PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown background-removal provider: {name!r}") from None
