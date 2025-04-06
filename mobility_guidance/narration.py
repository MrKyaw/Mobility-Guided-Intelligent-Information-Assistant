"""Deterministic narration composition with prioritisation and cooldowns."""

from __future__ import annotations

from .models import Frame, Guidance, HazardLevel
from .policy import Assessment

PROFILE_LIMITS: dict[str, int] = {
    "concise": 1,
    "standard": 2,
    "verbose": 3,
}


def message_for(assessment: Assessment) -> str:
    """Build one short, speakable message for an assessment."""
    label = assessment.label.lower()
    distance = assessment.obj.distance_m
    if assessment.level is HazardLevel.CRITICAL:
        if distance is None:
            return f"Stop. {label.capitalize()} is very close. Stop now."
        return f"Stop. {label.capitalize()} {distance:.1f} metres ahead. Stop now."
    if assessment.level is HazardLevel.WARNING:
        if distance is None:
            return f"Slow down. {label.capitalize()} is nearby."
        return f"Slow down. {label.capitalize()} {distance:.1f} metres ahead."
    if assessment.level is HazardLevel.CAUTION:
        if distance is None:
            return f"Caution: {label} nearby."
        return f"Caution: {label} {distance:.1f} metres ahead."
    if distance is None:
        return f"{label.capitalize()} detected."
    return f"{label.capitalize()} {distance:.1f} metres away."


class NarrationBuilder:
    """Select the most urgent assessments and avoid repetitive speech.

    Args:
        profile: ``concise`` (1 message/frame), ``standard`` (2), or
            ``verbose`` (3).
        cooldown_s: Minimum seconds before the same object can repeat a
            message at the same or lower urgency.
    """

    def __init__(self, profile: str = "standard", cooldown_s: float = 2.0) -> None:
        if profile not in PROFILE_LIMITS:
            raise ValueError(f"unknown profile: {profile!r}")
        if cooldown_s < 0:
            raise ValueError("cooldown_s must be >= 0")
        self.profile = profile
        self.cooldown_s = cooldown_s
        self._last: dict[str, tuple[float, HazardLevel]] = {}

    def reset(self) -> None:
        """Forget cooldown history (useful between independent videos)."""
        self._last.clear()

    def narrate(
        self, frame: Frame, assessments: tuple[Assessment, ...]
    ) -> tuple[Guidance, ...]:
        """Return at most one message per selected assessment.

        When any warning-or-worse hazard exists, informational objects are
        dropped from the spoken output so urgent guidance is not diluted.
        """
        candidates = list(assessments)
        if any(item.level.rank >= HazardLevel.WARNING.rank for item in candidates):
            candidates = [item for item in candidates if item.level is not HazardLevel.INFO]

        emitted: list[Guidance] = []
        for assessment in candidates[: PROFILE_LIMITS[self.profile]]:
            key = assessment.label.lower()
            previous = self._last.get(key)
            if previous is not None:
                previous_at, previous_level = previous
                within_cooldown = frame.timestamp_s - previous_at < self.cooldown_s
                if within_cooldown and assessment.level.rank <= previous_level.rank:
                    continue

            emitted.append(
                Guidance(
                    timestamp_s=frame.timestamp_s,
                    level=assessment.level,
                    message=message_for(assessment),
                    object_labels=(assessment.label,),
                    reasons=assessment.reasons,
                )
            )
            self._last[key] = (frame.timestamp_s, assessment.level)
        return tuple(emitted)
