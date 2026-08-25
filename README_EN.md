# SFS Pack Tool v22

> **Localization writing, Prefab/texture export, and Unity project recovery**  
> Embedded AssetRipper 1.1.4 · Windows x64 · GPL-3.0-compliant distribution
>
> Language / 语言：[简体中文](README.md) · [English](README_EN.md)

SFS Pack Tool processes SFS `.pack` mod files. It can extract translatable text, write translations into a new Pack, and export Unity AssetBundles as a Unity project containing real YAML Prefabs, textures, materials, and project configuration. Version 22 embeds the official AssetRipper 1.1.4 Windows x64 runtime, so no additional AssetRipper download or setup is required by default.

Use this tool only with mods and assets that you own, are authorized to modify, or are otherwise legally allowed to process. For mods that depend on custom game assemblies, exported Prefabs and assets can be inspected and edited, but game-specific scripts may not compile in a blank Unity project.

| Item | Details |
| --- | --- |
| Supported system | Windows 64-bit |
| Main program | `SFS_Pack_Tool_v22_Embedded_GPL.exe` |
| Embedded exporter | AssetRipper 1.1.4 Windows x64 |
| Interface languages | Chinese and English |
| License | GPL-3.0-or-later, with license text and corresponding source materials included |

## Features

The localization workflow reads the JSON container of an SFS `.pack` file and the Base64-encoded Unity AssetBundles inside it. It extracts displayable text for manual translation. When writing a translated Pack, it targets display-oriented fields such as `DisplayName`, `Description`, `TranslatableName`, and `Author`, while avoiding Unity object names, script references, and other high-risk serialized fields. Updated AssetBundles are saved with LZMA compression to preserve mod compatibility as far as possible.

| Feature | Result |
| --- | --- |
| Extract translatable text | Creates an editable JSON translation table at a user-selected location |
| Write localization and create Pack | Creates `original-name-CN.pack` beside the source Pack without overwriting it |
| Export a Unity project | Exports Prefabs, textures, materials, shaders, audio, `.meta` files, `Packages`, and `ProjectSettings` when present in the source assets |
| Embedded AssetRipper | Uses the bundled 1.1.4 release by default; a manually selected `AssetRipper.GUI.Free.exe` can override it |
| Safe output handling | Creates a new output subfolder and never clears, deletes, or overwrites the source Pack or existing user folders |
| Bilingual interface | Switch Chinese/English in the upper-right corner; the selection is saved automatically |

## Download and launch

Download the EXE from the release package and place it in a normal folder where you have write permission, for example `D:\Tools\SFS Pack Tool\`. Start it by double-clicking `SFS_Pack_Tool_v22_Embedded_GPL.exe`.

The EXE is signed with an AFuturestar self-signed certificate. Windows may still show an unknown publisher or SmartScreen warning on systems where that certificate has not been installed as a trusted publisher. Verify the public certificate and SHA-256 signature information provided in the release package before deciding whether to run it.

On the first Unity project export, the embedded AssetRipper files are extracted to an `AssetRipper-1.1.4` folder next to the EXE. If that folder is not writable, the tool uses the current user's local application-data folder instead. This process only creates or completes files belonging to the tool; it does not delete existing user files.

| File or location | Purpose |
| --- | --- |
| `SFS_Pack_Tool_v22_Embedded_GPL.exe` | Main program with the embedded runtime |
| `AssetRipper-1.1.4/` | Embedded AssetRipper files extracted on first export |
| `%LOCALAPPDATA%\AFuturestar\SFS-Pack-Tool\` | Fallback extraction location when the EXE folder is not writable |
| `settings.json` | Stores language, author signature, and path preferences |
| `LICENSE-GPL-3.0.txt` | Full GNU GPL v3.0 license text |
| `GPL_COMPLIANCE.md` | AssetRipper version, checksums, upstream link, and compliance information |

## Quick start

### 1. Select a Pack file

Click **Select source mod.pack** in the **Input Files** section and select the `.pack` file to process. The log shows the selected source file. Its parent folder is suggested as an export location, but it is never treated as a folder to clear.

### 2. Extract translatable text

Optionally click **Choose save location** in the **Localization** section to choose the path and filename for the translation JSON, then click **Extract translatable text**. If no custom location is set, the default filename is `texts_to_translate.json`.

The generated file uses an `original text: translated text` structure. Edit only the value on the right.

```json
{
  "Engine": "Engine",
  "Fuel Tank": "Fuel Tank"
}
```

Keep the JSON valid: keys and values require double quotes, entries require commas between them, and the final entry must not end with a comma.

### 3. Apply translation and create a new Pack

After editing the JSON, click **Select translation JSON** in the **Input Files** section and choose the translated file. You may change the **Translator signature** if needed; the default is `〈A Future star汉化〉`. Then click **Apply translation and create Pack**.

The tool creates `original-name-CN.pack` next to the original `.pack`. The original Pack is never overwritten.

### 4. Export a Unity project

Choose an **Export location** in the **Unity Prefab / Texture / Project Export** section, for example `D:\SFS_Exports\`, then click **Export Unity project**. The tool automatically creates a project folder such as:

```text
D:\SFS_Exports\
└── ModName_UnityProject\
    ├── Assets\
    ├── Packages\
    ├── ProjectSettings\
    ├── EXPORT_MANIFEST.json
    └── EXPORT_README.md
```

If the project folder or ZIP filename already exists, the tool creates `ModName_UnityProject_2`, `_3`, and so on. It does not delete or overwrite older results. Open the resulting folder through Unity Hub, or copy the entire `Assets/` folder together with its `.meta` files into an existing Unity project.

## AssetRipper behavior

Leave the **AssetRipper path** blank to use the embedded version. The tool extracts and starts AssetRipper 1.1.4 with only the options supported by that version: `--port` and `--launch-browser false`. It does not pass unsupported 1.1.4 options such as `--headless`, `--log`, or `--log-path`.

If you need another AssetRipper version, click **Select .exe** and choose its `AssetRipper.GUI.Free.exe`. This overrides the embedded version. If a manually selected version fails, clear that path and return to the embedded 1.1.4 release.

| Situation | Recommended action |
| --- | --- |
| First use | Leave the AssetRipper path empty and export normally |
| Existing AssetRipper is unstable | Clear the path and use the embedded 1.1.4 runtime |
| Testing another version | Use **Select .exe** to choose its `AssetRipper.GUI.Free.exe` |
| EXE folder is not writable | Move the EXE to a normal user folder or allow the local application-data fallback |

## Exported files

The Unity-project export preserves assets and references as far as possible. `.meta` files are especially important because they contain Unity GUID metadata; always copy them with their matching assets. `EXPORT_MANIFEST.json` provides an inventory of exported Prefabs, textures, materials, shaders, scripts/assemblies, audio, and project settings.

| Output | Description |
| --- | --- |
| `Assets/**/*.prefab` | Real Unity YAML Prefabs |
| `Assets/**/*.{png,jpg,tga,...}` | Exported textures when present |
| `Assets/**/*.mat` | Materials |
| `Assets/**/*.shader` | Shaders or ShaderGraphs |
| `Assets/**/*.meta` | Unity GUID metadata; keep these files |
| `Packages/` | Package dependency information when exported from the source assets |
| `ProjectSettings/` | Unity project settings when exported from the source assets |
| `EXPORT_MANIFEST.json` | Machine-readable asset inventory |
| `EXPORT_README.md` | Brief README for that exported project |

## Troubleshooting

### Will a selected folder or Pack file be deleted?

No. Version 22 only creates a new `ModName_UnityProject` folder under the selected location. If the name already exists, it adds a numeric suffix. The selected location, input Pack, old projects, and old ZIP files are not cleared or overwritten.

### What does “Unable to read .pack JSON” mean?

Confirm that the selected file is an SFS JSON-format `.pack`, not a ZIP file, another game file, or a truncated download. You can open the beginning of the file in a text editor to verify that it is a JSON object. Re-download the original mod if it cannot be read correctly.

### I only want localization, not Unity-project export

Use only **Extract translatable text** and **Apply translation and create Pack**. AssetRipper is not required for this workflow.

### Why are there so many files in the exported Unity project?

Prefabs depend on textures, materials, shaders, `.meta` files, and project settings. These dependencies are exported to reduce missing references and improve project usability. Keeping only `.prefab` files can remove visual assets and break references.

### Why do exported Prefabs show Missing Script?

This can be expected. Some mods depend on SFS game assemblies or custom `CodeAssembly` code that cannot be fully restored in a blank Unity project. Prefabs, textures, and most serialized fields remain available for viewing and editing.

### The embedded AssetRipper cannot be extracted or started

Ensure that the EXE folder is writable and that security software has not quarantined the EXE or the `AssetRipper-1.1.4` folder. Move the EXE to a new folder under Documents or Desktop and try again. Keep the complete log output when reporting an issue.

## License and source code

The embedded AssetRipper 1.1.4 runtime is licensed under GNU GPL v3.0. Accordingly, this embedded distribution is provided under GPL-3.0-or-later. The source-code package includes the complete AssetRipper 1.1.4 source ZIP, the official Windows x64 runtime ZIP, SFS Pack Tool source files, build materials, and the license text. See `GPL_COMPLIANCE.md` for version details, SHA-256 checksums, and upstream information.[1] [2]

> This README is usage documentation and not legal advice. When distributing or modifying this embedded edition, keep the GPL license, third-party notices, and corresponding source materials together.

## References

[1]: https://github.com/AssetRipper/AssetRipper "AssetRipper official repository"
[2]: https://www.gnu.org/licenses/gpl-3.0.html "GNU General Public License v3.0"

---

**SFS Pack Tool v22 · A Future star**
