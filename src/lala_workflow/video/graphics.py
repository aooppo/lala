from __future__ import annotations

import json
import os
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, ImageDraw, ImageFont

from ..config import load_yaml
from ..hashing import assert_within_directory, sha256_file
from .config import VideoConfigError


DRAFT_NOTICE = "DRAFT / NOT MTL APPROVED"
APPROVED_STATUSES = {"approved", "production_approved"}


@dataclass(frozen=True, slots=True)
class GraphicArtifact:
    asset_id: str
    path: Path
    sha256: str
    version: str
    approval_status: str
    draft: bool
    reviewer: str | None
    reviewed_at: str | None
    source_reference: str | None
    provenance: Mapping[str, Any]


def load_brand_assets(project_root: Path) -> dict[str, GraphicArtifact | None]:
    root = project_root.resolve()
    raw = load_yaml(root / "configs/brand-assets.yaml")
    assets = raw.get("assets")
    if not isinstance(assets, Mapping):
        raise VideoConfigError("brand-assets assets must be a mapping")
    result: dict[str, GraphicArtifact | None] = {}
    for asset_id, value in assets.items():
        if not isinstance(value, Mapping):
            raise VideoConfigError(f"brand asset {asset_id} must be a mapping")
        status = str(value.get("approval_status") or "missing")
        path_value = value.get("path")
        if status not in APPROVED_STATUSES:
            if path_value not in {None, ""}:
                raise VideoConfigError(
                    f"unapproved brand asset {asset_id} must not be loaded as an approved source"
                )
            result[str(asset_id)] = None
            continue
        if not path_value:
            raise VideoConfigError(f"approved brand asset {asset_id} path is required")
        relative = Path(str(path_value))
        if relative.is_absolute() or ".." in relative.parts:
            raise VideoConfigError(f"approved brand asset {asset_id} path is invalid")
        try:
            path = assert_within_directory(
                root / relative, root / "assets/brand/approved"
            )
        except ValueError as exc:
            raise VideoConfigError(
                f"approved brand asset {asset_id} must remain under assets/brand/approved"
            ) from exc
        expected = str(value.get("sha256") or "").lower()
        if not path.is_file() or sha256_file(path) != expected:
            raise VideoConfigError(f"approved brand asset {asset_id} digest mismatch")
        reviewer = str(value.get("reviewer") or "").strip()
        reviewed_at = str(value.get("reviewed_at") or "").strip()
        if not reviewer or not _timezone_timestamp(reviewed_at):
            raise VideoConfigError(
                f"approved brand asset {asset_id} requires reviewer and timezone reviewed_at"
            )
        version = str(value.get("version") or "").strip()
        source_reference = str(value.get("source_reference") or "").strip()
        if not version or not source_reference:
            raise VideoConfigError(
                f"approved brand asset {asset_id} requires version and source_reference"
            )
        result[str(asset_id)] = GraphicArtifact(
            asset_id=str(asset_id),
            path=path,
            sha256=expected,
            version=version,
            approval_status=status,
            draft=False,
            reviewer=reviewer,
            reviewed_at=reviewed_at,
            source_reference=source_reference,
            provenance={
                "kind": "approved_brand_asset",
                "configured_path": relative.as_posix(),
                "source_reference": source_reference,
            },
        )
    return result


def resolve_brand_graphic(
    project_root: Path,
    *,
    run_id: str,
    asset_id: str,
    exact_caption: str,
    script_sha256: str | None = None,
) -> GraphicArtifact:
    root = project_root.resolve()
    configured = load_brand_assets(root)
    if asset_id not in configured:
        raise VideoConfigError(f"unknown brand asset: {asset_id}")
    approved = configured[asset_id]
    if approved is not None:
        return approved
    output_dir = (root / "outputs/graphics" / run_id).resolve()
    graphics_root = (root / "outputs/graphics").resolve()
    if graphics_root not in output_dir.parents:
        raise VideoConfigError("graphic output escaped outputs/graphics")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{asset_id}-draft.png"
    sidecar = target.with_suffix(".json")
    if target.exists() or sidecar.exists():
        raise VideoConfigError(f"draft graphic output already exists: {target.name}")
    _render_draft_png(target, exact_caption)
    digest = sha256_file(target)
    evidence = {
        "asset_id": asset_id,
        "path": target.relative_to(root).as_posix(),
        "sha256": digest,
        "version": "deterministic-draft-v1",
        "approval_status": "draft",
        "notice": DRAFT_NOTICE,
        "exact_caption": exact_caption,
        "script_sha256": script_sha256,
        "generator": "Pillow/system-font deterministic local graphic",
        "ai_generated": False,
    }
    _write_json_new(sidecar, evidence)
    return GraphicArtifact(
        asset_id=asset_id,
        path=target,
        sha256=digest,
        version="deterministic-draft-v1",
        approval_status="draft",
        draft=True,
        reviewer=None,
        reviewed_at=None,
        source_reference=None,
        provenance={**evidence, "sidecar": sidecar.relative_to(root).as_posix()},
    )


def resolve_preset_graphics(
    project_root: Path,
    *,
    preset: str,
    run_id: str,
    exact_script: bytes,
    script_sha256: str,
) -> tuple[GraphicArtifact, ...]:
    """Resolve only the local graphics that are actually present in the selected preset."""

    try:
        caption = exact_script.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VideoConfigError("exact MTL script must be UTF-8 for local graphic rendering") from exc
    if preset == "tooltip":
        return (
            resolve_brand_graphic(
                project_root,
                run_id=run_id,
                asset_id="five_lala_likes",
                exact_caption=caption,
                script_sha256=script_sha256,
            ),
        )
    # The current product/home ``closing`` templates reprise the selected
    # talking performance; they are not configured as end-card shots.  An
    # end-card is resolved only when a preset explicitly adds that local role.
    return ()


def _render_draft_png(target: Path, caption: str) -> None:
    width, height = 960, 360
    image = Image.new("RGBA", (width, height), (38, 18, 52, 235))
    draw = ImageDraw.Draw(image)
    title_font = _font(30)
    body_font = _font(26)
    draw.rounded_rectangle(
        (4, 4, width - 5, height - 5), radius=28, outline=(242, 188, 255, 255), width=4
    )
    draw.text((36, 28), DRAFT_NOTICE, font=title_font, fill=(255, 198, 72, 255))
    wrapped = "\n".join(textwrap.wrap(caption.rstrip("\n"), width=58))
    draw.multiline_text(
        (36, 92), wrapped, font=body_font, fill=(255, 255, 255, 255), spacing=10
    )
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        image.save(temporary, format="PNG", optimize=False)
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
        image.close()


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "Arial Unicode.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _write_json_new(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            json.dump(dict(value), output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _timezone_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None
