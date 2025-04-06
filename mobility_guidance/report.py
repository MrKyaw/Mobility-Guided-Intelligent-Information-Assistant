"""Report building and Markdown/HTML/JSON rendering."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from typing import Any

from .models import Frame, Guidance, HazardLevel


@dataclass(frozen=True)
class GuidanceReport:
    """Complete result of an offline guidance run."""

    frames: tuple[Frame, ...]
    guidance: tuple[Guidance, ...]
    profile: str = "standard"

    def summary(self) -> dict[str, Any]:
        objects = [obj for frame in self.frames for obj in frame.objects]
        by_level = {level.value: 0 for level in HazardLevel}
        for item in self.guidance:
            by_level[item.level.value] += 1

        duration = 0.0
        if len(self.frames) > 1:
            duration = round(
                self.frames[-1].timestamp_s - self.frames[0].timestamp_s, 3
            )

        confidence = 0.0
        if objects:
            confidence = round(
                sum(float(obj.confidence) for obj in objects) / len(objects), 3
            )

        return {
            "frames": len(self.frames),
            "objects_seen": len(objects),
            "unique_labels": sorted({obj.label for obj in objects}),
            "guidance_count": len(self.guidance),
            "by_level": by_level,
            "duration_s": duration,
            "average_confidence": confidence,
            "critical": by_level[HazardLevel.CRITICAL.value] > 0,
        }


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(report: GuidanceReport) -> str:
    """Render a human-readable Markdown report."""
    summary = report.summary()
    lines = [
        "# Mobility Guidance Report",
        "",
        f"**Profile:** `{report.profile}` · **Frames:** {summary['frames']} · "
        f"**Duration:** {summary['duration_s']} s",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Objects seen | {summary['objects_seen']} |",
        f"| Unique labels | {', '.join(summary['unique_labels']) or '—'} |",
        f"| Guidance messages | {summary['guidance_count']} |",
        f"| Critical alerts | {summary['by_level']['critical']} |",
        f"| Warnings | {summary['by_level']['warning']} |",
        f"| Cautions | {summary['by_level']['caution']} |",
        f"| Info | {summary['by_level']['info']} |",
        f"| Average confidence | {summary['average_confidence']} |",
        "",
        "## Guidance log",
        "",
    ]
    if report.guidance:
        lines.extend(
            [
                "| Time (s) | Level | Message |",
                "| --- | --- | --- |",
            ]
        )
        for item in report.guidance:
            lines.append(
                f"| {item.timestamp_s:.1f} | {item.level.value} | "
                f"{_md_escape(item.message)} |"
            )
    else:
        lines.append("_No guidance was emitted._")
    lines.append("")

    lines.extend(["## Frames", ""])
    for frame in report.frames:
        lines.append(f"### t = {frame.timestamp_s:.1f} s")
        lines.append("")
        if frame.description:
            lines.append(_md_escape(frame.description))
            lines.append("")
        if not frame.objects:
            lines.append("_No objects detected._")
            lines.append("")
            continue
        lines.extend(
            [
                "| Object | Confidence | Distance (m) | In path | Closing (m/s) |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for obj in frame.objects:
            distance = "—" if obj.distance_m is None else f"{obj.distance_m:.1f}"
            lines.append(
                f"| {_md_escape(obj.label)} | {obj.confidence:.2f} | {distance} | "
                f"{'yes' if obj.in_path else 'no'} | {obj.closing_speed_mps:.1f} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_html(report: GuidanceReport) -> str:
    """Render a self-contained HTML report."""
    summary = report.summary()
    guidance_rows = "".join(
        f"<li class='{html.escape(item.level.value)}'>"
        f"<strong>{item.timestamp_s:.1f}s · {html.escape(item.level.value)}</strong> "
        f"{html.escape(item.message)}</li>"
        for item in report.guidance
    )
    if not guidance_rows:
        guidance_rows = "<li class='empty'>No guidance was emitted.</li>"

    frame_blocks: list[str] = []
    for frame in report.frames:
        if frame.objects:
            rows = "".join(
                "<tr>"
                f"<td>{html.escape(obj.label)}</td>"
                f"<td>{obj.confidence:.2f}</td>"
                f"<td>{'—' if obj.distance_m is None else f'{obj.distance_m:.1f}'}</td>"
                f"<td>{'yes' if obj.in_path else 'no'}</td>"
                f"<td>{obj.closing_speed_mps:.1f}</td>"
                "</tr>"
                for obj in frame.objects
            )
            table = (
                "<table><thead><tr><th>Object</th><th>Confidence</th>"
                "<th>Distance (m)</th><th>In path</th><th>Closing (m/s)</th>"
                f"</tr></thead><tbody>{rows}</tbody></table>"
            )
        else:
            table = "<p class='empty'>No objects detected.</p>"
        description = (
            f"<p>{html.escape(frame.description)}</p>" if frame.description else ""
        )
        frame_blocks.append(
            f"<section><h3>t = {frame.timestamp_s:.1f} s</h3>{description}{table}</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mobility Guidance Report</title>
<style>
body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 2rem auto; max-width: 960px; padding: 0 1rem; color: #1b1b1b; }}
h1 {{ margin-bottom: 0.25rem; }}
.meta {{ color: #555; }}
.cards {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }}
.card {{ border: 1px solid #ddd; border-radius: 10px; padding: 0.75rem 1rem; min-width: 130px; }}
.card strong {{ display: block; font-size: 1.5rem; }}
ul.guidance {{ list-style: none; padding: 0; }}
ul.guidance li {{ border-left: 5px solid #999; padding: 0.5rem 0.75rem; margin: 0.5rem 0; background: #fafafa; }}
li.critical {{ border-color: #b00020; }}
li.warning {{ border-color: #d97706; }}
li.caution {{ border-color: #2563eb; }}
li.info {{ border-color: #6b7280; }}
table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0 1.5rem; }}
th, td {{ text-align: left; border-bottom: 1px solid #e5e5e5; padding: 0.4rem 0.5rem; }}
.empty {{ color: #666; font-style: italic; }}
</style>
</head>
<body>
<h1>Mobility Guidance Report</h1>
<p class="meta">Profile: {html.escape(report.profile)} · Frames: {summary['frames']} · Duration: {summary['duration_s']} s</p>
<div class="cards">
  <div class="card"><strong>{summary['objects_seen']}</strong>objects seen</div>
  <div class="card"><strong>{summary['guidance_count']}</strong>guidance messages</div>
  <div class="card"><strong>{summary['by_level']['critical']}</strong>critical</div>
  <div class="card"><strong>{summary['by_level']['warning']}</strong>warnings</div>
  <div class="card"><strong>{summary['average_confidence']}</strong>avg confidence</div>
</div>
<h2>Guidance log</h2>
<ul class="guidance">{guidance_rows}</ul>
<h2>Frames</h2>
{''.join(frame_blocks)}
</body>
</html>
"""


def render_json(report: GuidanceReport) -> str:
    """Render a stable, machine-readable JSON report."""
    payload = {
        "profile": report.profile,
        "summary": report.summary(),
        "guidance": [item.to_dict() for item in report.guidance],
        "frames": [frame.to_dict() for frame in report.frames],
    }
    return json.dumps(payload, indent=2, sort_keys=True)
