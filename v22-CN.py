#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SFS Pack Tool v2.3.1."""

from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import UnityPy
import sfs_pack_prefab_export as prefab_exporter

DEFAULT_AUTHOR = "〈A Future star汉化〉"
VERSION = "2.3.1"
VERSION_TITLE = "V2.3.1"
EXCLUDE_WORDS = {
    "Color_Gray", "Toggle", "width", "target_state", "tank", "height", "DeployParachute",
    "Landing_Leg_Expanded", "Basic_Parts", "Color_Black", "Color_White", "Flat Smooth 4",
    "Flat Smooth", "Detach", "Flat Faces", "Liquid_Fuel", "Metal", "Panel_Expanded",
    "width_original", "Engine_2", "fairing", "mass", "Flat_Shadow", "Separation",
    "Expanded", "ToggleEnabled", "ToggleEngine", "cone", "Engines", "Nozzle_2",
    "Engine_Parts", "torque", "throttle", "Mass_Unit", "engine_on", "ToggleRCS",
    "ToggleTransfer", "Solid_Fuel",
}
# 承载可展示文本的叶字段名：标准扫描只收这些，天然避开内部变量名
DISPLAY_LEAF_FIELDS = {
    "DisplayName", "displayName", "Description", "description",
    "Author", "TranslatableName", "Text", "text", "Title", "title",
    "Label", "label", "Unit", "unit", "Units", "units",
}
# 深度扫描时排除的叶字段名（精确匹配末段）
INTERNAL_LEAF_FIELDS = {
    "m_MethodName", "m_ClassName", "m_Namespace", "m_TypeName", "m_Name", "m_Script",
    "variableName", "input", "output", "name", "id", "type", "key", "reference",
    "tag", "layer", "fragmentName", "saves", "points", "elements",
}
# 人工确认区标记键：深度扫描的疑似串放这里，绝不自动写回
CANDIDATES_KEY = "__CANDIDATES__"

BUILD_ORDER = ("AndroidBuild", "WindowsBuild", "MacBuild", "IOS_Build")
PLATFORM_KEYS = ("WindowsBuild", "AndroidBuild", "MacBuild", "IOS_Build")
PLATFORM_NAMES = {
    "WindowsBuild": "Windows",
    "AndroidBuild": "Android",
    "MacBuild": "Mac",
    "IOS_Build": "iOS",
}
PLATFORM_LABELS = {name: key for key, name in PLATFORM_NAMES.items()}
TEXT = {
    "zh": {
        "window": "SFS Pack Tool V2.3.1 - Localization & Unity Export-by A Future star",
        "title": "SFS Pack Tool " + VERSION_TITLE,
        "subtitle": "汉化写入 · Prefab · 贴图 · Unity 工程导出 · 免挂提取",
        "language": "语言",
        "chinese": "中文",
        "english": "English",
        "input_frame": "输入文件",
        "select_pack": "选择原始 mod.pack",
        "select_translation": "选择翻译 JSON",
        "no_pack": "尚未选择 mod.pack",
        "translator_frame": "汉化处理",
        "author": "汉化作者标识",
        "extract": "提取待翻译文本",
        "extract_path": "提取 JSON 保存路径",
        "select_json_path": "选择保存位置",
        "write": "写入汉化并生成 Pack",
        "export_frame": "Unity Prefab / 贴图 / 工程导出",
        "builtin_ripper_hint": "使用内置 AssetRipper 随工具打包 无需手动选择或下载",
        "export": "一键导出工程",
        "ready": "请选择pack文件",
        "select_pack_first": "请先选择原始 mod.pack",
        "no_pack_title": "未选择文件",
        "export_start": "开始导出",
        "toolkit_dir": "Modding Toolkit 工程路径",
        "select_toolkit": "选择 Toolkit",
        "toolkit_hint": "必填 部件会直接导出并合并进这个 Modding Toolkit 只新增 Toolkit 里没有的部件 已有部件自动跳过 导出会先在临时目录中转 完成后把新部件写进 Toolkit 的 Assets",
        "selected_toolkit": "已选择 Toolkit {path}",
        "installed_to_toolkit": "✔ 已完成 新增部件已合并进 Toolkit 新增 {new} 个 跳过已有 {skip} 个 拷贝资产 {copy} 个文件 打开 Toolkit 的 Assets/Resources/Parts/{sub} 即可看到并编辑",
        "need_toolkit": "需要 Modding Toolkit 路径",
        "need_toolkit_text": "导出前必须先选择有效的 Modding Toolkit 工程路径\n理由 导出的部件 prefab 引用的游戏脚本需要 Toolkit 提供 不填则部件会断链/无法编辑\n请点击 选择 Toolkit 并选中含 Assets\\Scripts 的 Toolkit 工程根目录",
        "need_toolkit_invalid": "Modding Toolkit 路径无效",
        "toolkit_root_fixed": "[TK] 所选目录不是 Toolkit 工程根 已自动上溯到 {path}",
        "need_toolkit_invalid_text": "所选目录不是有效的 Toolkit 工程 未在 Assets\\Scripts 下找到 .cs.meta 脚本\n请选择官方 Modding Toolkit 的工程根目录 内含 Assets\\Scripts\\Assembly-CSharp 等",
        "export_done": "✔ Unity 工程导出完成 请查看输出目录及同名 ZIP",
        "export_failed": "❌ Unity 工程导出失败 {error}",
        "export_busy": "⏳ 已有导出任务在进行 请等它完成再点",
        "export_running": "导出中",
        "install_opt": "导出后并入 Toolkit 不覆盖已有文件",
        "install_skipped_opt": "[安装] 未勾选 并入 Toolkit 合并包已生成 可自行按 MERGE_README.md 拷入",
        "install_refused": "[安装] [!] 检出 {n} 处 GUID 冲突 已取消写入 Toolkit 请先查看合并包里的 MERGE_README.md 人工核对",
        "install_skipped": "[安装] 已跳过 {n} 个 Toolkit 中已存在的文件 未覆盖任何既有内容",
        "install_failed": "[安装] 写入 Toolkit 失败 {error}",
        "shader_fixed": "[着色器] 已自动修复 {n} 个 AssetRipper 空壳着色器(零件渲成黑板的根因) 换成 Toolkit 真着色器源码",
        "shader_unmatched": "[着色器] [!] 还有 {n} 个着色器在 Toolkit 里找不到同名真身 {names}",
        "install_repaired": "[安装] 修复 {name} 悬空引用 {before} 处 -> {after} 处",
        "install_repair_done": "[安装] 已修复 {n} 个引用悬空的既有资产 原文件已备份到 {path}",
        "repair_toolkit_btn": "修复 Toolkit 空壳着色器·悬空引用",
        "repair_start": "开始清理 Toolkit 里残留的 AssetRipper 空壳着色器(零件渲成黑板的根因)...",
        "repair_done": "[修复] 已删除 {stubs} 个空壳着色器 重写 {refs} 处材质引用 同步 {names} 个资产名 备份于 {backup}",
        "repair_none": "[修复] 没发现空壳着色器 Toolkit 已是干净的",
        "repair_need_tk": "请先填写 Modding Toolkit 路径",
        "repair_dangling_none": "[悬空] 未发现悬空引用 Toolkit 已是干净的",
        "repair_dangling_scan": "[悬空] 扫描到 {n} 处悬空引用",
        "repair_dangling_redirected": "[悬空] 已按同名重定向 {n} 处",
        "repair_dangling_imported": "[悬空] 已补入 Toolkit 缺失资产 {m} 个：{names}",
        "repair_dangling_unresolved": "[悬空] 无法自动修复 {n} 处 清单见 {path}",
        "repair_dangling_nopkg": "[悬空] 未提供原始 mod 工程目录 仅扫描+清单 如需自动修复请填写原始 mod 工程目录",
        "repair_dangling_clean": "[修复] 悬空引用：重定向 {redirected} 处 补入 {imported} 个 未解决 {unresolved} 处",
        "package_dir_label": "原始 mod 工程目录(可选 用于按名修复悬空引用)",
        "select_package": "选择",
        "selected_pack": "已选择源文件 {name}",
        "selected_translation": "已选择翻译文件 {name}",
        "extract_start": "开始提取文本...",
        "no_pack_log": "❌ 未选择 mod.pack",
        "json_error": "❌ JSON 读取错误 {error}",
        "scan": "  扫描 {build}...",
        "unpack_error": "  ❌ {build} 解包失败 {error}",
        "extract_done": "✔ 提取完成 共 {count} 条文本 → {path}",
        "no_translation": "❌ 未选择翻译 JSON",
        "read_failed": "❌ 文件读取失败 {error}",
        "writing": "正在写入 {build}...",
        "decode_failed": "  ❌ {build} 解码失败 {error}",
        "write_done": "  ✔ {build} 完成 修改 {count} 处",
        "save_failed": "  ❌ {build} 保存失败 {error}",
        "pack_done": "✔ 最终文件已生成 {path}",
        "output_failed": "❌ 输出失败 {error}",
        "processing_failed": "❌ 处理失败 {error}",
        "strip_frame": "剥离 / 精简工具",
        "strip_hint": "剥离 = 只保留目标平台 Build 与 CodeAssembly 删除其他平台 大幅减小 .pack 体积",
        "target_platform": "目标平台",
        "select_strip_output": "输出位置",
        "pick_strip_output": "选择位置",
        "analyze": "包信息",
        "strip": "剥离到目标平台",
        "analyzing": "正在分析包信息...",
        "pack_size": "  包文件 {content} ({size})",
        "assembly": "    CodeAssembly {size}",
        "assembly_absent": "    CodeAssembly 未包含",
        "build_present": "    {plat} 解压后约 {size} {parts} 个部件",
        "build_absent": "   {plat} 未包含",
        "analyze_done": "✔ 包信息完成 共 {builds} 个平台 {parts} 个部件 解压共 {total}",
        "strip_no_target": "❌ 该 .pack 里没有 {plat} 平台的数据 无法剥离 请先用 包信息 确认包含哪些平台",
        "strip_output_is_input": "❌ 剥离输出不能就是源 .pack 会直接覆盖原模组 请另选一个路径",
        "strip_output_set": "剥离输出 {path}",
        "strip_no_pack": "❌ 未选择 mod.pack",
        "strip_no_output": "❌ 未设置输出位置 已在原目录生成",
        "strip_start": "开始剥离...",
        "strip_read_fail": "❌ 读取 .pack 失败 {error}",
        "strip_removed": "  删除 {plat}",
        "strip_keep": "  保留 {plat}",
        "strip_done": "✔ 剥离完成 {out} {size}",
        "strip_fail": "❌ 剥离失败 {error}",
    },
    "en": {
        "window": "SFS Pack Tool V2.3.1 - Localization & Unity Export-by A Future star",
        "title": "SFS Pack Tool " + VERSION_TITLE,
        "subtitle": "Localization · Prefab · Textures · Unity Export · Keep-alive extraction",
        "language": "Language:",
        "chinese": "中文",
        "english": "English",
        "input_frame": "Input Files",
        "select_pack": "Select source mod.pack",
        "select_translation": "Select translation JSON",
        "no_pack": "No mod.pack selected",
        "translator_frame": "Localization",
        "author": "Translator signature:",
        "extract": "Extract translatable text",
        "extract_path": "Extracted JSON save path:",
        "select_json_path": "Choose save location",
        "write": "Apply translation and create Pack",
        "export_frame": "Unity Prefab / Texture / Project Export",
        "builtin_ripper_hint": "Uses the built-in AssetRipper (bundled with the tool); no manual selection or download needed.",
        "export": "Export Unity project",
        "ready": "Ready. Select a mod.pack; export includes Prefabs, textures, materials, .meta files and Unity project files.",
        "select_pack_first": "Select the source mod.pack first.",
        "no_pack_title": "No input file",
        "export_start": "Starting Unity project export. The output includes Prefabs, textures, materials, .meta files, Packages and ProjectSettings.",
        "export_done": "✔ Unity project export completed. Check the output directory and its ZIP file.",
        "export_failed": "❌ Unity project export failed: {error}",
        "export_busy": "A export task is already running; please wait for it to finish.",
        "export_running": "Exporting...",
        "install_opt": "Merge into Toolkit after export (never overwrite existing files)",
        "install_skipped_opt": "[Install] Not enabled; the merge package is ready, copy it in manually per MERGE_README.md.",
        "install_refused": "[Install] [!] {n} GUID collisions found; cancelled writing into the Toolkit. Check MERGE_README.md first.",
        "install_skipped": "[Install] Skipped {n} files that already exist in the Toolkit (nothing overwritten).",
        "shader_fixed": "[Shader] Auto-fixed {n} AssetRipper stub shaders (the cause of black parts) with real Toolkit shader sources.",
        "shader_unmatched": "[Shader] [!] {n} shaders have no same-named counterpart in the Toolkit: {names}",
        "install_repaired": "[Install] Repaired {name}: dangling refs {before} -> {after}",
        "install_repair_done": "[Install] Repaired {n} existing assets with dangling refs; originals backed up to {path}",
        "repair_toolkit_btn": "Repair Toolkit stub shaders (black parts)",
        "repair_start": "Cleaning leftover AssetRipper stub shaders in the Toolkit (the cause of black parts)...",
        "repair_done": "[Repair] Deleted {stubs} stub shaders, rewrote {refs} material refs, synced {names} asset names. Backup at {backup}",
        "repair_none": "[Repair] No stub shaders found; the Toolkit is clean.",
        "repair_need_tk": "Please set the Modding Toolkit path first.",
        "repair_dangling_none": "[Dangling] No dangling references found; the Toolkit is clean.",
        "repair_dangling_scan": "[Dangling] Scanned {n} dangling references",
        "repair_dangling_redirected": "[Dangling] Redirected {n} references by name",
        "repair_dangling_imported": "[Dangling] Imported {m} missing assets into the Toolkit: {names}",
        "repair_dangling_unresolved": "[Dangling] {n} references could not be auto-fixed; manifest at {path}",
        "repair_dangling_nopkg": "[Dangling] No original mod project dir provided; scan+manifest only. To auto-fix, fill the original mod project dir.",
        "repair_dangling_clean": "[Repair] Dangling refs: redirected {redirected}, imported {imported}, unresolved {unresolved}",
        "package_dir_label": "Original mod project dir (optional; for name-based dangling repair)",
        "select_package": "Select",
        "install_failed": "[Install] Failed to write into the Toolkit: {error}",
        "selected_pack": "Source selected: {name}",
        "selected_translation": "Translation selected: {name}",
        "toolkit_dir": "Modding Toolkit project path:",
        "select_toolkit": "Select Toolkit",
        "toolkit_hint": "Required. Parts are exported and merged straight into this Modding Toolkit (only parts it does not already have are added). Staging is temporary; new parts are written into the Toolkit's Assets.",
        "selected_toolkit": "Toolkit selected: {path}",
        "installed_to_toolkit": "Done: {new} new parts merged into the Toolkit ({skip} already-present parts skipped, {copy} assets copied). Open Assets/Resources/Parts/{sub} in the Toolkit to see and edit them.",
        "need_toolkit": "Modding Toolkit path required",
        "need_toolkit_text": "You must choose a valid Modding Toolkit project path before exporting.\nReason: the exported part prefabs reference game scripts that come from the Toolkit; without it the parts will be broken/uneditable.\nSelect the Toolkit project root that contains Assets\\Scripts.",
        "need_toolkit_invalid": "Invalid Modding Toolkit path",
        "toolkit_root_fixed": "[TK] The chosen folder was not the Toolkit project root; using {path}",
        "need_toolkit_invalid_text": "The chosen folder is not a valid Toolkit project: no .cs.meta scripts found under Assets\\Scripts.\nSelect the official Modding Toolkit project root (containing Assets\\Scripts\\Assembly-CSharp, etc.).",
        "extract_start": "Extracting text...",
        "no_pack_log": "❌ No mod.pack selected",
        "json_error": "❌ JSON read error: {error}",
        "scan": "  Scanning {build}...",
        "unpack_error": "  ❌ {build} unpack failed: {error}",
        "extract_done": "✔ Extraction completed: {count} strings → {path}",
        "no_translation": "❌ No translation JSON selected",
        "read_failed": "❌ File read failed: {error}",
        "writing": "Writing {build}...",
        "decode_failed": "  ❌ {build} decode failed: {error}",
        "write_done": "  ✔ {build} done, {count} changes",
        "save_failed": "  ❌ {build} save failed: {error}",
        "pack_done": "✔ Output created: {path}",
        "output_failed": "❌ Output failed: {error}",
        "processing_failed": "❌ Processing failed: {error}",
        "strip_frame": "Strip / Slim Tool",
        "strip_hint": "Strip = keep only the target platform Build and CodeAssembly, remove other platforms to greatly reduce .pack size.",
        "target_platform": "Target platform:",
        "select_strip_output": "Output location:",
        "pick_strip_output": "Choose location",
        "analyze": "Pack info",
        "strip": "Strip to target platform",
        "analyzing": "Analyzing pack info...",
        "pack_size": "  Pack file: {content} ({size})",
        "assembly": "    CodeAssembly: {size}",
        "assembly_absent": "    CodeAssembly: not included",
        "build_present": "    {plat}: ~{size} decompressed, {parts} parts",
        "build_absent": "   {plat}: not included",
        "analyze_done": "✔ Pack info done: {builds} platforms, {parts} parts, ~{total} decompressed",
        "strip_no_target": "❌ This .pack has no {plat} data to strip. Run Pack info first to see which platforms it contains.",
        "strip_output_is_input": "❌ Strip output cannot be the source .pack (it would overwrite the original mod). Pick another path.",
        "strip_output_set": "Strip output: {path}",
        "strip_no_pack": "❌ No mod.pack selected",
        "strip_no_output": "❌ No output location set, created in the source folder",
        "strip_start": "Stripping...",
        "strip_read_fail": "❌ Failed to read .pack: {error}",
        "strip_removed": "  Removed {plat}",
        "strip_keep": "  Kept {plat}",
        "strip_done": "✔ Strip done: {out} ({size})",
        "strip_fail": "❌ Strip failed: {error}",
    },
}


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


APP_USER_MODEL_ID = "AFuturestar.SFSPackTool.2.3.1"
_WM_SETICON = 0x0080
_IMAGE_ICON = 1
_LR_LOADFROMFILE = 0x00000010


def set_window_icon(root: "tk.Tk") -> None:
    """设置标题栏与任务栏图标。

    Tk 的 iconbitmap 在 Windows 上只下发 16x16 小图标，任务栏仍显示 EXE 默认图标；
    Tk 的 PhotoImage 又不支持 ico，不能用 iconphoto 兜底。因此这里改用 WM_SETICON
    直接下发 16/32 两套图标，标题栏与任务栏都会更新。
    """
    icon = resource_path("assets/SFS_Pack_Tool_v22.ico")
    if not icon.is_file():  # 源码运行时没有 assets/ 这层，退回脚本同目录
        icon = Path(__file__).resolve().parent / "SFS_Pack_Tool_v22.ico"
    if not icon.is_file():
        return
    try:
        root.iconbitmap(default=str(icon))
    except tk.TclError:
        pass
    if os.name != "nt":
        return
    try:
        # 声明独立 AppUserModelID，否则任务栏可能把窗口归到 python/其他宿主名下
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError):
        pass

    def apply_native_icon() -> None:
        try:
            user32 = ctypes.windll.user32
            user32.LoadImageW.restype = ctypes.c_void_p
            root.update_idletasks()
            hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
            if not hwnd:
                return
            for size, which in ((32, 1), (16, 0)):  # ICON_BIG / ICON_SMALL
                handle = user32.LoadImageW(0, str(icon), _IMAGE_ICON, size, size, _LR_LOADFROMFILE)
                if handle:
                    user32.SendMessageW(hwnd, _WM_SETICON, which, handle)
        except (AttributeError, OSError):
            pass

    root.after(60, apply_native_icon)


def app_data_dir() -> Path:
    root = Path(os.environ.get("APPDATA", Path.home())) if os.name == "nt" else Path.home() / ".config"
    folder = root / "AFuturestar" / "SFS-Pack-Tool"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve_toolkit_root(path) -> Path | None:
    """把所选目录解析成 Toolkit 工程根。

    用户很容易点进 Assets/Scripts/Parts/Mesh 这类子目录，这里向上找出第一个
    真正含 Assets/Scripts 的目录；优先返回 Scripts 顶层就有 .cs.meta 的那个。
    都找不到返回 None。
    """
    current = Path(path).resolve()
    loose: Path | None = None
    for cand in [current, *current.parents]:
        scripts = cand / "Assets" / "Scripts"
        if not scripts.is_dir():
            continue
        if next(scripts.glob("*.cs.meta"), None) is not None:
            return cand
        if loose is None:
            loose = cand
    return loose


SETTINGS_PATH = app_data_dir() / "settings.json"


def load_settings() -> dict:
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def leaf_field(path: str) -> str:
    """取路径最末尾的字段名；列表元素去掉下标。"""
    return path.split(".")[-1].split("[")[0]


def is_exclude_word(text: object) -> bool:
    return isinstance(text, str) and text.strip() in EXCLUDE_WORDS


LOC_KEY_SUFFIXES = ("Name", "Description", "Text", "Title", "Label", "DisplayName", "Key", "Unit", "Units", "Author")
_LOC_SUFFIX_RE = re.compile(r"_(" + "|".join(LOC_KEY_SUFFIXES) + r")$")


def is_loc_key(text: object) -> bool:
    """是否形似本地化 key（如 "0_0_Description"）：纯 ASCII 标识符 + _字段名 结尾。"""
    if not isinstance(text, str):
        return False
    if not re.fullmatch(r"[A-Za-z0-9_]+", text):
        return False
    return bool(_LOC_SUFFIX_RE.search(text))


def is_meaningful_text(text: object) -> bool:
    """过滤太短/纯数字/程序符号/内部 key 的串。"""
    if not isinstance(text, str) or len(text) < 2:
        return False
    if re.match(r"^[0-9\s\.\,\%\+\-\*\/\(\)]+$", text):
        return False
    if is_loc_key(text):
        return False
    for token in ("UnityEngine", "Assembly-", "SFS.", "System.", "None"):
        if token in text:
            return False
    return True


def is_display_text(text: object, path: str) -> bool:
    """标准扫描：仅取“显示字段”叶节点的值，天然不碰内部变量名。"""
    if not is_meaningful_text(text) or is_exclude_word(text):
        return False
    return leaf_field(path) in DISPLAY_LEAF_FIELDS


def is_candidate_text(text: object, path: str) -> bool:
    """深度扫描：非显示、非明确内部字段的串，进人工确认区，绝不自动写回。"""
    leaf = leaf_field(path)
    if not is_meaningful_text(text) or is_exclude_word(text):
        return False
    return leaf not in DISPLAY_LEAF_FIELDS and leaf not in INTERNAL_LEAF_FIELDS


def recursive_walk(node: object, path: str, callback) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if isinstance(value, str):
                callback(node, key, value, child)
            elif isinstance(value, (dict, list)):
                recursive_walk(value, child, callback)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            child = f"{path}[{index}]"
            if isinstance(value, str):
                callback(node, index, value, child)
            elif isinstance(value, (dict, list)):
                recursive_walk(value, child, callback)


def extract_texts(input_file: str, output_file: str, translate, log) -> None:
    if not input_file:
        log(translate("no_pack_log"))
        return
    log(translate("extract_start"))
    try:
        data = json.loads(Path(input_file).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        log(translate("json_error", error=exc))
        return
    texts: set[str] = set()
    candidates: set[str] = set()
    for build in PLATFORM_KEYS:
        if not data.get(build):
            continue
        log(translate("scan", build=build))
        try:
            environment = UnityPy.load(base64.b64decode(data[build]))
        except Exception as exc:
            log(translate("unpack_error", build=build, error=exc))
            continue
        for obj in environment.objects:
            try:
                if obj.type.name == "MonoBehaviour":
                    tree = obj.read_typetree()
                    if tree is not None:

                        def collect(parent, key, value, path) -> None:
                            if is_display_text(value, path):
                                texts.add(value)
                            elif is_candidate_text(value, path):
                                candidates.add(value)

                        recursive_walk(tree, "", collect)
            except Exception:
                continue
    table = {item: item for item in sorted(texts)}
    if candidates:
        table[CANDIDATES_KEY] = {item: item for item in sorted(candidates)}
    output = Path(output_file) if output_file else Path(input_file).with_name("texts_to_translate.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(translate("extract_done", count=len(texts), path=output))


def write_translation(input_file: str, translation_file: str, author: str, translate, log) -> None:
    if not input_file:
        log(translate("no_pack_log"))
        return
    if not translation_file:
        log(translate("no_translation"))
        return
    try:
        data = json.loads(Path(input_file).read_text(encoding="utf-8-sig"))
        translations = json.loads(Path(translation_file).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        log(translate("read_failed", error=exc))
        return
    # 跳过“人工确认区”：不在标准翻译表里的疑似变量即使写了也绝不写回 Pack。
    translations = {
        source: target
        for source, target in translations.items()
        if isinstance(source, str) and source != target and source != CANDIDATES_KEY
    }
    for build in PLATFORM_KEYS:
        if not data.get(build):
            continue
        log(translate("writing", build=build))
        try:
            environment = UnityPy.load(base64.b64decode(data[build]))
        except Exception as exc:
            log(translate("decode_failed", build=build, error=exc))
            continue
        changed = 0
        for obj in environment.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                tree = obj.read_typetree()
                if not tree:
                    continue

                def replace(node: object, path: str = "") -> None:
                    nonlocal changed
                    if isinstance(node, dict):
                        for key, value in list(node.items()):
                            child = f"{path}.{key}" if path else str(key)
                            if isinstance(value, str):
                                if key == "Author":
                                    # 先翻译 Author 原文，再在结尾追加作者名（避免“吞掉翻译”）
                                    if not is_exclude_word(value) and value in translations:
                                        node[key] = translations[value]
                                        changed += 1
                                    if author and author not in node[key]:
                                        node[key] = node[key] + author
                                        changed += 1
                                elif not is_exclude_word(value) and value in translations:
                                    node[key] = translations[value]
                                    changed += 1
                            elif isinstance(value, (dict, list)):
                                replace(value, child)
                    elif isinstance(node, list):
                        for index, value in enumerate(node):
                            child = f"{path}[{index}]"
                            if isinstance(value, str) and not is_exclude_word(value) and value in translations:
                                node[index] = translations[value]
                                changed += 1
                            elif isinstance(value, (dict, list)):
                                replace(value, child)

                replace(tree)
                obj.save_typetree(tree)
            except Exception:
                continue
        try:
            data[build] = base64.b64encode(environment.file.save(packer="lzma")).decode("utf-8")
            log(translate("write_done", build=build, count=changed))
        except Exception as exc:
            log(translate("save_failed", build=build, error=exc))
    output = Path(input_file).with_name(f"{Path(input_file).stem}-CN.pack")
    try:
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(translate("pack_done", path=output))
    except OSError as exc:
        log(translate("output_failed", error=exc))


def human_size(num: float) -> str:
    """把字节数格式化为人类可读的 B / KB / MB / GB。"""
    step = 1024.0
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < step or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= step
    return f"{size:.1f} GB"


def decode_build_payload(build_value: object) -> bytes | None:
    """从 .pack 的某个平台 Build 字段解码 UnityFS 字节流。"""
    if not isinstance(build_value, str):
        return None
    try:
        return base64.b64decode(build_value)
    except (ValueError, TypeError):
        return None


def count_bundle_parts(payload: bytes) -> int:
    """数 bundle 里有多少个部件：一个部件 = 一个 prefab 根对象。

    不能拿 MonoBehaviour 计数：一个零件上挂着 ResourceModule、RenderSortingModule
    等好几个组件，那样数出来会是真实部件数的好几倍。这里数 m_Father 为空的
    Transform 对应的 GameObject，也就是 prefab 的根。
    """
    try:
        environment = UnityPy.load(payload)
    except Exception:
        return 0
    transforms = [obj for obj in environment.objects if obj.type.name in ("Transform", "RectTransform")]
    roots: set[object] = set()
    for obj in transforms:
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if not isinstance(tree, dict):
            continue
        father = tree.get("m_Father")
        if isinstance(father, dict):
            if (father.get("m_FileID") or 0) != 0 or (father.get("m_PathID") or 0) != 0:
                continue  # 有父节点 = 不是根
        else:
            continue
        game_object = tree.get("m_GameObject")
        if isinstance(game_object, dict) and game_object.get("m_PathID"):
            roots.add(game_object["m_PathID"])
        else:
            roots.add(obj.path_id)
    if roots:
        return len(roots)
    # 拿不到 typetree 时退化成 GameObject 总数，至少不至于报 0
    return sum(1 for obj in environment.objects if obj.type.name == "GameObject")


def analyze_pack(input_file: str, translate, log) -> None:
    """概览 .pack：总体积、各平台 Build 解压体积与部件数量。"""
    if not input_file:
        log(translate("strip_no_pack"))
        return
    try:
        data = json.loads(Path(input_file).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        log(translate("strip_read_fail", error=exc))
        return
    log(translate("analyzing"))
    content = Path(input_file).stat().st_size
    log(translate("pack_size", content=Path(input_file).name, size=human_size(content)))
    assembly = data.get("CodeAssembly")
    if isinstance(assembly, str) and assembly.strip():
        try:
            log(translate("assembly", size=human_size(len(base64.b64decode(assembly, validate=False)))))
        except Exception:
            log(translate("assembly", size=human_size(len(assembly))))
    else:
        log(translate("assembly_absent"))
    total = 0
    build_count = 0
    part_total = 0
    for key in BUILD_ORDER:
        payload = decode_build_payload(data.get(key))
        if payload is None:
            log(translate("build_absent", plat=PLATFORM_NAMES.get(key, key)))
            continue
        build_count += 1
        total += len(payload)
        parts = count_bundle_parts(payload)
        # 各平台装的是同一批部件，取最大值而不是累加，否则“共 N 个部件”会被乘上平台数
        part_total = max(part_total, parts)
        log(translate("build_present", plat=PLATFORM_NAMES.get(key, key), size=human_size(len(payload)), parts=parts))
    log(translate("analyze_done", builds=build_count, parts=part_total, total=human_size(total)))


def strip_pack(input_file: str, output_file: str, platform_key: str, translate, log) -> None:
    """剥离到目标平台：只保留 platform_key 与 CodeAssembly，删除其他平台 Build。"""
    if not input_file:
        log(translate("strip_no_pack"))
        return
    if platform_key not in PLATFORM_KEYS:
        log(translate("strip_fail", error=f"无效平台 {platform_key}"))
        return
    try:
        data = json.loads(Path(input_file).read_text(encoding="utf-8-sig"))
    except Exception as exc:
        log(translate("strip_read_fail", error=exc))
        return
    # 目标平台压根不在包里时，直接放弃：否则会写出一个只有 CodeAssembly、
    # 游戏根本加载不了的 .pack，而界面上还显示“剥离完成”。
    if decode_build_payload(data.get(platform_key)) is None:
        log(translate("strip_no_target", plat=PLATFORM_NAMES.get(platform_key, platform_key)))
        return
    if output_file:
        try:
            if Path(output_file).resolve() == Path(input_file).resolve():
                log(translate("strip_output_is_input"))
                return
        except OSError:
            pass
    log(translate("strip_start"))
    removed = []
    kept = []
    for key in list(data.keys()):
        if key == "CodeAssembly":
            kept.append(key)
            continue
        if key in PLATFORM_KEYS and key != platform_key:
            removed.append(PLATFORM_NAMES.get(key, key))
            data.pop(key, None)
        elif key == platform_key:
            kept.append(key)
    for name in removed:
        log(translate("strip_removed", plat=name))
    for name in kept:
        log(translate("strip_keep", plat=PLATFORM_NAMES.get(name, name)))
    if not output_file:
        output_file = str(Path(input_file).with_name(f"{Path(input_file).stem}-{PLATFORM_NAMES.get(platform_key, platform_key)}.pack"))
    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        log(translate("strip_fail", error=exc))
        return
    log(translate("strip_done", out=output_file, size=human_size(Path(output_file).stat().st_size)))


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = load_settings()
        self.locale = self.settings.get("language", "zh") if self.settings.get("language") in TEXT else "zh"
        self.input_file = ""
        self.translation_file = ""
        self.logs: list[str] = []
        self.author_var = tk.StringVar(value=self.settings.get("author", DEFAULT_AUTHOR))
        self.toolkit_dir_var = tk.StringVar(value=self.settings.get("toolkit_dir", ""))
        self.package_dir_var = tk.StringVar(value=self.settings.get("package_dir", ""))
        self.extract_output_var = tk.StringVar(value=self.settings.get("extract_output", ""))
        self.strip_output_var = tk.StringVar(value=self.settings.get("strip_output", ""))
        self.platform_var = tk.StringVar(value=PLATFORM_NAMES.get(self.settings.get("strip_platform", "WindowsBuild"), "Windows"))
        self.install_var = tk.BooleanVar(value=bool(self.settings.get("install_to_toolkit", False)))
        self.language_var = tk.StringVar()
        set_window_icon(self.root)
        self.build_ui()

    def t(self, key: str, **kwargs) -> str:
        return TEXT[self.locale][key].format(**kwargs)

    def build_ui(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self.t("window"))
        self.root.geometry("920x770")
        self.root.minsize(840, 680)
        self.language_var.set(self.t("chinese") if self.locale == "zh" else self.t("english"))

        header = tk.Frame(self.root)
        header.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(header, text=self.t("title"), font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        language_box = tk.Frame(header)
        language_box.pack(side="right")
        tk.Label(language_box, text=self.t("language")).pack(side="left")
        menu = tk.OptionMenu(language_box, self.language_var, self.t("chinese"), self.t("english"), command=self.change_language)
        menu.configure(width=10)
        menu.pack(side="left")
        tk.Label(self.root, text=self.t("subtitle"), fg="#555555").pack(pady=(0, 8))

        source = tk.LabelFrame(self.root, text=self.t("input_frame"), padx=8, pady=8)
        source.pack(fill="x", padx=12, pady=4)
        tk.Button(source, text=self.t("select_pack"), command=self.pick_input, width=22).grid(row=0, column=0, padx=4, pady=3)
        tk.Button(source, text=self.t("select_translation"), command=self.pick_translation, width=22).grid(row=0, column=1, padx=4, pady=3)
        self.input_label = tk.Label(source, text=self.input_file or self.t("no_pack"), anchor="w")
        self.input_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=3)
        source.columnconfigure(1, weight=1)

        translate_frame = tk.LabelFrame(self.root, text=self.t("translator_frame"), padx=8, pady=6)
        translate_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(translate_frame, text=self.t("author")).grid(row=0, column=0, sticky="w")
        tk.Entry(translate_frame, textvariable=self.author_var, width=55).grid(row=0, column=1, columnspan=2, sticky="ew", padx=5)
        tk.Label(translate_frame, text=self.t("extract_path")).grid(row=1, column=0, sticky="w", pady=(5, 0))
        tk.Entry(translate_frame, textvariable=self.extract_output_var).grid(row=1, column=1, sticky="ew", padx=5, pady=(5, 0))
        tk.Button(translate_frame, text=self.t("select_json_path"), command=self.pick_extract_output, width=14).grid(row=1, column=2, padx=3, pady=(5, 0))
        tk.Button(translate_frame, text=self.t("extract"), command=lambda: self.run_async(lambda log: extract_texts(self.input_file, self.extract_output_var.get().strip(), self.t, log))).grid(row=2, column=0, padx=4, pady=6)
        tk.Button(translate_frame, text=self.t("write"), command=lambda: self.run_async(lambda log: write_translation(self.input_file, self.translation_file, self.author_var.get(), self.t, log))).grid(row=2, column=1, sticky="w", padx=5, pady=6)
        translate_frame.columnconfigure(1, weight=1)

        export = tk.LabelFrame(self.root, text=self.t("export_frame"), padx=8, pady=8)
        export.pack(fill="x", padx=12, pady=4)
        tk.Label(export, text=self.t("toolkit_dir")).grid(row=0, column=0, sticky="w")
        tk.Entry(export, textvariable=self.toolkit_dir_var).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(export, text=self.t("select_toolkit"), command=self.pick_toolkit_dir, width=14).grid(row=0, column=2, padx=3)
        tk.Label(export, text=self.t("builtin_ripper_hint"), fg="#555555", wraplength=650, justify="left").grid(row=1, column=1, columnspan=2, sticky="w", padx=5)
        tk.Label(export, text=self.t("toolkit_hint"), fg="#555555", wraplength=650, justify="left").grid(row=2, column=1, columnspan=2, sticky="w", padx=5)
        tk.Checkbutton(export, text=self.t("install_opt"), variable=self.install_var,
                       command=self.save_user_settings, anchor="w", justify="left").grid(row=3, column=1, sticky="w", padx=5, pady=(7, 0))
        self.export_btn = tk.Button(export, text=self.t("export"), command=self.start_export, bg="#e6f7ff", width=14)
        self.export_btn.grid(row=3, column=2, padx=3, pady=(7, 0))
        tk.Button(export, text=self.t("repair_toolkit_btn"), command=self.start_repair_toolkit, bg="#fff3bf", width=24)\
            .grid(row=4, column=1, columnspan=2, sticky="w", padx=5, pady=(7, 0))
        tk.Label(export, text=self.t("package_dir_label")).grid(row=5, column=0, sticky="w", pady=(7, 0))
        tk.Entry(export, textvariable=self.package_dir_var).grid(row=5, column=1, sticky="ew", padx=5, pady=(7, 0))
        tk.Button(export, text=self.t("select_package"), command=self.pick_package_dir, width=14)\
            .grid(row=5, column=2, padx=3, pady=(7, 0))
        export.columnconfigure(1, weight=1)

        strip = tk.LabelFrame(self.root, text=self.t("strip_frame"), padx=8, pady=8)
        strip.pack(fill="x", padx=12, pady=4)
        tk.Label(strip, text=self.t("strip_hint"), fg="#555555", wraplength=820, justify="left").grid(row=0, column=0, columnspan=4, sticky="w", padx=2)
        tk.Label(strip, text=self.t("target_platform")).grid(row=1, column=0, sticky="w", pady=(7, 0))
        tk.OptionMenu(strip, self.platform_var, *PLATFORM_NAMES.values()).grid(row=1, column=1, sticky="w", padx=5, pady=(7, 0))
        tk.Button(strip, text=self.t("analyze"), command=lambda: self.run_async(lambda log: analyze_pack(self.input_file, self.t, log)), width=14).grid(row=1, column=2, padx=4, pady=(7, 0))
        tk.Button(strip, text=self.t("strip"), command=self.start_strip, bg="#ffe9d6", width=20).grid(row=1, column=3, padx=4, pady=(7, 0))
        tk.Label(strip, text=self.t("select_strip_output")).grid(row=2, column=0, sticky="w", pady=(7, 0))
        tk.Entry(strip, textvariable=self.strip_output_var).grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=(7, 0))
        tk.Button(strip, text=self.t("pick_strip_output"), command=self.pick_strip_output, width=14).grid(row=2, column=3, padx=4, pady=(7, 0))
        strip.columnconfigure(1, weight=1)

        self.log_widget = scrolledtext.ScrolledText(self.root, font=("Consolas", 10), height=16, state="disabled")
        self.log_widget.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        if not self.logs:
            self.logs.append(self.t("ready"))
        self.refresh_logs()

    def refresh_logs(self) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.delete("1.0", tk.END)
        self.log_widget.insert(tk.END, "\n".join(self.logs) + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state="disabled")

    def change_language(self, selection: str) -> None:
        self.locale = "zh" if selection == TEXT[self.locale]["chinese"] else "en"
        self.save_user_settings()
        self.build_ui()

    def save_user_settings(self) -> None:
        save_settings({
            "language": self.locale,
            "author": self.author_var.get(),
            "toolkit_dir": self.toolkit_dir_var.get().strip(),
            "package_dir": self.package_dir_var.get().strip(),
            "extract_output": self.extract_output_var.get().strip(),
            "strip_output": self.strip_output_var.get().strip(),
            "strip_platform": PLATFORM_LABELS.get(self.platform_var.get(), "WindowsBuild"),
            "install_to_toolkit": bool(self.install_var.get()),
        })

    def log(self, message: str) -> None:
        def append() -> None:
            self.logs.append(message)
            if len(self.logs) > 1200:  # 防止无上限增长
                self.logs[: len(self.logs) - 1200] = []
            if hasattr(self, "log_widget"):
                self.log_widget.configure(state="normal")
                self.log_widget.insert(tk.END, message + "\n")
                self.log_widget.see(tk.END)
                self.log_widget.configure(state="disabled")
        self.root.after(0, append)

    def run_async(self, operation) -> None:
        def worker() -> None:
            try:
                operation(self.log)
            except Exception as exc:
                self.log(self.t("processing_failed", error=exc))
        threading.Thread(target=worker, daemon=True).start()

    def pick_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("SFS Pack", "*.pack"), ("All files", "*.*")])
        if not path:
            return
        self.input_file = path
        self.input_label.configure(text=path)
        if not self.extract_output_var.get().strip():
            self.extract_output_var.set(str(Path(path).with_name("texts_to_translate.json")))
        if not self.strip_output_var.get().strip():
            self.strip_output_var.set(str(Path(path).with_name(f"{Path(path).stem}-{self.platform_var.get()}.pack")))
        self.log(self.t("selected_pack", name=Path(path).name))

    def pick_translation(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if path:
            self.translation_file = path
            self.log(self.t("selected_translation", name=Path(path).name))

    def pick_extract_output(self) -> None:
        initial = self.extract_output_var.get().strip() or (str(Path(self.input_file).with_name("texts_to_translate.json")) if self.input_file else "texts_to_translate.json")
        path = filedialog.asksaveasfilename(
            title=self.t("select_json_path"),
            initialfile=Path(initial).name,
            initialdir=str(Path(initial).parent),
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.extract_output_var.set(path)
            self.save_user_settings()

    def pick_toolkit_dir(self) -> None:
        path = filedialog.askdirectory(title=self.t("select_toolkit"))
        if path:
            resolved = resolve_toolkit_root(path)
            if resolved is not None:
                if str(resolved) != str(Path(path).resolve()):
                    self.log(self.t("toolkit_root_fixed", path=str(resolved)))
                path = str(resolved)
            self.toolkit_dir_var.set(path)
            self.save_user_settings()

    def pick_package_dir(self) -> None:
        path = filedialog.askdirectory(title=self.t("package_dir_label"))
        if path:
            self.package_dir_var.set(path)
            self.save_user_settings()
            self.log(self.t("selected_toolkit", path=path))

    def pick_strip_output(self) -> None:
        if self.input_file:
            default_name = f"{Path(self.input_file).stem}-{self.platform_var.get()}.pack"
        else:
            default_name = "stripped.pack"
        path = filedialog.asksaveasfilename(
            title=self.t("pick_strip_output"),
            initialfile=default_name,
            initialdir=str(Path(self.strip_output_var.get()).parent if self.strip_output_var.get() else ("/" if not sys.platform.startswith("win") else "C:/")),
            defaultextension=".pack",
            filetypes=[("SFS Pack", "*.pack"), ("All files", "*.*")],
        )
        if path:
            self.strip_output_var.set(path)
            self.log(self.t("strip_output_set", path=path))
            self.save_user_settings()

    def start_strip(self) -> None:
        if not self.input_file:
            messagebox.showwarning(self.t("no_pack_title"), self.t("strip_no_pack"))
            return
        platform_key = PLATFORM_LABELS.get(self.platform_var.get(), "WindowsBuild")
        output = self.strip_output_var.get().strip()
        if not output:
            output = str(Path(self.input_file).with_name(f"{Path(self.input_file).stem}-{PLATFORM_NAMES.get(platform_key, platform_key)}.pack"))
        self.save_user_settings()
        self.run_async(lambda log: strip_pack(self.input_file, output, platform_key, self.t, log))

    def start_export(self) -> None:
        if getattr(self, "_export_busy", False):
            self.log(self.t("export_busy"))
            return
        if not self.input_file:
            messagebox.showwarning(self.t("no_pack_title"), self.t("select_pack_first"))
            return
        input_path = Path(self.input_file).resolve()
        # 用打包内置的 AssetRipper，系统临时目录中转；内置版缺失时不联网下载，直接报错便于排查
        stage_root = Path(tempfile.gettempdir()) / "SFS_Pack_Stage"
        stage_root.mkdir(parents=True, exist_ok=True)
        output_path = stage_root / f"{input_path.stem}_export"
        output = str(output_path)
        toolkit_dir = self.toolkit_dir_var.get().strip()
        if not toolkit_dir or not Path(toolkit_dir).is_dir():
            messagebox.showerror(self.t("need_toolkit"), self.t("need_toolkit_text"))
            return
        resolved = resolve_toolkit_root(toolkit_dir)
        if resolved is None:
            messagebox.showerror(self.t("need_toolkit_invalid"), self.t("need_toolkit_invalid_text"))
            return
        if str(resolved) != str(Path(toolkit_dir).resolve()):
            toolkit_dir = str(resolved)
            self.toolkit_dir_var.set(toolkit_dir)
            self.log(self.t("toolkit_root_fixed", path=toolkit_dir))
        self.save_user_settings()
        self._export_busy = True
        if getattr(self, "export_btn", None):
            self.export_btn.configure(state="disabled", text=self.t("export_running"))

        def _run(log) -> None:
            try:
                self.export_project(log, output, toolkit_dir, bool(self.install_var.get()))
            finally:
                self.root.after(0, _done)

        def _done() -> None:
            self._export_busy = False
            if getattr(self, "export_btn", None):
                self.export_btn.configure(state="normal", text=self.t("export"))

        self.run_async(_run)

    def start_repair_toolkit(self) -> None:
        """按钮：清理 Toolkit 里残留的 AssetRipper 空壳着色器（黑板根因）。"""
        toolkit_dir = self.toolkit_dir_var.get().strip()
        if not toolkit_dir or not Path(toolkit_dir).is_dir():
            messagebox.showerror(self.t("need_toolkit"), self.t("repair_need_tk"))
            return
        resolved = resolve_toolkit_root(toolkit_dir)
        if resolved is None:
            messagebox.showerror(self.t("need_toolkit_invalid"), self.t("need_toolkit_invalid_text"))
            return
        package_dir = self.package_dir_var.get().strip()
        self.run_async(lambda log: self.repair_toolkit(log, str(resolved), package_dir))

    def repair_toolkit(self, log, toolkit_dir: str, package_dir: str = "") -> None:
        log(self.t("repair_start"))
        try:
            import sfs_script_keep_alive as keepalive
            keepalive.log = log
            rep = keepalive.repair_toolkit_shaders(Path(toolkit_dir), log=log, backup=True)
        except Exception as exc:
            log(self.t("processing_failed", error=exc))
            rep = {}
        if rep.get("stubs", 0) or rep.get("names_fixed", 0):
            log(self.t("repair_done", stubs=rep.get("stubs", 0), refs=rep.get("refs", 0),
                       names=rep.get("names_fixed", 0), backup=rep.get("backup_dir", "")))
        else:
            log(self.t("repair_none"))

        # 悬空引用自愈扫描（提供原始 mod 工程目录可自动修复，否则只扫描+清单）
        try:
            drep = keepalive.repair_toolkit_dangling_refs(
                Path(toolkit_dir), package_assets=package_dir or None, log=log, backup=True)
        except Exception as exc:
            log(self.t("processing_failed", error=exc))
            return
        if drep.get("dangling", 0) == 0:
            log(self.t("repair_dangling_none"))
        else:
            log(self.t("repair_dangling_clean", redirected=drep.get("redirected", 0),
                       imported=drep.get("imported", 0), unresolved=drep.get("unresolved", 0)))


    def export_project(self, log, output: str, toolkit_dir: str = "", install: bool = False) -> None:
        log(self.t("export_start"))
        args = SimpleNamespace(input=self.input_file, output_dir=output, zip=None, asset_ripper=None, no_download=True, no_zip=False, overwrite=True)
        previous_log = prefab_exporter.log
        prefab_exporter.log = log
        try:
            exported_dir = Path(prefab_exporter.export_prefabs(args))
        except Exception as exc:
            log(self.t("export_failed", error=exc))
            return
        finally:
            prefab_exporter.log = previous_log

        merge_dir = exported_dir.with_name(f"{exported_dir.name}_新增合并包")
        mrep: dict[str, object] = {}

        # 1) 脚本免挂对齐
        if toolkit_dir and Path(toolkit_dir).is_dir():
            try:
                import sfs_script_keep_alive as keepalive
                keepalive.log = log
                report = keepalive.align_scripts_to_toolkit(
                    exported_dir,
                    Path(self.input_file),
                    Path(toolkit_dir),
                    log=log,
                )
                if report.get("ok"):
                    log(f"[免挂] 完成 重写 {report.get('rewritten_prefabs', 0)} 个 prefab/asset {report.get('rewritten_refs', 0)} 处脚本引用")
                else:
                    log(f"[免挂] 未执行 {report.get('error')}")
            except Exception as exc:
                log(f"[免挂] 对齐失败 不影响已导出的工程 {exc}")

            # 1.5) 自动处理“黑板”：把 AssetRipper 空壳着色器就地换成 Toolkit 真源码
            try:
                import sfs_script_keep_alive as keepalive
                srep = keepalive.fix_stub_shaders(
                    exported_dir / "Assets", Path(toolkit_dir), log=log, mode="copy"
                )
                if srep.get("stubs"):
                    log(self.t("shader_fixed", n=srep["stubs"]))
                    if srep.get("unmatched"):
                        log(self.t("shader_unmatched", n=len(srep["unmatched"]), names=sorted(set(srep["unmatched"]))))
            except Exception as exc:
                log(f"[着色器] 处理失败 不影响已导出的工程 {exc}")

            # 2) 纯新增合并包
            try:
                import sfs_script_keep_alive as keepalive
                keepalive.log = log
                mrep = keepalive.build_merge_package(
                    exported_dir,
                    Path(self.input_file),
                    Path(toolkit_dir),
                    merge_dir,
                    log=log,
                )
                if mrep.get("ok"):
                    log(f"[合并] 纯新增合并包 {mrep['package_dir']} 新增部件 {mrep['new_parts']} 跳过已有 {mrep['skipped_parts']} 拷贝资产 {mrep['copied_files']}")
                else:
                    log(f"[合并] 未生成 {mrep.get('error')}")
            except Exception as exc:
                log(f"[合并] 生成失败 不影响已导出的工程 {exc}")

            # 3) 可选：并入 Toolkit。默认关闭；开启时绝不覆盖内容正常的既有文件，
            #    但会对"已存在却引用悬空"的资产做修复性覆盖（先备份）。
            #    注意这里不能再用 new_parts 做门槛：部件全都已存在时 new_parts=0，
            #    而那份已存在的 prefab 恰恰可能正是引用悬空、需要被修好的那个。
            if mrep.get("ok"):
                if not install:
                    log(self.t("install_skipped_opt"))
                else:
                    self.install_into_toolkit(log, Path(toolkit_dir), Path(str(mrep["package_dir"])), mrep)

            # 4) 导出后自检：校验导出工程所有 prefab 的脚本引用是否在 Toolkit 命中
            try:
                import sfs_pack_prefab_extract as prefab_verify
                guid_map = prefab_verify.build_script_guid_map(Path(toolkit_dir) / "Assets" / "Scripts")
                # mod 自有脚本(DLL/ModCode)的 guid 不在 Toolkit 内，但已保留在导出工程，
                # 纳入自检范围，避免自定义引用被误判为『缺失』
                try:
                    guid_map.update(prefab_verify.build_plugin_guid_map(exported_dir / "Assets"))
                except Exception:
                    pass
                total_refs = total_missing = 0
                missing_files: list[str] = []
                for prefab in (exported_dir / "Assets").rglob("*.prefab"):
                    res = prefab_verify.verify_prefab_script_refs(str(prefab), guid_map)
                    total_refs += res["total_refs"] if res["total_refs"] else 0
                    total_missing += res["missing"]
                    if res["missing"]:
                        missing_files.append(str(prefab.relative_to(exported_dir)))
                log(f"[校验] 导出工程脚本引用 命中 {total_refs - total_missing}/{total_refs} 缺失 {total_missing}")
                if total_missing:
                    log(f"[校验] [!] {len(missing_files)} 个 prefab 存在缺失脚本引用 {missing_files[:8]}{'...' if len(missing_files) > 8 else ''}")
                    try:
                        with (merge_dir / "MERGE_README.md").open("a", encoding="utf-8") as fh:
                            fh.write(f"\n- 导出工程自检 {total_missing} 处脚本引用缺失 涉及 {len(missing_files)} 个 prefab 多为 mod 自定义类 需 CodeAssembly\n")
                    except OSError:
                        pass
            except Exception as exc:
                log(f"[校验] 自检脚本引用失败 不影响导出结果 {exc}")

        log(self.t("export_done"))

    def install_into_toolkit(self, log, toolkit_dir: Path, package_dir: Path, mrep: dict[str, object]) -> None:
        """把合并包并入 Toolkit。

        默认只写新文件、绝不覆盖既有内容。唯一的例外是「悬空引用修复」：Toolkit 里
        已存在同名资产、但它的 guid 引用大量悬空，而包里这份已对齐好的版本悬空更少时，
        先把原文件备份到 `<Toolkit>/_PackToolBackup/<时间戳>/`，再覆盖。
        判据是「悬空引用数必须下降」，所以只会往好的方向改，不会把好的改坏。
        """
        collisions = mrep.get("guid_collisions") or []
        if collisions:
            log(self.t("install_refused", n=len(collisions)))
            return
        pkg_assets = package_dir / "Assets"
        tk_assets = toolkit_dir / "Assets"
        if not pkg_assets.is_dir():
            return

        # 悬空判断用的已知 GUID 全集：Toolkit 现有的 + 包内带的
        import sfs_script_keep_alive as keepalive
        known: set[str] = set()
        for meta in tk_assets.rglob("*.meta"):
            g = keepalive._meta_guid(meta)
            if g:
                known.add(g)
        for meta in pkg_assets.rglob("*.meta"):
            g = keepalive._meta_guid(meta)
            if g:
                known.add(g)

        repairable_suffixes = {".prefab", ".mat", ".asset"}
        written = written_parts = skipped_existing = repaired = 0
        backup_root = toolkit_dir / "_PackToolBackup" / time.strftime("%Y%m%d_%H%M%S")
        try:
            for src in sorted(pkg_assets.rglob("*")):
                if not src.is_file():
                    continue
                dest = tk_assets / src.relative_to(pkg_assets)
                if dest.exists():
                    # 已存在就跳过——除非这份是"引用悬空"的坏资产，而包里这份更好
                    if dest.is_file() and src.suffix.lower() in repairable_suffixes:
                        try:
                            old_text = dest.read_text(encoding="utf-8", errors="ignore")
                            new_text = src.read_text(encoding="utf-8", errors="ignore")
                        except OSError:
                            skipped_existing += 1
                            continue
                        old_bad = keepalive.count_dangling_refs(old_text, known)
                        new_bad = keepalive.count_dangling_refs(new_text, known)
                        if old_bad and new_bad < old_bad:
                            try:
                                saved = backup_root / dest.relative_to(tk_assets)
                                saved.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(dest, saved)
                            except OSError:
                                pass  # 备份失败就不动它，宁可漏修不可误覆盖
                            else:
                                shutil.copy2(src, dest)
                                repaired += 1
                                log(self.t("install_repaired", name=dest.name, before=old_bad, after=new_bad))
                                continue
                    skipped_existing += 1
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                written += 1
                if src.suffix.lower() == ".prefab":
                    written_parts += 1
        except OSError as exc:
            log(self.t("install_failed", error=exc))
            return
        if repaired:
            log(self.t("install_repair_done", n=repaired, path=backup_root))
        if skipped_existing:
            log(self.t("install_skipped", n=skipped_existing))
        if written_parts:
            log(f"[安装] 已把 {written_parts} 个新增部件并入 Toolkit {tk_assets}")
            log(self.t("installed_to_toolkit", new=mrep.get("new_parts", 0), skip=mrep.get("skipped_parts", 0), copy=mrep.get("copied_files", 0), sub=mrep.get("parts_subfolder", "")))
        elif written:
            log(f"[安装] 已写入 {written} 个文件 无新增 prefab {tk_assets}")
        elif not repaired:
            log("[安装] 没有新文件需要写入 Toolkit")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
