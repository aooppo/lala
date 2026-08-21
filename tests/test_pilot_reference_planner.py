from __future__ import annotations

import json
from pathlib import Path

import pytest

from lala_workflow.characters.errors import CharacterStateError
from lala_workflow.characters.references import plan_pilot_references, select_references
from lala_workflow.characters.resolver import CharacterResolver
from lala_workflow.cli import build_parser
from lala_workflow.hashing import sha256_file
from lala_workflow.runner import RunOptions, run_generation


PDP_URL = "https://decorolala.com/products/in3725"
SKU = "IN3725"


def _active_profile(project_root: Path):
    return CharacterResolver(project_root).resolve(None).profile


def _external_images(project_root: Path, image_factory):
    hero = image_factory(
        project_root / "tmp/henry/01-hero.jpg", size=(1248, 832), color=(90, 55, 30)
    )
    product = image_factory(
        project_root / "tmp/henry/02.jpg", size=(1280, 1280), color=(125, 75, 35)
    )
    return hero, product


def test_k1_active_character_resolves_exact_role_aware_slots(
    project_root, image_factory
) -> None:
    hero, _ = _external_images(project_root, image_factory)

    plan = plan_pilot_references(
        project_root,
        _active_profile(project_root),
        preset="pilot_home_keyframe",
        scene_reference=hero.relative_to(project_root),
        product_reference=None,
        source_url=PDP_URL,
        sku=SKU,
        max_references=3,
    )

    assert [item.slot for item in plan] == [1, 2, 3]
    assert [item.semantic_role for item in plan] == [
        "character_face",
        "character_full_body",
        "external_scene_product_reference",
    ]
    assert plan[2].sha256 == sha256_file(hero)


def test_k3_active_character_resolves_exact_role_aware_slots(
    project_root, image_factory
) -> None:
    hero, product = _external_images(project_root, image_factory)

    plan = plan_pilot_references(
        project_root,
        _active_profile(project_root),
        preset="pilot_product_keyframe",
        scene_reference=hero,
        product_reference=product,
        source_url=PDP_URL,
        sku=SKU,
        max_references=3,
    )

    assert [item.semantic_role for item in plan] == [
        "character_face",
        "external_scene_product_reference",
        "external_product_reference",
    ]
    assert [item.sha256 for item in plan[1:]] == [sha256_file(hero), sha256_file(product)]
    assert all(item.source_url == PDP_URL and item.sku == SKU for item in plan[1:])


def test_k2_reference_selection_behavior_is_unchanged(
    project_root, character_uploads
) -> None:
    from lala_workflow.characters.service import CharacterService

    profile = CharacterService(project_root).import_character(character_uploads, created_by="test")
    selection = select_references(profile, scene=None, context="medium", max_references=3)

    assert [item.logical_name for item in selection.references] == [
        "face",
        "three_quarter",
        "full_body",
    ]


def test_k1_dry_run_keeps_external_reference_and_records_provenance(
    project_root, image_factory
) -> None:
    hero, _ = _external_images(project_root, image_factory)

    outcome = run_generation(
        project_root,
        RunOptions(
            preset="pilot_home_keyframe",
            count=1,
            scene_reference=hero,
            reference_source_url=PDP_URL,
            reference_sku=SKU,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())["requests"][0]
    assert [item["semantic_role"] for item in request["references"]] == [
        "character_face",
        "character_full_body",
        "external_scene_product_reference",
    ]
    assert request["references"][2]["path"] == str(hero.resolve())
    assert request["references"][2]["sha256"] == sha256_file(hero)
    evidence = json.loads((outcome.run_dir / "anchor-hashes.json").read_text())
    assert evidence["references"][2] == {
        "height": 832,
        "mime_type": "image/jpeg",
        "name": "scene_reference",
        "path": str(hero.resolve()),
        "semantic_role": "external_scene_product_reference",
        "sha256": sha256_file(hero),
        "sku": SKU,
        "slot": 3,
        "source_type": "external_local_pdp_reference",
        "source_url": PDP_URL,
        "tag": "henry_scene",
        "width": 1248,
    }


def test_k3_dry_run_contains_both_pdp_references_without_provider_call(
    project_root, image_factory
) -> None:
    hero, product = _external_images(project_root, image_factory)

    outcome = run_generation(
        project_root,
        RunOptions(
            preset="pilot_product_keyframe",
            count=1,
            scene_reference=hero,
            product_reference=product,
            reference_source_url=PDP_URL,
            reference_sku=SKU,
        ),
    )

    request = json.loads((outcome.run_dir / "request.json").read_text())["requests"][0]
    assert [item["path"] for item in request["references"]] == [
        str((project_root / "assets/approved_anchors/face/lala-face-front.png").resolve()),
        str(hero.resolve()),
        str(product.resolve()),
    ]
    assert outcome.result.status.value == "DRY_RUN"
    assert outcome.result.tasks == ()
    assert outcome.result.outputs == ()


def test_missing_invalid_and_symlink_external_references_fail_before_run(
    project_root, image_factory
) -> None:
    profile = _active_profile(project_root)
    missing = project_root / "tmp/missing.jpg"
    with pytest.raises(CharacterStateError, match="missing or unsafe"):
        plan_pilot_references(
            project_root,
            profile,
            preset="pilot_home_keyframe",
            scene_reference=missing,
            product_reference=None,
            source_url=PDP_URL,
            sku=SKU,
            max_references=3,
        )

    invalid = project_root / "tmp/not-image.jpg"
    invalid.parent.mkdir(parents=True, exist_ok=True)
    invalid.write_text("not an image")
    with pytest.raises(CharacterStateError, match="invalid external reference image"):
        plan_pilot_references(
            project_root,
            profile,
            preset="pilot_home_keyframe",
            scene_reference=invalid,
            product_reference=None,
            source_url=PDP_URL,
            sku=SKU,
            max_references=3,
        )

    target = image_factory(project_root / "tmp/target.jpg")
    symlink = project_root / "tmp/link.jpg"
    symlink.symlink_to(target)
    with pytest.raises(CharacterStateError, match="unsafe symlink"):
        plan_pilot_references(
            project_root,
            profile,
            preset="pilot_home_keyframe",
            scene_reference=symlink,
            product_reference=None,
            source_url=PDP_URL,
            sku=SKU,
            max_references=3,
        )


def test_duplicate_reference_bytes_are_not_sent_and_reference_limit_hard_fails(
    project_root, image_factory
) -> None:
    hero, _ = _external_images(project_root, image_factory)
    profile = _active_profile(project_root)

    with pytest.raises(CharacterStateError, match="duplicate reference bytes"):
        plan_pilot_references(
            project_root,
            profile,
            preset="pilot_product_keyframe",
            scene_reference=hero,
            product_reference=hero,
            source_url=PDP_URL,
            sku=SKU,
            max_references=3,
        )
    with pytest.raises(CharacterStateError, match="BLOCKED_REFERENCE_LIMIT"):
        plan_pilot_references(
            project_root,
            profile,
            preset="pilot_home_keyframe",
            scene_reference=hero,
            product_reference=None,
            source_url=PDP_URL,
            sku=SKU,
            max_references=2,
        )


def test_cli_exposes_semantic_external_reference_arguments() -> None:
    args = build_parser().parse_args(
        [
            "generate",
            "--preset",
            "pilot_product_keyframe",
            "--scene-reference",
            "tmp/01-hero.jpg",
            "--product-reference",
            "tmp/02.jpg",
            "--reference-source-url",
            PDP_URL,
            "--reference-sku",
            SKU,
            "--dry-run",
        ]
    )

    assert args.scene_reference == Path("tmp/01-hero.jpg")
    assert args.product_reference == Path("tmp/02.jpg")
    assert args.reference_source_url == PDP_URL
    assert args.reference_sku == SKU
