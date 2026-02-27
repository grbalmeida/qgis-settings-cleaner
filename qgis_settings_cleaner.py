import os
import shutil
import sqlite3

from PyQt5.QtCore import QCoreApplication, QObject, QSettings, Qt, QTranslator
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QDialog,
    QFrame,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
)
from qgis.core import Qgis, QgsApplication, QgsMessageLog
from qgis.utils import iface

from . import resources_rc

resources_rc.qInitResources()

CATEGORIES = {
    "Language": ["locale"],
    "Proxy": ["proxy", "network/network-timeout", "qgis/networkAndProxy"],
    "CRS": ["qgis/coordinate-reference-system", "CRS"],
    "Database": [
        "connections/pgsql",
        "postgresql/connections",
        "connections/postgis",
        "connections/oracle",
        "oracle/connections",
        "connections/spatialite",
        "spatiaLite/connections",
        "providers/ogr/GPKG/connections",
        "mssql/connections",
        "hana/connections",
    ],
    "WFS/WMS": [
        "connections-wms",
        "qgis/connections-wms",
        "connections/ows/items/wms",
        "qgis/connections/wms",
        "connections-wfs",
        "qgis/connections-wfs",
        "connections/ows/items/wfs",
        "qgis/connections/wfs",
    ],
    "XYZ Tiles": ["connections/xyz", "qgis/connections-xyz"],
}

TAG = "QGIS Settings Cleaner"


class QGISSettingsCleaner(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.translator = None
        self.load_translation()
        self.action = None

    def load_translation(self):
        """
        Loads the plugin translation file based on the user's locale setting.

        If a corresponding .qm file exists in the i18n directory, it is loaded and
        installed using QTranslator to localize the plugin interface.
        """

        locale = QSettings().value("locale/userLocale", "en")
        base_locale = locale.split("_")[0]

        filename = f"QGISSettingsCleaner_{base_locale}.qm"
        i18n_path = os.path.join(self.plugin_dir, "i18n", filename)

        if os.path.exists(i18n_path):
            self.translator = QTranslator()
            if self.translator.load(i18n_path):
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path)
        self.action = QAction(
            icon, self.tr("Clean QGIS Settings"), self.iface.mainWindow()
        )
        self.action.triggered.connect(self.show_settings_dialog)
        self.iface.addPluginToMenu("&" + self.tr("Clean QGIS"), self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&" + self.tr("Clean QGIS"), self.action)
        self.iface.removeToolBarIcon(self.action)

    def remove_settings_by_prefix(self, prefix):
        """
        Removes all QGIS settings whose keys start with the given prefix.

        Returns a list of the removed keys.
        """

        settings = QSettings()
        keys = settings.allKeys()
        deleted = []

        for key in keys:
            if key.lower().startswith(prefix.lower()):
                settings.remove(key)
                deleted.append(key)

        settings.sync()
        return deleted

    def show_settings_dialog(self):
        """
        Displays a dialog for the user to select which QGIS settings to clean.
        Provides options for selective or full clean with explanatory disclaimer.
        """
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle(self.tr("Select Settings to Clean"))
        dialog.setStyleSheet("font-family: 'Sans Serif'; font-size: 13px;")
        dialog.setWindowIcon(QIcon(os.path.join(self.plugin_dir, "icon.png")))
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        title = QLabel(self.tr("Choose which settings you want to clean:"))
        title.setStyleSheet("font-weight: bold; font-size: 15px; margin-bottom: 10px;")
        layout.addWidget(title)
        layout.addSpacing(10)

        group_box = QGroupBox(self.tr("Settings Categories"))
        group_box.setStyleSheet("font-weight: bold; font-size: 13px;")
        group_layout = QVBoxLayout()
        checkboxes = {}

        for name in CATEGORIES:
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 13px;")
            group_layout.addWidget(cb)
            checkboxes[name] = cb

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        layout.addSpacing(20)

        btn_reset_selected = QPushButton(self.tr("Clean Selected Settings"))
        btn_reset_selected.setStyleSheet("""
            background-color: #f0f0f0;
            padding: 8px;
            font-size: 13px;
        """)
        btn_reset_selected.clicked.connect(
            lambda: self.perform_cleanup(dialog, checkboxes)
        )
        layout.addWidget(btn_reset_selected, alignment=Qt.AlignCenter)

        layout.addSpacing(15)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addSpacing(15)

        btn_reset_all = QPushButton(self.tr("Clean All Settings (Full Clean)"))
        btn_reset_all.setStyleSheet("""
            background-color: #dc3545;
            color: white;
            font-weight: bold;
            padding: 10px;
            font-size: 13px;
        """)
        btn_reset_all.clicked.connect(lambda: self.reset_qgis())
        layout.addWidget(btn_reset_all, alignment=Qt.AlignCenter)

        disclaimer = QLabel(
            self.tr(
                "Note: The first button removes only the selected configuration categories.\n\n"
                "The second button removes all QGIS settings, including additional internal preferences."
            )
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("font-size: 12px; color: #222222; margin-top: 10px;")
        layout.addWidget(disclaimer, alignment=Qt.AlignCenter)

        layout.addSpacerItem(
            QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        dialog.setLayout(layout)
        dialog.exec_()

    def perform_cleanup(self, dialog, checkboxes):
        """
        Cleans selected QGIS settings based on checked categories.

        Removes settings by prefix and clears custom CRS if selected.
        Prompts user confirmation and restart after cleanup.
        """

        confirm = QMessageBox.question(
            dialog,
            self.tr("Confirm"),
            self.tr("Are you sure you want to clean the selected QGIS settings?"),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        for name, checkbox in checkboxes.items():
            if checkbox.isChecked():
                for prefix in CATEGORIES[name]:
                    self.remove_settings_by_prefix(prefix)

                if name == "CRS":
                    self.remove_custom_qgis_crs()

        QMessageBox.information(
            dialog,
            self.tr("Done"),
            self.tr("Selected settings have been cleared. Please restart QGIS."),
        )

        self.dialog_close_qgis(True)

    def dialog_confirm(self, msg):
        res = QMessageBox.question(
            self.iface.mainWindow(),
            self.tr("Confirm"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        return res == QMessageBox.Yes

    def dialog_close_qgis(self, success):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information if success else QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Close | QMessageBox.Cancel)

        if success:
            msg.setText(self.tr("Settings cleared successfully."))
        else:
            msg.setText(self.tr("Some files could not be deleted."))

        if success:
            msg.setInformativeText(
                self.tr(
                    "Click Close to exit QGIS. You will need to reopen it manually."
                )
            )
        else:
            msg.setInformativeText(
                self.tr(
                    "Close QGIS and manually delete the remaining configuration files."
                )
            )

        msg.setWindowTitle(self.tr("Close QGIS"))
        btn = msg.exec_()

        if btn == QMessageBox.Close:
            iface.actionExit().trigger()

    def reset_qgis(self):
        msg = self.tr(
            """Are you sure you want to clear all QGIS settings? The following will be removed:

- Language settings
- Proxy settings
- CRS (Coordinate Reference System) settings
- Database connection settings
- WFS and WMS service settings
- XYZ tile settings
- ALL other QGIS settings on this machine

This action is irreversible. Do you want to continue?"""
        )

        if not self.dialog_confirm(msg):
            QgsMessageLog.logMessage(
                self.tr("Operation cancelled by the user."), TAG, Qgis.Info
            )
            return

        fp = os.path.realpath(QgsApplication.qgisUserDatabaseFilePath())
        problem_files = []

        QgsMessageLog.logMessage(
            self.tr("Clearing QGIS settings stored in the system configuration."),
            TAG,
            Qgis.Info,
        )

        s = QSettings()
        s.clear()

        def errorfunc(x, y, z):
            QgsMessageLog.logMessage(self.tr("Error deleting: ") + y, TAG, Qgis.Warning)
            problem_files.append(y)

        if os.path.isfile(fp):
            rp = fp.rsplit(os.sep, 1)[0]
            QgsMessageLog.logMessage(
                self.tr("Deleting QGIS user configuration folder: ") + rp,
                TAG,
                Qgis.Info,
            )
            shutil.rmtree(rp, ignore_errors=False, onerror=errorfunc)

        self.dialog_close_qgis(len(problem_files) == 0)

    def remove_custom_qgis_crs(self):
        """
        Remove all custom coordinate reference systems (CRS) from the active QGIS profile.

        Custom CRS entries are those without an authority name (e.g., user-defined).
        This function accesses the QGIS user database (qgis.db) and deletes all such CRS entries.

        Note:
            This action is irreversible and should be used with caution. It modifies the qgis.db file directly.

        Raises:
            sqlite3.DatabaseError: If there is an issue accessing or modifying the database.
        """
        db_path = QgsApplication.qgisUserDatabaseFilePath()

        if not os.path.exists(db_path):
            return

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        try:
            cur.execute("DELETE FROM tbl_srs WHERE auth_name IS NULL")
            conn.commit()
        finally:
            conn.close()
