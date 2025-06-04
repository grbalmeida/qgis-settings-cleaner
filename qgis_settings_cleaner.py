import os
import shutil
from PyQt5.QtWidgets import (
    QAction, QDialog, QVBoxLayout, QCheckBox, QPushButton, QMessageBox, QTextBrowser,
    QLabel, QSpacerItem, QSizePolicy, QGroupBox, QHBoxLayout, QFrame
)
from PyQt5.QtCore import QObject, QSettings, QTranslator, QCoreApplication, Qt
from PyQt5.QtGui import QIcon
from qgis.core import QgsApplication
from qgis.utils import iface
import sqlite3
from . import resources_rc

resources_rc.qInitResources()

CATEGORIES = {
    "Language": [
        "locale"
    ],
    "Proxy": [
        "proxy",
        "network/network-timeout",
        "qgis/networkAndProxy"
    ],
    "CRS": [
        "qgis/coordinate-reference-system",
        "CRS"
    ],
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
        "qgis/connections/wfs"
    ],
    "XYZ Tiles": [
        "connections/xyz",
        "qgis/connections-xyz"
    ]
}

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
        base_locale = locale.split('_')[0]

        filename = f"QGISSettingsCleaner_{base_locale}.qm"
        i18n_path = os.path.join(self.plugin_dir, 'i18n', filename)

        if os.path.exists(i18n_path):
            self.translator = QTranslator()
            if self.translator.load(i18n_path):
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        icon = QIcon(icon_path)
        self.action = QAction(icon, self.tr("Reset QGIS Settings"), self.iface.mainWindow())
        self.action.triggered.connect(self.show_settings_dialog)
        self.iface.addPluginToMenu("&" + self.tr("Reset QGIS"), self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&" + self.tr("Reset QGIS"), self.action)
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
        Displays a dialog for the user to select which QGIS settings to reset.
        Provides options for selective or full reset with explanatory disclaimer.
        """
        dialog = QDialog(self.iface.mainWindow())
        dialog.setWindowTitle(self.tr("Select Settings to Reset"))
        dialog.setStyleSheet("font-family: 'Sans Serif'; font-size: 13px;")
        dialog.setWindowIcon(QIcon(os.path.join(self.plugin_dir, "icon.png")))
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()

        title = QLabel(self.tr("Choose which settings you want to reset:"))
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

        btn_reset_selected = QPushButton(self.tr("Reset Selected Settings"))
        btn_reset_selected.setStyleSheet("""
            background-color: #f0f0f0;
            padding: 8px;
            font-size: 13px;
        """)
        btn_reset_selected.clicked.connect(lambda: self.perform_cleanup(dialog, checkboxes))
        layout.addWidget(btn_reset_selected, alignment=Qt.AlignCenter)

        layout.addSpacing(15)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addSpacing(15)

        btn_reset_all = QPushButton(self.tr("Reset All Settings (Full Reset)"))
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
        self.tr("Note: The first button removes only the selected configuration categories.\n\n"
                "The second button removes *all* QGIS settings, including additional internal preferences.")
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("font-size: 12px; color: #222222; margin-top: 10px;")
        layout.addWidget(disclaimer, alignment=Qt.AlignCenter)

        layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        dialog.setLayout(layout)
        dialog.exec_()

    def perform_cleanup(self, dialog, checkboxes):
        """
        Resets selected QGIS settings based on checked categories.

        Removes settings by prefix and clears custom CRS if selected.
        Prompts user confirmation and restart after cleanup.
        """
        
        confirm = QMessageBox.question(
            dialog,
            self.tr("Confirm Deletion"),
            self.tr("Are you sure you want to reset the selected QGIS settings?"),
            QMessageBox.Yes | QMessageBox.No
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
            self.tr("Selected settings have been reset. Please restart QGIS."))

        self.prompt_restart_qgis()

    def dialog_confirm(self, msg):
        res = QMessageBox.question(
            self.iface.mainWindow(),
            self.tr("Confirm"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        return res == QMessageBox.Yes

    def dialog_restart_qgis(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setText(self.tr("Operation completed successfully."))
        msg.setInformativeText(self.tr(
            "Click OK to close QGIS now. You must restart the application manually afterward."
        ))
        msg.setWindowTitle(self.tr("Restart QGIS"))
        btn = msg.exec_()

        if btn == QMessageBox.Ok:
            iface.actionExit().trigger()

    def prompt_restart_qgis(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setText(self.tr("Operation completed successfully."))
        msg.setInformativeText(self.tr(
            "Click OK to close QGIS now. You must restart the application manually afterward."
        ))
        msg.setWindowTitle(self.tr("Restart QGIS"))
        btn = msg.exec_()

        if btn == QMessageBox.Ok:
            iface.actionExit().trigger()

    def reset_qgis(self):
        plugin_text = QTextBrowser()
        msg = self.tr(
            """Are you sure you want to delete all QGIS settings? The following will be removed:

- Language settings
- Proxy settings
- CRS and coordinate system settings
- Database connection settings
- WFS and WMS service settings
- XYZ tile service settings
- ALL other QGIS settings on this machine

This operation cannot be undone. Do you want to continue?"""
        )

        if not self.dialog_confirm(msg):
            plugin_text.append(self.tr("The operation was cancelled by the user."))
            return

        fp = os.path.realpath(QgsApplication.qgisUserDatabaseFilePath())
        problem_files = []

        plugin_text.append(self.tr(
            "Removing QGIS settings stored in the Windows registry or ~/.config directory on Linux."
        ))

        s = QSettings()
        s.clear()

        def errorfunc(x, y, z):
            plugin_text.append(self.tr("Error deleting: ") + y)
            problem_files.append(y)

        if os.path.isfile(fp):
            rp = fp.rsplit(os.sep, 1)[0]
            plugin_text.append(self.tr("Deleting QGIS user configuration folder: ") + rp)
            shutil.rmtree(rp, ignore_errors=False, onerror=errorfunc)

            if len(problem_files) == 0:
                plugin_text.append(self.tr("Settings deleted. Please restart QGIS."))
            else:
                plugin_text.append(
                    self.tr("Some files could not be deleted. Close QGIS and delete the folder manually: ")
                    + rp
                )

        self.dialog_restart_qgis()

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