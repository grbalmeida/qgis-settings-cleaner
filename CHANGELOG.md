# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-06-04
### Added
- New **settings selection dialog** allowing users to selectively reset specific QGIS configuration categories (Language, Proxy, CRS, etc.).
- New `CATEGORIES` dictionary to define logical groups of QGIS settings by prefix.
- `remove_settings_by_prefix()` method to programmatically clear settings by prefix.
- `show_settings_dialog()` UI with:
  - Grouped checkboxes for selecting settings categories.
  - Dual reset buttons: partial reset and full reset.
  - Styled disclaimer and layout improvements.
- `perform_cleanup()` method to handle partial reset logic.
- `remove_custom_qgis_crs()` method to delete user-defined CRS entries directly from the `qgis.db` database using SQLite.

### Changed
- The `initGui()` now connects to the new `show_settings_dialog()` method instead of calling `reset_qgis()` directly.
- Renamed and refactored `dialog_restart_qgis()` to `prompt_restart_qgis()` (with some duplicate code remaining for compatibility).
- Improved code documentation and docstrings throughout the file.
- Added minor UI styling to buttons and labels in the reset dialog.

### Fixed
- Better sync after removing keys in `remove_settings_by_prefix()` using `settings.sync()`.

## [1.0.0] - 2025-05-19
### Added
- Initial version of the plugin **QGISSettingsCleaner**.
- `reset_qgis()` method to perform a full QGIS settings wipe (language, proxies, CRS, database connections, services, etc.).
- Confirmation and restart dialogs after settings reset.
- Internationalization support via `QTranslator`.
- Plugin icon and integration with QGIS toolbar and menu.