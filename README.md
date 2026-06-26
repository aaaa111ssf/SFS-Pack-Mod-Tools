# SFS-pack Mod Localization Script | SFS-pack 模组汉化脚本
A UnityPy-based SFS.pack writing script, primarily used for mod localization.  
基于 UnityPy 的 SFS.pack 写入脚本，主要用于汉化模组。

---

## Usage | 使用方法

### Install UnityPy and tkinter | 安装 UnityPy 和 tkinter
```bash
pip install UnityPy
pip install tkinter
```
Run the script in the CMD window.  
在 cmd 窗口运行脚本。

Place the script and required files in the same directory, then execute:  
将脚本与所需文件放在同一目录下，执行：

```bash
python script_name.py
```

### Required Files | 所需文件（与脚本位于同一目录）
- `mod.pack` — The original mod pack file.  
  `mod.pack` —— 原始模组 pack 文件
- `texts_to_translated_zh.json` — The JSON file containing texts to be translated (format see below).  
  `texts_to_translated_zh.json` —— 待翻译的文本 JSON 文件（格式见下方）

### Output File | 输出文件
- `mod_CN.pack` — The localized pack file.  
  `mod_CN.pack` —— 汉化后的 pack 文件

*(The original JSON file remains unchanged; no modification needed.)*  
*（原始 JSON 文件保持不变，无需修改）*

---

## `texts_to_translated_zh.json` Format Example | 格式示例

```json
{
    "Height": "高度",
    "Width": "宽度",
    "Angle": "角度",
    "X Size": "X尺寸",
    "Y Size": "Y尺寸",
    "Angle Smooth": "角度微调",
    "X Size Smooth": "X尺寸微调",
    "Y Size Smooth": "Y尺寸微调",
    "Width Smooth": "宽度微调",
    "Height Smooth": "高度微调",
    "Layer": "层级",
    "Depth": "深度"
}
```

---

## ⚠️ Important Notes | 重要注意事项

If any text is missed, you can manually add it. **Note: It must match the in-game displayed text exactly, not a single character less.**  
若有漏掉的文本，可以使用手动添加。**注意：必须与游戏显示文本完全相同，一个字都不能少。**

---

## Contact | 联系方式
If you have any questions or feedback, please contact QQ: 2107478976  
如有问题或反馈，请联系 QQ：2107478976
