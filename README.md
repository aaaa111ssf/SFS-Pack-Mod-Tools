# SFS-pack 模组汉化脚本  
基于 UnityPy 的 SFS.pack 写入脚本，主要用于汉化模组。  

# 使用方法  
## 安装 UnityPy和tkinter  
pip install UnityPy    
pip install tkinter
在 cmd 窗口运行脚本  

将脚本与所需文件放在同一目录下，执行：  

python 脚本名.py  
所需文件（与脚本位于同一目录）  
mod.pack —— 原始模组 pack 文件  
texts_to_translated_zh.json —— 待翻译的文本 JSON 文件（格式见下方）  
输出文件  
mod_CN.pack —— 汉化后的 pack 文件  
（原始 JSON 文件保持不变，无需修改）  
# texts_to_translated_zh.json 格式示例  
Json  
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
}  
# ⚠️ 重要注意事项  
问题	说明
v18 提取文本过多	当前 v18 版本存在提取文本过多的问题，请挨个核对翻译，否则会导致部件无法使用。  
浅版本问题	“qian”版本存在提取过少等问题。  
建议搭配使用	若有漏掉的文本，可以使用手动添加（注意：必须与游戏显示文本完全相同，一个字都不能少）。  
# 联系方式   
如有问题或反馈，请联系 QQ：2107478976
