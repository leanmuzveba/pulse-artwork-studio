"""Unit tests for the AI provider registry (needs no model download)."""

from __future__ import annotations

import pytest

from worker.services import ai_providers
from worker.services.ai_providers import (
    RembgBackgroundRemovalProvider,
    get_background_removal_provider,
)


def test_default_provider_is_rembg_local():
    provider = get_background_removal_provider()
    assert isinstance(provider, RembgBackgroundRemovalProvider)
    assert provider.name == "rembg_local"


def test_get_provider_respects_settings_override(monkeypatch):
    class FakeSettings:
        ai_background_removal_provider = "rembg_local"

    monkeypatch.setattr(ai_providers, "get_settings", lambda: FakeSettings())
    assert get_background_removal_provider().name == "rembg_local"


def test_unknown_provider_name_raises():
    with pytest.raises(ValueError, match="Unknown background-removal provider"):
        get_background_removal_provider("not-a-real-provider")


# rembg wraps a real ONNX model — the actual segmentation is rembg's problem to
# test; these tests only verify our wiring (session reuse, parameter
# passthrough) at that boundary, so no model download is needed here.


def test_rembg_provider_passes_input_and_parameters_through(monkeypatch):
    ai_providers._rembg_session.cache_clear()
    monkeypatch.setattr(ai_providers.rembg, "new_session", lambda name: f"session:{name}")
    calls = []

    def fake_remove(data, session=None, alpha_matting=False):
        calls.append((data, session, alpha_matting))
        return b"fake-output"

    monkeypatch.setattr(ai_providers.rembg, "remove", fake_remove)

    out = RembgBackgroundRemovalProvider().remove(b"input-bytes", alpha_matting=True)

    assert out == b"fake-output"
    assert calls == [(b"input-bytes", "session:u2net", True)]


def test_rembg_provider_reuses_cached_session(monkeypatch):
    ai_providers._rembg_session.cache_clear()
    session_calls = []
    monkeypatch.setattr(
        ai_providers.rembg, "new_session", lambda name: session_calls.append(name) or "sess"
    )
    monkeypatch.setattr(
        ai_providers.rembg, "remove", lambda data, session=None, alpha_matting=False: b"x"
    )

    provider = RembgBackgroundRemovalProvider()
    provider.remove(b"a")
    provider.remove(b"b")

    assert len(session_calls) == 1
