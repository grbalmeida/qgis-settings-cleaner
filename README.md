# QGIS Settings Cleaner

A simple QGIS plugin that allows users to **reset QGIS settings to factory defaults** with a single click.

## Features

- Deletes all user-specific QGIS settings:
  - Language configuration
  - Proxy settings
  - CRS and coordinate system preferences
  - Database connection settings
  - WFS/WMS and XYZ tile services
  - Any other user-modified settings
- Works across platforms (Linux, Windows, macOS)
- Supports multiple languages (English, Portuguese - Brazil)
- Requires confirmation before performing any irreversible action
- Prompts user to restart QGIS after reset

## Why use this plugin?

Sometimes QGIS settings become corrupted or overly complex due to extensive customization. This plugin offers a **quick and safe way to reset everything** and start fresh, which is especially useful for:

- Troubleshooting
- Testing new versions
- Training environments
- Shared workstations

## Usage

1. Install the plugin from the QGIS Plugin Repository.
2. In QGIS, go to the **Plugins** menu and click on **Reset QGIS** → **Reset QGIS Settings**.
3. Confirm the operation in the dialog box.
4. Restart QGIS when prompted.

⚠️ **Note:** This operation is irreversible. All user settings will be permanently removed.

## Installation

This plugin is available via the [QGIS Plugin Repository](https://plugins.qgis.org/), or you can install manually:

1. Download or clone this repository.
2. Copy the folder to your QGIS plugins directory:
   - **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
3. Restart QGIS and activate the plugin via the **Plugins** menu.

## 🔧 Generating `resources_rc.py`

This plugin uses Qt resource files defined in `resources.qrc`. The compiled Python file `resources_rc.py` is **not included in version control** (`.gitignore`), so it must be generated manually.

### Generate with:

```bash
pyrcc5 resources.qrc -o resources_rc.py
```

Ensure pyrcc5 is installed:

```bash
sudo apt install pyqt5-dev-tools
```

## Translations

The plugin supports the following languages:
- English (`en`)
- Portuguese (`pt`)

Additional translations can be added by contributing `.ts` and `.qm` files in the `i18n/` folder.

## License

This program is licensed under GNU GPL v.2 or any later version.