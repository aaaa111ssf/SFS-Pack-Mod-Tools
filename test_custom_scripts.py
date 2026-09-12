#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自定义脚本还原离线验证：pack 带 CodeAssembly 时把反编译源码接回工程。

不依赖真实 ilspycmd —— 用假的「反编译产物目录」替换掉反编译步骤，
只验证接回逻辑：GUID 复用、stub 删除、Toolkit 同名类跳过、辅助类一并带入。
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sfs_script_keep_alive.py"

STUB = """using UnityEngine;

namespace AssetsofIce
{
	public class PowerModule : MonoBehaviour
	{
		/*
		Dummy class. This could have happened for several reasons:
		1. No dll files were provided to AssetRipper.
		*/
	}
}
"""

REAL = """using UnityEngine;

namespace AssetsofIce;

public class PowerModule : MonoBehaviour
{
	public float maxGeneration;

	public void Tick()
	{
		maxGeneration += 1f;
	}
}
"""

HELPER = """namespace AssetsofIce;

public class FuelManager
{
	public int count;
}
"""

TOOLKIT_SAME_NAME = """namespace SFS.Parts.Modules;

public class MassModule : MonoBehaviour
{
	public float mass;
}
"""


def load_module():
    spec = importlib.util.spec_from_file_location("keep_alive", SRC)
    module = importlib.util.module_from_spec(spec)
    sys.modules["keep_alive"] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str, guid: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if guid:
        Path(str(path) + ".meta").write_text(
            f"fileFormatVersion: 2\nguid: {guid}\nMonoImporter:\n  externalObjects: {{}}\n",
            encoding="utf-8",
        )


def main() -> int:
    ka = load_module()
    temp = Path(tempfile.mkdtemp(prefix="sfs_custom_"))
    project = temp / "Export"

    stub_guid = "a" * 32
    write(
        project / "Assets/Scripts/Assembly-CSharp/AssetsofIce/PowerModule.cs",
        STUB,
        stub_guid,
    )

    decompiled = temp / "Decompiled"
    write(decompiled / "AssetsofIce/PowerModule.cs", REAL)
    write(decompiled / "AssetsofIce/FuelManager.cs", HELPER)
    # 与 Toolkit 同名 —— 必须跳过，否则 CS0101
    write(decompiled / "SFS.Parts.Modules/MassModule.cs", TOOLKIT_SAME_NAME)

    ok = 0
    fail = 0

    def check(label: str, cond: bool):
        nonlocal ok, fail
        print(f"  [{'OK ' if cond else 'FAIL'}] {label}")
        ok += bool(cond)
        fail += not cond

    # 用假的反编译产物替换掉需要 .NET 的那一步
    ka.extract_code_assembly = lambda pack, out: (
        out.parent.mkdir(parents=True, exist_ok=True),
        out.write_bytes(b"MZfake"),
        out,
    )[-1]
    ka.decompile_assembly = lambda dll, out, log: decompiled

    logs: list[str] = []
    rep = ka.restore_custom_scripts(
        project, temp / "x.pack", {"MassModule"}, ["PowerModule"], logs.append
    )
    for line in logs:
        print("    " + line)

    mod = project / "Assets" / "Scripts" / ka.MOD_CODE_DIRNAME
    print("\n=== 1. 自定义脚本接回 ===")
    check("还原成功", rep["ok"] is True)
    check("写进了 ModCode 目录", (mod / "AssetsofIce/PowerModule.cs").is_file())
    check("源码是反编译版本(不是 stub)",
          "maxGeneration" in (mod / "AssetsofIce/PowerModule.cs").read_text(encoding="utf-8"))
    check("记录了还原的类", rep["classes"] == ["PowerModule"])

    print("\n=== 2. GUID 复用 —— prefab 引用不用改 ===")
    meta = mod / "AssetsofIce/PowerModule.cs.meta"
    check("生成了 .meta", meta.is_file())
    check("复用了原 stub 的 GUID", stub_guid in meta.read_text(encoding="utf-8"))
    check("原 stub 已删除",
          not (project / "Assets/Scripts/Assembly-CSharp/AssetsofIce/PowerModule.cs").is_file())
    check("原 stub 的 .meta 也已删除",
          not (project / "Assets/Scripts/Assembly-CSharp/AssetsofIce/PowerModule.cs.meta").is_file())

    print("\n=== 3. 辅助类带入 / Toolkit 同名类跳过 ===")
    check("DLL 里的辅助类一并拷入(否则 CS0246)", (mod / "AssetsofIce/FuelManager.cs").is_file())
    check("辅助类也有 .meta", (mod / "AssetsofIce/FuelManager.cs.meta").is_file())
    check("与 Toolkit 同名的类被跳过", not (mod / "SFS.Parts.Modules/MassModule.cs").is_file())

    print("\n=== 4. 工程内不再有重复定义 ===")
    dups = ka.find_duplicate_types(project / "Assets")
    check("无重复类型", not dups)
    m = ka.scan_script_meta(project / "Assets" / "Scripts")
    check("PowerModule 的 GUID 已指向新文件", m.get("PowerModule") == stub_guid)
    check("FuelManager 也被索引到", "FuelManager" in m)
    check("MassModule 不在工程里", "MassModule" not in m)

    print("\n=== 5. 没有 CodeAssembly 时优雅降级 ===")
    ka.extract_code_assembly = lambda pack, out: None
    rep2 = ka.restore_custom_scripts(
        project, temp / "y.pack", {"MassModule"}, ["PowerModule"], lambda _m: None
    )
    check("标记为无程序集", rep2["reason"] == "no_code_assembly")
    check("未误报成功", rep2["ok"] is False)
    check("没有动任何文件", rep2["files"] == 0)

    print(f"\n结果: {ok} 通过 {fail} 失败")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
