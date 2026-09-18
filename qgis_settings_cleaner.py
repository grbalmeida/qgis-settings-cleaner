"""QGIS Settings Cleaner: deletes the active QGIS user profile and closes QGIS.

Copyright (C) 2025-2026 SEGEO/DITEC/PF
Author: Gilvan Ribeiro de Almeida

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
"""

import os
import shutil

from qgis.core import Qgis, QgsApplication, QgsMessageLog
from qgis.PyQt.QtCore import QCoreApplication, QObject, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

TAG = "QGIS Settings Cleaner"


class QGISSettingsCleaner(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.translator = None
        self.action = None
        self.load_translation()

    def load_translation(self):
        """Installs the plugin translation for the QGIS locale, when there is one."""

        locale = QSettings().value("locale/userLocale", "en")
        base_locale = locale.split("_")[0]

        filename = f"QGISSettingsCleaner_{base_locale}.qm"
        i18n_path = os.path.join(self.plugin_dir, "i18n", filename)

        if os.path.exists(i18n_path):
            self.translator = QTranslator()
            if self.translator.load(i18n_path):
                QCoreApplication.installTranslator(self.translator)

    def menu_title(self):
        return "&" + self.tr("QGIS Settings Cleaner")

    def initGui(self):
        icon = QIcon(os.path.join(self.plugin_dir, "icon.png"))
        self.action = QAction(
            icon,
            self.tr("Clean All Settings and Close QGIS..."),
            self.iface.mainWindow(),
        )
        self.action.triggered.connect(self.clean_settings)
        # Menu only: a one-click wipe does not belong on the toolbar.
        self.iface.addPluginToMenu(self.menu_title(), self.action)

    def unload(self):
        self.iface.removePluginMenu(self.menu_title(), self.action)
        self.action = None

    @staticmethod
    def profile_path():
        """Folder of the active user profile (QGIS3.ini, qgis.db, plugins, ...)."""

        return os.path.normpath(QgsApplication.qgisSettingsDirPath())

    def clean_settings(self):
        profile = self.profile_path()

        if not self.confirm(profile):
            QgsMessageLog.logMessage(
                self.tr("Operation cancelled by the user."),
                TAG,
                Qgis.MessageLevel.Info,
            )
            return

        leftovers = self.delete_profile(profile)
        if leftovers:
            self.warn_leftovers(profile)

        self.iface.actionExit().trigger()

    def confirm(self, profile):
        box = QMessageBox(self.iface.mainWindow())
        box.setWindowTitle(self.tr("Clean QGIS Settings"))
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(self.tr("Delete the active QGIS user profile and close QGIS?"))
        box.setInformativeText(
            self.tr(
                "The profile folder will be deleted:\n{}\n\n"
                "This removes every QGIS setting and everything else kept in the "
                "profile: data source connections and saved passwords, installed "
                "plugins, user styles, bookmarks, and Processing models and scripts. "
                "Your project and data files are not affected.\n\n"
                "QGIS will close. Open it again to start with a fresh profile. "
                "This cannot be undone."
            ).format(profile)
        )
        delete = box.addButton(
            self.tr("Delete Profile and Close QGIS"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel = box.addButton(QMessageBox.StandardButton.Cancel)
        # Enter and Esc both cancel; the wipe takes a deliberate click.
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        return box.clickedButton() is delete

    def delete_profile(self, profile):
        """Deletes the profile folder and returns the paths it could not remove."""

        leftovers = []

        def on_error(function, path, exc_info):
            QgsMessageLog.logMessage(
                self.tr("Could not delete: ") + path, TAG, Qgis.MessageLevel.Warning
            )
            leftovers.append(path)

        QgsMessageLog.logMessage(
            self.tr("Deleting the QGIS user profile: ") + profile,
            TAG,
            Qgis.MessageLevel.Info,
        )

        # Also drop the in-memory copy, or QGIS writes the old values back on exit.
        settings = QSettings()
        settings.clear()
        settings.sync()

        if os.path.isdir(profile):
            shutil.rmtree(profile, onerror=on_error)

        return leftovers

    def warn_leftovers(self, profile):
        box = QMessageBox(self.iface.mainWindow())
        box.setWindowTitle(self.tr("Clean QGIS Settings"))
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(self.tr("Some files could not be deleted."))
        box.setInformativeText(
            self.tr(
                "They are probably still open by QGIS. QGIS will close now; "
                "delete this folder by hand before opening QGIS again:\n{}\n\n"
                'The files are listed in the QGIS log, under "{}".'
            ).format(profile, TAG)
        )
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()
