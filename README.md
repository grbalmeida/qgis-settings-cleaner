# QGIS Settings Cleaner

A simple QGIS plugin that allows users to **clear QGIS settings for a fresh start** in just a few steps.

## Features

- Selective or full cleanup: choose individual categories or clean everything at once
  - Language configuration
  - Proxy settings
  - CRS (Coordinate Reference System) preferences
  - Database connection settings
  - WFS/WMS and XYZ tile services
  - Any other user-modified settings
- Works across platforms (Linux, Windows, macOS)
- Supports multiple languages (English, Portuguese - Brazil)
- Requires confirmation before performing any irreversible action
- Closes QGIS after cleanup for a fresh restart

## Why use this plugin?

Sometimes QGIS settings become corrupted or overly complex due to extensive customization. This plugin offers a **quick and safe way to clean everything** and start fresh, which is especially useful for:

- Troubleshooting
- Testing new versions
- Training environments
- Shared workstations

## Usage

1. Install the plugin from the QGIS Plugin Repository.
2. In QGIS, go to the **Plugins** menu and click on **Clean QGIS** → **Clean QGIS Settings**.
3. Select which setting categories to clean, or use **Clean All Settings (Full Clean)** to remove everything.
4. Confirm the operation in the dialog box.
5. Click Close to exit QGIS, then reopen it manually.

⚠️ **Note:** Cleared settings will be permanently removed.

## Installation

This plugin is available via the [QGIS Plugin Repository](https://plugins.qgis.org/), or you can install manually:

1. Download or clone this repository.
2. Copy the folder to your QGIS plugins directory:
   - **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Restart QGIS and activate the plugin via the **Plugins** menu.

## Translations

The plugin supports the following languages:
- English (`en`)
- Portuguese (`pt`)

Additional translations can be added by contributing `.ts` and `.qm` files in the `i18n/` folder.

## Generating `resources_rc.py`

This plugin uses Qt resource files defined in `resources.qrc`. The compiled Python file `resources_rc.py` is **not included in version control** (`.gitignore`), so it must be generated manually.

### Generate with:

```bash
pyrcc5 resources.qrc -o resources_rc.py
```

On Linux, install `pyrcc5` with:

```bash
sudo apt install pyqt5-dev-tools
```

On Windows and macOS, `pyrcc5` is typically bundled with the PyQt5 package.

## License

This program is licensed under GNU GPL v.2 or any later version.

## Credits

This plugin is published on behalf of the Brazilian Federal Police (SEGEO/DITEC/PF), under authorization of the institution, and is part of the Inteligeo initiative.

Official release authorized by the [Technical-Scientific Directorate of the Brazilian Federal Police (SEGEO/DITEC/PF)](https://www.gov.br/pf/pt-br/acesso-a-informacao/estatisticas/diretoria-tecnico-cientifica-ditec).
