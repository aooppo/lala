from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .prompts import load_video_prompt, normalize_runway_prompt_text, utf16_code_units


PROJECT_TARGET_UTF16 = 850
PROVIDER_LIMIT_UTF16 = 1000
COFFEE_TABLE_PROMPTS = {
    "TASK-01": Path("prompts/coffee-table-task-01-establish-approach-v4.txt"),
    "TASK-02": Path("prompts/coffee-table-task-02-place-turn-sofa-v3.txt"),
    "TASK-03": Path("prompts/coffee-table-task-03-room-beauty-v5.txt"),
    "TASK-04": Path("prompts/coffee-table-task-04-final-sofa-hero-v6.txt"),
}


class CoffeeTablePromptPreflightError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CoffeeTablePromptCheck:
    task_id: str
    path: Path
    utf16_units: int

    @property
    def target_pass(self) -> bool:
        return self.utf16_units <= PROJECT_TARGET_UTF16

    @property
    def provider_pass(self) -> bool:
        return self.utf16_units <= PROVIDER_LIMIT_UTF16


def preflight_coffee_table_prompts(project_root: Path) -> tuple[CoffeeTablePromptCheck, ...]:
    root = project_root.resolve()
    checks: list[CoffeeTablePromptCheck] = []
    for task_id, relative_path in COFFEE_TABLE_PROMPTS.items():
        path = root / relative_path
        if not path.is_file() or path.is_symlink():
            raise CoffeeTablePromptPreflightError(f"Coffee Table prompt is missing: {relative_path}")
        resolved = load_video_prompt(root, relative_path)
        text = normalize_runway_prompt_text(resolved.text)
        if not text.strip():
            raise CoffeeTablePromptPreflightError(f"Coffee Table prompt is empty: {relative_path}")
        units = utf16_code_units(text)
        if units > PROVIDER_LIMIT_UTF16:
            raise CoffeeTablePromptPreflightError(
                f"{task_id} prompt exceeds provider UTF-16 limit "
                f"({units} > {PROVIDER_LIMIT_UTF16}): {relative_path}"
            )
        if units > PROJECT_TARGET_UTF16:
            raise CoffeeTablePromptPreflightError(
                f"{task_id} prompt exceeds project UTF-16 target "
                f"({units} > {PROJECT_TARGET_UTF16}): {relative_path}"
            )
        checks.append(CoffeeTablePromptCheck(task_id, relative_path, units))
    return tuple(checks)


def format_preflight(checks: tuple[CoffeeTablePromptCheck, ...]) -> str:
    lines = ["Coffee Table Runway Prompt UTF-16 Preflight", ""]
    for check in checks:
        lines.extend(
            [
                check.task_id,
                f"file: {check.path.as_posix()}",
                f"utf16_units: {check.utf16_units}",
                f"project_target: <={PROJECT_TARGET_UTF16}",
                f"provider_limit: <={PROVIDER_LIMIT_UTF16}",
                f"status: {'PASS' if check.target_pass and check.provider_pass else 'FAIL'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    print(format_preflight(preflight_coffee_table_prompts(root)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
