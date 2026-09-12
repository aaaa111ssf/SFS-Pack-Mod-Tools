#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SFS Pack Tool 离线回归测试（无需真实 .pack / AssetRipper）。

用桩件替代 UnityPy，在临时目录里搭最小工程验证核心链路：
  1. 脚本免挂对齐：删 stub -> 整拷 Toolkit 脚本 -> 重写 .prefab/.asset 的 m_Script GUID
  2. 合并包：新增部件归一化到 Assets/Resources/Parts，且不含 .cs
  3. 新增部件同名去重
  4. 并入 Toolkit 时绝不覆盖既有文件

运行：python test_keepalive_smoke.py
"""
from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

BUILD_KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(BUILD_KIT))

TOOLKIT_PART = "a" * 32
TOOLKIT_BASE = "b" * 32
STUB_IN_SCRIPTS = "c" * 32
STUB_IN_MONOSCRIPT = "d" * 32
MOD_DLL_GUID = "68295d573e80e1c18ab7ad250963a526"


class Result:
    def __init__(self) -> None:
        self.ok = True

    def check(self, label: str, cond: bool) -> None:
        print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
        if not cond:
            self.ok = False


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def unity_meta(guid: str) -> str:
    return f"fileFormatVersion: 2\nguid: {guid}\nMonoImporter:\n  externalObjects: {{}}\n"


def install_fake_unitypy(dirpath: Path, classes: list[str]) -> None:
    write(dirpath / "UnityPy.py", (
        "class _Obj:\n"
        "    def __init__(self, cls):\n"
        "        self.type = type('T', (), {'name': 'MonoScript'})()\n"
        "        self._cls = cls\n"
        "    def read(self):\n"
        "        return type('MS', (), {'m_ClassName': self._cls})()\n"
        "class _Env:\n"
        "    def __init__(self, objs): self.objects = objs\n"
        f"def load(raw):\n"
        f"    return _Env([_Obj(c) for c in {classes!r}])\n"
    ))
    sys.path.insert(0, str(dirpath))


def make_toolkit(root: Path) -> Path:
    toolkit = root / "Toolkit"
    scripts = toolkit / "Assets" / "Scripts"
    write(scripts / "Part.cs", "// class FakeInComment\npublic class Part : Base {}\n")
    write(scripts / "Part.cs.meta", unity_meta(TOOLKIT_PART))
    write(scripts / "Base.cs", "public class Base {}\n")
    write(scripts / "Base.cs.meta", unity_meta(TOOLKIT_BASE))
    return toolkit


def make_pack(root: Path) -> Path:
    pack = root / "mod.pack"
    write(pack, json.dumps({"WindowsBuild": base64.b64encode(b"UnityFS-fake").decode()}))
    return pack


def mono_yaml(guid: str) -> str:
    return f"  m_Script: {{fileID: 11500000, guid: {guid}, type: 3}}\n"


def test_alignment(tmp: Path, r: Result) -> None:
    print("\n=== 1. 脚本免挂对齐 ===")
    import sfs_script_keep_alive as ka

    toolkit = make_toolkit(tmp)
    pack = make_pack(tmp)
    project = tmp / "Project"
    write(project / "Assets" / "Scripts" / "Part.cs", "public class Part {}\n")
    write(project / "Assets" / "Scripts" / "Part.cs.meta", unity_meta(STUB_IN_SCRIPTS))
    write(project / "Assets" / "MonoScript" / "Part.cs", "public class Part {}\n")
    write(project / "Assets" / "MonoScript" / "Part.cs.meta", unity_meta(STUB_IN_MONOSCRIPT))
    write(project / "Assets" / "Parts" / "Engine.prefab", mono_yaml(STUB_IN_SCRIPTS) + mono_yaml(STUB_IN_MONOSCRIPT))
    write(project / "Assets" / "Configs" / "Settings.asset", mono_yaml(STUB_IN_SCRIPTS))

    logs: list[str] = []
    rep = ka.align_scripts_to_toolkit(project, pack, toolkit, log=logs.append)
    for line in logs:
        print("   ", line)

    scripts = project / "Assets" / "Scripts"
    part_meta = (scripts / "Part.cs.meta").read_text(encoding="utf-8")
    prefab = (project / "Assets" / "Parts" / "Engine.prefab").read_text(encoding="utf-8")
    asset = (project / "Assets" / "Configs" / "Settings.asset").read_text(encoding="utf-8")

    r.check("stub 已删除，Part.cs 换成 Toolkit GUID", TOOLKIT_PART in part_meta)
    r.check("依赖闭包已整拷（Base.cs）", (scripts / "Base.cs").is_file())
    r.check("Assets/MonoScript 下的 stub 也被清理", not (project / "Assets" / "MonoScript" / "Part.cs").exists())
    r.check(".prefab 引用已重写", TOOLKIT_PART in prefab and STUB_IN_SCRIPTS not in prefab)
    r.check("第二处引用（另一 stub）也重写", STUB_IN_MONOSCRIPT not in prefab)
    r.check(".asset 引用已重写（ScriptableObject 覆盖）", TOOLKIT_PART in asset)
    r.check("未误报 unresolved", rep.get("unresolved_classes") == [])


def test_merge_and_dedupe(tmp: Path, r: Result) -> None:
    print("\n=== 2. 合并包 + 同名去重 ===")
    import sfs_script_keep_alive as ka

    toolkit = make_toolkit(tmp)
    pack = make_pack(tmp)
    project = tmp / "Project2"
    for i, sub in enumerate(("A", "B")):
        write(project / "Assets" / sub / "Engine.prefab", mono_yaml(TOOLKIT_PART))
    write(project / "Assets" / "A" / "Other.prefab", mono_yaml(TOOLKIT_PART))

    logs: list[str] = []
    merge = tmp / "Merge2"
    mrep = ka.build_merge_package(project, pack, toolkit, merge, log=logs.append)
    for line in logs:
        print("   ", line)

    parts = merge / "Assets" / "Resources" / "Parts"
    r.check("新增部件归一化到 Resources/Parts", mrep.get("ok", False) and (parts / "Engine.prefab").is_file())
    r.check("同名 prefab 已去重（只保留 1 个 Engine）", mrep.get("new_parts") == 2 and mrep.get("duplicate_parts"))
    r.check("合并包内不含 .cs", not any(merge.rglob("*.cs")))


def test_toolkit_selfcheck(tmp: Path, r: Result) -> None:
    print("\n=== 3. Toolkit 前提自检 ===")
    import sfs_script_keep_alive as ka

    good = make_toolkit(tmp / "good")
    write(good / "Assets" / "Resources" / "Parts" / "Stock.prefab", mono_yaml(TOOLKIT_PART))
    ok = ka.verify_toolkit_self(good)
    print("    good:", ok)
    r.check("同版本 Toolkit 自检 0 缺失", ok["missing"] == 0 and ok["refs"] == 1)

    bad = make_toolkit(tmp / "bad")
    write(bad / "Assets" / "Scripts" / "Part.cs.meta", unity_meta("9" * 32))  # 模拟 meta 被重新生成
    write(bad / "Assets" / "Resources" / "Parts" / "Stock.prefab", mono_yaml(TOOLKIT_PART))
    ng = ka.verify_toolkit_self(bad)
    print("    bad :", ng)
    r.check("GUID 不符时自检能报出缺失", ng["missing"] == 1)


def test_install_never_overwrites(tmp: Path, r: Result) -> None:
    print("\n=== 4. 并入 Toolkit 不覆盖既有文件 ===")
    spec = importlib.util.spec_from_file_location("v22_cn_app", BUILD_KIT / "v22-CN.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    class _Shell:  # 只需要 install_into_toolkit 用到的 self.t()
        t = staticmethod(lambda key, **kw: f"{key}:{kw}")

    toolkit = tmp / "Toolkit3"
    write(toolkit / "Assets" / "Textures" / "metal.png.meta", unity_meta("1" * 32))
    write(toolkit / "Assets" / "Textures" / "metal.png", "ORIGINAL")  # 用户既有内容
    package = tmp / "Pkg3"
    write(package / "Assets" / "Textures" / "metal.png", "FROM_MOD")
    write(package / "Assets" / "Textures" / "metal.png.meta", unity_meta("1" * 32))
    write(package / "Assets" / "Resources" / "Parts" / "New.prefab", mono_yaml("2" * 32))

    logs: list[str] = []
    module.App.install_into_toolkit(_Shell(), logs.append, toolkit, package, {"new_parts": 1})
    for line in logs:
        print("   ", line)

    r.check("既有文件未被覆盖", (toolkit / "Assets" / "Textures" / "metal.png").read_text() == "ORIGINAL")
    r.check("新文件已写入", (toolkit / "Assets" / "Resources" / "Parts" / "New.prefab").is_file())
    r.check("提示了跳过数量", any("install_skipped" in line for line in logs))


def test_merge_keeps_mod_dll(tmp: Path, r: Result) -> None:
    print("\n=== 5. 合并包必须携带 mod 自有程序集(DLL) ===")
    import sfs_script_keep_alive as ka

    toolkit = make_toolkit(tmp)
    pack = make_pack(tmp)
    project = tmp / "Project5"
    # mod 自有程序集：AssetRipper 放进 Plugins，prefab 的 m_Script 直接指向它的 guid
    (project / "Assets" / "Plugins").mkdir(parents=True, exist_ok=True)
    (project / "Assets" / "Plugins" / "AssetsofIce.dll").write_bytes(b"MZ-fake-assembly-bytes")
    write(project / "Assets" / "Plugins" / "AssetsofIce.dll.meta", unity_meta(MOD_DLL_GUID))
    # 一个引用该 DLL 的部件（同时引用一个 Toolkit 类，模拟混合引用）
    write(project / "Assets" / "Parts" / "Reactor.prefab",
          mono_yaml(MOD_DLL_GUID) + mono_yaml(TOOLKIT_PART))

    logs: list[str] = []
    merge = tmp / "Merge5"
    mrep = ka.build_merge_package(project, pack, toolkit, merge, log=logs.append)
    for line in logs:
        print("   ", line)

    dll_out = merge / "Assets" / "Plugins" / "AssetsofIce.dll"
    meta_out = merge / "Assets" / "Plugins" / "AssetsofIce.dll.meta"
    r.check("合并包含 mod DLL", dll_out.is_file())
    r.check("合并包含 DLL 的 .meta(guid 一致)", meta_out.is_file()
            and MOD_DLL_GUID in meta_out.read_text(encoding="utf-8"))
    r.check("报告里记录了携带的 DLL 数", mrep.get("mod_custom_dll", 0) == 1)
    r.check("DLL 不被 MERGE_SKIP_SUFFIXES 误删", mrep.get("ok", False))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="sfs_smoke_"))
    r = Result()
    try:
        install_fake_unitypy(tmp / "stubmod", ["Part"])
        test_alignment(tmp, r)
        test_merge_and_dedupe(tmp, r)
        test_toolkit_selfcheck(tmp, r)
        test_merge_keeps_mod_dll(tmp, r)
        test_install_never_overwrites(tmp, r)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + ("ALL PASS" if r.ok else "SOME FAILED"))
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
