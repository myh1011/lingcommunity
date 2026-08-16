"""角色打包导出接口：将创建器内容打包为 LingChat 角色目录格式的 zip。"""
import json
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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


def _zip_response(buffer, folder: str) -> Response:
    filename = quote(f"{folder}.zip")
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{filename}",
        },
    )


@router.post("/character")
async def export_character(
    settings: str = Form(...),
    avatar: Optional[UploadFile] = File(None),
    avatar_url: Optional[str] = Form(None),
    emotion_names: Optional[List[str]] = Form(None),
    emotion_files: Optional[List[UploadFile]] = File(None),
    emotions_json: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """将角色创建器内容打包为 zip 下载（不发布到社区）。

    settings: 角色设定 JSON 字符串（必须包含 resource_folder）
    avatar / avatar_url: 新头像文件或已有头像的本地路径
    emotion_names/emotion_files: 新上传的情绪立绘
    emotions_json: 已有情绪立绘 {情绪名: 本地URL} 的 JSON 字符串
    """
    try:
        settings_dict = json.loads(settings)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="settings 不是合法的 JSON")
    if not isinstance(settings_dict, dict):
        raise HTTPException(status_code=400, detail="settings 必须是 JSON 对象")

    folder = validate_resource_folder(settings_dict.get("resource_folder"))
    if not folder:
        raise HTTPException(status_code=400, detail="请填写角色目录名（resource_folder）")

    # 头像
    avatar_bytes = None
    avatar_ext = ".png"
    if avatar is not None:
        avatar_bytes = avatar.file.read()
        avatar_ext = file_ext_from(avatar.filename)
    elif avatar_url:
        avatar_bytes = read_local_upload(avatar_url)
        if avatar_bytes:
            avatar_ext = file_ext_from(str(avatar_url))
    if not avatar_bytes:
        raise HTTPException(status_code=400, detail="请上传角色头像")

    # 情绪立绘
    existing_emotions = {}
    if emotions_json:
        try:
            existing_emotions = json.loads(emotions_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="emotions_json 不是合法的 JSON")
        if not isinstance(existing_emotions, dict):
            raise HTTPException(status_code=400, detail="emotions_json 必须是 JSON 对象")
    emotions, emotion_exts = collect_emotions(emotion_names, emotion_files, existing_emotions)
    if not emotions:
        raise HTTPException(status_code=400, detail="请至少上传 1 个情绪立绘")

    buffer = build_character_zip(settings_dict, folder, avatar_bytes, avatar_ext, emotions, emotion_exts)
    return _zip_response(buffer, folder)
