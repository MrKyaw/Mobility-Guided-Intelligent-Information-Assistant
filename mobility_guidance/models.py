"""Typed scene model for the offline mobility guidance pipeline."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class SceneError(ValueError):
    """Raised when a scene or detection payload is malformed."""


class HazardLevel(str, Enum):
    """Ordered urgency levels used for sorting and reporting."""

    INFO = "info"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {
            HazardLevel.INFO: 0,
            HazardLevel.CAUTION: 1,
            HazardLevel.WARNING: 2,
            HazardLevel.CRITICAL: 3,
        }[self]


@dataclass(frozen=True)
class SceneObject:
    """One detected object in a frame."""

    label: str
    confidence: float
    distance_m: float | None = None
    bearing_deg: float = 0.0
    closing_speed_mps: float = 0.0
    in_path: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise SceneError("label must be a non-empty string")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise SceneError("confidence must be a number")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise SceneError("confidence must be between 0 and 1")
        if self.distance_m is not None:
            if isinstance(self.distance_m, bool) or not isinstance(self.distance_m, (int, float)):
                raise SceneError("distance_m must be a number or None")
            if not math.isfinite(float(self.distance_m)) or self.distance_m < 0:
                raise SceneError("distance_m must be finite and >= 0")
        if not -180.0 <= float(self.bearing_deg) <= 180.0:
            raise SceneError("bearing_deg must be between -180 and 180")
        if not math.isfinite(float(self.closing_speed_mps)):
            raise SceneError("closing_speed_mps must be finite")
        if not isinstance(self.in_path, bool):
            raise SceneError("in_path must be a boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SceneObject":
        if not isinstance(payload, Mapping):
            raise SceneError("object must be a JSON object")
        if "label" not in payload or "confidence" not in payload:
            raise SceneError("object requires label and confidence")
        try:
            return cls(
                label=payload["label"],
                confidence=payload["confidence"],
                distance_m=payload.get("distance_m"),
                bearing_deg=payload.get("bearing_deg", 0.0),
                closing_speed_mps=payload.get("closing_speed_mps", 0.0),
                in_path=payload.get("in_path", False),
            )
        except SceneError:
            raise
        except (TypeError, ValueError) as exc:
            raise SceneError(f"invalid object: {exc}") from exc


@dataclass(frozen=True)
class Frame:
    """A timestamped snapshot of the scene."""

    timestamp_s: float
    objects: tuple[SceneObject, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.timestamp_s, bool) or not isinstance(self.timestamp_s, (int, float)):
            raise SceneError("timestamp_s must be a number")
        if not math.isfinite(float(self.timestamp_s)) or self.timestamp_s < 0:
            raise SceneError("timestamp_s must be finite and >= 0")
        if not isinstance(self.objects, tuple):
            raise SceneError("objects must be a tuple of SceneObject")
        for obj in self.objects:
            if not isinstance(obj, SceneObject):
                raise SceneError("objects must contain SceneObject instances")
        if not isinstance(self.description, str):
            raise SceneError("description must be a string")

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_s": self.timestamp_s,
            "description": self.description,
            "objects": [
                {
                    "label": obj.label,
                    "confidence": obj.confidence,
                    "distance_m": obj.distance_m,
                    "bearing_deg": obj.bearing_deg,
                    "closing_speed_mps": obj.closing_speed_mps,
                    "in_path": obj.in_path,
                }
                for obj in self.objects
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Frame":
        if not isinstance(payload, Mapping):
            raise SceneError("frame must be a JSON object")
        if "timestamp_s" not in payload:
            raise SceneError("frame requires timestamp_s")
        raw_objects = payload.get("objects", [])
        if not isinstance(raw_objects, list):
            raise SceneError("objects must be a list")
        return cls(
            timestamp_s=payload["timestamp_s"],
            objects=tuple(SceneObject.from_dict(item) for item in raw_objects),
            description=payload.get("description", ""),
        )


@dataclass(frozen=True)
class Guidance:
    """One prioritised spoken guidance message."""

    timestamp_s: float
    level: HazardLevel
    message: str
    object_labels: tuple[str, ...]
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_s": self.timestamp_s,
            "level": self.level.value,
            "message": self.message,
            "object_labels": list(self.object_labels),
            "reasons": list(self.reasons),
        }
