# Design decisions

## 1. Decision layer, not perception model
**Context:** The original prototype depends on YOLO/DeepLab/Llama-Vision and large media.
**Decision:** Extract the deterministic decision layer so it can be tested without models.
**Consequence:** Reviewers can evaluate the engineering in seconds.

## 2. Explainable scoring
**Context:** Safety guidance must be auditable.
**Decision:** Every assessment carries reasons (distance, path, speed, confidence, TTC).
**Consequence:** Reviewers can see why a level was chosen.

## 3. Time-to-contact can escalate
**Context:** A close, fast object is dangerous even with low confidence.
**Decision:** TTC ≤ 1.5 s forces `critical`.
**Consequence:** Conservative behaviour for the most dangerous cases.

## 4. Cooldowns are per object
**Context:** Repeating the same message is noise.
**Decision:** Suppress repeats for the same label unless urgency increases.
**Consequence:** Speech stays useful.

## 5. Profiles control volume
**Context:** Different users need different verbosity.
**Decision:** Concise (1), standard (2), verbose (3) messages per frame.
**Consequence:** Accessibility without changing the policy.

## 6. Stable, escaped reports
**Context:** Reports are shared and embedded.
**Decision:** Sorted frames/labels, escaped HTML/Markdown, deterministic JSON.
**Consequence:** Reports are diffable and safe.

## 7. Fail-fast validation
**Context:** Malformed scenes should not produce misleading guidance.
**Decision:** `SceneObject`/`Frame` raise `SceneError`.
**Consequence:** Clear errors and exit code 2 in the CLI.

## 8. Remove committed secrets
**Context:** `src/.env` contained a Together API key.
**Decision:** Remove it, add `.env.example`, ignore `.env`.
**Consequence:** New clones are safe; the key must be rotated.
