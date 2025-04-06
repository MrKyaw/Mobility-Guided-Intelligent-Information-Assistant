# Testing

## Run

```bash
python -m pip install -e ".[dev]"
pytest --cov=mobility_guidance --cov-branch --cov-report=term-missing
```

## Evidence (Python 3.12.8)

```text
109 passed in 0.33s

Name                             Stmts   Miss Branch BrPart  Cover
------------------------------------------------------------------
mobility_guidance/__init__.py        8      0      0      0   100%
mobility_guidance/__main__.py       69      0     18      0   100%
mobility_guidance/demo.py            3      0      0      0   100%
mobility_guidance/models.py         90      0     40      0   100%
mobility_guidance/narration.py      49      0     26      0   100%
mobility_guidance/pipeline.py       22      0      6      0   100%
mobility_guidance/policy.py         70      0     28      0   100%
mobility_guidance/report.py         68      0     24      0   100%
------------------------------------------------------------------
TOTAL                              379      0    142      0   100%
```

`fail_under = 100` is enforced in `pyproject.toml`.

## Coverage matrix

| Area | Cases |
|---|---|
| `SceneObject` | label/confidence/distance/bearing/speed/in_path validation; types; NaN; `from_dict`. |
| `Frame` | timestamp validation; objects tuple; description; `from_dict`; `to_dict`. |
| `SafetyPolicy` | every threshold; every distance band; low confidence; no distance; closing speed; TTC escalation; high-risk class; `assess_frame` sorting. |
| `NarrationBuilder` | profile/cooldown validation; reset; info filtering; cooldown skip; escalation; profile limits; empty input. |
| `message_for` | every level with and without distance; capitalisation. |
| `GuidanceReport` | empty/populated summary; duration; Markdown/HTML/JSON; pipe escaping; no objects. |
| `GuidancePipeline` | sorting; non-Frame rejection; empty input; builder reset; custom policy. |
| CLI | demo (markdown/json/html/concise); input file (object and list); output file; write error; fail-on-critical; no source; missing/bad/empty/invalid input; profile validation; `--version`; parser. |

## CI

`.github/workflows/ci.yml` runs the suite on Python 3.10, 3.11, and 3.12 with the coverage gate and a CLI smoke test.

## Manual verification

```bash
python -m mobility_guidance --demo
python -m mobility_guidance --demo --format json | python -m json.tool
python -m mobility_guidance --input frames.json --format html --output report.html
```
