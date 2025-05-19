def classFactory(iface):
    from .qgis_settings_cleaner import QGISSettingsCleaner
    return QGISSettingsCleaner(iface)