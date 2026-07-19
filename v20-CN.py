import base64
import json
import UnityPy
import os
import re
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

INPUT_FILE = ""
TRANSLATED_FILE = ""
OUTPUT_FILE = "mod_CN.pack"
EXTRACTED_FILE = "texts_to_translate.json"
DEFAULT_AUTHOR = "〈A Future star汉化〉"

# 黑名单：这些词在任何情况下都不应汉化
EXCLUDE_WORDS = [
    "Color_Gray", "Toggle", "width", "target_state", "tank", "height","DeployParachute","Landing_Leg_Expanded","Basic_Parts", "Color_Black", "Color_White", "Flat Smooth 4", "Flat Smooth", "Detach", "Flat Faces", "Liquid_Fuel", "Metal", "Panel_Expanded", "width_original", "Engine_2", "fairing", "mass", 
    "Flat_Shadow", "Separation", "Expanded", "ToggleEnabled", "ToggleEngine", "cone", "Engines", "Nozzle_2", "Engine_Parts", "torque", "throttle",  "Mass_Unit", "engine_on", "ToggleRCS", "ToggleTransfer"
]

# 危险路径
DANGER_PATH_KEYWORDS = {
    'm_MethodName', 'm_ClassName', 'm_Namespace', 'm_TypeName',
    'variableName', 'input', 'output', 'name', 'id', 'type', 'key',
    'reference', 'tag', 'layer', 'fragmentName', 'saves', 'points',
    'elements', 'm_Name', 'm_Script'
}

# 白名单
SAFE_FIELDS = {
    'displayName', 'description', 'label', 'DisplayName', 
    'Description', 'Author', 'TranslatableName', 'text', 'title', 'units'
}

def is_path_safe(path):
    if any(sf in path for sf in SAFE_FIELDS):
        last_part = path.split('.')[-1].split('[')[0]
        if last_part in SAFE_FIELDS:
            return True
    
    for dk in DANGER_PATH_KEYWORDS:
        if dk in path:
            return False
    return True

def is_exclude_word(text):
    if not isinstance(text, str): return False
    text_clean = text.strip()
    return text_clean in EXCLUDE_WORDS

def validate_input():
    if not INPUT_FILE: return "未选择 mod.pack"
    return None

def validate_full():
    if not INPUT_FILE: return "未选择 mod.pack"
    if not TRANSLATED_FILE: return "未选择翻译文件"
    return None

def run_async(func, log):
    def wrapper():
        try:
            func(log)
        except Exception as e:
            log(f"线程崩溃: {e}")
    t = threading.Thread(target=wrapper, daemon=True)
    t.start()

def recursive_walk(node, path='', callback=None):
    if isinstance(node, dict):
        for k, v in node.items():
            child_path = f"{path}.{k}" if path else k
            if isinstance(v, str):
                callback(node, k, v, child_path)
            elif isinstance(v, (dict, list)):
                recursive_walk(v, child_path, callback)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            child_path = f"{path}[{i}]"
            if isinstance(v, str):
                callback(node, i, v, child_path)
            elif isinstance(v, (dict, list)):
                recursive_walk(v, child_path, callback)

def is_display_text_extract(s, path):
    if not s or len(s) < 2: return False
    # 必须是安全路径
    if not is_path_safe(path): return False
    # 排除纯数字/符号
    if re.match(r'^[0-9\s\.\,\%\+\-\*\/\(\)]+$', s): return False
    # 排除代码标识符
    if 'UnityEngine' in s or 'Assembly-' in s or 'SFS.' in s: return False
    if '/' in s or '\\' in s: return False
    # 排除黑名单
    if is_exclude_word(s): return False
    return True

def extract_texts(log, mode="deep"):
    err = validate_input()
    if err:
        log(f"❌ {err}")
        return
    log(f"开始提取文本 ({mode} 模式)...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        log(f"❌ JSON读取错误: {e}")
        return
    
    all_texts = set()
    build_keys = ['AndroidBuild', 'WindowsBuild', 'MacBuild', 'IOS_Build']
    for build_key in build_keys:
        if build_key not in data or not data[build_key]: continue
        log(f"  扫描 {build_key}...")
        try:
            env = UnityPy.load(base64.b64decode(data[build_key]))
        except Exception as e:
            log(f"❌ {build_key} 解包失败: {e}")
            continue
            
        for obj in env.objects:
            try:
                if obj.type.name == "MonoBehaviour":
                    tree = obj.read_typetree()
                    if tree is None: continue
                    def collect(parent, key, value, path):
                        if is_display_text_extract(value, path):
                            all_texts.add(value)
                    recursive_walk(tree, '', collect)
            except: continue
            
    output_dict = {text: text for text in sorted(list(all_texts))}
    with open(EXTRACTED_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)
    log(f"提取完成！共 {len(output_dict)} 条文本 → {EXTRACTED_FILE}")

def write(log, author_text):
    global OUTPUT_FILE
    OUTPUT_FILE = "mod_CN.pack"
    err = validate_full()
    if err:
        log(f"❌ {err}")
        return
    try:
        with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        with open(TRANSLATED_FILE, "r", encoding="utf-8") as f:
            trans = json.load(f)
    except Exception as e:
        log(f"❌ 文件读取失败: {e}")
        return
    
    # 仅处理有变化的翻译
    trans = {k: v for k, v in trans.items() if k != v}
    
    for key in ["AndroidBuild", "WindowsBuild", "MacBuild", "IOS_Build"]:
        if key not in data: continue
        log(f"正在写入 {key}...")
        try:
            env = UnityPy.load(base64.b64decode(data[key]))
        except: continue
        
        changed = 0
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour": continue
            try:
                tree = obj.read_typetree()
                if not tree: continue
                
                def rep(node, path=''):
                    nonlocal changed
                    if isinstance(node, dict):
                        for k, v in list(node.items()):
                            child_path = f"{path}.{k}" if path else k
                            if isinstance(v, str):
                                # 处理作者
                                if k == "Author":
                                    if author_text and author_text not in v:
                                        node[k] = v + author_text
                                        changed += 1
                                    continue
                                
                                # 核心判断
                                if is_path_safe(child_path) and not is_exclude_word(v):
                                    if v in trans:
                                        node[k] = trans[v]
                                        changed += 1
                            elif isinstance(v, (dict, list)):
                                rep(v, child_path)
                    elif isinstance(node, list):
                        for i, v in enumerate(node):
                            child_path = f"{path}[{i}]"
                            if isinstance(v, str):
                                if is_path_safe(child_path) and not is_exclude_word(v) and v in trans:
                                    node[i] = trans[v]
                                    changed += 1
                            elif isinstance(v, (dict, list)):
                                rep(v, child_path)
                
                rep(tree)
                obj.save_typetree(tree)
            except: continue
            
        try:
            # 使用 UnityPy 的 save 方法重新打包
            repaired_bundle = env.file.save(packer="lzma")
            data[key] = base64.b64encode(repaired_bundle).decode('utf-8')
            log(f"✔ {key} 完成，修改 {changed} 处")
        except Exception as e:
            log(f"❌ {key} 保存失败: {e}")
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"✔ 最终文件已生成：{OUTPUT_FILE}")

class App:
    def __init__(self, root):
        self.root = root
        root.title("SFS Pack Tool v20")
        root.geometry("800x650")
        
        self.author_var = tk.StringVar(value=DEFAULT_AUTHOR)
        
        tk.Label(root, text="SFS 汉化工具 V20", font=("微软雅黑", 14, "bold")).pack(pady=10)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="1. 选择原始 mod.pack", command=self.pick_input, width=25).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="2. 选择翻译 JSON", command=self.pick_trans, width=25).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(root, text="汉化作者标识：").pack()
        tk.Entry(root, textvariable=self.author_var, width=60).pack(pady=5)
        
        tk.Label(root, text="--- 提取步骤 ---").pack(pady=5)
        tk.Button(root, text="提取待翻译文本 (自动过滤)", command=lambda: run_async(lambda l: extract_texts(l), self.log_print), bg="#e6f7ff", width=50).pack(pady=5)
        
        tk.Label(root, text="--- 写入步骤 ---").pack(pady=5)
        tk.Button(root, text="写入汉化并生成新 Pack", command=lambda: run_async(lambda l: write(l, self.author_var.get()), self.log_print), bg="#f6ffed", width=50).pack(pady=5)
        
        self.log = scrolledtext.ScrolledText(root, font=("Consolas", 10), height=15)
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

    def log_print(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.root.update()

    def pick_input(self):
        global INPUT_FILE
        INPUT_FILE = filedialog.askopenfilename(filetypes=[("Pack文件", "*.pack"), ("所有文件", "*.*")])
        if INPUT_FILE: self.log_print(f"已选择源文件：{os.path.basename(INPUT_FILE)}")

    def pick_trans(self):
        global TRANSLATED_FILE
        TRANSLATED_FILE = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")])
        if TRANSLATED_FILE: self.log_print(f"已选择翻译文件：{os.path.basename(TRANSLATED_FILE)}")

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
