"""CLI for the offline mobility guidance pipeline.

Usage:
    python -m mobility_guidance --demo
    python -m mobility_guidance --demo --format html --output report.html
    python -m mobility_guidance --input frames.json --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import __version__
from .demo import DEMO_FRAMES
from .models import Frame
from .narration import PROFILE_LIMITS, NarrationBuilder
from .pipeline import GuidancePipeline
from .report import GuidanceReport, render_html, render_json, render_markdown

RENDERERS = {
    "markdown": render_markdown,
    "html": render_html,
    "json": render_json,
}


class ScriptError(ValueError):
    """Raised when an input file is not a valid frame document."""


def parse_frames(payload: Any) -> tuple[Frame, ...]:
    """Parse a JSON list or ``{"frames": [...]}`` document."""
    if isinstance(payload, Mapping):
        if "frames" not in payload:
            raise ScriptError("input object must contain a 'frames' list")
        raw = payload["frames"]
    elif isinstance(payload, list):
        raw = payload
    else:
        raise ScriptError("input must be a JSON list or an object with 'frames'")

    if not isinstance(raw, list) or not raw:
        raise ScriptError("input must contain at least one frame")
    return tuple(Frame.from_dict(item) for item in raw)


def load_frames(path: Path) -> tuple[Frame, ...]:
    """Load frames from a UTF-8 JSON file."""
    return parse_frames(json.loads(path.read_text(encoding="utf-8")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mobility_guidance",
        description="Offline mobility scene narration and safety-guidance reports.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="run the built-in scenario")
    source.add_argument("--input", type=Path, help="frame JSON file")
    parser.add_argument(
        "--format",
        choices=sorted(RENDERERS),
        default="markdown",
        help="output format (default: markdown)",
    )
    parser.add_argument("--output", type=Path, help="write the report to a file")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_LIMITS),
        default="standard",
        help="speech verbosity (default: standard)",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="exit 1 if any critical guidance is emitted",
    )
    parser.add_argument("--version", action="version", version=f"mobility_guidance {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.demo:
        frames = DEMO_FRAMES
    elif args.input is not None:
        try:
            frames = load_frames(args.input)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        print("error: provide --demo or --input", file=sys.stderr)
        return 2

    try:
        pipeline = GuidancePipeline(builder=NarrationBuilder(profile=args.profile))
        report: GuidanceReport = pipeline.run(frames)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    text = RENDERERS[args.format](report)
    if not text.endswith("\n"):
        text += "\n"

    if args.output is not None:
        try:
            args.output.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    else:
        print(text, end="")

    if args.fail_on_critical and report.summary()["critical"]:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through tests
    raise SystemExit(main())
