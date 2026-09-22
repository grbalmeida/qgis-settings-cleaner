"""QGIS Settings Cleaner: clears every QGIS setting and closes QGIS.

Copyright (C) 2025-2026 SEGEO/DITEC/PF
Author: Gilvan Ribeiro de Almeida

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.
"""

import os
import shutil

from qgis.core import Qgis, QgsApplication, QgsTask
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QObject,
    QSettings,
    QTimer,
    QTranslator,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

NAME = "QGIS Settings Cleaner"
HINT_SETTING = "plugins/qgis_settings_cleaner/where_to_find_shown"
HINT_DELAY_MS = 5000


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
            self.tr("Clear All QGIS Settings and Close..."),
            self.iface.mainWindow(),
        )
        self.action.triggered.connect(self.clean_settings)
        self.iface.addPluginToMenu("&" + NAME, self.action)
        self.iface.addToolBarIcon(self.action)
        self.show_where_to_find()

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&" + NAME, self.action)
        QCoreApplication.removeTranslator(self.translator)

    def show_where_to_find(self):
        """Says where the plugin is, once: a menu entry is easy to miss.

        The flag lives in the settings this plugin deletes, so the message
        comes back for whoever installs it again. The wait lets the messages
        other plugins push while QGIS starts come first, so this one is the
        one on top; the flag is only set once the message is really shown.
        """

        if QSettings().value(HINT_SETTING, False, type=bool):
            return
        QTimer.singleShot(HINT_DELAY_MS, self.push_where_to_find)

    def push_where_to_find(self):
        QSettings().setValue(HINT_SETTING, True)
        # No timeout: the message is shown once, and it waits to be read.
        self.iface.messageBar().pushMessage(
            NAME,
            self.tr(
                "Installed. It is the broom on the Plugins toolbar, and it is "
                "in the Plugins menu."
            ),
            Qgis.MessageLevel.Info,
            0,
        )

    @staticmethod
    def settings_path():
        """Folder QGIS keeps its settings in, without the trailing separator QGIS adds."""

        return os.path.normpath(QgsApplication.qgisSettingsDirPath())

    def clean_settings(self):
        # QGIS refuses to exit while such tasks run, so it would stay open on
        # an emptied folder; refusing here keeps everything in place. (Tasks
        # flagged CancelWithoutPrompt, like the news feed, QGIS cancels itself.)
        tasks = QgsApplication.taskManager().activeTasks()
        if any(not (task.flags() & QgsTask.Flag.CancelWithoutPrompt) for task in tasks):
            self.warn(
                self.tr("QGIS is still running tasks in the background."),
                self.tr(
                    "Wait for them to finish, or cancel them in the status bar, "
                    "and try again. Nothing was deleted."
                ),
            )
            return

        folder = self.settings_path()
        if not self.confirm(folder):
            return

        # Closing the project first lets QGIS ask about unsaved changes while
        # cancelling still saves everything; it also releases the files that
        # open layers hold.
        if not self.iface.newProject(True):
            return

        leftovers = self.empty_folder(folder)
        if leftovers:
            self.warn_leftovers(folder, leftovers)

        self.iface.actionExit().trigger()

    def confirm(self, folder):
        box = QMessageBox(self.iface.mainWindow())
        box.setWindowTitle(NAME)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(self.tr("Clear all QGIS settings and close QGIS?"))
        box.setInformativeText(
            self.tr(
                "QGIS will go back to the state it had right after installation. "
                "This deletes everything QGIS keeps about you: settings and "
                "options, data source connections and saved passwords, installed "
                "plugins (this one included), styles, spatial bookmarks, and "
                "Processing models and scripts.\n\n"
                "This applies to every installation of this QGIS version on this "
                "computer, because they share these files. Your projects and data "
                "files are not affected.\n\n"
                "This cannot be undone. If the current project has unsaved "
                "changes, QGIS asks about them first; then QGIS closes. Open it "
                "again to start over.\n\n"
                "Folder that will be emptied:\n{}"
            ).format(folder)
        )
        clear = box.addButton(
            self.tr("Clear Settings and Close QGIS"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        # Enter cancels; the deletion takes a deliberate click.
        box.setDefaultButton(box.addButton(QMessageBox.StandardButton.Cancel))
        box.exec()
        return box.clickedButton() is clear

    @staticmethod
    def empty_folder(folder):
        """Deletes what the settings folder holds; returns (path, reason) for what it could not.

        The folder itself stays, so a folder that is a symbolic link keeps
        pointing where it did.
        """

        leftovers = []

        def on_error(function, path, exc_info):
            leftovers.append((path, exc_info[1].strerror))

        for entry in os.scandir(folder):
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, onerror=on_error)
            else:
                try:
                    os.unlink(entry.path)
                except OSError as error:
                    leftovers.append((entry.path, error.strerror))

        return leftovers

    def warn_leftovers(self, folder, leftovers):
        self.warn(
            self.tr("Some files could not be deleted."),
            self.tr(
                "They are probably still in use. QGIS will close now; before "
                "opening it again, delete what is left in this folder by hand:\n{}\n\n"
                "The files are listed under Show Details."
            ).format(folder),
            "\n".join(f"{path}: {reason}" for path, reason in leftovers),
        )

    def warn(self, text, informative, details=""):
        box = QMessageBox(self.iface.mainWindow())
        box.setWindowTitle(NAME)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(text)
        box.setInformativeText(informative)
        box.setDetailedText(details)
        box.exec()
