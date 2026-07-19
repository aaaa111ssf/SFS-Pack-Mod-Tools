#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFS Pack Tool v20 - Termux / CLI Edition
Compatible with Android Termux and headless environments
Author: A Future star
"""

import base64
import json
import os
import re
import sys
import argparse

try:
    import UnityPy
except ImportError:
    print("Error: UnityPy not installed. Run: pip install UnityPy")
    sys.exit(1)

# ==================== CONFIG ====================
OUTPUT_FILE = "mod_CN.pack"
EXTRACTED_FILE = "texts_to_translate.json"
DEFAULT_AUTHOR = "〈A Future star汉化〉"

EXCLUDE_WORDS = [
    "Color_Gray", "Toggle", "width", "target_state", "tank", "height",
    "DeployParachute", "Landing_Leg_Expanded", "Basic_Parts", "Color_Black",
    "Color_White", "Flat Smooth 4", "Flat Smooth", "Detach", "Flat Faces",
    "Liquid_Fuel", "Metal", "Panel_Expanded", "width_original", "Engine_2",
    "fairing", "mass", "Flat_Shadow", "Separation", "Expanded", "ToggleEnabled",
    "ToggleEngine", "cone", "Engines", "Nozzle_2", "Engine_Parts", "torque",
    "throttle", "Mass_Unit", "engine_on", "ToggleRCS", "ToggleTransfer"
]

DANGER_PATH_KEYWORDS = {
    'm_MethodName', 'm_ClassName', 'm_Namespace', 'm_TypeName',
    'variableName', 'input', 'output', 'name', 'id', 'type', 'key',
    'reference', 'tag', 'layer', 'fragmentName', 'saves', 'points',
    'elements', 'm_Name', 'm_Script'
}

SAFE_FIELDS = {
    'displayName', 'description', 'label', 'DisplayName',
    'Description', 'Author', 'TranslatableName', 'text', 'title', 'units'
}

# ==================== CORE LOGIC ====================
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


# ==================== FUNCTIONS ====================
def extract_texts(input_file, output_file="texts_to_translate.json"):
    if not input_file or not os.path.exists(input_file):
        print("❌ mod.pack not found")
        return

    print(f"[*] Starting text extraction...")
    try:
        with open(input_file, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ JSON read error: {e}")
        return

    all_texts = set()
    build_keys = ['AndroidBuild', 'WindowsBuild', 'MacBuild', 'IOS_Build']

    for build_key in build_keys:
        if build_key not in data or not data[build_key]:
            continue
        print(f"    Scanning {build_key}...")
        try:
            env = UnityPy.load(base64.b64decode(data[build_key]))
        except Exception as e:
            print(f"    ⚠ {build_key} unpack failed: {e}")
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
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)
    print(f"[✔] Extraction complete! Total {len(output_dict)} texts → {output_file}")


def write_translation(input_file, translated_file, author_text=DEFAULT_AUTHOR, output_file="mod_CN.pack"):
    if not input_file or not os.path.exists(input_file):
        print("❌ mod.pack not found")
        return
    if not translated_file or not os.path.exists(translated_file):
        print("❌ Translation file not found")
        return

    print("[*] Loading files...")
    try:
        with open(input_file, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        with open(translated_file, "r", encoding="utf-8") as f:
            trans = json.load(f)
    except Exception as e:
        print(f"❌ File read failed: {e}")
        return

    trans = {k: v for k, v in trans.items() if k != v}
    if not trans:
        print("⚠ No valid translations found (all keys equal values). Aborting.")
        return

    for key in ["AndroidBuild", "WindowsBuild", "MacBuild", "IOS_Build"]:
        if key not in data:
            continue
        print(f"[*] Writing {key}...")
        try:
            env = UnityPy.load(base64.b64decode(data[key]))
        except Exception as e:
            print(f"    ⚠ Unpack failed: {e}")
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
            print(f"    [✔] {key} done, {changed} changes applied")
        except Exception as e:
            print(f"    ❌ {key} save failed: {e}")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[✔] Final file generated: {output_file}")
    except Exception as e:
        print(f"❌ Output failed: {e}")


def auto_process(input_file, author_text=DEFAULT_AUTHOR, output_file="mod_CN.pack"):
    extracted = "texts_to_translate.json"
    extract_texts(input_file, extracted)
    if os.path.exists(extracted):
        write_translation(input_file, extracted, author_text, output_file)
    else:
        print("❌ Extraction failed, aborting auto-process.")


# ==================== INTERACTIVE MENU ====================
def ask_path(prompt, must_exist=True):
    while True:
        p = input(prompt).strip().strip('"\'')
        if not p:
            return None
        if must_exist and not os.path.exists(p):
            print("    File not found, please try again.")
            continue
        return p


def interactive_menu():
    input_file = None
    print("\n" + "=" * 55)
    print("  SFS Pack Tool v20 - Termux / CLI Edition")
    print("  by A Future star | Feedback: QQ 923038827")
    print("=" * 55)

    while True:
        print("\n[Main Menu]")
        print("  1. Extract translatable texts")
        print("  2. Apply translation & generate new pack")
        print("  3. Auto process (Extract then Write)")
        print("  4. Set input mod.pack")
        print("  0. Exit")
        choice = input(">>> ").strip()

        if choice == "0":
            print("Goodbye.")
            break

        if choice == "4":
            p = ask_path("Enter mod.pack path: ")
            if p:
                input_file = p
                print(f"  Input set: {input_file}")
            continue

        if choice in ("1", "2", "3"):
            if not input_file:
                p = ask_path("Enter mod.pack path: ")
                if not p:
                    continue
                input_file = p
            else:
                print(f"  Current input: {input_file}")
                use = input("  Press ENTER to use it, or type new path: ").strip().strip('"\'')
                if use:
                    if os.path.exists(use):
                        input_file = use
                    else:
                        print("  File not found, using current.")

        if choice == "1":
            out = input(f"  Output filename (ENTER for {EXTRACTED_FILE}): ").strip()
            extract_texts(input_file, out or EXTRACTED_FILE)

        elif choice == "2":
            t = ask_path("  Translation JSON path: ")
            if not t:
                continue
            a = input(f"  Author tag (ENTER for {DEFAULT_AUTHOR}): ").strip()
            o = input(f"  Output filename (ENTER for {OUTPUT_FILE}): ").strip()
            write_translation(input_file, t, a or DEFAULT_AUTHOR, o or OUTPUT_FILE)

        elif choice == "3":
            a = input(f"  Author tag (ENTER for {DEFAULT_AUTHOR}): ").strip()
            o = input(f"  Output filename (ENTER for {OUTPUT_FILE}): ").strip()
            auto_process(input_file, a or DEFAULT_AUTHOR, o or OUTPUT_FILE)

        else:
            print("  Invalid option.")


# ==================== CLI ENTRY ====================
def main():
    parser = argparse.ArgumentParser(
        description="SFS Pack Tool v20 - Termux CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-i", "--input", help="Original mod.pack file path")
    parser.add_argument("-t", "--trans", help="Translated JSON file path")
    parser.add_argument("-o", "--output", default="mod_CN.pack", help="Output pack filename")
    parser.add_argument("-a", "--author", default=DEFAULT_AUTHOR, help="Translator signature")
    parser.add_argument("-e", "--extracted", default="texts_to_translate.json", help="Extraction output filename")
    parser.add_argument("-m", "--mode", choices=["extract", "write", "auto"], help="""
Mode:
  extract = Extract translatable texts
  write   = Apply translation and generate pack
  auto    = Extract then immediately write
""")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        interactive_menu()
        return

    if not args.input:
        print("❌ Please specify -i <mod.pack> or run without arguments for interactive mode.")
        sys.exit(1)

    if args.mode == "extract":
        extract_texts(args.input, args.extracted)
    elif args.mode == "write":
        if not args.trans:
            print("❌ write mode requires -t <translation.json>")
            sys.exit(1)
        write_translation(args.input, args.trans, args.author, args.output)
    elif args.mode == "auto":
        auto_process(args.input, args.author, args.output)
    else:
        print("❌ Please specify -m mode: extract / write / auto")
        sys.exit(1)


if __name__ == "__main__":
    main()
