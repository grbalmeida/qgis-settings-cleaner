import os
import shutil
from PyQt5.QtWidgets import QAction, QMessageBox, QTextBrowser
from PyQt5.QtCore import QObject, QSettings, QTranslator, QCoreApplication, QLocale
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon
from qgis.core import QgsApplication
from qgis.utils import iface
from . import resources_rc

resources_rc.qInitResources()

class QGISSettingsCleaner(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.translator = None
        self.load_translation()
        self.action = None

    def load_translation(self):
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
        self.action.triggered.connect(self.reset_qgis)
        self.iface.addPluginToMenu("&" + self.tr("Reset QGIS"), self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&" + self.tr("Reset QGIS"), self.action)
        self.iface.removeToolBarIcon(self.action)

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
