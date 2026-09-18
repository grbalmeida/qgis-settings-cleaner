"""QGIS Settings Cleaner. Copyright (C) 2025-2026 SEGEO/DITEC/PF; GPL v2 or later."""


def classFactory(iface):
    from .qgis_settings_cleaner import QGISSettingsCleaner

    return QGISSettingsCleaner(iface)
