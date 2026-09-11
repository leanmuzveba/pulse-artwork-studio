"""Domain enums.

Stored as short strings (``native_enum=False``) so adding a value never needs a
Postgres enum migration. Validation happens at the application layer.
"""

from __future__ import annotations

from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ArtworkKind(str, Enum):
    ORIGINAL = "original"   # immutable source upload
    DERIVED = "derived"     # produced by a processing operation


class ArtworkStatus(str, Enum):
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class JobStatus(str, Enum):
    REQUESTED = "requested"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobOperation(str, Enum):
    METADATA = "metadata"
    ENHANCE = "enhance"
    UPSCALE = "upscale"
    BACKGROUND_REMOVAL = "background_removal"
    VECTORIZE = "vectorize"
    HALFTONE = "halftone"
    EMBROIDERY = "embroidery"
    DTF_CHECK = "dtf_check"
    CROP = "crop"
    ROTATE = "rotate"
    FLIP = "flip"
    RESIZE = "resize"
    UNDERBASE_PREVIEW = "underbase_preview"


class ExportFormat(str, Enum):
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"


class ExportStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class PlanTier(str, Enum):
    FREE = "free"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
