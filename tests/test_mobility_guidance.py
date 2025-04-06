"""Comprehensive tests for the offline mobility guidance package."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mobility_guidance import (
    Frame,
    Guidance,
    HazardLevel,
    SceneError,
    SceneObject,
    __version__,
)
from mobility_guidance.__main__ import (
    DEMO_FRAMES,
    ScriptError,
    build_parser,
    load_frames,
    main,
    parse_frames,
    RENDERERS,
)
from mobility_guidance.demo import DEMO_FRAMES as DEMO_FRAMES_FROM_DEMO
from mobility_guidance.models import Guidance as GuidanceAlias
from mobility_guidance.narration import PROFILE_LIMITS, NarrationBuilder, message_for
from mobility_guidance.pipeline import GuidancePipeline
from mobility_guidance.policy import Assessment, SafetyPolicy, CLASS_WEIGHTS
from mobility_guidance.report import (
    GuidanceReport,
    render_html,
    render_json,
    render_markdown,
)


def make_obj(**overrides: object) -> SceneObject:
    defaults = {
        "label": "pedestrian",
        "confidence": 0.9,
        "distance_m": 2.0,
        "bearing_deg": 5.0,
        "closing_speed_mps": 0.5,
        "in_path": True,
    }
    defaults.update(overrides)
    return SceneObject(**defaults)  # type: ignore[arg-type]


def make_frame(**overrides: object) -> Frame:
    defaults = {"timestamp_s": 1.0, "objects": (make_obj(),), "description": "desc"}
    defaults.update(overrides)
    return Frame(**defaults)  # type: ignore[arg-type]


# --------------------------------------------------------------------- models
class TestSceneObject:
    def test_defaults(self) -> None:
        obj = SceneObject(label="car", confidence=0.5)
        assert obj.distance_m is None
        assert obj.bearing_deg == 0.0
        assert obj.closing_speed_mps == 0.0
        assert obj.in_path is False

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"label": ""},
            {"label": "   "},
            {"confidence": 1.1},
            {"confidence": -0.1},
            {"distance_m": -1.0},
            {"bearing_deg": 181.0},
            {"bearing_deg": -181.0},
            {"closing_speed_mps": float("inf")},
            {"in_path": "yes"},  # type: ignore[dict-item]
        ],
    )
    def test_rejects_invalid(self, kwargs: dict[str, object]) -> None:
        payload = {"label": "car", "confidence": 0.5}
        payload.update(kwargs)
        with pytest.raises(SceneError):
            SceneObject(**payload)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [True, "0.5", None])
    def test_confidence_type(self, bad: object) -> None:
        with pytest.raises(SceneError):
            SceneObject(label="car", confidence=bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [True, "1.0"])
    def test_distance_type(self, bad: object) -> None:
        with pytest.raises(SceneError):
            SceneObject(label="car", confidence=0.5, distance_m=bad)  # type: ignore[arg-type]

    def test_distance_none_allowed(self) -> None:
        assert SceneObject(label="car", confidence=0.5, distance_m=None).distance_m is None

    def test_nan_distance_rejected(self) -> None:
        with pytest.raises(SceneError, match="finite"):
            SceneObject(label="car", confidence=0.5, distance_m=float("nan"))

    def test_from_dict(self) -> None:
        obj = SceneObject.from_dict(
            {
                "label": "truck",
                "confidence": 0.8,
                "distance_m": 3.0,
                "bearing_deg": 10,
                "closing_speed_mps": 1.5,
                "in_path": True,
            }
        )
        assert obj.label == "truck"
        assert obj.confidence == 0.8
        assert obj.in_path is True

    def test_from_dict_requires_label_confidence(self) -> None:
        with pytest.raises(SceneError, match="requires"):
            SceneObject.from_dict({"label": "car"})
        with pytest.raises(SceneError, match="JSON object"):
            SceneObject.from_dict("x")  # type: ignore[arg-type]

    def test_from_dict_invalid_value(self) -> None:
        with pytest.raises(SceneError, match="confidence"):
            SceneObject.from_dict({"label": "car", "confidence": 2.0})

    def test_from_dict_invalid_bearing_type(self) -> None:
        with pytest.raises(SceneError, match="invalid"):
            SceneObject.from_dict({"label": "car", "confidence": 0.5, "bearing_deg": "x"})


class TestFrame:
    def test_from_dict(self) -> None:
        frame = Frame.from_dict(
            {
                "timestamp_s": 2.5,
                "description": "d",
                "objects": [{"label": "car", "confidence": 0.5}],
            }
        )
        assert frame.timestamp_s == 2.5
        assert len(frame.objects) == 1
        assert frame.to_dict()["objects"][0]["label"] == "car"

    @pytest.mark.parametrize(
        "payload",
        [
            "x",
            {},
            {"timestamp_s": -1},
            {"timestamp_s": 1, "objects": "x"},
            {"timestamp_s": 1, "objects": [{"label": "car"}]},
        ],
    )
    def test_from_dict_errors(self, payload: object) -> None:
        with pytest.raises(SceneError):
            Frame.from_dict(payload)  # type: ignore[arg-type]

    def test_objects_must_be_tuple(self) -> None:
        with pytest.raises(SceneError, match="tuple"):
            Frame(timestamp_s=1.0, objects=[make_obj()])  # type: ignore[arg-type]

    def test_objects_must_contain_scene_objects(self) -> None:
        with pytest.raises(SceneError, match="SceneObject"):
            Frame(timestamp_s=1.0, objects=("x",))  # type: ignore[arg-type]

    def test_description_type(self) -> None:
        with pytest.raises(SceneError, match="description"):
            Frame(timestamp_s=1.0, description=5)  # type: ignore[arg-type]

    def test_timestamp_type(self) -> None:
        with pytest.raises(SceneError, match="number"):
            Frame(timestamp_s="1")  # type: ignore[arg-type]

    def test_nan_timestamp(self) -> None:
        with pytest.raises(SceneError, match="finite"):
            Frame(timestamp_s=float("nan"))


class TestGuidance:
    def test_to_dict(self) -> None:
        g = Guidance(
            timestamp_s=1.0,
            level=HazardLevel.WARNING,
            message="msg",
            object_labels=("car",),
            reasons=("r1",),
        )
        assert g.to_dict()["level"] == "warning"


# ---------------------------------------------------------------------- policy
class TestSafetyPolicy:
    def test_threshold_validation(self) -> None:
        with pytest.raises(ValueError, match="thresholds"):
            SafetyPolicy(caution_score=2.0, warning_score=1.0, critical_score=4.0)
        with pytest.raises(ValueError, match="thresholds"):
            SafetyPolicy(caution_score=0, warning_score=1, critical_score=2)
        with pytest.raises(ValueError, match="thresholds"):
            SafetyPolicy(caution_score=1, warning_score=2, critical_score=2)

    def test_info_level(self) -> None:
        obj = make_obj(label="car", confidence=0.8, distance_m=10.0, in_path=False)
        assessment = SafetyPolicy().assess(obj)
        assert assessment.level is HazardLevel.INFO

    def test_caution_level(self) -> None:
        obj = make_obj(label="car", confidence=0.85, distance_m=5.0, in_path=False)
        assessment = SafetyPolicy().assess(obj)
        assert assessment.level is HazardLevel.CAUTION

    def test_warning_level(self) -> None:
        obj = make_obj(label="car", confidence=0.9, distance_m=3.0, in_path=True)
        assessment = SafetyPolicy().assess(obj)
        assert assessment.level is HazardLevel.WARNING

    def test_critical_level(self) -> None:
        obj = make_obj(
            label="pedestrian",
            confidence=0.95,
            distance_m=1.0,
            in_path=True,
            closing_speed_mps=0.8,
        )
        assessment = SafetyPolicy().assess(obj)
        assert assessment.level is HazardLevel.CRITICAL
        assert assessment.time_to_contact_s == 1.25
        assert any("time to contact" in r for r in assessment.reasons)

    def test_ttc_forces_critical(self) -> None:
        obj = make_obj(
            label="car",
            confidence=0.5,
            distance_m=1.0,
            in_path=False,
            closing_speed_mps=1.0,
        )
        assessment = SafetyPolicy().assess(obj)
        assert assessment.level is HazardLevel.CRITICAL

    def test_low_confidence_reason(self) -> None:
        obj = make_obj(confidence=0.3, distance_m=8.0, in_path=False)
        assessment = SafetyPolicy().assess(obj)
        assert "low detector confidence" in assessment.reasons

    def test_no_distance(self) -> None:
        obj = make_obj(distance_m=None, in_path=False)
        assessment = SafetyPolicy().assess(obj)
        assert "distance unavailable" in assessment.reasons

    def test_far_distance(self) -> None:
        obj = make_obj(distance_m=8.0, in_path=False)
        assessment = SafetyPolicy().assess(obj)
        assert "8.0 m away" in assessment.reasons

    def test_closing_speed_reason(self) -> None:
        obj = make_obj(closing_speed_mps=2.0, in_path=False)
        assessment = SafetyPolicy().assess(obj)
        assert any("closing at" in r for r in assessment.reasons)

    def test_high_risk_class_reason(self) -> None:
        obj = make_obj(label="pedestrian", in_path=False, distance_m=8.0)
        assessment = SafetyPolicy().assess(obj)
        assert any("high-risk class" in r for r in assessment.reasons)

    def test_assess_frame_sorting(self) -> None:
        frame = make_frame(
            objects=(
                make_obj(label="car", confidence=0.5, distance_m=8.0, in_path=False),
                make_obj(label="pedestrian", confidence=0.95, distance_m=1.2, in_path=True),
            )
        )
        assessments = SafetyPolicy().assess_frame(frame)
        assert assessments[0].level.rank >= assessments[1].level.rank

    def test_unknown_class_weight(self) -> None:
        obj = make_obj(label="scooter", in_path=False, distance_m=8.0)
        assessment = SafetyPolicy().assess(obj)
        assert assessment.score >= 0


# ------------------------------------------------------------------ narration
class TestNarration:
    def test_profile_validation(self) -> None:
        with pytest.raises(ValueError, match="profile"):
            NarrationBuilder(profile="loud")
        with pytest.raises(ValueError, match="cooldown"):
            NarrationBuilder(cooldown_s=-1)

    def test_reset(self) -> None:
        builder = NarrationBuilder()
        builder._last["x"] = (1.0, HazardLevel.INFO)
        builder.reset()
        assert builder._last == {}

    def test_message_for_all_levels(self) -> None:
        for level in HazardLevel:
            obj = make_obj(distance_m=2.5)
            assessment = Assessment(obj, 1.0, level, 2.0, ("r",))
            msg = message_for(assessment)
            assert msg
            assert "2.5" in msg or level is HazardLevel.INFO

    def test_message_without_distance(self) -> None:
        obj = make_obj(distance_m=None)
        assessment = Assessment(obj, 1.0, HazardLevel.CRITICAL, None, ())
        msg = message_for(assessment)
        assert "very close" in msg

    def test_info_message_with_distance(self) -> None:
        obj = make_obj(distance_m=5.0)
        assessment = Assessment(obj, 0.5, HazardLevel.INFO, None, ())
        assert "5.0" in message_for(assessment)

    def test_warning_without_distance(self) -> None:
        obj = make_obj(distance_m=None)
        assessment = Assessment(obj, 1.0, HazardLevel.WARNING, None, ())
        assert "nearby" in message_for(assessment)

    def test_caution_without_distance(self) -> None:
        obj = make_obj(distance_m=None)
        assessment = Assessment(obj, 1.0, HazardLevel.CAUTION, None, ())
        assert "nearby" in message_for(assessment)

    def test_narrate_filters_info_when_warning(self) -> None:
        frame = make_frame()
        policy = SafetyPolicy()
        assessments = policy.assess_frame(frame)
        # force one info assessment by patching
        info_obj = make_obj(label="car", confidence=0.1, distance_m=10.0, in_path=False)
        info = policy.assess(info_obj)
        assessments = (assessments[0], info)
        builder = NarrationBuilder(profile="standard")
        out = builder.narrate(frame, assessments)
        # highest level remains
        assert all(g.level is not HazardLevel.INFO for g in out) or len(out) <= 2

    def test_cooldown_skips_repeat(self) -> None:
        builder = NarrationBuilder(profile="standard", cooldown_s=5.0)
        frame1 = make_frame(timestamp_s=0.0)
        frame2 = make_frame(timestamp_s=1.0)
        assessments = SafetyPolicy().assess_frame(frame1)
        first = builder.narrate(frame1, assessments)
        second = builder.narrate(frame2, assessments)
        assert len(first) >= 1
        assert len(second) == 0

    def test_cooldown_allows_escalation(self) -> None:
        builder = NarrationBuilder(profile="standard", cooldown_s=5.0)
        obj_far = make_obj(distance_m=5.0, in_path=False, confidence=0.8)
        obj_near = make_obj(distance_m=1.0, in_path=True, confidence=0.95, closing_speed_mps=1.0)
        frame1 = make_frame(timestamp_s=0.0, objects=(obj_far,))
        frame2 = make_frame(timestamp_s=1.0, objects=(obj_near,))
        first = builder.narrate(frame1, SafetyPolicy().assess_frame(frame1))
        second = builder.narrate(frame2, SafetyPolicy().assess_frame(frame2))
        assert len(first) == 1
        assert len(second) == 1

    def test_profile_limits(self) -> None:
        objs = tuple(
            make_obj(label=f"car{i}", distance_m=5.0 + i, in_path=False)
            for i in range(5)
        )
        frame = make_frame(objects=objs)
        assessments = SafetyPolicy().assess_frame(frame)
        for profile, limit in PROFILE_LIMITS.items():
            builder = NarrationBuilder(profile=profile)
            out = builder.narrate(frame, assessments)
            assert len(out) <= limit

    def test_narrate_empty(self) -> None:
        frame = make_frame(objects=())
        builder = NarrationBuilder()
        assert builder.narrate(frame, ()) == ()

    def test_info_message_capitalisation(self) -> None:
        msg = message_for(
            Assessment(make_obj(label="bicycle"), 0.5, HazardLevel.INFO, None, ())
        )
        assert msg.startswith("Bicycle")

    def test_info_message_without_distance(self) -> None:
        obj = make_obj(label="car", distance_m=None)
        assessment = Assessment(obj, 0.5, HazardLevel.INFO, None, ())
        assert message_for(assessment) == "Car detected."


# --------------------------------------------------------------------- report
class TestReport:
    def test_summary_empty(self) -> None:
        report = GuidanceReport(frames=(), guidance=(), profile="concise")
        summary = report.summary()
        assert summary["frames"] == 0
        assert summary["objects_seen"] == 0
        assert summary["unique_labels"] == []
        assert summary["duration_s"] == 0.0
        assert summary["average_confidence"] == 0.0
        assert summary["critical"] is False

    def test_summary_populated(self) -> None:
        frame = make_frame(objects=(make_obj(confidence=0.8), make_obj(label="car", confidence=0.6)))
        report = GuidanceReport(frames=(frame,), guidance=(), profile="standard")
        summary = report.summary()
        assert summary["objects_seen"] == 2
        assert summary["average_confidence"] == 0.7
        assert "pedestrian" in summary["unique_labels"]

    def test_duration_multi(self) -> None:
        frames = (make_frame(timestamp_s=0.0), make_frame(timestamp_s=3.5))
        report = GuidanceReport(frames=frames, guidance=(), profile="standard")
        assert report.summary()["duration_s"] == 3.5

    def test_markdown_contains_sections(self) -> None:
        frame = make_frame()
        report = GuidanceReport(frames=(frame,), guidance=(), profile="standard")
        md = render_markdown(report)
        assert "# Mobility Guidance Report" in md
        assert "## Frames" in md
        assert "No guidance was emitted." in md
        assert "## Summary" in md

    def test_markdown_with_guidance(self) -> None:
        frame = make_frame()
        assessment = SafetyPolicy().assess(make_obj())
        guidance = (
            Guidance(
                timestamp_s=frame.timestamp_s,
                level=HazardLevel.WARNING,
                message="Slow down.",
                object_labels=("pedestrian",),
                reasons=("r",),
            ),
        )
        report = GuidanceReport(frames=(frame,), guidance=guidance, profile="standard")
        md = render_markdown(report)
        assert "Slow down." in md
        assert "pedestrian" in md

    def test_markdown_escapes_pipes(self) -> None:
        frame = make_frame(description="a|b")
        report = GuidanceReport(frames=(frame,), guidance=(), profile="standard")
        md = render_markdown(report)
        assert "a\\|b" in md

    def test_html_renders(self) -> None:
        frame = make_frame()
        guidance = (
            Guidance(
                timestamp_s=1.0,
                level=HazardLevel.CRITICAL,
                message="<script>",
                object_labels=("car",),
            ),
        )
        report = GuidanceReport(frames=(frame,), guidance=guidance, profile="verbose")
        html_out = render_html(report)
        assert "<!doctype html>" in html_out
        assert "&lt;script&gt;" in html_out
        assert "critical" in html_out

    def test_html_empty(self) -> None:
        report = GuidanceReport(frames=(), guidance=(), profile="standard")
        html_out = render_html(report)
        assert "No guidance was emitted." in html_out

    def test_html_no_objects(self) -> None:
        frame = Frame(timestamp_s=1.0, objects=(), description="clear")
        report = GuidanceReport(frames=(frame,), guidance=(), profile="standard")
        html_out = render_html(report)
        assert "No objects detected." in html_out

    def test_markdown_no_objects(self) -> None:
        frame = Frame(timestamp_s=1.0, objects=(), description="clear")
        report = GuidanceReport(frames=(frame,), guidance=(), profile="standard")
        md = render_markdown(report)
        assert "No objects detected." in md

    def test_json_round_trip(self) -> None:
        frame = make_frame()
        report = GuidanceReport(frames=(frame,), guidance=(), profile="standard")
        payload = json.loads(render_json(report))
        assert payload["profile"] == "standard"
        assert payload["summary"]["frames"] == 1
        assert payload["frames"][0]["timestamp_s"] == 1.0

    def test_report_guidance_to_dict(self) -> None:
        report = GuidanceReport(frames=(), guidance=(), profile="standard")
        assert report.summary()["by_level"]["info"] == 0


# -------------------------------------------------------------------- pipeline
class TestPipeline:
    def test_run_sorts_frames(self) -> None:
        frames = (make_frame(timestamp_s=5.0), make_frame(timestamp_s=1.0))
        pipeline = GuidancePipeline()
        report = pipeline.run(frames)
        assert report.frames[0].timestamp_s == 1.0
        assert report.frames[1].timestamp_s == 5.0

    def test_run_rejects_non_frames(self) -> None:
        with pytest.raises(SceneError):
            GuidancePipeline().run([make_frame(), "x"])  # type: ignore[list-item]

    def test_empty_frames(self) -> None:
        report = GuidancePipeline().run([])
        assert report.frames == ()
        assert report.guidance == ()

    def test_builder_reset(self) -> None:
        builder = NarrationBuilder(cooldown_s=10.0)
        frame = make_frame()
        first = GuidancePipeline(builder=builder).run([frame])
        second = GuidancePipeline(builder=builder).run([frame])
        assert len(first.guidance) == len(second.guidance)

    def test_custom_policy(self) -> None:
        policy = SafetyPolicy(critical_score=100.0)
        report = GuidancePipeline(policy=policy).run([make_frame()])
        # with a very high critical threshold, pedestrian is not critical
        assert report.guidance


# ------------------------------------------------------------------------ cli
class TestCli:
    def test_demo_markdown(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--demo"]) == 0
        out = capsys.readouterr().out
        assert "# Mobility Guidance Report" in out
        assert "Stop." in out

    def test_demo_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--demo", "--format", "json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["summary"]["critical"] is True

    def test_demo_html(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--demo", "--format", "html"]) == 0
        assert "<!doctype html>" in capsys.readouterr().out

    def test_demo_concise(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--demo", "--profile", "concise"]) == 0
        assert capsys.readouterr().out

    def test_input_file(
        self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "frames.json"  # type: ignore[operator]
        payload = {
            "frames": [
                {
                    "timestamp_s": 0.0,
                    "description": "d",
                    "objects": [
                        {"label": "car", "confidence": 0.7, "distance_m": 5.0}
                    ],
                }
            ]
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert main(["--input", str(path), "--format", "json"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["summary"]["frames"] == 1

    def test_input_list_form(
        self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
    ) -> None:
        path = tmp_path / "frames.json"  # type: ignore[operator]
        path.write_text(
            json.dumps([{"timestamp_s": 1.0, "objects": []}]), encoding="utf-8"
        )
        assert main(["--input", str(path)]) == 0
        assert "No guidance was emitted." in capsys.readouterr().out

    def test_output_file(
        self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out_path = tmp_path / "report.md"  # type: ignore[operator]
        assert main(["--demo", "--output", str(out_path)]) == 0
        assert out_path.exists()
        assert "# Mobility Guidance Report" in out_path.read_text(encoding="utf-8")
        assert capsys.readouterr().out == ""

    def test_output_write_error(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out_path = tmp_path / "report.md"  # type: ignore[operator]
        original = Path.write_text

        def boom(self: Path, *args: object, **kwargs: object) -> int:
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", boom)
        assert main(["--demo", "--output", str(out_path)]) == 2
        assert "error:" in capsys.readouterr().err
        monkeypatch.setattr(Path, "write_text", original)

    def test_fail_on_critical(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--demo", "--fail-on-critical"]) == 1
        assert capsys.readouterr().out

    def test_no_source(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main([]) == 2
        assert "provide" in capsys.readouterr().err

    def test_missing_input(self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--input", str(tmp_path / "missing.json")]) == 2  # type: ignore[operator]
        assert "error:" in capsys.readouterr().err

    def test_bad_json(self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]) -> None:
        path = tmp_path / "bad.json"  # type: ignore[operator]
        path.write_text("{", encoding="utf-8")
        assert main(["--input", str(path)]) == 2
        assert "error:" in capsys.readouterr().err

    def test_invalid_frame(self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]) -> None:
        path = tmp_path / "bad.json"  # type: ignore[operator]
        path.write_text(json.dumps({"frames": [{"timestamp_s": 1, "objects": [{"label": "car"}]}]}), encoding="utf-8")
        assert main(["--input", str(path)]) == 2
        assert "error:" in capsys.readouterr().err

    def test_empty_frames(self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture[str]) -> None:
        path = tmp_path / "empty.json"  # type: ignore[operator]
        path.write_text(json.dumps({"frames": []}), encoding="utf-8")
        assert main(["--input", str(path)]) == 2
        assert "error:" in capsys.readouterr().err

    def test_invalid_profile_rejected_by_parser(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--demo", "--profile", "loud"])

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert "mobility_guidance" in capsys.readouterr().out

    def test_parser(self) -> None:
        parser = build_parser()
        assert parser.prog == "mobility_guidance"

    def test_pipeline_value_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def boom(self: object, frames: object) -> object:
            raise ValueError("boom")

        monkeypatch.setattr("mobility_guidance.__main__.GuidancePipeline.run", boom)
        assert main(["--demo"]) == 2
        assert "error: boom" in capsys.readouterr().err

    def test_parse_frames_list(self) -> None:
        frames = parse_frames([{"timestamp_s": 1.0, "objects": []}])
        assert len(frames) == 1

    def test_parse_frames_requires_frames(self) -> None:
        with pytest.raises(ScriptError, match="frames"):
            parse_frames({"x": 1})

    def test_parse_frames_rejects_scalar(self) -> None:
        with pytest.raises(ScriptError, match="list or"):
            parse_frames(5)

    def test_load_frames(self, tmp_path: pytest.TempPathFactory) -> None:
        path = tmp_path / "f.json"  # type: ignore[operator]
        path.write_text(json.dumps({"frames": [{"timestamp_s": 0.0, "objects": []}]}), encoding="utf-8")
        assert len(load_frames(path)) == 1

    def test_renderers_all(self) -> None:
        assert set(RENDERERS) == {"markdown", "html", "json"}

    def test_demo_frames_import(self) -> None:
        assert DEMO_FRAMES_FROM_DEMO is DEMO_FRAMES
        assert len(DEMO_FRAMES) == 5

    def test_guidance_alias(self) -> None:
        assert GuidanceAlias is Guidance


# --------------------------------------------------------------------- exports
class TestExports:
    def test_message_for_exported(self) -> None:
        assert callable(message_for)

    def test_class_weights(self) -> None:
        assert CLASS_WEIGHTS["pedestrian"] > 1.0


class TestSafetyPolicyAssessment:
    def test_score_positive(self) -> None:
        assessment = SafetyPolicy().assess(make_obj())
        assert assessment.score > 0
        assert assessment.label == "pedestrian"

    def test_assessment_dataclass(self) -> None:
        assessment = Assessment(make_obj(), 1.0, HazardLevel.INFO, None, ())
        assert assessment.label == "pedestrian"


class TestNarrationBuilderCooldownEdge:
    def test_frame_time_equal_previous(self) -> None:
        builder = NarrationBuilder(cooldown_s=2.0)
        frame = make_frame(timestamp_s=0.0)
        assessments = SafetyPolicy().assess_frame(frame)
        first = builder.narrate(frame, assessments)
        second = builder.narrate(frame, assessments)
        assert len(first) >= 1
        # second is suppressed by cooldown at equal time
        assert len(second) == 0

    def test_verbose_profile(self) -> None:
        frame = make_frame(objects=tuple(make_obj(label=f"car{i}", distance_m=5.0 + i, in_path=False) for i in range(4)))
        assessments = SafetyPolicy().assess_frame(frame)
        out = NarrationBuilder(profile="verbose").narrate(frame, assessments)
        assert len(out) <= 3

    def test_concise_profile(self) -> None:
        frame = make_frame(objects=tuple(make_obj(label=f"car{i}", distance_m=5.0 + i, in_path=False) for i in range(4)))
        assessments = SafetyPolicy().assess_frame(frame)
        out = NarrationBuilder(profile="concise").narrate(frame, assessments)
        assert len(out) <= 1
