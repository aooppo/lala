from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from ...hashing import sha256_file
from .subject_lock import analyze_video_to_artifacts, load_subject_lock_thresholds


class ReviewPackageError(ValueError):
    pass


_SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\bauthorization\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|api[_-]?secret)\s*[:=]\s*['\"]?\S+", re.IGNORECASE),
    re.compile(r"[?&](?:X-Amz-Signature|Signature|token)=[^\s&]+", re.IGNORECASE),
)
_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".jsonl"}


def finalize_subject_lock_package(project_root: Path, run_id: str, package_dir: Path) -> dict[str, Any]:
    root = project_root.resolve()
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ReviewPackageError("invalid motion smoke run ID")
    run_dir = (root / "runs" / run_id).resolve()
    if (root / "runs").resolve() not in run_dir.parents or not run_dir.is_dir():
        raise ReviewPackageError(f"motion smoke run does not exist: {run_id}")
    package = package_dir if package_dir.is_absolute() else root / package_dir
    package = package.resolve()
    packages_root = (root / "outputs/review-packages").resolve()
    if packages_root not in package.parents or not package.is_dir():
        raise ReviewPackageError("package directory must exist under outputs/review-packages")
    video = package / "video.mp4"
    review = package / "review.csv"
    if not video.is_file() or not review.is_file():
        raise ReviewPackageError("review package requires video.mp4 and review.csv")
    run_review = run_dir / "review.csv"
    if review.read_bytes() != run_review.read_bytes():
        raise ReviewPackageError("packaged review must remain the byte-identical blank run review")
    try:
        request = json.loads((run_dir / "request.json").read_text(encoding="utf-8"))
        results = json.loads((run_dir / "provider-results.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewPackageError("motion smoke run evidence is unreadable") from exc
    if request.get("action") != "motion_smoke" or results.get("status") != "SUCCEEDED":
        raise ReviewPackageError("subject-lock packages require a successful motion smoke run")
    artifacts = [
        artifact
        for row in (results.get("results") or [])
        for artifact in (row.get("artifacts") or [])
        if isinstance(artifact, dict)
    ]
    if len(artifacts) != 1 or artifacts[0].get("sha256") != sha256_file(video):
        raise ReviewPackageError("package video does not match motion smoke evidence")
    protected = {video: video.read_bytes(), review: review.read_bytes(), run_review: run_review.read_bytes()}
    thresholds = load_subject_lock_thresholds(root)
    result = analyze_video_to_artifacts(video, package, thresholds=thresholds, run_id=run_id)
    for path, original in protected.items():
        if path.read_bytes() != original:
            raise ReviewPackageError(f"diagnostics changed protected evidence: {path.name}")
    manifest = _write_checksum_manifest(package)
    archive = package.with_suffix(".zip")
    _write_deterministic_zip(package, archive)
    verify = verify_review_package(package, archive)
    secret_scan = scan_review_package_secrets(package)
    if not secret_scan["passed"]:
        raise ReviewPackageError("review package secret scan failed")
    return {
        "run_id": run_id,
        "package_dir": package.relative_to(root).as_posix(),
        "archive": archive.relative_to(root).as_posix(),
        "subject_lock": result.evidence(run_id=run_id),
        "sha256_manifest": manifest.relative_to(root).as_posix(),
        "integrity": verify,
        "secret_scan": secret_scan,
        "human_review_modified": False,
        "provider_calls": 0,
    }


def _write_checksum_manifest(package: Path) -> Path:
    manifest = package / "SHA256SUMS.txt"
    members = sorted(
        path for path in package.rglob("*") if path.is_file() and path != manifest
    )
    lines = [f"{sha256_file(path)}  ./{path.relative_to(package).as_posix()}" for path in members]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def _write_deterministic_zip(package: Path, archive: Path) -> None:
    temporary = archive.with_name(f".{archive.name}.tmp")
    temporary.unlink(missing_ok=True)
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(item for item in package.rglob("*") if item.is_file()):
            relative = Path(package.name) / path.relative_to(package)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes())
    temporary.replace(archive)


def verify_review_package(package: Path, archive: Path | None = None) -> dict[str, Any]:
    manifest = package / "SHA256SUMS.txt"
    if not manifest.is_file():
        raise ReviewPackageError("review package checksum manifest is missing")
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, separator, relative = line.partition("  ./")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ReviewPackageError("review package checksum manifest is invalid")
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ReviewPackageError("review package checksum path is unsafe")
        expected[relative] = digest
    actual_members = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file() and path != manifest
    }
    if set(expected) != actual_members:
        raise ReviewPackageError("review package checksum membership mismatch")
    for relative, digest in expected.items():
        if sha256_file(package / relative) != digest:
            raise ReviewPackageError(f"review package checksum mismatch: {relative}")
    archive = archive or package.with_suffix(".zip")
    if not archive.is_file():
        raise ReviewPackageError("review package ZIP is missing")
    expected_zip = {f"{package.name}/{relative}" for relative in actual_members | {"SHA256SUMS.txt"}}
    with zipfile.ZipFile(archive) as source:
        names = set(source.namelist())
        if names != expected_zip or source.testzip() is not None:
            raise ReviewPackageError("review package ZIP integrity or membership mismatch")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ReviewPackageError("review package ZIP contains an unsafe path")
    return {"passed": True, "checksummed_files": len(expected), "zip_members": len(expected_zip)}


def scan_review_package_secrets(package: Path) -> dict[str, Any]:
    matches: list[str] = []
    scanned = 0
    for path in sorted(item for item in package.rglob("*") if item.is_file() and item.suffix.lower() in _TEXT_SUFFIXES):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            matches.append(path.relative_to(package).as_posix())
            continue
        if any(pattern.search(text) for pattern in _SECRET_PATTERNS):
            matches.append(path.relative_to(package).as_posix())
    return {"passed": not matches, "files_scanned": scanned, "matches": matches}
