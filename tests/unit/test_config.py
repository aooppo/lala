from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from lala_workflow.config import ConfigError, load_project_config, parse_manifest


ROOT = Path(__file__).resolve().parents[2]


def test_load_project_config_maps_required_anchors_and_presets() -> None:
    config = load_project_config(ROOT)

    assert set(config.manifest.anchors) == {"face", "full_body", "scene"}
    assert set(config.presets) == {
        "baseline_identity",
        "home_decor",
        "pilot_home_keyframe",
        "pilot_product_keyframe",
        "pilot_talking_keyframe",
        "product_page_clean",
    }
    assert config.presets["baseline_identity"].default_count == 10
    assert config.manifest.qa_references["character_sheet"].generation_input is False


def test_manifest_rejects_duplicate_tag() -> None:
    data = yaml.safe_load((ROOT / "configs/anchor-manifest.yaml").read_text())
    duplicate = deepcopy(data)
    duplicate["anchors"]["scene"]["tag"] = duplicate["anchors"]["face"]["tag"]

    with pytest.raises(ConfigError, match="duplicate anchor tag"):
        parse_manifest(duplicate, ROOT)


def test_manifest_rejects_duplicate_role() -> None:
    data = yaml.safe_load((ROOT / "configs/anchor-manifest.yaml").read_text())
    duplicate = deepcopy(data)
    duplicate["anchors"]["scene"]["role"] = duplicate["anchors"]["face"]["role"]

    with pytest.raises(ConfigError, match="duplicate anchor role"):
        parse_manifest(duplicate, ROOT)


def test_manifest_rejects_missing_required_anchor() -> None:
    data = yaml.safe_load((ROOT / "configs/anchor-manifest.yaml").read_text())
    del data["anchors"]["face"]

    with pytest.raises(ConfigError, match="missing required anchors: face"):
        parse_manifest(data, ROOT)


def test_project_config_rejects_missing_anchor_file(project_root: Path) -> None:
    (project_root / "assets/approved_anchors/face/lala-face-front.png").unlink()

    with pytest.raises(ConfigError, match=r"invalid anchor face: image file does not exist"):
        load_project_config(project_root)
