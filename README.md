# SFS Pack Mos Tools 是一站式 mod 工具，覆盖：
• 汉化：提取/写入 mod.pack 的可翻译文本
• Prefab 导出：用内置 AssetRipper 把 .pack 反编译成 Unity 工程
• 免挂对齐：自动把 AssetRipper 占位脚本换成 Toolkit 真源码
• 空壳着色器修复：把导致「黑板」的占位着色器换成真着色器
• 悬空引用自愈：按同名/同 GUID 修复或补入缺失资产
• 合并包：只裁剪 Toolkit 没有的新内容，安全并入

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
