from __future__ import annotations

from lala_workflow.characters.errors import CharacterValidationError, PreviewUnavailableError
from lala_workflow.characters.service import CharacterService
from lala_workflow.ui.app import friendly_error, view_state


def test_ui_module_imports_without_streamlit_and_view_state_is_ordinary_language(
    project_root, character_uploads
) -> None:
    service = CharacterService(project_root)
    profile = service.import_character(character_uploads, display_name="候选人物", created_by="test")
    service.build(profile.character_id)
    state = view_state(service.show(profile.character_id))
    assert state["display_name"] == "候选人物"
    assert state["show_final_decisions"] is False
    assert len(state["sources"]) == 3
    assert state["static_preview"] is None
    assert "provider" not in state
    assert "prompt" not in state


def test_ui_uses_role_specific_error_message() -> None:
    error = CharacterValidationError("internal detail", user_message="请上传正面清晰照片。")
    assert friendly_error(error) == "请上传正面清晰照片。"
    assert friendly_error(RuntimeError("secret detail")) == "操作未完成，请稍后重试；当前人物不会改变。"


def test_ui_hides_preview_environment_details_from_nontechnical_users() -> None:
    error = PreviewUnavailableError(
        "motion preview requires exact VIDEO_ALLOW_LIVE_CALLS=true"
    )
    message = friendly_error(error)
    assert message == (
        "预览服务暂时不可用。人物资料已安全保存，请稍后重试或联系技术人员；当前人物不会改变。"
    )
    assert "VIDEO_ALLOW_LIVE_CALLS" not in message
    assert "true" not in message
