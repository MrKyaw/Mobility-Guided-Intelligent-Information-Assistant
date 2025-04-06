# About — Mobility-Guided Intelligent Information Assistant

**Tagline:** A dependency-free scene-guidance core that turns detections into explainable risk scores, accessible narration, and auditable reports.

## The problem

Multimodal demos usually stop at “the model saw something.” Real mobility assistance needs answers to harder questions:

- Which object is actually dangerous right now?
- Why is it dangerous?
- What should be said, and how often?
- Can a reviewer audit what happened?

## The approach

1. **Validate** scene payloads (`SceneObject`, `Frame`).
2. **Score** each object with an explainable policy.
3. **Select** the most urgent messages with cooldowns and accessibility profiles.
4. **Report** in Markdown, HTML, and stable JSON.

## What is verified

- 109 tests, 100% line and branch coverage of `mobility_guidance`.
- Risk scoring, time-to-contact, level thresholds, cooldown suppression, escalation.
- Profile limits (1/2/3 messages), Markdown/HTML/JSON rendering, frame sorting, CLI.
- Malformed inputs raise `SceneError`; CLI returns exit code 2.

## Honest boundaries

- This is a **decision layer**, not a perception model.
- The original YOLO/DeepLab/Llama-Vision path is preserved but not CI-verified.
- Demo frames are synthetic.
- No accuracy, latency, or safety-certification claims are made.

## Keywords / tags

`mobility` · `accessibility` · `scene-understanding` · `risk-scoring` · `explainable-ai` · `narration` · `speech-scheduling` · `reporting` · `markdown` · `html` · `json` · `python` · `pytest` · `100-percent-coverage` · `offline` · `dependency-free` · `computer-vision` · `autonomous-vehicle` · `assistive-technology` · `audit-trail`

## Author

Kyaw Kyaw Oo — [github.com/MrKyaw](https://github.com/MrKyaw) — kyaw.tech@gmail.com
