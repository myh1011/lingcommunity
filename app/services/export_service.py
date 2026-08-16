"""角色导出打包：将创建器内容打包为 LingChat 角色目录格式的 zip。

目录格式（参考 LingChat data/game_data/characters/<目录名>/）：
    <目录名>/
    ├── settings.yml                 # 角色设定（与 CharacterSettings 字段一致）
    ├── ai模式<角色名>.txt            # system_prompt 文本
    └── avatar/
        ├── 头像.<ext>
        └── <情绪>.<ext>             # 哭泣→伤心、难为情→羞耻（与 LingChat 落盘名一致）
"""
import io
import os
import re
import zipfile
from typing import Dict, List, Optional, Any, Tuple

import yaml
from fastapi import HTTPException, UploadFile

from app.services.page_service import EMOTION_SLOTS, validate_resource_folder, ALLOWED_AVATAR_EXT

# 上传槽位名 -> 落盘文件名（与 LingChat EMOTION_STORAGE_NAME_MAP 一致）
EMOTION_STORAGE_NAME_MAP = {
    "哭泣": "伤心",
    "难为情": "羞耻",
}

# settings.yml 中 voice_models 的全部键（与 LingChat CharacterSettings 一致）
VOICE_MODEL_KEYS = [
    "sva_speaker_id", "sbv2_name", "sbv2_speaker_id", "bv2_speaker_id",
    "sbv2api_name", "sbv2api_speaker_id", "gsv_voice_text", "gsv_voice_filename",
    "gsv_gpt_model_name", "gsv_sovits_model_name", "aivis_model_uuid",
    "opentts_voice", "fish_s2_voice", "sbv2_local_voice_id",
    "sbv2_local_speaker_id", "sbv2_local_style_id", "sbv2_local_length_scale",
    "sbv2_local_sdp_ratio", "sbv2_local_cloud_fallback_model",
    "sbv2_local_cloud_fallback_speaker_id",
]

_INVALID_FOLDER_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f\s]')


def safe_folder_name(name: str, fallback: str = "character") -> str:
    """将任意名称转换为安全的目录名。"""
    cleaned = _INVALID_FOLDER_CHARS_RE.sub("_", str(name or "").strip())
    cleaned = cleaned[:64].strip("._")
    return cleaned or fallback


def read_local_upload(url: Optional[str]) -> Optional[bytes]:
    """读取本地上传目录中的文件（仅允许 /static/uploads/ 下，防止路径穿越）。"""
    if not url or not str(url).startswith("/static/uploads/"):
        return None
    path = os.path.join("app", str(url).lstrip("/"))
    try:
        if os.path.isfile(path):
            with open(path, "rb") as f:
                return f.read()
    except OSError:
        return None
    return None


def file_ext_from(filename: Optional[str], fallback: str = ".png") -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in ALLOWED_AVATAR_EXT else fallback


def emotion_storage_name(name: str) -> str:
    return EMOTION_STORAGE_NAME_MAP.get(name, name)


def normalize_settings(settings: Dict[str, Any], folder: str) -> Dict[str, Any]:
    """整理为与 LingChat settings.yml 一致的字段结构（顺序与参考一致）。"""
    src = {k: v for k, v in (settings or {}).items() if not k.startswith("__")}

    voice_models: Dict[str, Any] = {k: None for k in VOICE_MODEL_KEYS}
    provided_vm = src.get("voice_models")
    if isinstance(provided_vm, dict):
        for k in VOICE_MODEL_KEYS:
            if k in provided_vm:
                voice_models[k] = provided_vm[k]

    def num(v, default):
        try:
            return float(v) if v is not None and v != "" else float(default)
        except (TypeError, ValueError):
            return float(default)

    def text(v, default=""):
        return str(v) if v is not None and v != "" else default

    clothes = src.get("clothes")
    if not isinstance(clothes, list):
        clothes = []
    clothes = [
        {"name": text(c.get("name") if isinstance(c, dict) else None, "未命名"),
         "prompt": text(c.get("prompt") if isinstance(c, dict) else None)}
        for c in clothes if isinstance(c, dict)
    ]

    tts_type = src.get("tts_type") or None

    return {
        "ai_name": text(src.get("ai_name"), folder),
        "ai_subtitle": text(src.get("ai_subtitle")),
        "user_name": text(src.get("user_name"), "用户"),
        "user_subtitle": text(src.get("user_subtitle")),
        "title": text(src.get("title"), src.get("ai_name") or folder),
        "info": src.get("info") or None,
        "body_part": src.get("body_part") if isinstance(src.get("body_part"), dict) else None,
        "scale": num(src.get("scale"), 1),
        "offset_x": num(src.get("offset_x"), 0),
        "offset_y": num(src.get("offset_y"), 0),
        "clothes_name": src.get("clothes_name") or None,
        "clothes": clothes,
        "scale_p": num(src.get("scale_p"), 1),
        "offset_x_p": num(src.get("offset_x_p"), 0),
        "offset_y_p": num(src.get("offset_y_p"), 0),
        "voice_models": voice_models,
        "tts_type": tts_type,
        "voice_lang": text(src.get("voice_lang"), "zh"),
        "thinking_message": text(src.get("thinking_message"), "正在思考中..."),
        "bubble_top": int(num(src.get("bubble_top"), 5)),
        "bubble_left": int(num(src.get("bubble_left"), 20)),
        "system_prompt": src.get("system_prompt") or None,
        "system_prompt_example": src.get("system_prompt_example") or None,
        "system_prompt_example_old": src.get("system_prompt_example_old") or None,
        "character_folder": folder,
    }


def build_settings_yml(settings: Dict[str, Any], folder: str) -> str:
    """生成 settings.yml 内容（与参考格式一致：块状多行字符串、null 空值）。"""
    data = normalize_settings(settings, folder)

    def str_presenter(dumper, value):
        if "\n" in value:
            style = "|-" if value.endswith("\n") else "|"
            return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)

    class Dumper(yaml.SafeDumper):
        pass

    Dumper.add_representer(str, str_presenter)
    return yaml.dump(
        data,
        Dumper=Dumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    )


def build_prompt_txt(settings: Dict[str, Any], ai_name: str) -> Optional[str]:
    """生成 ai模式<角色名>.txt 内容（无 system_prompt 时返回 None）。"""
    prompt = (settings or {}).get("system_prompt") or ""
    if not prompt.strip():
        return None
    prompt = prompt.rstrip("\n")
    return f'system_prompt = """\n{prompt}\n"""\n'


def build_character_zip(
    settings: Dict[str, Any],
    folder: str,
    avatar_bytes: Optional[bytes],
    avatar_ext: str,
    emotions: Dict[str, bytes],
    emotion_exts: Dict[str, str],
) -> io.BytesIO:
    """构建 LingChat 格式的角色 zip（内存中）。"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # settings.yml
        zf.writestr(f"{folder}/settings.yml", build_settings_yml(settings, folder))

        # ai模式<角色名>.txt
        ai_name = safe_folder_name(str(settings.get("ai_name") or ""), folder)
        txt = build_prompt_txt(settings, ai_name)
        if txt:
            zf.writestr(f"{folder}/ai模式{ai_name}.txt", txt)

        # avatar/
        if avatar_bytes:
            zf.writestr(f"{folder}/avatar/头像{avatar_ext}", avatar_bytes)
        for name, data in emotions.items():
            if not data:
                continue
            ext = emotion_exts.get(name, ".png")
            storage = emotion_storage_name(name)
            zf.writestr(f"{folder}/avatar/{storage}{ext}", data)

    buffer.seek(0)
    return buffer


def collect_emotions(
    emotion_names: Optional[List[str]],
    emotion_files: Optional[List[UploadFile]],
    existing_emotions: Optional[Dict[str, str]],
) -> Tuple[Dict[str, bytes], Dict[str, str]]:
    """合并新上传与已有（URL 指向本地文件）的情绪立绘。

    返回 ({情绪名: bytes}, {情绪名: 扩展名})。
    """
    data: Dict[str, bytes] = {}
    exts: Dict[str, str] = {}

    # 已有立绘（从本地上传目录读取）
    for name, url in (existing_emotions or {}).items():
        name = str(name).strip()
        if name not in EMOTION_SLOTS:
            continue
        content = read_local_upload(url)
        if content:
            data[name] = content
            exts[name] = file_ext_from(str(url))

    # 新上传的立绘覆盖同名已有立绘
    names = list(emotion_names or [])
    files = list(emotion_files or [])
    if not names and not files:
        return data, exts
    if len(names) != len(files):
        raise HTTPException(status_code=400, detail="情绪立绘名称与文件数量不匹配")
    if len(set(names)) != len(names):
        raise HTTPException(status_code=400, detail="情绪立绘名称存在重复")
    for name, upload in zip(names, files):
        name = str(name).strip()
        if name not in EMOTION_SLOTS:
            raise HTTPException(status_code=400, detail=f"未知的情绪立绘：{name}")
        ext = file_ext_from(upload.filename)
        data[name] = upload.file.read()
        exts[name] = ext
    return data, exts
