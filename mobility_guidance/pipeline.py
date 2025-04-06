"""Offline guidance pipeline: frames in, prioritised report out."""

from __future__ import annotations

from typing import Iterable

from .models import Frame, SceneError
from .narration import NarrationBuilder
from .policy import SafetyPolicy
from .report import GuidanceReport


class GuidancePipeline:
    """Compose the safety policy with narration and reporting."""

    def __init__(
        self,
        policy: SafetyPolicy | None = None,
        builder: NarrationBuilder | None = None,
    ) -> None:
        self.policy = policy or SafetyPolicy()
        self.builder = builder or NarrationBuilder()

    def run(self, frames: Iterable[Frame]) -> GuidanceReport:
        """Process frames in timestamp order and return a deterministic report."""
        materialized = list(frames)
        for frame in materialized:
            if not isinstance(frame, Frame):
                raise SceneError("frames must contain Frame instances")

        ordered = sorted(materialized, key=lambda frame: frame.timestamp_s)
        self.builder.reset()

        guidance = []
        for frame in ordered:
            assessments = self.policy.assess_frame(frame)
            guidance.extend(self.builder.narrate(frame, assessments))

        return GuidanceReport(
            frames=tuple(ordered),
            guidance=tuple(guidance),
            profile=self.builder.profile,
        )
