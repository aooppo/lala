from __future__ import annotations

from pathlib import Path
from typing import Any

from lala_workflow.characters.domain import CharacterStatus, CharacterUpload, CharacterView
from lala_workflow.characters.errors import CharacterError
from lala_workflow.characters.service import CharacterService


STATUS_LABELS = {
    CharacterStatus.DRAFT: "资料已保存",
    CharacterStatus.VALIDATING: "正在检查照片",
    CharacterStatus.BUILDING: "正在创建人物",
    CharacterStatus.READY_FOR_GENERATION: "等待生成预览",
    CharacterStatus.READY_FOR_PREVIEW: "正在生成动态预览",
    CharacterStatus.READY_FOR_APPROVAL: "等待最终决定",
    CharacterStatus.ACTIVE: "正在使用",
    CharacterStatus.INACTIVE: "历史人物",
    CharacterStatus.FAILED: "预览未完成，可重试",
    CharacterStatus.REJECTED: "已拒绝",
}


def view_state(view: CharacterView) -> dict[str, Any]:
    build = view.build
    ready = view.profile.status is CharacterStatus.READY_FOR_APPROVAL
    return {
        "character_id": view.profile.character_id,
        "display_name": view.profile.display_name or view.profile.character_id,
        "status": STATUS_LABELS[view.profile.status],
        "is_active": view.is_active,
        "sources": [item.path.as_posix() for item in view.profile.references.values()],
        "static_preview": build.static_preview.path.as_posix() if build and build.static_preview else None,
        "motion_preview": build.motion_preview.path.as_posix() if build and build.motion_preview else None,
        "technical_checks": dict(build.technical_checks) if build else {},
        "diagnostic": dict(build.subject_lock or {}) if build else {},
        "show_final_decisions": ready and not view.is_active,
    }


def friendly_error(error: Exception) -> str:
    if isinstance(error, CharacterError):
        return error.user_message
    return "操作未完成，请稍后重试；当前人物不会改变。"


def run(project_root: Path | None = None) -> None:
    # Streamlit remains an optional dependency; CLI/package imports never load it.
    import streamlit as st

    root = (project_root or Path.cwd()).resolve()
    service = CharacterService(root)
    st.set_page_config(page_title="人物更换", page_icon="✨", layout="wide")
    st.title("人物更换")
    st.caption("上传三张照片，查看静态和动态预览，最后只需选择拒绝或启用。")

    registry = service.list_characters()
    choices = list(registry.characters)
    initial = st.session_state.get("character_id", registry.active_character)
    selected = st.selectbox(
        "当前 / 历史人物",
        choices,
        index=choices.index(initial) if initial in choices else 0,
        format_func=lambda item: registry.characters[item].display_name or item,
    )
    st.session_state["character_id"] = selected

    with st.container(border=True):
        st.subheader("创建新人物")
        name = st.text_input("人物名称（可选）")
        face = st.file_uploader("正面清晰照片", type=["png", "jpg", "jpeg", "webp"], key="face")
        body = st.file_uploader("全身照片", type=["png", "jpg", "jpeg", "webp"], key="body")
        three = st.file_uploader("3/4 角度照片", type=["png", "jpg", "jpeg", "webp"], key="three")
        with st.expander("更多参考照片（可选）"):
            side = st.file_uploader("侧面照片", type=["png", "jpg", "jpeg", "webp"], key="side")
            expression = st.file_uploader(
                "表情照片", type=["png", "jpg", "jpeg", "webp"], key="expression"
            )
            product_pose = st.file_uploader(
                "产品展示姿势", type=["png", "jpg", "jpeg", "webp"], key="product_pose"
            )
            hair = st.file_uploader(
                "发型 / 配饰参考", type=["png", "jpg", "jpeg", "webp"], key="hair"
            )
        if st.button("创建人物", type="primary", use_container_width=True):
            if not all((face, body, three)):
                st.error("请上传正面、全身和 3/4 角度三张照片。")
            else:
                try:
                    uploads = {
                        "face": CharacterUpload("face", face.getvalue(), face.name, face.type),
                        "full_body": CharacterUpload("full_body", body.getvalue(), body.name, body.type),
                        "three_quarter": CharacterUpload(
                            "three_quarter", three.getvalue(), three.name, three.type
                        ),
                    }
                    for role, upload in (
                        ("side", side),
                        ("expression", expression),
                        ("product_pose", product_pose),
                        ("hair_accessory", hair),
                    ):
                        if upload is not None:
                            uploads[role] = CharacterUpload(
                                role, upload.getvalue(), upload.name, upload.type
                            )
                    profile = service.import_character(
                        uploads,
                        display_name=name or None,
                        created_by="local_ui",
                    )
                    service.build(profile.character_id)
                    service.preview(profile.character_id, live=False)
                    st.session_state["character_id"] = profile.character_id
                    st.success("人物资料已创建并完成安全检查。预览生成尚未获授权时，可稍后继续。")
                    st.rerun()
                except Exception as exc:
                    st.error(friendly_error(exc))

    view = service.show(st.session_state["character_id"])
    state = view_state(view)
    st.subheader(state["display_name"])
    st.write("当前状态：", "正在使用" if state["is_active"] else state["status"])
    columns = st.columns(3)
    for column, reference in zip(columns, view.profile.references.values()):
        column.image(str(root / reference.path), caption=reference.logical_name)

    if state["static_preview"]:
        st.image(str(root / state["static_preview"]), caption="静态预览（非生产批准素材）")
    if state["motion_preview"]:
        st.video(str(root / state["motion_preview"]), format="video/mp4")
    if not state["is_active"] and view.profile.status in {
        CharacterStatus.READY_FOR_GENERATION,
        CharacterStatus.FAILED,
    }:
        if st.button("生成静态与动态预览", use_container_width=True):
            try:
                service.preview(view.profile.character_id, live=True)
                st.rerun()
            except Exception as exc:
                st.error(friendly_error(exc))

    with st.expander("技术检查与诊断（仅供参考）"):
        st.json({"technical_checks": state["technical_checks"], "diagnostic_only": state["diagnostic"]})

    if state["show_final_decisions"]:
        reject, activate = st.columns(2)
        if reject.button("拒绝", use_container_width=True):
            try:
                service.reject(view.profile.character_id, expected_revision=view.registry_revision)
                st.rerun()
            except Exception as exc:
                st.error(friendly_error(exc))
        if activate.button("批准并启用", type="primary", use_container_width=True):
            try:
                service.approve_and_activate(
                    view.profile.character_id, expected_revision=view.registry_revision
                )
                st.success("人物已安全切换。")
                st.rerun()
            except Exception as exc:
                st.error(friendly_error(exc))


if __name__ == "__main__":
    run()
