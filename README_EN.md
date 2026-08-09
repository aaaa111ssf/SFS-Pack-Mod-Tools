# SFS-pack Mod Localization Script

[中文](README.md)

A UnityPy-based SFS.pack writing script, primarily used for mod localization.

## Usage

### Install UnityPy and tkinter

```bash
pip install UnityPy
pip install tkinter
```

Run the script in the CMD window.

Place the script and required files in the same directory, then execute:

```bash
python script_name.py
```

### termux

```bash
# 1. Install dependencies
pkg install python
pip install UnityPy
# 2. Run the interactive menu directly
python v20-CN.py
# 3. Or use command line arguments
# Extract texts
python v20-CN.py -i mod.pack -m extract
# Auto process
python v20-CN.py -i mod.pack -m auto -o mod_CN.pack
```

### Required Files (same directory as the script)

- `mod.pack`: the original mod pack file
- `texts_to_translated_zh.json`: the JSON file containing texts to be translated (format below)

### Output File

- `mod_CN.pack`: the localized pack file

## `texts_to_translated_zh.json` Format Example

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

## Important Notes

If any text is missed, you can manually add it. Note: it must match the in-game displayed text exactly, not a single character less.

## Contact

If you have any questions or feedback, please contact QQ: 2107478976 Discord:afuturestar_78289
