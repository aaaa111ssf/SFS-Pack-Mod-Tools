#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SFS Pack Tool v22."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import threading
import webbrowser
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import UnityPy
import sfs_pack_prefab_export as prefab_exporter

DEFAULT_AUTHOR = "〈A Future star汉化〉"
ASSET_RIPPER_DOWNLOAD_PAGE = "https://github.com/AssetRipper/AssetRipper/releases/latest"
EXCLUDE_WORDS = {
    "Color_Gray", "Toggle", "width", "target_state", "tank", "height", "DeployParachute",
    "Landing_Leg_Expanded", "Basic_Parts", "Color_Black", "Color_White", "Flat Smooth 4",
    "Flat Smooth", "Detach", "Flat Faces", "Liquid_Fuel", "Metal", "Panel_Expanded",
    "width_original", "Engine_2", "fairing", "mass", "Flat_Shadow", "Separation",
    "Expanded", "ToggleEnabled", "ToggleEngine", "cone", "Engines", "Nozzle_2",
    "Engine_Parts", "torque", "throttle", "Mass_Unit", "engine_on", "ToggleRCS",
    "ToggleTransfer", "Solid_Fuel",
}
DANGER_PATH_KEYWORDS = {
    "m_MethodName", "m_ClassName", "m_Namespace", "m_TypeName", "variableName", "input",
    "output", "name", "id", "type", "key", "reference", "tag", "layer", "fragmentName",
    "saves", "points", "elements", "m_Name", "m_Script",
}
SAFE_FIELDS = {
    "displayName", "description", "label", "DisplayName", "Description", "Author",
    "TranslatableName", "text", "title", "units",
}

TEXT = {
    "zh": {
        "window": "SFS Pack Tool v22-by A Future star",
        "title": "SFS Pack Tool V22",
        "subtitle": "汉化写入 · Prefab · 贴图 · Unity 工程导出",
        "language": "语言：",
        "chinese": "中文",
        "english": "English",
        "input_frame": "输入文件",
        "select_pack": "选择原始 mod.pack",
        "select_translation": "选择翻译 JSON",
        "no_pack": "尚未选择 mod.pack",
        "translator_frame": "汉化处理",
        "author": "汉化作者标识：",
        "extract": "提取待翻译文本",
        "extract_path": "提取 JSON 保存路径：",
        "select_json_path": "选择保存位置",
        "write": "写入汉化并生成 Pack",
        "export_frame": "Unity Prefab / 贴图 / 工程导出",
        "asset_ripper": "AssetRipper 路径：",
        "select_exe": "选择 .exe",
        "download_page": "官方下载页",
        "asset_hint": "留空时将提示自动下载；手动下载后选择 AssetRipper.GUI.Free.exe。",
        "output_dir": "导出位置：",
        "select_dir": "选择位置",
        "export": "一键导出工程",
        "ready": "请选择pack文件",
        "select_pack_first": "请先选择原始 mod.pack。",
        "no_pack_title": "未选择文件",
        "path_invalid": "路径无效",
        "path_invalid_text": "所选 AssetRipper 路径不存在，请重新选择或清空后自动下载。",
        "need_ripper": "需要 AssetRipper",
        "auto_download_prompt": "尚未选择 AssetRipper。是否从官方发布页自动下载 Windows 版本？\n\n选择“是”后会自动下载；选择“否”将打开官方下载页。",
        "opened_download": "已打开官方 AssetRipper 下载页。下载并解压后，请点击“选择 .exe”。",
        "export_start": "开始导出",
        "export_done": "✔ Unity 工程导出完成。请查看输出目录及同名 ZIP。",
        "export_failed": "❌ Unity 工程导出失败：{error}",
        "selected_pack": "已选择源文件：{name}",
        "selected_translation": "已选择翻译文件：{name}",
        "selected_ripper": "已选择 AssetRipper：{path}",
        "extract_start": "开始提取文本...",
        "no_pack_log": "❌ 未选择 mod.pack",
        "json_error": "❌ JSON 读取错误：{error}",
        "scan": "  扫描 {build}...",
        "unpack_error": "  ❌ {build} 解包失败：{error}",
        "extract_done": "✔ 提取完成：共 {count} 条文本 → {path}",
        "no_translation": "❌ 未选择翻译 JSON",
        "read_failed": "❌ 文件读取失败：{error}",
        "writing": "正在写入 {build}...",
        "decode_failed": "  ❌ {build} 解码失败：{error}",
        "write_done": "  ✔ {build} 完成，修改 {count} 处",
        "save_failed": "  ❌ {build} 保存失败：{error}",
        "pack_done": "✔ 最终文件已生成：{path}",
        "output_failed": "❌ 输出失败：{error}",
        "processing_failed": "❌ 处理失败：{error}",
    },
    "en": {
        "window": "SFS Pack Tool v22 - Localization & Unity Export-by A Future star",
        "title": "SFS Pack Tool V22",
        "subtitle": "Localization · Prefabs · Textures · Unity Project Export",
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
        "asset_ripper": "AssetRipper path:",
        "select_exe": "Select .exe",
        "download_page": "Official download",
        "asset_hint": "Leave blank to be prompted for automatic download; choose AssetRipper.GUI.Free.exe after manual download.",
        "output_dir": "Export location:",
        "select_dir": "Choose location",
        "export": "Export Unity project",
        "ready": "Ready. Select a mod.pack; export includes Prefabs, textures, materials, .meta files and Unity project files.",
        "select_pack_first": "Select the source mod.pack first.",
        "no_pack_title": "No input file",
        "path_invalid": "Invalid path",
        "path_invalid_text": "The selected AssetRipper path does not exist. Select it again or clear it for automatic download.",
        "need_ripper": "AssetRipper required",
        "auto_download_prompt": "No AssetRipper has been selected. Download the Windows version from the official release page automatically?\n\nChoose Yes to download automatically. Choose No to open the official download page.",
        "opened_download": "The official AssetRipper download page is open. Download and extract it, then select the .exe file.",
        "export_start": "Starting Unity project export. The output includes Prefabs, textures, materials, .meta files, Packages and ProjectSettings.",
        "export_done": "✔ Unity project export completed. Check the output directory and its ZIP file.",
        "export_failed": "❌ Unity project export failed: {error}",
        "selected_pack": "Source selected: {name}",
        "selected_translation": "Translation selected: {name}",
        "selected_ripper": "AssetRipper selected: {path}",
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
    },
}


def compact_chinese_text(text: str) -> str:
    text = re.sub(r"(?<!\d)[，。,.]+|[，。,.]+(?!\d)", " ", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def app_data_dir() -> Path:
    root = Path(os.environ.get("APPDATA", Path.home())) if os.name == "nt" else Path.home() / ".config"
    folder = root / "AFuturestar" / "SFS-Pack-Tool"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


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


def is_path_safe(path: str) -> bool:
    if any(field in path for field in SAFE_FIELDS):
        if path.split(".")[-1].split("[")[0] in SAFE_FIELDS:
            return True
    return not any(key in path for key in DANGER_PATH_KEYWORDS)


def is_exclude_word(text: object) -> bool:
    return isinstance(text, str) and text.strip() in EXCLUDE_WORDS


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


def is_display_text(text: str, path: str) -> bool:
    if not text or len(text) < 2 or not is_path_safe(path) or is_exclude_word(text):
        return False
    if re.match(r"^[0-9\s\.\,\%\+\-\*\/\(\)]+$", text):
        return False
    return not ("UnityEngine" in text or "Assembly-" in text or "SFS." in text or "/" in text or "\\" in text or "None" in text or re.search(r"_(Name|Description)$", text))


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
    for build in ("AndroidBuild", "WindowsBuild", "MacBuild", "IOS_Build"):
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
                        recursive_walk(tree, "", lambda parent, key, value, path: texts.add(value) if is_display_text(value, path) else None)
            except Exception:
                continue
    output = Path(output_file) if output_file else Path(input_file).with_name("texts_to_translate.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({item: item for item in sorted(texts)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        translations = json.loads(Path(translation_file).read_text(encoding="utf-8"))
    except Exception as exc:
        log(translate("read_failed", error=exc))
        return
    translations = {source: target for source, target in translations.items() if source != target}
    for build in ("AndroidBuild", "WindowsBuild", "MacBuild", "IOS_Build"):
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
                                if key == "Author" and author and author not in value:
                                    node[key] = value + author
                                    changed += 1
                                elif is_path_safe(child) and not is_exclude_word(value) and value in translations:
                                    node[key] = translations[value]
                                    changed += 1
                            elif isinstance(value, (dict, list)):
                                replace(value, child)
                    elif isinstance(node, list):
                        for index, value in enumerate(node):
                            child = f"{path}[{index}]"
                            if isinstance(value, str) and is_path_safe(child) and not is_exclude_word(value) and value in translations:
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


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = load_settings()
        self.locale = self.settings.get("language", "zh") if self.settings.get("language") in TEXT else "zh"
        self.input_file = ""
        self.translation_file = ""
        self.logs: list[str] = []
        self.author_var = tk.StringVar(value=self.settings.get("author", DEFAULT_AUTHOR))
        self.asset_ripper_var = tk.StringVar(value=self.settings.get("asset_ripper", ""))
        self.export_dir_var = tk.StringVar(value=self.settings.get("export_parent", ""))
        self.extract_output_var = tk.StringVar(value=self.settings.get("extract_output", ""))
        self.language_var = tk.StringVar()
        icon = resource_path("assets/SFS_Pack_Tool_v22.ico")
        if icon.is_file():
            try:
                self.root.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        self.build_ui()

    def t(self, key: str, **kwargs) -> str:
        text = TEXT[self.locale][key].format(**kwargs)
        return compact_chinese_text(text) if self.locale == "zh" else text

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
        tk.Label(export, text=self.t("asset_ripper")).grid(row=0, column=0, sticky="w")
        tk.Entry(export, textvariable=self.asset_ripper_var).grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(export, text=self.t("select_exe"), command=self.pick_asset_ripper, width=14).grid(row=0, column=2, padx=3)
        tk.Button(export, text=self.t("download_page"), command=lambda: webbrowser.open(ASSET_RIPPER_DOWNLOAD_PAGE), width=14).grid(row=0, column=3, padx=3)
        tk.Label(export, text=self.t("asset_hint"), fg="#555555", wraplength=650, justify="left").grid(row=1, column=1, columnspan=3, sticky="w", padx=5)
        tk.Label(export, text=self.t("output_dir")).grid(row=2, column=0, sticky="w", pady=(7, 0))
        tk.Entry(export, textvariable=self.export_dir_var).grid(row=2, column=1, sticky="ew", padx=5, pady=(7, 0))
        tk.Button(export, text=self.t("select_dir"), command=self.pick_export_dir, width=14).grid(row=2, column=2, padx=3, pady=(7, 0))
        tk.Button(export, text=self.t("export"), command=self.start_export, bg="#e6f7ff", width=14).grid(row=2, column=3, padx=3, pady=(7, 0))
        export.columnconfigure(1, weight=1)

        self.log_widget = scrolledtext.ScrolledText(self.root, font=("Consolas", 10), height=19, state="disabled")
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
            "asset_ripper": self.asset_ripper_var.get().strip(),
            "export_parent": self.export_dir_var.get().strip(),
            "extract_output": self.extract_output_var.get().strip(),
        })

    def log(self, message: str) -> None:
        message = compact_chinese_text(message) if self.locale == "zh" else message
        def append() -> None:
            self.logs.append(message)
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
        if not self.export_dir_var.get().strip():
            self.export_dir_var.set(str(Path(path).parent))
        if not self.extract_output_var.get().strip():
            self.extract_output_var.set(str(Path(path).with_name("texts_to_translate.json")))
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

    def pick_asset_ripper(self) -> None:
        path = filedialog.askopenfilename(title="AssetRipper.GUI.Free.exe", filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.asset_ripper_var.set(path)
            self.save_user_settings()
            self.log(self.t("selected_ripper", path=path))

    def pick_export_dir(self) -> None:
        initial = self.export_dir_var.get().strip() or (str(Path(self.input_file).parent) if self.input_file else str(Path.home()))
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self.export_dir_var.set(path)
            self.save_user_settings()

    def start_export(self) -> None:
        if not self.input_file:
            messagebox.showwarning(self.t("no_pack_title"), self.t("select_pack_first"))
            return
        input_path = Path(self.input_file).resolve()
        export_parent = Path(self.export_dir_var.get().strip() or input_path.parent).resolve()
        output_path = export_parent / f"{input_path.stem}_UnityProject"
        output = str(output_path)
        ripper = self.asset_ripper_var.get().strip()
        if ripper and not Path(ripper).is_file():
            messagebox.showerror(self.t("path_invalid"), self.t("path_invalid_text"))
            return
        if not ripper and not messagebox.askyesno(self.t("need_ripper"), self.t("auto_download_prompt")):
            webbrowser.open(ASSET_RIPPER_DOWNLOAD_PAGE)
            self.log(self.t("opened_download"))
            return
        self.save_user_settings()
        self.run_async(lambda log: self.export_project(log, output, ripper))

    def export_project(self, log, output: str, ripper: str) -> None:
        log(self.t("export_start"))
        args = SimpleNamespace(input=self.input_file, output_dir=output, zip=None, asset_ripper=ripper or None, no_download=False, no_zip=False, overwrite=True)
        previous_log = prefab_exporter.log
        prefab_exporter.log = log
        try:
            prefab_exporter.export_prefabs(args)
            log(self.t("export_done"))
        except Exception as exc:
            log(self.t("export_failed", error=exc))
        finally:
            prefab_exporter.log = previous_log


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
