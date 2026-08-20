from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageDraw

from lala_workflow.video.qa.subject_lock import (
    ColorRegionSubjectTracker,
    SubjectLockError,
    SubjectLockThresholds,
    analyze_subject_frames,
    load_subject_lock_thresholds,
)


def _frames(boxes):
    result = []
    for index, box in enumerate(boxes):
        image = Image.new("RGB", (160, 120), "black")
        if box:
            ImageDraw.Draw(image).rectangle(box, fill=(220, 20, 30))
        result.append((index, float(index), image))
    return result


def _thresholds(rate=0.8):
    return SubjectLockThresholds(10, 3, rate, sample_count=3, analysis_width=160, min_component_pixels=10)


def test_subject_lock_perfect_lock() -> None:
    result = analyze_subject_frames(_frames([(40, 20, 100, 110)] * 3), ColorRegionSubjectTracker(analysis_width=160, min_component_pixels=10), _thresholds())
    assert result.diagnostic_status == "WITHIN_THRESHOLD"
    assert result.first_to_last_dx_px == pytest.approx(0)
    assert result.first_to_last_dy_px == pytest.approx(0)
    assert result.max_scale_change_pct == pytest.approx(0)


def test_subject_lock_translation() -> None:
    result = analyze_subject_frames(_frames([(40, 10, 100, 70), (50, 25, 110, 85), (60, 40, 120, 100)]), ColorRegionSubjectTracker(analysis_width=160, min_component_pixels=10), _thresholds())
    assert result.first_to_last_dx_px == pytest.approx(20, abs=1)
    assert result.first_to_last_dy_px == pytest.approx(30, abs=1)
    assert result.diagnostic_status == "OUTSIDE_THRESHOLD"


def test_subject_lock_scale() -> None:
    result = analyze_subject_frames(_frames([(30, 10, 130, 110), (35, 15, 125, 105), (35, 15, 125, 105)]), ColorRegionSubjectTracker(analysis_width=160, min_component_pixels=10), _thresholds())
    assert result.first_to_last_width_change_pct == pytest.approx(-10, abs=1)
    assert result.first_to_last_height_change_pct == pytest.approx(-10, abs=1)
    assert result.diagnostic_status == "OUTSIDE_THRESHOLD"


def test_subject_lock_tracking_loss() -> None:
    result = analyze_subject_frames(_frames([(40, 20, 100, 100), None, None]), ColorRegionSubjectTracker(analysis_width=160, min_component_pixels=10), _thresholds())
    assert result.diagnostic_status == "INSUFFICIENT_EVIDENCE"
    assert result.first_to_last_dx_px is None
    assert result.max_scale_change_pct is None


def test_subject_lock_threshold_config(tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/video-qa.yaml").write_text(yaml.safe_dump({"subject_lock": {"max_center_drift_px": 12, "max_scale_change_pct": 4, "min_tracking_success_rate": 0.9}}))
    assert load_subject_lock_thresholds(tmp_path).max_center_drift_px == 12
    with pytest.raises(SubjectLockError):
        SubjectLockThresholds(0, 3, 0.8)
