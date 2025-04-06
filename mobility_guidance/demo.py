"""Built-in demonstration frames for the offline guidance CLI."""

from __future__ import annotations

from .models import Frame, SceneObject

DEMO_FRAMES: tuple[Frame, ...] = (
    Frame(
        timestamp_s=0.0,
        description="Approaching a marked crossing; a pedestrian is stepping into the path.",
        objects=(
            SceneObject(
                label="pedestrian",
                confidence=0.95,
                distance_m=1.2,
                bearing_deg=2.0,
                closing_speed_mps=0.8,
                in_path=True,
            ),
            SceneObject(
                label="car",
                confidence=0.90,
                distance_m=9.0,
                bearing_deg=12.0,
                in_path=False,
            ),
        ),
    ),
    Frame(
        timestamp_s=4.0,
        description="The pedestrian has moved across but is still close to the kerb.",
        objects=(
            SceneObject(
                label="pedestrian",
                confidence=0.90,
                distance_m=5.0,
                bearing_deg=-4.0,
                in_path=True,
            ),
        ),
    ),
    Frame(
        timestamp_s=8.0,
        description="A cyclist is passing on the left, outside the travel path.",
        objects=(
            SceneObject(
                label="cyclist",
                confidence=0.80,
                distance_m=4.0,
                bearing_deg=-30.0,
            ),
        ),
    ),
    Frame(
        timestamp_s=12.0,
        description="A car is visible far ahead.",
        objects=(
            SceneObject(
                label="car",
                confidence=0.85,
                distance_m=10.0,
                bearing_deg=10.0,
            ),
        ),
    ),
    Frame(timestamp_s=16.0, description="The path is clear."),
)
