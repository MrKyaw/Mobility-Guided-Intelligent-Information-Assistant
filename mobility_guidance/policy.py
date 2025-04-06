"""Explainable hazard scoring for mobility guidance."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Frame, HazardLevel, SceneObject

CLASS_WEIGHTS: dict[str, float] = {
    "pedestrian": 1.8,
    "cyclist": 1.6,
    "motorcycle": 1.5,
    "truck": 1.4,
    "bus": 1.4,
    "dog": 1.3,
    "car": 1.2,
    "stop sign": 1.0,
    "traffic light": 0.9,
}
DEFAULT_WEIGHT = 1.0


@dataclass(frozen=True)
class Assessment:
    """Risk assessment for one object."""

    obj: SceneObject
    score: float
    level: HazardLevel
    time_to_contact_s: float | None
    reasons: tuple[str, ...]

    @property
    def label(self) -> str:
        return self.obj.label


class SafetyPolicy:
    """Deterministic, explainable risk scoring.

    The score combines class risk, detector confidence, proximity, whether the
    object is in the travel path, and closing speed. Time-to-contact can force
    a critical level even when the aggregate score is lower.
    """

    def __init__(
        self,
        *,
        caution_score: float = 1.2,
        warning_score: float = 2.5,
        critical_score: float = 4.0,
    ) -> None:
        if not 0 < caution_score < warning_score < critical_score:
            raise ValueError("score thresholds must satisfy 0 < caution < warning < critical")
        self.caution_score = caution_score
        self.warning_score = warning_score
        self.critical_score = critical_score

    def assess(self, obj: SceneObject) -> Assessment:
        reasons: list[str] = []
        weight = CLASS_WEIGHTS.get(obj.label.lower(), DEFAULT_WEIGHT)
        if weight > 1.2:
            reasons.append(f"high-risk class ({obj.label})")

        distance = obj.distance_m
        if distance is None:
            proximity = 0.8
            reasons.append("distance unavailable")
        elif distance <= 1.5:
            proximity = 2.2
            reasons.append(f"{distance:.1f} m away")
        elif distance <= 3.0:
            proximity = 1.6
            reasons.append(f"{distance:.1f} m away")
        elif distance <= 6.0:
            proximity = 1.1
            reasons.append(f"{distance:.1f} m away")
        else:
            proximity = 0.7
            reasons.append(f"{distance:.1f} m away")

        path_factor = 1.6 if obj.in_path else 1.0
        if obj.in_path:
            reasons.append("in travel path")

        closing = max(0.0, float(obj.closing_speed_mps))
        speed_factor = 1.0 + min(closing / 4.0, 1.0)
        if closing > 0:
            reasons.append(f"closing at {closing:.1f} m/s")

        confidence_factor = float(obj.confidence)
        if confidence_factor < 0.5:
            reasons.append("low detector confidence")
            confidence_factor *= 0.7

        ttc: float | None = None
        if distance is not None and closing > 0:
            ttc = round(distance / closing, 2)

        score = round(weight * confidence_factor * proximity * path_factor * speed_factor, 2)
        if ttc is not None and ttc <= 1.5:
            level = HazardLevel.CRITICAL
            reasons.append(f"time to contact {ttc:.1f} s")
        elif score >= self.critical_score:
            level = HazardLevel.CRITICAL
        elif score >= self.warning_score:
            level = HazardLevel.WARNING
        elif score >= self.caution_score:
            level = HazardLevel.CAUTION
        else:
            level = HazardLevel.INFO

        return Assessment(obj, score, level, ttc, tuple(reasons))

    def assess_frame(self, frame: Frame) -> tuple[Assessment, ...]:
        """Assess every object, ordered by urgency then score then label."""
        return tuple(
            sorted(
                (self.assess(obj) for obj in frame.objects),
                key=lambda item: (-item.level.rank, -item.score, item.label),
            )
        )
