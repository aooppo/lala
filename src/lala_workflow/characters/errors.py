from __future__ import annotations

from dataclasses import dataclass

from ..redaction import redact_text


ROLE_LABELS = {
    "face": "正面清晰照片",
    "full_body": "全身照片",
    "three_quarter": "3/4 角度照片",
    "side": "侧面照片",
    "expression": "表情照片",
    "product_pose": "产品展示姿势",
    "hair_accessory": "发型 / 配饰参考",
}


class CharacterError(ValueError):
    code = "character_error"

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(redact_text(message))
        self.user_message = redact_text(user_message or message)


class CharacterValidationError(CharacterError):
    code = "character_validation_error"


class CharacterIntegrityError(CharacterError):
    code = "character_integrity_error"


class CharacterStateError(CharacterError):
    code = "character_state_error"


class RegistryConflictError(CharacterError):
    code = "registry_conflict"


class PreviewUnavailableError(CharacterError):
    code = "preview_unavailable"

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(
            message,
            user_message=(
                user_message
                or "预览服务暂时不可用。人物资料已安全保存，请稍后重试或联系技术人员；当前人物不会改变。"
            ),
        )


def upload_message(role: str, reason: str) -> str:
    label = ROLE_LABELS.get(role, "人物素材")
    messages = {
        "missing": f"请上传{label}。",
        "empty": f"{label}是空文件，请重新上传 PNG/JPG/WebP 图片。",
        "oversized": f"{label}文件过大，请选择更小的 PNG/JPG/WebP 图片。",
        "unsupported": f"{label}格式不支持，请上传 PNG/JPG/WebP 图片。",
        "corrupt": f"{label}无法读取，请重新上传 PNG/JPG/WebP 图片。",
        "duplicate": f"{label}与另一张必填照片内容相同，请上传对应角度的独立照片。",
    }
    return messages.get(reason, f"{label}无法使用，请重新上传。")
