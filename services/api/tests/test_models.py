"""Verify all models register on the shared metadata (DB-free)."""

from __future__ import annotations

import app.db.models  # noqa: F401  (registers tables)
from app.db.base import Base

EXPECTED_TABLES = {
    "users",
    "projects",
    "artworks",
    "processing_jobs",
    "exports",
    "entitlements",
    "audit_logs",
}


def test_all_tables_registered():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_processing_job_columns():
    cols = set(Base.metadata.tables["processing_jobs"].columns.keys())
    assert {
        "project_id",
        "artwork_id",
        "result_artwork_id",
        "operation",
        "parameters",
        "status",
        "progress",
    } <= cols


def test_artwork_self_reference():
    assert "parent_artwork_id" in Base.metadata.tables["artworks"].columns


def test_entitlement_user_is_unique():
    uniques = {
        tuple(c.name for c in con.columns)
        for con in Base.metadata.tables["entitlements"].constraints
        if con.__class__.__name__ == "UniqueConstraint"
    }
    assert ("user_id",) in uniques
