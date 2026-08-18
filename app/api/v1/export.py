"""角色打包导出接口：将创建器内容打包为 LingChat 角色目录格式的 zip。"""
import json
import re
from typing import Dict, List, Optional
from urllib.parse import quote

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app.core.security import get_current_user
from app.models.user import User
from app.services.export_service import (
    build_character_zip,
    collect_emotions,
    file_ext_from,
    read_local_upload,
    safe_folder_name,
    validate_resource_folder,
)

router = APIRouter()

_CLOTHES_KEY_RE = re.compile(r"^clothes\.(\d+)\.(.+)$")


def _zip_response(buffer, folder: str) -> Response:
    filename = quote(f"{folder}.zip")
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}",
        },
    )


def _parse_body_part(raw: Optional[str]) -> Optional[dict]:
    """解析 body_part（触摸部位）YAML/JSON 文本。"""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"body_part YAML 解析失败：{e}")
    if parsed is None:
        return None
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="body_part 必须是 YAML 对象")
    return parsed


def _parse_clothes_portraits(form) -> Dict[str, dict]:
    """解析每套服装的专属立绘（clothes.<i>.xxx 字段组）。"""
    indexes = set()
    for key in form.keys():
        m = _CLOTHES_KEY_RE.match(key)
        if m:
            indexes.add(int(m.group(1)))

    result: Dict[str, dict] = {}
    for i in sorted(indexes):
        name = form.get(f"clothes.{i}.name")
        name = str(name).strip() if name else ""
        if not name:
            continue

        avatar = form.get(f"clothes.{i}.avatar")
        avatar_url = form.get(f"clothes.{i}.avatar_url")
        avatar_bytes = None
        avatar_ext = ".png"
        if avatar is not None:
            avatar_bytes = avatar.file.read()
            avatar_ext = file_ext_from(avatar.filename)
        elif avatar_url:
            avatar_bytes = read_local_upload(str(avatar_url))
            if avatar_bytes:
                avatar_ext = file_ext_from(str(avatar_url))

        existing = {}
        emotions_json = form.get(f"clothes.{i}.emotions_json")
        if emotions_json:
            try:
                existing = json.loads(str(emotions_json))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail=f"服装「{name}」的 emotions_json 不是合法的 JSON")
            if not isinstance(existing, dict):
                raise HTTPException(status_code=400, detail=f"服装「{name}」的 emotions_json 必须是 JSON 对象")

        emotions, emotion_exts = collect_emotions(
            form.getlist(f"clothes.{i}.emotion_names"),
            form.getlist(f"clothes.{i}.emotion_files"),
            existing,
        )

        if not avatar_bytes and not emotions:
            continue  # 没有立绘的服装不生成子目录

        result[safe_folder_name(name, f"clothes{i}")] = {
            "avatar_bytes": avatar_bytes,
            "avatar_ext": avatar_ext,
            "emotions": emotions,
            "emotion_exts": emotion_exts,
        }
    return result


@router.post("/character")
async def export_character(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """将角色创建器内容打包为 zip 下载（不发布到社区）。

    表单字段：
      settings                     角色设定 JSON 字符串（必须包含 resource_folder）
      avatar / avatar_url          新头像文件或已有头像的本地路径
      emotion_names / emotion_files 新上传的情绪立绘
      emotions_json                已有情绪立绘 {情绪名: 本地URL} 的 JSON 字符串
      clothes.<i>.name            第 i 套服装的名称（作为 avatar/ 子目录名）
      clothes.<i>.avatar / .avatar_url / .emotion_names / .emotion_files / .emotions_json
                                  该服装的专属立绘（可选）
    """
    form = await request.form()

    settings_raw = form.get("settings")
    if not settings_raw:
        raise HTTPException(status_code=400, detail="缺少 settings 参数")
    try:
        settings_dict = json.loads(str(settings_raw))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="settings 不是合法的 JSON")
    if not isinstance(settings_dict, dict):
        raise HTTPException(status_code=400, detail="settings 必须是 JSON 对象")

    # body_part 支持直接粘贴 YAML 文本
    settings_dict["body_part"] = _parse_body_part(settings_dict.get("body_part"))

    folder = validate_resource_folder(settings_dict.get("resource_folder"))
    if not folder:
        raise HTTPException(status_code=400, detail="请填写角色目录名（resource_folder）")

    # 头像
    avatar = form.get("avatar")
    avatar_url = form.get("avatar_url")
    avatar_bytes = None
    avatar_ext = ".png"
    if avatar is not None:
        avatar_bytes = avatar.file.read()
        avatar_ext = file_ext_from(avatar.filename)
    elif avatar_url:
        avatar_bytes = read_local_upload(str(avatar_url))
        if avatar_bytes:
            avatar_ext = file_ext_from(str(avatar_url))
    if not avatar_bytes:
        raise HTTPException(status_code=400, detail="请上传角色头像")

    # 情绪立绘
    existing_emotions = {}
    emotions_json = form.get("emotions_json")
    if emotions_json:
        try:
            existing_emotions = json.loads(str(emotions_json))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="emotions_json 不是合法的 JSON")
        if not isinstance(existing_emotions, dict):
            raise HTTPException(status_code=400, detail="emotions_json 必须是 JSON 对象")
    emotions, emotion_exts = collect_emotions(
        form.getlist("emotion_names"), form.getlist("emotion_files"), existing_emotions
    )
    if not emotions:
        raise HTTPException(status_code=400, detail="请至少上传 1 个情绪立绘")

    clothes_portraits = _parse_clothes_portraits(form)

    buffer = build_character_zip(
        settings_dict, folder, avatar_bytes, avatar_ext, emotions, emotion_exts, clothes_portraits
    )
    return _zip_response(buffer, folder)
