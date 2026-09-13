#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脚本免挂对齐：把导出工程 prefab 的 m_Script GUID 重指向 Modding Toolkit 真脚本。

.prefab 的 MonoBehaviour 靠 m_Script(指向 MonoScript 的 GUID) 定位脚本类；
AssetRipper 生成的 stub GUID 与包内原始引用不一致，打开工程就会 Missing Script。
流程：读回包内脚本类名 → 按类名取 Toolkit GUID → 删 stub(防 CS0101)
→ 整拷 Assets/Scripts(防 CS0246) → 重写 .prefab/.asset → 上报无法解析的类。
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# Unity YAML 里脚本引用整行，形如：
#   m_Script: {fileID: 11500000, guid: 305b12a83390f5c488a64145b53f92bd, type: 3}
SCRIPT_REF_RE = re.compile(
    r"(m_Script:\s*\{\s*fileID:\s*\d+\s*,\s*guid:\s*)([0-9a-fA-F]{32})(\s*,\s*type:\s*3\s*\})",
    re.IGNORECASE,
)
CLASS_DECL_RE = re.compile(r"\b(?:partial\s+|abstract\s+|sealed\s+|static\s+)*class\s+(\w+)")
COMMENT_RE = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
# 剥字符串字面量，避免里面的花括号干扰深度统计（含 @"..." 与 $"{...}" 形式）
STRING_RE = re.compile(r'@?"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')
NS_DECL_RE = re.compile(r"^\s*namespace\s+([\w.]+)", re.MULTILINE)
TYPE_DECL_RE = re.compile(
    r"^\s*(?:\[[^\]\n]*\]\s*)?"
    r"(?:(?:public|internal|private|protected)\s+)?"
    r"(?:(?:abstract|sealed|static|unsafe|readonly|new)\s+)*"
    r"(partial\s+)?"
    r"(?:class|struct|interface|enum)\s+(\w+)",
    re.MULTILINE,
)

PRE_BUILD_KEYS = ("WindowsBuild", "AndroidBuild", "MacBuild", "IOS_Build")

# 反编译出来的作者自定义脚本统一放这个子目录，跟 Toolkit 自带的 Scripts 分开
MOD_CODE_DIRNAME = "ModCode"
MONO_META_TEMPLATE = (
    "fileFormatVersion: 2\n"
    "guid: {guid}\n"
    "MonoImporter:\n"
    "  externalObjects: {{}}\n"
    "  serializedVersion: 2\n"
    "  defaultReferences: []\n"
    "  executionOrder: 0\n"
    "  icon: {{instanceID: 0}}\n"
    "  userData: \n"
    "  assetBundleName: \n"
    "  assetBundleVariant: \n"
)

ASSET_GUID_RE = re.compile(r"guid:\s*([0-9a-fA-F]{32})")
# 合并包里绝不携带脚本源码/已编译程序集（Toolkit 自己就有），避免重复导致 CS0263。
MERGE_SKIP_SUFFIXES = {".cs", ".dll"}


def class_name_of_file(cs_path: Path) -> str:
    """推断 .cs 的类名：文件名优先，其次取首个 class 声明。"""
    try:
        text = cs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return cs_path.stem
    text = COMMENT_RE.sub("", text)  # 先剥注释，避免注释里的 "class Foo" 干扰
    declared = CLASS_DECL_RE.findall(text)
    if cs_path.stem in declared:
        return cs_path.stem
    return declared[0] if declared else cs_path.stem


def declared_types(cs_path: Path) -> set[tuple[str, bool]]:
    """取 .cs 里**顶层**声明的类型，返回 {(全限定名, 是否 partial)}。

    嵌套类型(如 AdaptModule 里的 Point)一律不计：不同外层类里同名嵌套类型是合法的，
    算进来会把它误判成重复定义进而误删真脚本。
    partial 标记必须保留 —— partial 与同名非 partial 共存是编译错误(CS0260)，
    但多个 partial 分片共存合法，分组后靠这个标记区分。
    """
    try:
        text = cs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    text = STRING_RE.sub('""', COMMENT_RE.sub("", text))
    ns_match = NS_DECL_RE.search(text)
    ns = ns_match.group(1) if ns_match else ""
    out: set[tuple[str, bool]] = set()
    depth = 0
    # 顶层类型的深度基准：块命名空间(namespace X {)下一层是 1，
    # 文件级命名空间(namespace X;)下一层是 0。ILSpy 反编译产物两种都会出现。
    base = 0
    for line in text.splitlines():
        m = TYPE_DECL_RE.match(line)
        if m and m.group(2) and depth == base:
            out.add((f"{ns}.{m.group(2)}" if ns else m.group(2), bool(m.group(1))))
        nm = NS_DECL_RE.match(line)
        if nm:
            # 只有 `namespace X;` 是文件级；`namespace X {` 与换行写 `{` 的都是块级
            base = depth + (0 if line.strip().endswith(";") else 1)
        depth += line.count("{") - line.count("}")
    return out


def is_asset_ripper_stub(cs_path: Path) -> bool:
    """识别 AssetRipper 生成的占位脚本（内容含 Dummy class 说明）。"""
    try:
        return "Dummy class" in cs_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def find_duplicate_types(root: Path) -> dict[str, tuple[list[Path], list[Path]]]:
    """扫描目录下同一类型被多处定义的情况。

    返回 {全限定名: (出现的全部文件, 其中非 partial 声明的文件)}。
    全是 partial 的跨文件分片属合法定义，不计入。
    """
    groups: dict[str, list[tuple[Path, bool]]] = {}
    for cs in sorted(Path(root).rglob("*.cs")):
        for fq, partial in declared_types(cs):
            groups.setdefault(fq, []).append((cs, partial))
    out: dict[str, tuple[list[Path], list[Path]]] = {}
    for fq, members in groups.items():
        files = sorted({p for p, _ in members})
        if len(files) < 2:
            continue
        solid = sorted({p for p, partial in members if not partial})
        if not solid:
            continue
        out[fq] = (files, solid)
    return out


def stub_conflicts(toolkit_scripts: Path) -> set[Path]:
    """Toolkit 里同一类既有真脚本又有 Dummy stub 时，返回该跳过的 stub 路径。

    Toolkit 若被 AssetRipper 处理过就会混进 stub，整拷时会把重复定义一起带给导出工程。
    """
    real: dict[str, Path] = {}
    stubs: dict[str, list[Path]] = {}
    for cs in Path(toolkit_scripts).rglob("*.cs"):
        for fq, _ in declared_types(cs):
            if is_asset_ripper_stub(cs):
                stubs.setdefault(fq, []).append(cs)
            else:
                real[fq] = cs
    out: set[Path] = set()
    for fq, paths in stubs.items():
        if fq in real:
            out.update(paths)
    return out


def asset_guid_of(file_path: Path) -> str:
    """读 .meta 里的 guid，读不到返回空串。"""
    meta = Path(str(file_path) + ".meta")
    if not meta.is_file():
        return ""
    m = re.search(r"^guid:\s*([0-9a-fA-F]+)", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    return m.group(1).lower() if m else ""


def dedupe_conflicting_scripts(project_dir: Path, toolkit_root: Path, toolkit_guids: set[str], log) -> tuple[int, list[str]]:
    """删除同一类型被多处定义的 .cs，杜绝 CS0101。

    整拷 Toolkit 之后仍可能残留 AssetRipper stub(例如落在 Scripts/Assembly-CSharp
    这种按命名空间镜像的目录下)，与 Toolkit 副本同名同类 → 编译报重复定义。
    保留优先级：路径在 Toolkit 树里存在 → GUID 属于 Toolkit → 不在 Assembly-CSharp 下 → 路径短。
    """
    assets = Path(project_dir) / "Assets"
    if not assets.is_dir():
        return 0, []
    toolkit_root = Path(toolkit_root)
    stubs = {p for p in assets.rglob("*.cs") if is_asset_ripper_stub(p)}

    def score(p: Path) -> tuple:
        rel = p.relative_to(assets).as_posix()
        is_stub = 1 if p in stubs else 0
        in_toolkit = 0 if (toolkit_root / "Assets" / rel).is_file() else 1
        is_tk_guid = 0 if asset_guid_of(p) in toolkit_guids else 1
        under_asm = 1 if ("Assembly-CSharp" in rel) else 0
        return (is_stub, in_toolkit, is_tk_guid, under_asm, len(rel), rel)

    removed = 0
    conflicts: list[str] = []
    for fq, (files, solid) in find_duplicate_types(assets).items():
        # 只能删非 partial 的声明；有 partial 参与时 solid 全属多余，否则保留评分最优的一份
        drop = sorted(solid, key=score)
        if len(solid) == len(files):
            drop = drop[1:]
        if not drop:
            continue
        keep = sorted(set(files) - set(drop), key=score)[0]
        conflicts.append(fq)
        log(f"[免挂] [!] 类型重复定义 {fq} 保留 {keep.relative_to(assets).as_posix()}"
            f"删除 {len(drop)} 处")
        for p in drop:
            for f in (p, Path(str(p) + ".meta")):
                try:
                    if f.is_file():
                        f.unlink()
                except OSError:
                    pass
            removed += 1
    return removed, conflicts


def scan_script_meta(scripts_dir) -> dict[str, str]:
    """扫描一个脚本目录下的 .cs.meta，返回 {类名: guid}。"""
    scripts_dir = Path(scripts_dir)
    result: dict[str, str] = {}
    rank: dict[str, tuple[int, int]] = {}
    if not scripts_dir.is_dir():
        return result
    for meta in scripts_dir.rglob("*.cs.meta"):
        m = re.search(r"^guid:\s*([0-9a-fA-F]+)", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
        if not m:
            continue
        cs = meta.with_suffix("").with_suffix(".cs")
        name = class_name_of_file(cs)
        # 同名类可能混进 AssetRipper stub，优先记真脚本(非 stub、非 Assembly-CSharp)的 GUID
        cand = (0 if is_asset_ripper_stub(cs) else 1, 0 if "Assembly-CSharp" in cs.as_posix() else 1)
        if name in result and cand <= rank[name]:
            continue
        result[name] = m.group(1).lower()
        rank[name] = cand
    return result


def build_toolkit_guid_map(toolkit_root) -> dict[str, str]:
    """扫描 Toolkit 工程的 Assets/Scripts，返回 {类名: guid}。

    入参是工程根目录；若手上已是脚本目录，直接调 scan_script_meta()。
    """
    return scan_script_meta(Path(toolkit_root) / "Assets" / "Scripts")


def collect_monoscript_classes(pack_path: Path, platforms: tuple[str, ...] = PRE_BUILD_KEYS) -> set[str]:
    """取各平台 Build 里 MonoScript 类名的并集。

    单个平台缺失/损坏就跳过；一个都解析不到时抛 ValueError，避免免挂静默失效。
    """
    import UnityPy

    data = json.loads(Path(pack_path).read_text(encoding="utf-8-sig"))
    classes: set[str] = set()
    loaded_any = False
    for platform in platforms:
        value = data.get(platform)
        if not isinstance(value, str):
            continue
        try:
            raw = base64.b64decode(value, validate=False)
        except (ValueError, UnicodeError):
            continue
        if not raw:
            continue
        try:
            env = UnityPy.load(raw)
        except Exception:
            continue  # 该平台 bundle 损坏/无法解析则跳过，不强判
        loaded_any = True
        for obj in env.objects:
            if obj.type.name != "MonoScript":
                continue
            try:
                cls = getattr(obj.read(), "m_ClassName", "")
                if cls:
                    classes.add(cls)
            except Exception:
                continue
    # 不要求特定 bundle 魔数，只要“一个平台都没能加载”才判定失败，避免误伤异签名 bundle。
    if not loaded_any:
        raise ValueError(f"无法解析 .pack 中的任何 AssetBundle 检查字段 {', '.join(platforms)}")
    if not classes:
        raise ValueError("已读取 AssetBundle 但解析不到任何 MonoScript 类名")
    return classes


def rewrite_script_guids(text: str, stub_to_toolkit: dict[str, str]) -> tuple[str, int]:
    """把文本中命中 stub 的 m_Script GUID 替换为 Toolkit GUID，返回 (新文本, 替换次数)。"""
    changed = 0

    def do_replace(mm: re.Match) -> str:
        nonlocal changed
        new_guid = stub_to_toolkit.get(mm.group(2))
        if new_guid:
            changed += 1
            return mm.group(1) + new_guid + mm.group(3)
        return mm.group(0)

    return SCRIPT_REF_RE.sub(do_replace, text), changed


def collect_unresolved(text: str, stub_guid_to_class: dict[str, str], stub_to_toolkit: dict[str, str]) -> list[str]:
    """返回该文本里仍未解析(指向 stub 且未重写)的类名清单。

    入参是**已重写后的文本**，调用方负责传入，避免重复读盘。
    """
    unresolved: list[str] = []
    for mm in SCRIPT_REF_RE.finditer(text):
        guid = mm.group(2)
        if guid in stub_to_toolkit:
            continue
        cls = stub_guid_to_class.get(guid)
        if cls and cls not in unresolved:
            unresolved.append(cls)
    return unresolved


def verify_toolkit_self(toolkit_root) -> dict[str, int]:
    """自检 Toolkit 本身：它自带的官方部件 prefab，能否命中它自己的脚本 GUID。

    这是"还原到打包前"能否成立的前提。Toolkit 脚本的 GUID 随版本固定，
    如果这款 Toolkit 自带的部件都对不上，说明它的版本/来源与 mod 作者用的
    不一致（或 .meta 被重新生成过），此时无论怎么对齐都不会成功。
    """
    toolkit_root = Path(toolkit_root)
    guids = set(scan_script_meta(toolkit_root / "Assets" / "Scripts").values())
    parts_dir = toolkit_root / "Assets" / "Resources" / "Parts"
    if not guids or not parts_dir.is_dir():
        return {"prefabs": 0, "refs": 0, "missing": 0}
    result = {"prefabs": 0, "refs": 0, "missing": 0}
    for prefab in parts_dir.rglob("*.prefab"):
        result["prefabs"] += 1
        try:
            text = prefab.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for mm in SCRIPT_REF_RE.finditer(text):
            result["refs"] += 1
            if mm.group(2).lower() not in guids:
                result["missing"] += 1
    return result


def extract_code_assembly(pack_path: Path, out_file: Path) -> Path | None:
    """把 pack 里的 CodeAssembly 解成 DLL 文件。

    pack 没带 / 不是 PE 文件都返回 None —— 那不是错误，只是这个 mod 没有自带程序集。
    """
    try:
        data = json.loads(Path(pack_path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = data.get("CodeAssembly")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        blob = base64.b64decode(raw, validate=False)
    except (ValueError, UnicodeError):
        return None
    if blob[:2] != b"MZ":
        return None
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_bytes(blob)
    return out_file


def find_ilspy() -> str | None:
    """定位 ilspycmd：先 PATH，再 dotnet global tool 的默认安装位置。"""
    found = shutil.which("ilspycmd") or shutil.which("ilspycmd.exe")
    if found:
        return found
    home = Path.home()
    for name in ("ilspycmd.exe", "ilspycmd"):
        candidate = home / ".dotnet" / "tools" / name
        if candidate.is_file():
            return str(candidate)
    return None


def decompile_assembly(dll: Path, out_dir: Path, log) -> Path | None:
    """调 ilspycmd 把 DLL 反编译成 .cs 工程目录，失败返回 None。"""
    tool = find_ilspy()
    if not tool:
        log("[自定义] [!] 未找到 ilspycmd 跳过自动反编译")
        return None
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [tool, "-p", "-o", str(out_dir), str(dll)],
            capture_output=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"[自定义] [!] 反编译调用失败 {exc}")
        return None
    if not next(out_dir.rglob("*.cs"), None):
        tail = (proc.stderr or proc.stdout or b"").decode("utf-8", "ignore")[:200]
        log(f"[自定义] [!] 反编译没有产出 {tail}")
        return None
    return out_dir


def _guid_of_meta(meta_path) -> str:
    """读 .meta 文件首行的 guid（与 asset_guid_of 不同：这里直接读 .meta 文件本身）。"""
    p = Path(meta_path)
    if not p.is_file():
        return ""
    m = re.search(r"^guid:\s*([0-9a-fA-F]{32})", p.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    return m.group(1).lower() if m else ""


def _copy_tree(src: Path, dst: Path) -> int:
    """递归拷贝目录(仅文件)到 dst，返回拷贝文件数。"""
    n = 0
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(Path(src).rglob("*")):
        if p.is_file():
            d = dst / p.relative_to(src)
            d.parent.mkdir(parents=True, exist_ok=True)
            d.write_bytes(p.read_bytes())
            n += 1
    return n


def _find_mod_assembly_dll(assets: Path, extracted_dll):
    """在导出工程 Plugins 里找出与包内 CodeAssembly 同源(字节一致)的 DLL 及其 meta guid。

    命中即说明 AssetRipper 把 mod 自有程序集当 Plugin 放进了工程，prefab 的 m_Script
    已正确指向它(FileID=类ID, guid=DLL.meta)。返回 (Path, guid) 或 (None, "")。
    """
    plugins = Path(assets) / "Plugins"
    if not plugins.is_dir() or not extracted_dll or not Path(extracted_dll).is_file():
        return None, ""
    blob = Path(extracted_dll).read_bytes()
    for dll in sorted(plugins.glob("*.dll")):
        if dll.read_bytes() == blob:
            g = _guid_of_meta(dll.with_suffix(".dll.meta"))
            if g:
                return dll, g
    return None, ""


def find_referenced_plugin_dlls(project_assets: Path, prefab_paths: list) -> list:
    """返回被给定 prefab 的 m_Script 引用、且存在于工程 Plugins 的 DLL 路径列表。"""
    assets = Path(project_assets)
    referenced: set[str] = set()
    HEX = "0123456789abcdefABCDEF"
    for pf in prefab_paths:
        try:
            txt = Path(pf).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in txt.splitlines():
            if "m_Script:" not in line:
                continue
            gi = line.find("guid:")
            if gi < 0:
                continue
            g = line[gi + 6:].lstrip().split(",")[0].strip()
            if len(g) == 32 and all(c in HEX for c in g):
                referenced.add(g.lower())
    out = []
    plugins = assets / "Plugins"
    if plugins.is_dir():
        for dll in sorted(plugins.glob("*.dll")):
            g = _guid_of_meta(dll.with_suffix(".dll.meta"))
            if g and g.lower() in referenced:
                out.append(dll)
    return out


def restore_custom_scripts(
    project_dir: Path,
    pack_path: Path,
    toolkit_classes: set[str],
    unresolved_classes: list[str],
    log,
) -> dict[str, object]:
    """用 pack 自带的 CodeAssembly 反编译出作者自定义脚本，接回导出工程。

    关键手法：新脚本的 .meta 直接复用原 stub 的 GUID，prefab 上指向旧 stub 的
    m_Script 因此自动命中，一个引用都不用改；stub 随之删除，避免重复定义。

    返回 {"ok", "dll", "decompiled", "classes", "files", "reason"}
    """
    result: dict[str, object] = {
        "ok": False, "dll": "", "decompiled": "", "classes": [], "files": 0, "reason": "",
    }
    base = Path(project_dir)
    assets = base / "Assets"
    if not assets.is_dir():
        return result

    dll = extract_code_assembly(pack_path, base.parent / f"{base.name}_CodeAssembly.dll")
    if dll is None:
        result["reason"] = "no_code_assembly"
        return result
    result["dll"] = str(dll)
    log(f"[自定义] 检出 CodeAssembly {dll.stat().st_size:,} 字节 已导出 {dll.name}")

    src = decompile_assembly(dll, base.parent / f"{base.name}_Decompiled", log)
    if src is None:
        result["reason"] = "decompile_unavailable"
        log(f"[自定义] [!] 已把 DLL 放在 {dll} 可用 ILSpy 或 dnSpy 手动反编译")
        return result
    result["decompiled"] = str(src)

    # 情形1：AssetRipper 已把 mod 自有程序集当 Plugin 放进 Assets/Plugins，
    #        prefab 的 m_Script 直接指向它(FileID=类ID, guid=DLL.meta)。
    #        此时保留 DLL 即可解析；不要再写同名源码，否则与 DLL 重复定义 -> CS0101 编译失败。
    mod_dll, mod_guid = _find_mod_assembly_dll(assets, dll)
    if mod_dll is not None:
        result["ok"] = True
        result["via"] = "dll"
        result["dll_guid"] = mod_guid
        ref = base / "ModCode_Reference"
        copied = _copy_tree(src, ref)
        log(f"[自定义] 保留 mod 自有程序集 {mod_dll.name} (meta guid {mod_guid[:8]}…)")
        log(f"[自定义] prefab 的自定义脚本引用已指向该 DLL → 导出工程可直接解析，无需挂接")
        log(f"[自定义] 反编译源码另存为工程外 {ref.name}/ ({copied} 文件) 供阅读 / 改后重编译")
        return result

    # 情形2：原逻辑 —— AssetRipper 把 mod 程序集导成了 stub(.cs Dummy) 没保留 DLL，
    #        prefab 指向 stub 的 GUID，这里写入真源码并复用 stub GUID，引用自动命中。
    # 反编译产物索引 {短类名: 文件}（同一文件可能含多个类型）
    class_to_file: dict[str, Path] = {}
    for cs in sorted(src.rglob("*.cs")):
        for fq, _ in declared_types(cs):
            class_to_file.setdefault(fq.rsplit(".", 1)[-1], cs)

    # 工程里现存的 {短类名: (guid, 文件)}，用来复用 stub 的 GUID
    existing_guid: dict[str, str] = {}
    existing_file: dict[str, Path] = {}
    for cs in assets.rglob("*.cs"):
        g = asset_guid_of(cs)
        for fq, _ in declared_types(cs):
            short = fq.rsplit(".", 1)[-1]
            if g:
                existing_guid.setdefault(short, g)
            existing_file.setdefault(short, cs)

    target_root = assets / "Scripts" / MOD_CODE_DIRNAME
    written = 0
    restored: list[str] = []
    for cs in sorted(set(class_to_file.values())):
        names = {fq.rsplit(".", 1)[-1] for fq, _ in declared_types(cs)}
        if names & set(toolkit_classes):
            continue  # Toolkit 里已有同名类，拷进去会 CS0101
        guid = next((existing_guid[n] for n in names if n in existing_guid), None)
        if guid is None:
            guid = uuid.uuid4().hex
        dest = target_root / cs.relative_to(src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(cs.read_bytes())
        Path(str(dest) + ".meta").write_text(
            MONO_META_TEMPLATE.format(guid=guid), encoding="utf-8"
        )
        written += 1
        # GUID 已经转移给新文件，原 stub 必须删掉，否则重复定义
        for n in names:
            old = existing_file.get(n)
            if old is None or old == dest or not old.is_file():
                continue
            Path(str(old) + ".meta").unlink(missing_ok=True)
            old.unlink(missing_ok=True)
        for n in names:
            if n in unresolved_classes:
                restored.append(n)

    result["files"] = written
    result["classes"] = sorted(restored)
    result["ok"] = written > 0
    if written:
        log(f"[自定义] 已从 DLL 还原 {written} 个自定义脚本文件 → Assets/Scripts/{MOD_CODE_DIRNAME}")
        if restored:
            log(f"[自定义] 其中 {len(restored)} 个是 prefab 引用的类 {restored}")
    else:
        result["reason"] = "nothing_to_restore"
    return result


def align_scripts_to_toolkit(
    project_dir: Path,
    pack_path: Path,
    toolkit_root: Path,
    log=None,
) -> dict[str, object]:
    """对 AssetRipper 导出的工程执行脚本免挂对齐。"""
    if log is None:
        log = print
    report: dict[str, object] = {"ok": False}

    toolkit_map = build_toolkit_guid_map(toolkit_root)  # {类名: guid}
    if not toolkit_map:
        report["error"] = f"未在 Toolkit 中找到脚本 .meta {toolkit_root}"
        return report
    log(f"[免挂] Toolkit 脚本数 {len(toolkit_map)}")

    # 前提自检：Toolkit 自己有没有同名类重复(被 AssetRipper 处理过的 Toolkit 会混进 stub)
    toolkit_dups = find_duplicate_types(Path(toolkit_root) / "Assets" / "Scripts")
    if toolkit_dups:
        sample = [f"{fq}({len(v[0])}处)" for fq, v in list(toolkit_dups.items())[:5]]
        log(f"[免挂] [!!] Toolkit 自身有 {len(toolkit_dups)} 个重复类型定义 {sample}"
            f"{'...' if len(toolkit_dups) > 5 else ''}")
        log(f"[免挂] [!!] 说明这份 Toolkit 混入了 AssetRipper 占位 stub"
            f"会自动跳过这些 stub 但建议换成干净的 Toolkit 工程")

    # 前提自检：这份 Toolkit 自带的部件本身能不能命中自己的脚本
    selfcheck = verify_toolkit_self(toolkit_root)
    if selfcheck["refs"]:
        log(f"[免挂] Toolkit 自检 自带部件 {selfcheck['prefabs']} 个"
            f"脚本引用命中 {selfcheck['refs'] - selfcheck['missing']}/{selfcheck['refs']}")
        if selfcheck["missing"]:
            log(f"[免挂] [!!] 这份 Toolkit 自带的部件就有 {selfcheck['missing']} 处脚本对不上"
                f"通常是 Toolkit 版本与 mod 作者用的不一致 或 .meta 被重新生成过"
                f"这种情况下免挂不会生效 请换成与 mod 作者相同的 Toolkit 版本")

    try:
        mono_classes = collect_monoscript_classes(pack_path)  # 四平台并集，为空即抛错
    except ImportError:
        report["error"] = "缺少 UnityPy 无法解析 MonoBehaviour 脚本类"
        return report
    except Exception as exc:
        report["error"] = f"解析 .pack 脚本类失败 {exc}"
        return report
    log(f"[免挂] 包内脚本类数(并集) {len(mono_classes)}")

    assets = project_dir / "Assets"
    unresolved_classes = sorted(c for c in mono_classes if c not in toolkit_map)

    # 0) 记录现有 stub：{stub_guid: 类名}
    stub_guid_to_class: dict[str, str] = {}
    # 注意：这一步必须在删 stub 之前，删掉之后就拿不到旧 GUID 与类名的对应关系了
    if assets.is_dir():
        for meta in assets.rglob("*.cs.meta"):
            m = re.search(r"^guid:\s*([0-9a-fA-F]+)", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
            if not m:
                continue
            cs = meta.with_suffix("").with_suffix(".cs")
            stub_guid_to_class[m.group(1).lower()] = class_name_of_file(cs)

    toolkit_scripts = toolkit_root / "Assets" / "Scripts"
    target_scripts = project_dir / "Assets" / "Scripts"

    # 1) 删掉将被 Toolkit 替换的 stub，避免同名类重复 → CS0101
    #    只删 GUID 与 Toolkit 不一致的（真正的 stub），重复运行时不会误删刚拷入的副本。
    #    扫描整个 Assets：AssetRipper 的 stub 也可能落在 Assets/MonoScript 等目录。
    removed_stub = 0
    if assets.is_dir():
        for meta in sorted(assets.rglob("*.cs.meta")):
            m = re.search(r"^guid:\s*([0-9a-fA-F]+)", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
            if not m:
                continue
            g = m.group(1).lower()
            clazz = class_name_of_file(meta.with_suffix("").with_suffix(".cs"))
            if clazz in toolkit_map and g != toolkit_map[clazz]:
                cs = meta.with_suffix("").with_suffix(".cs")
                try:
                    meta.unlink()
                    if cs.exists():
                        cs.unlink()
                    removed_stub += 1
                except OSError:
                    pass
    log(f"[免挂] 已删除 {removed_stub} 个将被替换的 AssetRipper stub 脚本")

    # 2) 整拷 Assets/Scripts，连基类/枚举/接口一起补齐 → 消 CS0246
    #    Toolkit 若混有 AssetRipper stub(同名类已有真脚本)则跳过，否则会把重复定义带给导出工程
    imported = 0
    skipped_stub_source = 0
    if toolkit_scripts.is_dir():
        skip_stub = stub_conflicts(toolkit_scripts)
        for cs in toolkit_scripts.rglob("*.cs"):
            if cs in skip_stub:
                skipped_stub_source += 1
                continue
            rel = cs.relative_to(toolkit_scripts)
            dest = target_scripts / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(cs.read_bytes())
            imported += 1
            meta = Path(str(cs) + ".meta")
            if meta.is_file():
                Path(str(dest) + ".meta").write_bytes(meta.read_bytes())
    else:
        log(f"[免挂] [!] 未找到 Toolkit 脚本目录 跳过导入 {toolkit_scripts}")
    log(f"[免挂] 已整拷 {imported} 个 Toolkit 脚本(含 .meta)")
    if skipped_stub_source:
        log(f"[免挂] 已跳过 {skipped_stub_source} 个 Toolkit 自带的 AssetRipper stub"
            f"这份 Toolkit 被 AssetRipper 处理过 建议清理后重试")

    # 2.5) 自定义脚本还原：pack 带 CodeAssembly 时反编译出源码接回工程，
    #      复用原 stub 的 GUID 所以 prefab 上一个引用都不用改。
    custom = restore_custom_scripts(
        project_dir, pack_path, set(toolkit_map), unresolved_classes, log
    )
    if custom["reason"] == "no_code_assembly" and unresolved_classes:
        log(f"[免挂] [!] 该 pack 未携带 CodeAssembly 这 {len(unresolved_classes)} 个自定义脚本"
            f"拿不到源码 只能保留空壳 stub {unresolved_classes[:8]}"
            f"{'...' if len(unresolved_classes) > 8 else ''}")

    # 2.6) 兜底去重：放最后一道，整拷残留的 stub 与反编译引入的重复都能一并清掉 → CS0101
    removed_dup, dup_classes = dedupe_conflicting_scripts(
        project_dir, toolkit_root, set(toolkit_map.values()), log
    )
    if removed_dup:
        log(f"[免挂] 已删除 {removed_dup} 个重复类型定义 涉及 {len(dup_classes)} 个类")

    # 3) 重写目标表。target_scripts 已是脚本目录，只能调 scan_script_meta；
    #    用 build_toolkit_guid_map 会再拼一层 Assets/Scripts，返回空表。
    imported_toolkit_guid = scan_script_meta(target_scripts)
    if not imported_toolkit_guid:
        report["error"] = "Toolkit 脚本已拷贝 但未能读出任何 .cs.meta GUID"
        return report

    # 4) 按类名建立 stub_guid -> toolkit_guid
    stub_to_toolkit: dict[str, str] = {}
    remapped_classes: set[str] = set()
    for stub_guid, class_name in stub_guid_to_class.items():
        tk_guid = imported_toolkit_guid.get(class_name)
        if tk_guid:
            stub_to_toolkit[stub_guid] = tk_guid
            remapped_classes.add(class_name)
    log(f"[免挂] 已建立脚本 GUID 重写映射 {len(stub_to_toolkit)} 条")

    # 5) 重写 .prefab / .asset 的 m_Script（ScriptableObject 上的引用同样会挂）
    files = []
    if assets.is_dir():
        files = sorted(assets.rglob("*.prefab")) + sorted(assets.rglob("*.asset"))
    rewritten_count = 0
    total_rewrite = 0
    unresolved_prefab_names: list[str] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "m_Script:" not in text:
            continue
        new_text, n = rewrite_script_guids(text, stub_to_toolkit)
        if n:
            f.write_text(new_text, encoding="utf-8")
            rewritten_count += 1
            total_rewrite += n
        if collect_unresolved(new_text, stub_guid_to_class, stub_to_toolkit):
            unresolved_prefab_names.append(str(f.relative_to(project_dir)))
    log(f"[免挂] 已重写 {rewritten_count} 个 prefab/asset 共 {total_rewrite} 处脚本引用")
    if unresolved_classes:
        log(f"[免挂] [!] 以下类在 Toolkit 中无源码 无法保证解析(可能来自 mod 的 CodeAssembly) {unresolved_classes}")
    if unresolved_prefab_names:
        log(f"[免挂] [!] {len(unresolved_prefab_names)} 个文件仍存在未解析脚本引用 {unresolved_prefab_names[:8]}{'...' if len(unresolved_prefab_names) > 8 else ''}")

    report.update(
        {
            "ok": True,
            "toolkit_scripts": len(toolkit_map),
            "pack_classes": len(mono_classes),
            "remap_rules": len(stub_to_toolkit),
            "rewritten_prefabs": rewritten_count,
            "rewritten_refs": total_rewrite,
            "removed_stubs": removed_stub,
            "removed_duplicates": removed_dup,
            "duplicate_classes": dup_classes,
            "toolkit_duplicates": sorted(toolkit_dups),
            "skipped_stub_sources": skipped_stub_source,
            "toolkit_selfcheck": selfcheck,
            "custom_scripts": custom,
            "unresolved_classes": unresolved_classes,
            "unresolved_prefabs": unresolved_prefab_names,
        }
    )
    return report


def index_asset_guids(assets_dir: Path) -> dict[str, Path]:
    """扫描某 Assets 下所有文件的 .meta，返回 {guid: 资产文件}。"""
    result: dict[str, Path] = {}
    if not assets_dir.is_dir():
        return result
    for meta in assets_dir.rglob("*.meta"):
        try:
            m = re.search(r"^guid:\s*([0-9a-fA-F]{32})", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
        except OSError:
            continue
        if not m:
            continue
        asset = meta.with_suffix("")  # Foo.cs.meta -> Foo.cs, Foo.mat.meta -> Foo.mat
        if asset.is_file() and asset.suffix.lower() not in MERGE_SKIP_SUFFIXES:
            result[m.group(1).lower()] = asset
    return result


def collect_referenced_assets(assets_dir: Path, roots: list[Path], guid_map: dict[str, Path]) -> set[Path]:
    """从根部 prefab 出发，按 GUID 引用广度优先收集其依赖资产。"""
    needed: set[Path] = set()
    q: list[Path] = list(roots)
    while q:
        p = q.pop()
        if p in needed:
            continue
        needed.add(p)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for g in set(ASSET_GUID_RE.findall(text)):
            target = guid_map.get(g.lower())
            if target is None or target in needed or target.suffix.lower() in MERGE_SKIP_SUFFIXES:
                continue
            q.append(target)
    return needed


def copy_with_meta(src: Path, dest: Path) -> int:
    """拷贝文件并连同其 .meta，返回拷贝的文件数(含.meta)。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    n = 1
    smeta = Path(str(src) + ".meta")
    if smeta.is_file():
        Path(str(dest) + ".meta").write_bytes(smeta.read_bytes())
        n += 1
    return n


def _merge_copy_custom_scripts(project_assets: Path, prefabs: list, package_assets: Path, log=None) -> dict:
    """合并包必须把 mod 自有脚本带进去，否则贴进 Toolkit 后自定义脚本引用悬空。

    情形1：prefab 的 m_Script 指向 mod 自有程序集 DLL(在 Assets/Plugins)，复制 DLL + .meta。
    情形2：反编译源码落在 Assets/Scripts/ModCode，整体复制 .cs + .meta。
    这两类在依赖收集阶段被 MERGE_SKIP_SUFFIXES 跳过，必须在此显式补上
    —— 这正是之前『没挂上』的根因之一(合并包漏带了程序集)。
    Toolkit 自带脚本不在此处理(已在 Toolkit 内，且依赖收集阶段已被排除)。
    """
    if log is None:
        log = print
    stats: dict[str, object] = {"dll": 0, "cs": 0, "assets": []}
    # 情形1：被 prefab 引用的 mod DLL（仅拷被引用者，避免顺手带无关程序集）
    for dll in find_referenced_plugin_dlls(project_assets, prefabs):
        meta = dll.with_suffix(".dll.meta")
        dest = package_assets / "Plugins" / dll.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dll, dest)
        stats["assets"].append(dest)
        if meta.is_file():
            Path(str(dest) + ".meta").write_bytes(meta.read_bytes())
        stats["dll"] += 1
    # 情形2：ModCode 自定义源码（restore_custom_scripts 已剔除与 Toolkit 重名的类，安全）
    modcode = Path(project_assets) / "Scripts" / MOD_CODE_DIRNAME
    if modcode.is_dir():
        for cs in sorted(modcode.rglob("*.cs")):
            rel = cs.relative_to(project_assets)
            dest = package_assets / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cs, dest)
            stats["assets"].append(dest)
            smeta = Path(str(cs) + ".meta")
            if smeta.is_file():
                Path(str(dest) + ".meta").write_bytes(smeta.read_bytes())
            stats["cs"] += 1
    return stats


def _parts_subfolder_name(pack_path: Path) -> str:
    """新增部件归入的子目录名：取 .pack 文件名，去掉文件系统非法字符。

    直接塞进 Resources/Parts 会把玩家导入的部件和 Toolkit 自带部件混在一起，
    建一层以模组命名的子目录，方便整包管理、定位与删除。
    """
    stem = Path(pack_path).stem if pack_path else ""
    stem = re.sub(r'[<>:"/\\|?*]', "_", stem).strip().strip(". ")
    return stem or "Imported"


# 材质里着色器引用，形如 m_Shader: {fileID: 4800000, guid: xxxx..., type: 3}
SHADER_REF_RE = re.compile(
    r"(m_Shader:\s*\{\s*fileID:\s*\d+\s*,\s*guid:\s*)([0-9a-fA-F]{32})(\s*,\s*type:\s*3\s*\})",
    re.IGNORECASE,
)
# .shader 文件里声明的着色器名，形如 Shader "SFS/Weird"
SHADER_NAME_RE = re.compile(r'^\s*Shader\s+"([^"]+)"', re.MULTILINE)
# AssetRipper 反编译不了着色器时写下的占位标记
DUMMY_SHADER_MARK = "DummyShaderTextExporter"
# 真着色器一般几 KB；超过这个体积就不当占位版处理，避免误伤 mod 自制着色器
STUB_MAX_BYTES = 8192


def _shader_declared_name(shader: Path) -> str:
    """读 .shader 里声明的着色器名（如 SFS/Weird）。"""
    try:
        m = SHADER_NAME_RE.search(shader.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return ""
    return m.group(1) if m else ""


def _shader_guid(meta: Path) -> str:
    try:
        m = re.search(r"^guid:\s*([0-9a-fA-F]{32})", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    except OSError:
        return ""
    return m.group(1).lower() if m else ""


def fix_stub_shaders(
    project_assets: Path,
    toolkit_root: Path,
    log=None,
    mode: str = "copy",
) -> dict[str, object]:
    """把工程里的 AssetRipper 空壳着色器换成 Toolkit 真着色器。

    AssetRipper 反编译不了 SFS 的自定义着色器，会写成带 DummyShaderTextExporter
    标记的不透明 Standard 占位版 —— 零件因此渲成一整块黑板（**不会报错**）。
    按 .shader 里声明的 Shader 名匹配 Toolkit 真着色器，两种模式：

    - mode="copy"：把空壳文件的**内容**换成真着色器源码（保留文件名与 GUID），
      材质一行都不用改，工程自身即可正确渲染 —— **导出工程用这个**。
    - mode="remap"：把材质 m_Shader 的 GUID 重指向 Toolkit 真着色器并**删掉重复文件**，
      避免往 Toolkit 里塞进两个同名 Shader —— **合并包用这个**。

    判定为“空壳/重复”的条件：声明的 Shader 名能在 Toolkit 里找到同名真身，
    且 GUID 与 Toolkit 不同（满足其一即可：带 DummyShaderTextExporter 标记，
    或文件很短——真着色器一般几 KB，占位版只有几百 B）。
    已修过的文件再跑一遍是幂等的。
    """
    if log is None:
        log = print
    result: dict[str, object] = {
        "stubs": 0,
        "fixed": 0,
        "refs": 0,
        "deleted": 0,
        "unmatched": [],
        "map": {},  # 空壳 guid -> Toolkit 真 guid
    }
    project_assets = Path(project_assets)
    toolkit_assets = Path(toolkit_root) / "Assets"
    if not project_assets.is_dir() or not toolkit_assets.is_dir():
        return result

    # 1) Toolkit 真着色器：声明名 -> (guid, 源文件)
    real: dict[str, tuple[str, Path]] = {}
    for meta in toolkit_assets.rglob("*.shader.meta"):
        shader = meta.with_suffix("").with_suffix(".shader")
        if not shader.is_file():
            continue
        name = _shader_declared_name(shader)
        guid = _shader_guid(meta)
        if name and guid:
            real[name] = (guid, shader)

    # 2) 工程里的空壳着色器
    stubs: list[tuple[str, Path, str]] = []  # (声明名, .shader 文件, stub guid)
    for meta in project_assets.rglob("*.shader.meta"):
        shader = meta.with_suffix("").with_suffix(".shader")
        if not shader.is_file():
            continue
        try:
            text = shader.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        name = _shader_declared_name(shader)
        guid = _shader_guid(meta)
        if not name or not guid:
            continue
        hit = real.get(name)
        if not hit:
            # Toolkit 里没同名真身 —— 多半是 mod 自制着色器，原样保留
            if DUMMY_SHADER_MARK in text:
                result["unmatched"].append(name)
            continue
        real_guid = hit[0]
        if real_guid == guid:
            continue  # 本身就是 Toolkit 那份，无需处理
        # 只认两类：带占位标记的，或短得不像真着色器的
        if DUMMY_SHADER_MARK not in text and len(text) > STUB_MAX_BYTES:
            continue
        result["stubs"] += 1
        stubs.append((name, shader, guid))

    if not stubs:
        return result

    result["map"] = {guid: real[name][0] for name, _, guid in stubs}

    if mode == "remap":
        # 3a) 材质 GUID 重指向 Toolkit 真着色器
        stub_to_real = {guid: real[name][0] for name, _, guid in stubs}

        def repl(mm: re.Match) -> str:
            new = stub_to_real.get(mm.group(2).lower())
            if not new:
                return mm.group(0)
            result["refs"] += 1
            return mm.group(1) + new + mm.group(3)

        for pattern in ("*.mat", "*.prefab", "*.asset", "*.unity"):
            for f in project_assets.rglob(pattern):
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "m_Shader:" not in text:
                    continue
                new_text = SHADER_REF_RE.sub(repl, text)
                if new_text != text:
                    f.write_text(new_text, encoding="utf-8")
        # 4) 删掉空壳，别把占位版带进 Toolkit
        for _, shader, _ in stubs:
            for p in (shader, Path(str(shader) + ".meta")):
                try:
                    if p.is_file():
                        p.unlink()
                        result["deleted"] += 1
                except OSError:
                    pass
    else:
        # 3b) 就地换成真着色器源码，保留文件名与 GUID
        for name, shader, _ in stubs:
            src = real[name][1]
            try:
                shader.write_bytes(src.read_bytes())
                result["fixed"] += 1
            except OSError:
                continue

    result["fixed"] = result["fixed"] or len(stubs)
    extra = ""
    if mode == "remap":
        extra = " 重写材质引用 {} 处 删除空壳文件 {} 个".format(result["refs"], result["deleted"])
    log("[着色器] 空壳 {} 个 已换成 Toolkit 真着色器 {} 个{}".format(result["stubs"], len(stubs), extra))
    if result["unmatched"]:
        log(f"[着色器] [!] Toolkit 里找不到同名真着色器 {sorted(set(result['unmatched']))}")
    return result


def build_merge_package(
    project_dir: Path,
    pack_path: Path,
    toolkit_root: Path,
    package_dir: Path,
    log=None,
) -> dict[str, object]:
    """裁剪出只含“Toolkit 没有的新内容”的合并包。

    产物不含 .cs/.dll（脚本由 Toolkit 提供，避免 CS0263），prefab 的 m_Script
    已指向 Toolkit 真脚本；新增部件归一化到 Assets/Resources/Parts/<模组名>/，
    自动替换 AssetRipper 空壳着色器（黑板根因），并做 GUID 冲突预检。
    """
    if log is None:
        log = print
    report: dict[str, object] = {"ok": False}
    project_dir = Path(project_dir)
    project_assets = project_dir / "Assets"
    if not project_assets.is_dir():
        report["error"] = "导出工程缺少 Assets 目录"
        return report

    toolkit_map = build_toolkit_guid_map(toolkit_root)
    if not toolkit_map:
        report["error"] = f"未在 Toolkit 中找到脚本 .meta {toolkit_root}"
        return report

    # 1) Toolkit 已有部件（按 prefab 文件名判定）
    parts_dir = Path(toolkit_root) / "Assets" / "Resources" / "Parts"
    existing_parts = set()
    if parts_dir.is_dir():
        existing_parts = {p.stem for p in parts_dir.rglob("*.prefab")}
    log(f"[合并] Toolkit 已有部件 {len(existing_parts)} 个")

    # 2) stub->toolkit GUID 映射并重写所有 prefab（幂等）
    try:
        mono_classes = collect_monoscript_classes(pack_path)
    except Exception:
        # .pack 解析失败时退化：映射 Toolkit 里全部脚本类
        mono_classes = set(toolkit_map)
    imported_toolkit_guid = {name: g for name, g in toolkit_map.items() if name in mono_classes}
    stub_to_toolkit: dict[str, str] = {}
    stub_guid_to_class: dict[str, str] = {}
    for meta in project_assets.rglob("*.cs.meta"):
        m = re.search(r"^guid:\s*([0-9a-fA-F]+)", meta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
        if not m:
            continue
        cs = meta.with_suffix("").with_suffix(".cs")
        clazz = class_name_of_file(cs)
        g = m.group(1).lower()
        stub_guid_to_class[g] = clazz
        if clazz in imported_toolkit_guid:
            stub_to_toolkit[g] = imported_toolkit_guid[clazz]
    prefabs = sorted(project_assets.rglob("*.prefab"))
    total_rewrite = 0
    rewritten_text: dict[Path, str] = {}
    for prefab in prefabs:
        text, n = rewrite_script_guids(prefab.read_text(encoding="utf-8", errors="ignore"), stub_to_toolkit)
        rewritten_text[prefab] = text
        if n:
            prefab.write_text(text, encoding="utf-8")
            total_rewrite += n
    log(f"[合并] 已重写 {total_rewrite} 处脚本引用")

    # 2.5) 自动处理“黑板”：AssetRipper 反编译不了 SFS 自定义着色器，会留下带
    #      DummyShaderTextExporter 的占位 shader，零件因此渲成纯黑板且**不报错**。
    #      先用 copy 模式就地换真源码（保留 GUID，导出工程自身即可正确渲染），
    #      放在依赖收集之前，这样拷进包里的就是修好的着色器。
    try:
        fix_stub_shaders(project_assets, toolkit_root, log=log, mode="copy")
    except Exception as e:  # 着色器修复失败不应阻断合并
        log(f"[合并] [!] 空壳着色器处理失败 {e}")

    # 3) 挑出新增部件并按文件名去重：归一化到 Resources/Parts 时同名会互相覆盖
    new_prefabs: list[Path] = []
    skipped: list[Path] = []
    duplicate_parts: list[str] = []
    seen_stems: set[str] = set()
    for p in prefabs:
        if p.stem in existing_parts:
            skipped.append(p)
            continue
        if p.stem in seen_stems:
            duplicate_parts.append(str(p.relative_to(project_assets)))
            continue
        seen_stems.add(p.stem)
        new_prefabs.append(p)
    log(f"[合并] 新增部件 {len(new_prefabs)} Toolkit 已有而跳过 {len(skipped)}")
    if duplicate_parts:
        log(f"[合并] [!] {len(duplicate_parts)} 个新增部件文件名重复 只保留第一个 {duplicate_parts[:8]}")

    # 4) 广度收集依赖并拷贝：依赖保留原路径，新增部件归一化到 Resources/Parts
    guid_map = index_asset_guids(project_assets)
    needed = collect_referenced_assets(project_assets, new_prefabs, guid_map)
    package_assets = package_dir / "Assets"
    package_assets.mkdir(parents=True, exist_ok=True)

    new_prefab_set = {p.resolve() for p in new_prefabs}
    deps = [p for p in needed if p.resolve() not in new_prefab_set]
    copied = 0
    for src in deps:
        try:
            rel = src.relative_to(project_assets)
        except ValueError:
            continue
        copied += copy_with_meta(src, package_assets / rel)
    # 新建一层以 .pack 命名的子目录，避免玩家部件和 Toolkit 自带部件混在一起
    sub_name = _parts_subfolder_name(pack_path)
    parts_out = package_assets / "Resources" / "Parts" / sub_name
    parts_out.mkdir(parents=True, exist_ok=True)
    new_names = []
    for prefab in new_prefabs:
        dest = parts_out / prefab.name
        copied += copy_with_meta(prefab, dest)
        new_names.append(prefab.stem)

    # 4.5) 显式补拷 mod 自有脚本 artifacts：情形1=DLL(Plugins)，情形2=ModCode 源码。
    #      依赖收集阶段被 MERGE_SKIP_SUFFIXES 跳过了这两类，必须在此补上，否则贴进
    #      Toolkit 后自定义脚本引用悬空(就是之前『没挂上』的根因之一)。
    mod_custom = _merge_copy_custom_scripts(project_assets, new_prefabs, package_assets, log)
    for p in mod_custom["assets"]:
        needed.add(Path(p))  # 纳入后面的 GUID 冲突预检
    if mod_custom["dll"]:
        log(f"[合并] 已带上 mod 程序集 {mod_custom['dll']} 个(DLL) 自定义脚本引用据此解析")
    if mod_custom["cs"]:
        log(f"[合并] 已带上 ModCode 自定义脚本 {mod_custom['cs']} 个 自定义脚本引用据此解析")

    # 4.6) 合并包里改成 remap：Toolkit 本身就有真着色器，材质重指向它的 GUID
    #      并删掉重复文件，避免 Toolkit 的 Shader 下拉里出现两个同名 SFS/Weird。
    shader_fix: dict[str, object] = {"stubs": 0, "fixed": 0, "refs": 0, "deleted": 0, "unmatched": [], "map": {}}
    try:
        shader_fix = fix_stub_shaders(package_assets, toolkit_root, log=log, mode="remap")
    except Exception as e:  # 着色器修复失败不应阻断合并
        log(f"[合并] [!] 合并包着色器重指向失败 {e}")

    # 5) GUID 冲突预检：包内资产 GUID 与 Toolkit 已有资产求交
    toolkit_guid_index = index_asset_guids(Path(toolkit_root) / "Assets")
    collisions: list[str] = []
    for src in needed:
        smeta = Path(str(src) + ".meta")
        if not smeta.is_file():
            continue
        m = re.search(r"^guid:\s*([0-9a-fA-F]{32})", smeta.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
        if not m:
            continue
        g = m.group(1).lower()
        tk_asset = toolkit_guid_index.get(g)
        if tk_asset is not None and tk_asset.resolve() != src.resolve():
            collisions.append(f"{src.name} ({g[:8]} ) -> Toolkit 已存在 {tk_asset}")
    if collisions:
        log(f"[合并] [!] GUID 冲突 {len(collisions)} 处 拷入后可能与 Toolkit 既有资产撞 GUID")
        for c in collisions[:10]:
            log(f"[合并]    - {c}")

    # 6) 计算新增部件里仍未解析的类，写进使用说明
    merge_unresolved: list[str] = []
    for prefab in new_prefabs:
        for cls in collect_unresolved(rewritten_text.get(prefab, ""), stub_guid_to_class, stub_to_toolkit):
            if cls not in merge_unresolved:
                merge_unresolved.append(cls)
    readme_lines = [
        "# SFS 新增部件合并包\n",
        f"来源 .pack {pack_path.name}\n",
        f"- 新增部件 {len(new_prefabs)} 个 Toolkit 已有并跳过 {len(skipped)} 个 已拷贝资产 {copied} 个文件(含.meta)\n",
    ]
    if mod_custom["dll"] or mod_custom["cs"]:
        readme_lines.append(
            f"- 本包**含 mod 自定义脚本** {mod_custom['dll']} 个程序集(DLL) + {mod_custom['cs']} 个源码(ModCode)"
            " 已与 prefab 引用一一对应 贴进 Toolkit 后无需重新挂接\n"
        )
    else:
        readme_lines.append(
            "- 本包**不含脚本** 脚本由你的 Modding Toolkit 提供 因此**不会重复 不会触发 CS0263**\n"
        )
    readme_lines += [
        "- 用法 把 `Assets/` 里的内容拷进 Toolkit 工程 `Assets/` 保留全部 `.meta`\n",
        f"- 新增部件统一放在 `Assets/Resources/Parts/{sub_name}/` 子目录(以模组名命名) 与 Toolkit 自带部件分开\n",
        "- 新增部件 prefab 的脚本引用已指向 Toolkit 真实脚本 GUID 导入后即能正常解析 可编辑\n",
        "\n---\n",
    ]
    if shader_fix["stubs"]:
        readme_lines.append(
            "- **已自动修复黑板** 检出 AssetRipper 空壳着色器 {} 个 重写材质引用 {} 处"
            " 删除空壳 {} 个 材质现指向 Toolkit 真着色器\n".format(
                shader_fix["stubs"], shader_fix["refs"], shader_fix["deleted"]
            )
        )
        if shader_fix["unmatched"]:
            readme_lines.append(
                f"- [!] 仍有 {len(shader_fix['unmatched'])} 个着色器在 Toolkit 里找不到同名真身 {sorted(set(shader_fix['unmatched']))}\n"
            )
    if collisions:
        readme_lines.append(f"- **GUID 冲突 {len(collisions)} 处** 请人工核对后再拷入\n")
    if duplicate_parts:
        readme_lines.append(f"- **{len(duplicate_parts)} 个部件文件名重复** 只保留了第一个 {duplicate_parts[:8]}\n")
    if merge_unresolved:
        readme_lines.append(f"- 新增部件中存在 Toolkit 无源码的类 仍可能 Missing(来自 mod 的 CodeAssembly) {merge_unresolved}\n")
    else:
        readme_lines.append("- 未发现新增部件里有 Toolkit 无法解析的脚本类\n")
    (package_dir / "MERGE_README.md").write_text("".join(readme_lines), encoding="utf-8")

    report.update(
        {
            "ok": True,
            "new_parts": len(new_prefabs),
            "skipped_parts": len(skipped),
            "rewritten_refs": total_rewrite,
            "copied_files": copied,
            "package_dir": str(package_dir),
            "new_part_names": new_names,
            "duplicate_parts": duplicate_parts,
            "guid_collisions": collisions,
            "mod_custom_dll": mod_custom["dll"],
            "mod_custom_cs": mod_custom["cs"],
            "shader_stubs": shader_fix["stubs"],
            "shader_refs": shader_fix["refs"],
            "shader_deleted": shader_fix["deleted"],
            "parts_subfolder": sub_name,
        }
    )
    return report


if __name__ == "__main__":
    _project = sys.argv[1]
    _pack = sys.argv[2]
    _toolkit = sys.argv[3]
    r = align_scripts_to_toolkit(Path(_project), Path(_pack), Path(_toolkit))
    import pprint
    pprint.pprint(r)