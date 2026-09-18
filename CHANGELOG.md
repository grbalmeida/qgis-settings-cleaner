# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-09-18

### Changed

- **Selective cleanup by category was removed** (issue #1). It matched setting keys by prefix, and the prefixes drift between QGIS releases (QGIS 4 moved the GeoPackage connections, for one), so the plugin reported success without cleaning everything. QGIS covers that case natively: remove a connection from the Browser panel, change an option in **Settings → Options**, or start fresh with **Settings → User Profiles → New Profile**.
- The plugin now does one thing: resets the active user profile and closes QGIS. The menu entry is **Reset User Profile and Close QGIS...**.
- The confirmation dialog shows the folder that will be emptied and lists what is in it (settings, saved passwords, plugins — this one included —, styles, bookmarks, Processing models). **Cancel** is the default button; Enter no longer confirms the deletion.
- The current project is closed before anything is deleted, so QGIS asks about unsaved changes first and cancelling there keeps the profile. Before, the profile was already gone when QGIS asked, and cancelling left QGIS running without one. For the same reason the plugin refuses to run while background tasks are active.
- After a successful cleanup QGIS closes right away, without a second dialog. When some files could not be deleted, the message shows the folder to clean by hand and lists the files under **Show Details**.
- The toolbar button was removed; the plugin lives in **Plugins → QGIS Settings Cleaner**.
- All messages are translated to Portuguese, with the words QGIS itself uses (perfil, complementos, favoritos espaciais), and the compiled `.qm` is versioned so a clone of the repository works as is.

### Added

- QGIS 4 (Qt 6 / PyQt6) support, keeping QGIS 3.34+: `qgis.PyQt` imports, scoped enums, `exec()`, `qgisMaximumVersion=4.99`.
- A test suite that runs on the QGIS Python of both versions (see README, "Tests").

### Removed

- `resources.qrc`: the icon is read from disk. The generated `resources_rc.py` imported PyQt5 and was not versioned, so a clone did not load.

## [1.1.0] - 2026-02-27

### Added

- New **settings selection dialog** allowing users to selectively clean specific QGIS configuration categories (Language, Proxy, CRS, etc.).
- New `CATEGORIES` dictionary to define logical groups of QGIS settings by prefix.
- `remove_settings_by_prefix()` method to programmatically clear settings by prefix.
- `show_settings_dialog()` UI with:
  - Grouped checkboxes for selecting settings categories.
  - Two action buttons: selective clean and full clean.
  - Styled disclaimer and layout improvements.
- `perform_cleanup()` method to handle selective clean logic.
- `remove_custom_qgis_crs()` method to delete user-defined CRS entries directly from the `qgis.db` database using SQLite.

### Changed

- Renamed plugin menu from "Reset QGIS" to "Clean QGIS" for accuracy (the plugin clears settings, it doesn't reset them to defaults).
- Revised all user-facing strings for clarity and consistency ("Reset/Delete" → "Clean/Clear").
- Used proper terminology: "CRS (Coordinate Reference System)" instead of "CRS and coordinate system".
- Removed platform-specific details from user-facing messages.
- Replaced invisible `QTextBrowser` logging with `QgsMessageLog`.
- Merged duplicate `dialog_restart_qgis()`/`prompt_restart_qgis()` into a single `dialog_close_qgis()` method using `QMessageBox.Close`.
- The `initGui()` now connects to the new `show_settings_dialog()` method instead of calling `reset_qgis()` directly.
- Updated Portuguese translations to match all revised English strings.
- Updated `metadata.txt` and `README.md` descriptions.

### Fixed

- Better sync after removing keys in `remove_settings_by_prefix()` using `settings.sync()`.
- Removed stale `<location>` tags from the `.ts` translation file.

## [1.0.0] - 2025-05-19

### Added

- Initial version of the plugin **QGISSettingsCleaner**.
- `reset_qgis()` method to perform a full QGIS settings wipe (language, proxies, CRS, database connections, services, etc.).
- Confirmation and restart dialogs after cleanup.
- Internationalization support via `QTranslator`.
- Plugin icon and integration with QGIS toolbar and menu.
