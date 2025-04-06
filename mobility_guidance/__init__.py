"""Offline mobility guidance: explainable risk scoring, narration and reports.

The original repository explored YOLO/DeepLab/Llama-Vision perception over a
driving video. This package isolates the deterministic decision layer that can
be tested without models, GPUs, or API keys: scene validation, hazard scoring,
accessible narration selection, cooldown handling, and Markdown/HTML/JSON
reporting.
"""

from .demo import DEMO_FRAMES
from .models import Frame, Guidance, HazardLevel, SceneError, SceneObject
from .narration import PROFILE_LIMITS, NarrationBuilder, message_for
from .pipeline import GuidancePipeline
from .policy import Assessment, CLASS_WEIGHTS, SafetyPolicy
from .report import GuidanceReport, render_html, render_json, render_markdown

__version__ = "1.0.0"

__all__ = [
    "Assessment",
    "CLASS_WEIGHTS",
    "DEMO_FRAMES",
    "Frame",
    "Guidance",
    "GuidancePipeline",
    "GuidanceReport",
    "HazardLevel",
    "NarrationBuilder",
    "PROFILE_LIMITS",
    "SafetyPolicy",
    "SceneError",
    "SceneObject",
    "message_for",
    "render_html",
    "render_json",
    "render_markdown",
]
