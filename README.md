# QGIS Settings Cleaner

A small QGIS plugin that **clears all QGIS settings**: it deletes everything QGIS keeps about
you and closes QGIS, which then starts as if it had just been installed.

Runs on QGIS 3.34+ and QGIS 4.

## What it does

QGIS keeps everything about *your* QGIS in one folder, the active user profile: settings
(language, proxy, CRS, ...), data source connections and their saved passwords, installed
plugins, user styles, spatial bookmarks, Processing models and scripts. The plugin deletes
everything in that folder, this plugin included, and closes QGIS. Only that folder is emptied;
project files and data are not touched.

Every installation of the same QGIS version on the computer shares that folder, so all of them
are affected. QGIS 3 and QGIS 4 keep separate folders, and the plugin only clears the one of
the QGIS it is running in.

When QGIS closes it writes a few things back (window layout, an empty bookmark list, the Python
console history), so the folder is left with only those; everything else starts from the defaults.

It is a quick way to get a machine back to a known state, for troubleshooting, testing new
versions, training rooms and shared workstations.

## Usage

1. In QGIS, click the broom on the **Plugins** toolbar, or open
   **Plugins → QGIS Settings Cleaner → Clear All QGIS Settings and Close...**
2. Read the confirmation: it says what is deleted and shows the folder that will be emptied.
   **Cancel** is the default; click **Clear Settings and Close QGIS** to go ahead.
3. If the current project has unsaved changes, QGIS asks whether to save it. Cancelling there
   cancels the cleanup too; nothing has been deleted yet.
4. QGIS closes. Open it again to start over.

While tasks run in the background (a Processing algorithm, a layer export), the plugin refuses
with a message and deletes nothing: QGIS would not close with them running. On QGIS 3 there is
one more case: an unsaved script in the Python console editor is only asked about when QGIS
exits, after the folder was emptied, and cancelling there leaves QGIS open on an empty folder.
QGIS 4 asks before, together with the project.

If some files could not be deleted (QGIS may still have them open), the plugin says so and
shows the folder to clean by hand before opening QGIS again; **Show Details** lists the files.

⚠️ There is no undo. If you only want to remove some connections or change one option, use
QGIS itself: right-click the connection in the Browser panel, or **Settings → Options**. To
start fresh *without* losing the current setup, use **Settings → User Profiles → New Profile**,
which leaves the current settings untouched in their own profile.

## Installation

From the [QGIS Plugin Repository](https://plugins.qgis.org/plugins/qgis_settings_cleaner/)
(**Plugins → Manage and Install Plugins...**), or by hand:

1. Download or clone this repository.
2. Copy the folder to the plugins folder of your profile, renamed to `qgis_settings_cleaner`. In
   QGIS, **Settings → User Profiles → Open Active Profile Folder** takes you there; the
   plugins live in `python/plugins/` inside it.
3. Restart QGIS and enable the plugin in **Plugins → Manage and Install Plugins...**

The first time the plugin loads it says, in the message bar, where to find it.

## Translations

The interface is in English and Portuguese (`i18n/QGISSettingsCleaner_pt.ts`), following the
QGIS locale setting. The compiled `.qm` is versioned so that a clone works as is. After changing
a string in the code, refresh the `.ts`, fill in the new translations and recompile:

```bash
pylupdate5 -noobsolete qgis_settings_cleaner.py -ts i18n/QGISSettingsCleaner_pt.ts
lrelease i18n/QGISSettingsCleaner_pt.ts
```

Both tools come with Qt 5 (`pyqt5-dev-tools` and `qttools5-dev-tools` on Debian/Ubuntu); the
`.qm` they produce also works on QGIS 4. The QGIS LTR container image has both, so from the
repository root:

```bash
podman run --rm -v "$PWD:/repo" -w /repo docker.io/qgis/qgis:ltr sh -c \
  "pylupdate5 -noobsolete qgis_settings_cleaner.py -ts i18n/QGISSettingsCleaner_pt.ts && \
   lrelease i18n/QGISSettingsCleaner_pt.ts"
```

## Compatibility

The plugin supports QGIS 3.34+ (Qt 5 / PyQt5) and QGIS 4 (Qt 6 / PyQt6) from the same code:

- Qt is imported through `qgis.PyQt`, never `PyQt5` or `PyQt6` directly (`ruff check` flags it).
- Enums use the scoped form (`QMessageBox.StandardButton.Cancel`), the only one PyQt6 has.
- Dialogs use `exec()`, not `exec_()`.
- The icon is read from disk; there is no `resources.qrc` (the `pyrcc5` output imports PyQt5).

## Tests

`test/test_clean.py` runs the plugin inside the QGIS Python, without a QGIS window, on a
throwaway profile. With the QGIS 4 Flatpak, from the repository root:

```bash
flatpak run --filesystem="$PWD:ro" --filesystem=/tmp --command=python3 org.qgis.qgis -c \
  "import sys; sys.path.insert(0, '/app/share/qgis/python'); sys.path.insert(0, 'test'); \
   import unittest; unittest.main(module=None, argv=['t', 'discover', '-s', 'test'])"
```

On QGIS 3 LTR, with the official container image:

```bash
podman run --rm -v "$PWD:/repo:ro" -w /repo -e QT_QPA_PLATFORM=offscreen \
  docker.io/qgis/qgis:ltr python3 -m unittest discover -s test
```

## Release

The zip for [plugins.qgis.org](https://plugins.qgis.org/plugins/qgis_settings_cleaner/) is a
`git archive` of the tag; `.gitattributes` keeps the tests and tooling out of it:

```bash
git archive --format=zip --prefix=qgis_settings_cleaner/ -o qgis_settings_cleaner-2.0.0.zip v2.0.0
```

## License

Copyright (C) 2025-2026 SEGEO/DITEC/PF. This program is licensed under the GNU GPL v2 or any
later version; see `LICENSE`.

## Credits

This plugin is part of the Inteligeo initiative and is published on behalf of SEGEO/DITEC, the
geoprocessing service of the [Technical-Scientific Directorate of the Brazilian Federal
Police](https://www.gov.br/pf/pt-br/acesso-a-informacao/estatisticas/diretoria-tecnico-cientifica-ditec),
with the authorization of the institution.
