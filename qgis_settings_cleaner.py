"""QGIS Settings Cleaner: empties the active QGIS user profile and closes QGIS.

Copyright (C) 2025-2026 SEGEO/DITEC/PF
Author: Gilvan Ribeiro de Almeida

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
"""

import os
import shutil

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, QObject, QSettings, QTranslator
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

NAME = "QGIS Settings Cleaner"


class QGISSettingsCleaner(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        # Kept as an attribute: Qt only borrows the translator, and a dropped
        # reference would garbage-collect it.
        self.translator = QTranslator()
        self.load_translation()

    def load_translation(self):
        language = QSettings().value("locale/userLocale", "en").split("_")[0]
        filename = os.path.join(
            self.plugin_dir, "i18n", f"QGISSettingsCleaner_{language}.qm"
        )
        if self.translator.load(filename):
            QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self.action = QAction(
            QIcon(os.path.join(self.plugin_dir, "icon.png")),
            self.tr("Delete User Profile and Close QGIS..."),
            self.iface.mainWindow(),
        )
        self.action.triggered.connect(self.clean_settings)
        # Menu only: a one-click wipe does not belong on the toolbar.
        self.iface.addPluginToMenu("&" + NAME, self.action)

    def unload(self):
        self.iface.removePluginMenu("&" + NAME, self.action)
        QCoreApplication.removeTranslator(self.translator)

    @staticmethod
    def profile_path():
        """Folder of the active user profile, without the trailing separator QGIS adds."""

        return os.path.normpath(QgsApplication.qgisSettingsDirPath())

    def clean_settings(self):
        profile = self.profile_path()

        if not self.confirm(profile):
            return

        # Closing the project first lets QGIS ask about unsaved changes while
        # cancelling still saves everything; it also releases the files that
        # open layers hold.
        if not self.iface.newProject(True):
            return

        leftovers = self.empty_profile(profile)
        if leftovers:
            self.warn_leftovers(profile, leftovers)

        self.iface.actionExit().trigger()

    def confirm(self, profile):
        box = QMessageBox(self.iface.mainWindow())
        box.setWindowTitle(NAME)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(self.tr("Delete the active QGIS user profile and close QGIS?"))
        box.setInformativeText(
            self.tr(
                "Everything in this folder will be deleted:\n{}\n\n"
                "That is every QGIS setting and everything else kept in the "
                "profile: data source connections and saved passwords, installed "
                "plugins (this one included), user styles, spatial bookmarks, and "
                "Processing models and scripts. Project and data files are not "
                "affected.\n\n"
                "If the current project has unsaved changes, QGIS asks whether to "
                "save it; then QGIS closes. Open it again to start with a fresh "
                "profile. This cannot be undone."
            ).format(profile)
        )
        delete = box.addButton(
            self.tr("Delete Profile and Close QGIS"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        # Enter cancels; the wipe takes a deliberate click.
        box.setDefaultButton(box.addButton(QMessageBox.StandardButton.Cancel))
        box.exec()
        return box.clickedButton() is delete

    @staticmethod
    def empty_profile(profile):
        """Deletes what the profile folder holds; returns (path, reason) for what it could not.

        The folder itself stays, so a profile that is a symbolic link keeps
        pointing where it did.
        """

        leftovers = []

        def on_error(function, path, exc_info):
            leftovers.append((path, str(exc_info[1])))

        if not os.path.isdir(profile):
            return leftovers
        for entry in os.scandir(profile):
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, onerror=on_error)
            else:
                try:
                    os.unlink(entry.path)
                except OSError as error:
                    leftovers.append((entry.path, str(error)))

        return leftovers

    def warn_leftovers(self, profile, leftovers):
        box = QMessageBox(self.iface.mainWindow())
        box.setWindowTitle(NAME)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(self.tr("Some files could not be deleted."))
        box.setInformativeText(
            self.tr(
                "They are probably still in use. QGIS will close now; before "
                "opening it again, delete what is left in this folder by hand:\n{}\n\n"
                "The files are listed under Show Details."
            ).format(profile)
        )
        box.setDetailedText(
            "\n".join(f"{path}: {reason}" for path, reason in leftovers)
        )
        box.exec()
