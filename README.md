# SFS Pack Tool v22

> **汉化写入、Prefab/贴图导出与 Unity 工程恢复工具**  
> 内置 AssetRipper 1.1.4 · Windows x64 · GPL-3.0 合规分发
>
> Language / 语言：[简体中文](README.md) · [English](README_EN.md)

SFS Pack Tool 用于处理 SFS `.pack` 模组文件。它可以提取可翻译文本、将翻译写回新的 Pack，并将 Unity AssetBundle 导出为含真实 YAML Prefab、贴图、材质与项目配置的 Unity 工程。v22 内置官方 AssetRipper 1.1.4 Windows x64 运行包，默认无需额外下载或手动配置。

本工具应仅用于你拥有、获授权或法律允许处理的模组与资源。对于含自定义游戏程序集的模组，导出的 Prefab 与资源可用于研究和编辑，但原始游戏脚本依赖未必能在空白 Unity 工程中直接编译。

| 项目 | 说明 |
| --- | --- |
| 适用系统 | Windows 64 位 |
| 主程序 | `SFS_Pack_Tool_v22_Embedded_GPL.exe` |
| 内置导出器 | AssetRipper 1.1.4 Windows x64 |
| 默认语言 | 中文，可在窗口右上角切换为 English |
| 许可证 | GPL-3.0-or-later；随附完整许可证、对应源码和第三方材料 |

## 功能介绍

工具的汉化部分会读取 `.pack` 的 JSON 容器及其中 Base64 编码的 Unity AssetBundle，提取可显示的文本供人工翻译。写入时只处理面向显示的字段，例如 `DisplayName`、`Description`、`TranslatableName` 与 `Author`，并避免修改 Unity 对象名、脚本引用及其他高风险序列化字段。写入后的 AssetBundle 使用 LZMA 重新封装，以尽可能保持 SFS 模组兼容性。

| 功能 | 结果 |
| --- | --- |
| 提取待翻译文本 | 生成可编辑的 JSON 翻译表，支持自定义保存位置与文件名 |
| 写入汉化并生成 Pack | 在源文件同目录生成 `原文件名-CN.pack`，不覆盖原始 `.pack` |
| Unity 工程导出 | 导出 Prefab、贴图、材质、Shader、音频、`.meta`、`Packages` 和 `ProjectSettings`（资源存在时） |
| 内置 AssetRipper | 默认使用内置 1.1.4；仍可手动选择其他 `AssetRipper.GUI.Free.exe` 覆盖默认版本 |
| 安全目录策略 | 只创建新的输出子目录；不清空、不删除、不覆盖原 Pack 或用户已存在的目录 |
| 中英文界面 | 右上角切换语言，选择会自动保存 |

## 下载与启动

请下载发行包中的 EXE，并放置到一个你有写入权限的普通文件夹，例如 `D:\Tools\SFS Pack Tool\`。双击 `SFS_Pack_Tool_v22_Embedded_GPL.exe` 启动即可。程序带有 AFuturestar 自签名证书；如果 Windows 显示未知发布者或 SmartScreen 提示，可先核对发行包中的公开证书与 SHA-256 签名信息，再按你的安全策略决定是否运行。

首次使用 Unity 工程导出功能时，内置 AssetRipper 会释放到 EXE 旁边的 `AssetRipper-1.1.4` 文件夹。若 EXE 所在目录没有写入权限，程序会改用当前用户的本地应用数据目录。该过程仅创建或补齐工具自身的文件，不会删除已有文件。

| 文件或位置 | 用途 |
| --- | --- |
| `SFS_Pack_Tool_v22_Embedded_GPL.exe` | 主程序，已内置运行包 |
| `AssetRipper-1.1.4/` | 首次导出后自动释放的内置 AssetRipper 文件 |
| `%LOCALAPPDATA%\AFuturestar\SFS-Pack-Tool\` | EXE 同目录不可写时的备用释放位置 |
| `settings.json` | 自动保存语言、作者标识、路径等偏好 |
| `LICENSE-GPL-3.0.txt` | GNU GPL v3.0 完整文本 |
| `GPL_COMPLIANCE.md` | AssetRipper 版本、校验值和对应源码说明 |

## 快速开始

### 1. 选择 Pack 文件

在“输入文件”区域点击 **选择原始 mod.pack**，选择需要处理的 `.pack` 文件。选择后，日志会显示源文件名；工具默认把同目录作为建议的导出位置，但不会把该目录当作可清空的工程目录。

### 2. 提取待翻译文本

在“汉化处理”区域可先点击 **选择保存位置**，指定待翻译 JSON 的路径与文件名；然后点击 **提取待翻译文本**。如未另行指定，默认文件名为 `texts_to_translate.json`。生成的 JSON 采用“原文: 原文”格式，编辑时只修改冒号右侧的文本。

```json
{
  "Engine": "发动机",
  "Fuel Tank": "燃料箱"
}
```

请保持 JSON 语法有效：每一行的键和值均使用英文双引号，条目之间使用逗号，最后一个条目后不要添加逗号。

### 3. 写入汉化并生成新 Pack

完成翻译后，在“输入文件”区域点击 **选择翻译 JSON** 选择刚保存的 JSON。需要时可修改“汉化作者标识”；默认标识为 `〈A Future star汉化〉`。然后点击 **写入汉化并生成 Pack**。

工具会在原 `.pack` 同目录生成 `原文件名-CN.pack`。原始 Pack 不会被覆盖；如需重新处理，请以原始文件或新生成文件为明确输入进行操作。

### 4. 导出 Unity 工程

在“Unity Prefab / 贴图 / 工程导出”区域选择一个 **导出位置**，例如 `D:\SFS_Exports\`，然后点击 **一键导出工程**。程序会自动创建：

```text
D:\SFS_Exports\
└── 模组名称_UnityProject\
    ├── Assets\
    ├── Packages\
    ├── ProjectSettings\
    ├── EXPORT_MANIFEST.json
    └── EXPORT_README.md
```

若 `模组名称_UnityProject` 或同名 ZIP 已存在，程序会创建 `模组名称_UnityProject_2`、`_3` 等新目录和文件，不会删除或覆盖旧结果。导出完成后，可使用 Unity Hub 打开工程目录，或将整个 `Assets/` 连同 `.meta` 文件复制到现有 Unity 项目。

## AssetRipper 说明

默认情况下，AssetRipper 路径可以保持为空。程序将优先释放并使用内置的 1.1.4 版本，其启动参数只使用该版本支持的 `--port` 与 `--launch-browser false`，不会再传入旧版本不认识的 `--headless`、`--log` 或 `--log-path` 参数。

如果你已自行安装新版或其他特定版本，可点击 **选择 .exe** 指定 `AssetRipper.GUI.Free.exe`。这会覆盖内置版本；手动指定版本发生异常时，建议清空该路径并恢复使用内置 1.1.4。

| 场景 | 建议操作 |
| --- | --- |
| 第一次使用 | 保持 AssetRipper 路径为空，直接导出 |
| 已有 AssetRipper 但版本不稳定 | 清空路径，使用内置 1.1.4 |
| 希望测试其他版本 | 点击“选择 .exe”指定其 `AssetRipper.GUI.Free.exe` |
| EXE 所在位置不可写 | 将 EXE 移至普通文件夹，或让程序使用本地应用数据目录 |

## 输出文件说明

Unity 工程导出尽力保留资源与引用关系。`.meta` 文件尤其重要，因为它们保存 Unity GUID；复制资源时请连同 `.meta` 一起复制。`EXPORT_MANIFEST.json` 会列出 Prefab、贴图、材质、Shader、脚本/程序集、音频和工程配置等导出统计。

| 文件或目录 | 说明 |
| --- | --- |
| `Assets/**/*.prefab` | 实际 Unity YAML Prefab |
| `Assets/**/*.{png,jpg,tga,...}` | 已导出的贴图资源，数量取决于原包内容 |
| `Assets/**/*.mat` | 材质 |
| `Assets/**/*.shader` | Shader 或 ShaderGraph |
| `Assets/**/*.meta` | Unity GUID 元数据，应保留 |
| `Packages/` | 包依赖信息，原资源可导出时生成 |
| `ProjectSettings/` | Unity 项目设置，原资源可导出时生成 |
| `EXPORT_MANIFEST.json` | 机器可读的资源统计 |
| `EXPORT_README.md` | 该次导出工程的简要说明 |

## 常见问题

### 选择的目录或 Pack 会被删除吗？

不会。v22 的导出流程只在所选位置下创建新的 `模组名称_UnityProject` 目录。如果目标名称已存在，会自动追加序号；不会清空所选目录、输入 Pack、旧工程或旧 ZIP。

### 提示“无法读取 .pack JSON”怎么办？

请确认选中的确实是 SFS 的 JSON 格式 `.pack` 文件，而不是 ZIP、其他游戏文件或被截断的下载文件。可用文本编辑器打开文件开头检查其是否为 JSON 对象；如文件无法正常显示，请重新获取原始模组文件。

### 只想汉化，不需要 Unity 工程导出

只使用“提取待翻译文本”和“写入汉化并生成 Pack”两个功能即可。此流程不需要 AssetRipper。

### 为什么导出的 Unity 工程里有很多文件？

Prefab 依赖贴图、材质、Shader、`.meta` 与项目设置。导出这些依赖是为了减少引用丢失并提高工程可打开性。若只保留 `.prefab`，许多组件外观和资源引用可能会丢失。

### 导出的 Prefab 显示 Missing Script 是否正常？

可能正常。部分模组的逻辑依赖 SFS 游戏自身程序集或自定义 `CodeAssembly`，这些脚本无法在没有游戏依赖的空白 Unity 工程中完整还原。Prefab、贴图和大多数序列化字段仍可用于查看与编辑。

### 内置 AssetRipper 无法释放或启动怎么办？

请确认 EXE 所在目录可写，且安全软件没有隔离 EXE 或 `AssetRipper-1.1.4` 目录。也可将 EXE 移至用户文档或桌面下的新文件夹后重新运行。保留日志全文有助于定位问题。

## 许可证与源码

内置 AssetRipper 1.1.4 使用 GNU GPL v3.0，因此本内置分发以 GPL-3.0-or-later 提供。对应源码包中包含 AssetRipper 1.1.4 的完整源码 ZIP、官方 Windows x64 运行包、SFS Pack Tool 源码、构建材料与许可证文本。详细版本、SHA-256 校验和与上游信息见 `GPL_COMPLIANCE.md`。[1] [2]

> 本 README 是使用说明，不构成法律意见。分发或修改该内置版时，请同时保留 GPL 许可证、第三方声明与对应源码材料。

## 参考资料

[1]: https://github.com/AssetRipper/AssetRipper "AssetRipper 官方仓库"
[2]: https://www.gnu.org/licenses/gpl-3.0.html "GNU General Public License v3.0"

---

**SFS Pack Tool v22 · A Future star**
