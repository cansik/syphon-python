"""Check the repository benchmark tool without imposing timing thresholds."""

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("numpy")
SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark.py"
spec = importlib.util.spec_from_file_location("frame_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def run_benchmark(tmp_path, *arguments):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--backend",
            "host",
            "--width",
            "8",
            "--height",
            "4",
            "--iterations",
            "2",
            "--repeats",
            "2",
            *arguments,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_saved_host_run_and_comparison(tmp_path):
    before, after = tmp_path / "runs/before.json", tmp_path / "runs/after.json"
    result = run_benchmark(tmp_path, "--output", str(before))
    assert result.returncode == 0, result.stderr
    baseline = json.loads(before.read_text())
    assert baseline["environment"]["device"] is None
    assert (baseline["width"], baseline["height"]) == (8, 4)
    assert {row["name"] for row in baseline["results"]} == {"host/upload", "host/download", "host/download-reuse"}
    for row in baseline["results"]:
        assert math.isfinite(row["ms"]) and row["ms"] > 0
        assert row["peak_mib"] >= 0
        assert len(row["samples_ms"]) == 2
    result = run_benchmark(tmp_path, "--compare", str(before), "--output", str(after))
    assert result.returncode == 0, result.stderr
    report = json.loads(after.read_text())
    assert report["comparison_warnings"] == []
    assert len(report["comparison"]) == 3
    assert all(math.isfinite(row["speedup"]) and row["speedup"] > 0 for row in report["comparison"])


@pytest.mark.metal
def test_metal_run_separates_async_submission_from_completion(tmp_path):
    import Metal

    if Metal.MTLCreateSystemDefaultDevice() is None:
        pytest.skip("A Metal device is required")
    path = tmp_path / "metal.json"
    result = run_benchmark(tmp_path, "--backend", "metal", "--output", str(path))
    assert result.returncode == 0, result.stderr
    rows = {row["name"] for row in json.loads(path.read_text())["results"]}
    assert "metal/publish-complete" in rows
    assert "metal/publish-async-submission" in rows
    assert "metal/publish-submission" not in rows


def report(rows, *, device="Example GPU"):
    return {"schema_version": 1, "width": 8, "height": 4, "environment": {"device": device}, "results": rows}


def test_comparison_matches_names_and_marks_new_cases():
    previous = report([{"name": "download", "ms": 2, "peak_mib": 8}])
    current = report([{"name": "new", "ms": 1, "peak_mib": 0}, {"name": "download", "ms": 1, "peak_mib": 4}])
    comparisons, warnings = benchmark.compare_reports(current, previous)
    assert warnings == []
    assert comparisons[0]["previous_ms"] is None
    assert comparisons[0]["speedup"] is None
    assert comparisons[1]["speedup"] == 2
    assert comparisons[1]["previous_peak_mib"] == 8


def test_environment_differences_are_flagged():
    _, warnings = benchmark.compare_reports(report([], device="Other GPU"), report([]))
    assert len(warnings) == 1 and "Environment differs: device" in warnings[0]


@pytest.mark.parametrize("field,value", [("ms", 0), ("ms", -1), ("peak_mib", -1), ("peak_mib", None)])
def test_invalid_measurements_fail_cleanly(tmp_path, field, value):
    row = {"name": "host/upload", "ms": 1, "peak_mib": 0}
    row[field] = value
    path = tmp_path / "previous.json"
    path.write_text(json.dumps(report([row])))
    result = run_benchmark(tmp_path, "--compare", str(path))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_different_dimensions_fail_before_measurement(tmp_path):
    previous = report([])
    previous["width"] = 16
    path = tmp_path / "previous.json"
    path.write_text(json.dumps(previous))
    result = run_benchmark(tmp_path, "--compare", str(path))
    assert result.returncode == 2
    assert "different image dimensions" in result.stderr


@pytest.mark.parametrize("contents", ["not json", "{}", '{"schema_version": 2}'])
def test_invalid_reports_fail_cleanly(tmp_path, contents):
    path = tmp_path / "previous.json"
    path.write_text(contents)
    result = run_benchmark(tmp_path, "--compare", str(path))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_empty_images_are_rejected(tmp_path):
    result = run_benchmark(tmp_path, "--width", "0")
    assert result.returncode == 2
    assert "positive integer" in result.stderr
