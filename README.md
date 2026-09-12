# SFS Pack Tool V2.3
> **汉化写入、剥离精简、Prefab/贴图导出与 Unity 工程恢复工具**  
> 内置 AssetRipper 1.1.4 · Windows x64 · GPL-3.0 合规分发
>
> Language / 语言：[简体中文](README.md) · [English](README_EN.md)

SFS Pack Tool 用于处理 SFS `.pack` 模组文件。它可以提取可翻译文本、将翻译写回新的 Pack，剥离冗余平台以精简体积，并把 Unity AssetBundle 导出为含真实 YAML Prefab、贴图、材质与项目配置的 Unity 工程。V2.3 内置官方 AssetRipper 1.1.4 Windows x64 运行包，全程无需下载、无需手动配置；工程导出会直接把新部件合并进你指定的 Modding Toolkit。

本工具应仅用于你拥有、获授权或法律允许处理的模组与资源。对于含自定义游戏程序集的模组，导出的 Prefab 与资源可用于研究和编辑，但原始游戏脚本依赖未必能在空白 Unity 工程中直接编译。

| 项目 | 说明 |
| --- | --- |
| 适用系统 | Windows 64 位 |
| 主程序 | `SFS_Pack_Tool_v2.3_Embedded_GPL_prev.exe` |
| 内置导出器 | AssetRipper 1.1.4 Windows x64（强制内置，无手动选择/下载） |
| 默认语言 | 中文，可在窗口右上角切换为 English |
| 许可证 | GPL-3.0-or-later；随附完整许可证、对应源码和第三方材料 |

## 功能介绍

工具的汉化部分会读取 `.pack` 的 JSON 容器及其中 Base64 编码的 Unity AssetBundle，提取可显示的文本供人工翻译。写入时只处理面向显示的字段，例如 `DisplayName`、`Description`、`TranslatableName` 与 `Author`，并避免修改 Unity 对象名、脚本引用及其他高风险序列化字段。写入后的 AssetBundle 使用 LZMA 重新封装，以尽可能保持 SFS 模组兼容性。

| 功能 | 结果 |
| --- | --- |
| 提取待翻译文本 | 生成可编辑的 JSON 翻译表，支持自定义保存位置与文件名 |
| 写入汉化并生成 Pack | 在源文件同目录生成 `原文件名-CN.pack`，不覆盖原始 `.pack` |
| 剥离 / 精简工具 | 只保留目标平台 Build 与 CodeAssembly，删除其他平台，大幅减小 `.pack` 体积 |
| 包信息分析 | 显示包体积、CodeAssembly 大小，以及各平台“解压后体积 + 部件数”概览 |
| Unity 工程导出 | 导出 Prefab、贴图、材质、Shader、音频、`.meta` 并**直接合并进 Modding Toolkit** |
| 内置 AssetRipper | 始终使用内置 1.1.4，无需也不能手动选择路径 |
| 免挂导入 | 导出部件按 Toolkit 脚本重写 GUID 引用，避免脚本组件挂掉 |
| 安全目录策略 | 只新增 Toolkit 里没有的部件；已有部件自动跳过，不清空、不覆盖 |
| 中英文界面 | 右上角切换语言，选择会自动保存 |

## 下载与启动

请下载发行包中的 EXE，并放置到一个你有写入权限的普通文件夹，例如 `D:\Tools\SFS Pack Tool\`。双击 `SFS_Pack_Tool_v22_Embedded_GPL.exe` 启动即可。程序带有 AFuturestar 自签名证书；如果 Windows 显示未知发布者或 SmartScreen 提示，可先核对发行包中的公开证书与 SHA-256 签名信息，再按你的安全策略决定是否运行。

内置 AssetRipper 已随程序打包，无需单独下载。首次导出时它会释放到 EXE 旁边的 `AssetRipper-1.1.4` 文件夹；若 EXE 所在目录没有写入权限，程序会改用当前用户的本地应用数据目录。该过程仅创建或补齐工具自身的文件，不会删除已有文件。

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
在“输入文件”区域点击 **选择原始 mod.pack**，选择需要处理的 `.pack` 文件。选择后，日志会显示源文件名。

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
完成翻译后，在“输入文件”区域点击 **选择翻译 JSON** 选择刚保存的 JSON。需要时可修改“汉化作者标识”；默认标识为 `〈A Future star汉化〉`。然后点击 **写入汉化并生成 Pack**。工具会在原 `.pack` 同目录生成 `原文件名-CN.pack`，不覆盖原始 Pack。

### 4. 导出并合入 Modding Toolkit
在“Unity Prefab / 贴图 / 工程导出”区域点击 **选择 Toolkit**，选中含 `Assets\Scripts` 的官方 Modding Toolkit 工程根目录，然后点击 **一键导出工程**。

部件会直接导出并合并进这个 Toolkit：只新增 Toolkit 里没有的部件，已有部件自动跳过；导出先在临时目录中转，完成后把新部件写进 Toolkit 的 `Assets`。脚本引用会按 Toolkit 实际脚本重写 GUID，避免导入后脚本组件“挂掉”。完成后打开 Toolkit 的 `Assets/Resources/Parts` 即可看到并编辑新部件。

- 若界面提示“Modding Toolkit 路径无效”：你选中的目录里没在 `Assets\Scripts` 下找到 `.cs.meta` 脚本，请换官方 Toolkit 的工程根目录。
- 未填 Toolkit 路径就导出会直接报错；不导出部件、只做汉化时无需填它。

### 5. 剥离精简（可选）
在“剥离 / 精简工具”区域，先点击 **包信息** 查看各平台体积与部件数；再选择 **目标平台** 与（可选）**输出位置**，点击 **剥离到目标平台**。工具会只保留目标平台 Build 与 CodeAssembly、删除其余平台，生成精简后的新 `.pack`（未设输出位置时在原目录生成 `原文件名-平台.pack`）。

## AssetRipper 说明

V2.3 始终使用随程序内置的 AssetRipper 1.1.4，不再提供 AssetRipper 路径输入框，也无需任何手动选择或联网下载。程序只传入该版本支持的 `--port` 与 `--launch-browser false` 启动参数，不会使用旧版本不认识的选项。

内置版本若异常结束，程序会改用兼容参数从**同一个内置可执行文件**重启，全程不联网下载。若 EXE 无法释放或启动，请确认所在目录可写、安全软件未隔离 `AssetRipper-1.1.4` 目录，并保留日志全文以便定位。

## 输出文件说明

导出结果写进所选的 Modding Toolkit，新增部件落在其 `Assets/Resources/Parts`。`.meta` 文件保存 Unity GUID，脚本引用会按 Toolkit 脚本对齐，复制资源时请连同 `.meta` 一起复制。仅做汉化时不会创建任何导出工程。

| 输出或位置 | 说明 |
| --- | --- |
| `Toolkit/Assets/Resources/Parts/**/*.prefab` | 合并进 Toolkit 的新增部件（真实 Unity YAML Prefab） |
| 各平台资料 Build 内贴图/材质/Shader 等 | 随部件一起释放的序列化资源 |
| `*.cs.meta` | Unity GUID 元数据，已按 Toolkit 脚本重写对齐 |
| 汉化输出 `原文件名-CN.pack` | 汉化写入后的新 Pack，位于源文件同目录 |
| 剥离输出 `原文件名-平台.pack` | 剥离后仅剩目标平台的精简 Pack |

## 常见问题

### 选择的目录或 Pack 会被删除吗？
不会。导出只把“新增部件”写进 Toolkit 的 `Assets`，已有部件自动跳过；不清空、不删除、不覆盖 Toolkit 里的既有内容，也不改动输入 Pack 或汉化输出。

### 修改 Toolkit 脚本对导出有影响吗？
导出会把部件脚本引用对齐到 Toolkit 里实际存在的脚本。建议使用与部件来源兼容的 Toolkit 版本；脚本缺失时对应 `m_Script` 引用可能仍无法解析。

### 提示“无法读取 .pack JSON”怎么办？
请确认选中的确实是 SFS 的 JSON 格式 `.pack` 文件，而不是 ZIP、其他游戏文件或被截断的下载文件。可用文本编辑器打开文件开头检查其是否为 JSON 对象；如文件无法正常显示，请重新获取原始模组文件。

### 只想汉化，不需要 Unity 工程导出
只使用“提取待翻译文本”和“写入汉化并生成 Pack”两个功能即可。此流程不需要 AssetRipper，也不需要 Modding Toolkit。

### 导出的 Prefab 显示 Missing Script 是否正常？
可能正常。部分模组的逻辑依赖 SFS 游戏自身程序集或自定义 `CodeAssembly`，这些脚本无法在没有游戏依赖的空白 Unity 工程中完整还原。Prefab、贴图和大多数序列化字段仍可用于查看与编辑；凡能由 Toolkit 脚本解决的引用，V2.3 的免挂对齐会自动处理。

### 内置 AssetRipper 无法释放或启动怎么办？
请确认 EXE 所在目录可写，且安全软件没有隔离 EXE 或 `AssetRipper-1.1.4` 目录。也可将 EXE 移至用户文档或桌面下的新文件夹后重新运行。V2.3 崩溃后会用内置版兼容参数自动重启，不联网下载。保留日志全文有助于定位问题。

## 许可证与源码

内置 AssetRipper 1.1.4 使用 GNU GPL v3.0，因此本内置分发以 GPL-3.0-or-later 提供。对应源码包中包含 AssetRipper 1.1.4 的完整源码 ZIP、官方 Windows x64 运行包、SFS Pack Tool 源码、构建材料与许可证文本。详细版本、SHA-256 校验和与上游信息见 `GPL_COMPLIANCE.md`。

> 本 README 是使用说明，不构成法律意见。分发或修改该内置版时，请同时保留 GPL 许可证、第三方声明与对应源码材料。

## 参考资料

[1]: https://github.com/AssetRipper/AssetRipper "AssetRipper 官方仓库"
[2]: https://www.gnu.org/licenses/gpl-3.0.html "GNU General Public License v3.0"

---
**SFS Pack Tool V2.3 · A Future star**
