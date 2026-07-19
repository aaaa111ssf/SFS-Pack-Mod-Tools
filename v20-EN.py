import base64
import json
import UnityPy
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext

INPUT_FILE = ""
TRANSLATED_FILE = ""
OUTPUT_FILE = "mod_Localized.pack"
EXTRACTED_FILE = "texts_to_translate.json"
DEFAULT_AUTHOR = "<A Future star Translation>"

# Blacklist: never translate these
EXCLUDE_WORDS = [
    "Color_Gray", "Toggle", "width", "target_state", "tank", "height",
    "DeployParachute", "Landing_Leg_Expanded", "Basic_Parts", "Color_Black",
    "Color_White", "Flat Smooth 4", "Flat Smooth", "Detach", "Flat Faces",
    "Liquid_Fuel", "Metal", "Panel_Expanded", "width_original", "Engine_2",
    "fairing", "mass", "Flat_Shadow", "Separation", "Expanded", "ToggleEnabled",
    "ToggleEngine", "cone", "Engines", "Nozzle_2", "Engine_Parts", "torque",
    "throttle", "Mass_Unit", "engine_on", "ToggleRCS", "ToggleTransfer"
]

# Dangerous path keywords
DANGER_PATH_KEYWORDS = {
    'm_MethodName', 'm_ClassName', 'm_Namespace', 'm_TypeName',
    'variableName', 'input', 'output', 'name', 'id', 'type', 'key',
    'reference', 'tag', 'layer', 'fragmentName', 'saves', 'points',
    'elements', 'm_Name', 'm_Script'
}

# Whitelist safe fields
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
    if not isinstance(text, str):
        return False
    return text.strip() in EXCLUDE_WORDS


def validate_input():
    if not INPUT_FILE:
        return "mod.pack not selected"
    return None


def validate_full():
    if not INPUT_FILE:
        return "mod.pack not selected"
    if not TRANSLATED_FILE:
        return "Translation file not selected"
    return None


def run_async(func, log):
    def wrapper():
        try:
            func(log)
        except Exception as e:
            log(f"Thread crashed: {e}")
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
    if not s or len(s) < 2:
        return False
    if not is_path_safe(path):
        return False
    if re.match(r'^[0-9\s\.\,\%\+\-\*\/\(\)]+$', s):
        return False
    if 'UnityEngine' in s or 'Assembly-' in s or 'SFS.' in s:
        return False
    if '/' in s or '\\' in s:
        return False
    if is_exclude_word(s):
        return False
    return True


def extract_texts(log, mode="deep"):
    err = validate_input()
    if err:
        log(f"❌ {err}")
        return
    log(f"Starting text extraction ({mode} mode)...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        log(f"❌ JSON read error: {e}")
        return

    all_texts = set()
    build_keys = ['AndroidBuild', 'WindowsBuild', 'MacBuild', 'IOS_Build']
    for build_key in build_keys:
        if build_key not in data or not data[build_key]:
            continue
        log(f"  Scanning {build_key}...")
        try:
            env = UnityPy.load(base64.b64decode(data[build_key]))
        except Exception as e:
            log(f"❌ {build_key} unpack failed: {e}")
            continue

        for obj in env.objects:
            try:
                if obj.type.name == "MonoBehaviour":
                    tree = obj.read_typetree()
                    if tree is None:
                        continue
                    def collect(parent, key, value, path):
                        if is_display_text_extract(value, path):
                            all_texts.add(value)
                    recursive_walk(tree, '', collect)
            except Exception:
                continue

    output_dict = {text: text for text in sorted(list(all_texts))}
    with open(EXTRACTED_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)
    log(f"✔ Extraction complete! Total {len(output_dict)} texts → {EXTRACTED_FILE}")


def write(log, author_text):
    global OUTPUT_FILE
    OUTPUT_FILE = "mod_Localized.pack"
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
        log(f"❌ File read failed: {e}")
        return

    trans = {k: v for k, v in trans.items() if k != v}

    for key in ["AndroidBuild", "WindowsBuild", "MacBuild", "IOS_Build"]:
        if key not in data:
            continue
        log(f"Writing {key}...")
        try:
            env = UnityPy.load(base64.b64decode(data[key]))
        except Exception:
            continue

        changed = 0
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                tree = obj.read_typetree()
                if not tree:
                    continue

                def rep(node, path=''):
                    nonlocal changed
                    if isinstance(node, dict):
                        for k, v in list(node.items()):
                            child_path = f"{path}.{k}" if path else k
                            if isinstance(v, str):
                                if k == "Author":
                                    if author_text and author_text not in v:
                                        node[k] = v + author_text
                                        changed += 1
                                    continue

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
            except Exception:
                continue

        try:
            repaired_bundle = env.file.save(packer="lzma")
            data[key] = base64.b64encode(repaired_bundle).decode('utf-8')
            log(f"✔ {key} done, {changed} changes applied")
        except Exception as e:
            log(f"❌ {key} save failed: {e}")

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"✔ Final file generated: {OUTPUT_FILE}")
    except Exception as e:
        log(f"❌ Output failed: {e}")


class App:
    def __init__(self, root):
        self.root = root
        root.title("SFS Pack Tool v20")
        root.geometry("800x650")

        self.author_var = tk.StringVar(value=DEFAULT_AUTHOR)

        tk.Label(root, text="SFS Localization Tool V20", font=("Segoe UI", 14, "bold")).pack(pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="1. Select original mod.pack", command=self.pick_input, width=28).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(btn_frame, text="2. Select translation JSON", command=self.pick_trans, width=28).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(root, text="Translator Signature:").pack()
        tk.Entry(root, textvariable=self.author_var, width=60).pack(pady=5)

        tk.Label(root, text="--- Extraction Step ---").pack(pady=5)
        tk.Button(root, text="Extract translatable texts (auto-filter)",
                  command=lambda: run_async(lambda l: extract_texts(l), self.log_print),
                  bg="#e6f7ff", width=50).pack(pady=5)

        tk.Label(root, text="--- Writing Step ---").pack(pady=5)
        tk.Button(root, text="Apply translation & generate new Pack",
                  command=lambda: run_async(lambda l: write(l, self.author_var.get()), self.log_print),
                  bg="#f6ffed", width=50).pack(pady=5)

        self.log = scrolledtext.ScrolledText(root, font=("Consolas", 10), height=15)
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

    def log_print(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.root.update()

    def pick_input(self):
        global INPUT_FILE
        INPUT_FILE = filedialog.askopenfilename(filetypes=[("Pack files", "*.pack"), ("All files", "*.*")])
        if INPUT_FILE:
            self.log_print(f"Source selected: {os.path.basename(INPUT_FILE)}")

    def pick_trans(self):
        global TRANSLATED_FILE
        TRANSLATED_FILE = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if TRANSLATED_FILE:
            self.log_print(f"Translation selected: {os.path.basename(TRANSLATED_FILE)}")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
