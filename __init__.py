"""QGIS Settings Cleaner: deletes the active QGIS user profile and closes QGIS.

Copyright (C) 2025-2026 SEGEO/DITEC/PF
Author: Gilvan Ribeiro de Almeida

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
"""


def classFactory(iface):
    from .qgis_settings_cleaner import QGISSettingsCleaner

    return QGISSettingsCleaner(iface)
