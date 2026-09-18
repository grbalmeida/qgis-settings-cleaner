"""Runs the plugin inside the QGIS Python, without a QGIS window, on a throwaway profile.

QGIS_CUSTOM_CONFIG_PATH must be set before QgsApplication starts, so it is set here,
on import, and the profile lives under a temporary folder for the whole process.
"""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CONFIG_ROOT = tempfile.mkdtemp(prefix="qgis-settings-cleaner-test-")
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = CONFIG_ROOT
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgis.core import QgsApplication  # noqa: E402
from qgis.PyQt.QtCore import QObject, QSettings  # noqa: E402
from qgis.PyQt.QtWidgets import QAction, QMainWindow, QMessageBox  # noqa: E402

from qgis_settings_cleaner import QGISSettingsCleaner  # noqa: E402

APP = QgsApplication([], True)
APP.initQgis()


class FakeIface(QObject):
    """The part of QgisInterface the plugin touches."""

    def __init__(self):
        super().__init__()
        self._main = QMainWindow()
        self.exit_action = QAction(self._main)
        self.exit_triggered = 0
        self.exit_action.triggered.connect(self._count_exit)
        self.menus = []

    def _count_exit(self):
        self.exit_triggered += 1

    def mainWindow(self):
        return self._main

    def actionExit(self):
        return self.exit_action

    def addPluginToMenu(self, menu, action):
        self.menus.append((menu, action))

    def removePluginMenu(self, menu, action):
        self.menus.remove((menu, action))


class CleanTest(unittest.TestCase):
    def setUp(self):
        self.profile = QGISSettingsCleaner.profile_path()
        self.assertTrue(self.profile.startswith(CONFIG_ROOT), self.profile)
        shutil.rmtree(self.profile, ignore_errors=True)
        os.makedirs(os.path.join(self.profile, "python", "plugins"))
        for name in ("qgis.db", "qgis-auth.db", "symbology-style.db"):
            with open(os.path.join(self.profile, name), "w") as f:
                f.write("x")
        settings = QSettings()
        settings.setValue("locale/userLocale", "pt_BR")
        settings.setValue("proxy/proxyEnabled", True)
        settings.sync()
        self.assertTrue(os.path.isfile(settings.fileName()))

        self.iface = FakeIface()
        self.plugin = QGISSettingsCleaner(self.iface)
        self.plugin.initGui()

    def tearDown(self):
        self.plugin.unload()

    def test_menu_only_no_toolbar(self):
        self.assertEqual(len(self.iface.menus), 1)
        self.assertFalse(hasattr(self.iface, "addToolBarIcon"))

    def test_portuguese_translation_is_loaded(self):
        self.assertEqual(
            self.plugin.action.text(),
            "Limpar Todas as Configurações e Fechar o QGIS...",
        )

    def test_cancel_keeps_everything(self):
        self.plugin.confirm = lambda profile: False
        self.plugin.clean_settings()
        self.assertTrue(os.path.isfile(os.path.join(self.profile, "qgis.db")))
        self.assertEqual(QSettings().value("locale/userLocale"), "pt_BR")
        self.assertEqual(self.iface.exit_triggered, 0)

    def test_confirm_deletes_profile_and_exits(self):
        self.plugin.confirm = lambda profile: True
        self.plugin.clean_settings()
        self.assertFalse(os.path.exists(self.profile))
        self.assertEqual(QSettings().allKeys(), [])
        self.assertEqual(self.iface.exit_triggered, 1)

    def test_leftovers_are_reported_and_qgis_still_closes(self):
        # Stands in for the databases QGIS keeps open on Windows.
        busy = os.path.join(self.profile, "busy.db")
        with open(busy, "w") as f:
            f.write("x")
        real_unlink = os.unlink

        def unlink(path, *args, **kwargs):
            if os.path.basename(path) == "busy.db":
                raise PermissionError(13, "in use", path)
            return real_unlink(path, *args, **kwargs)

        warned = []
        self.plugin.confirm = lambda profile: True
        self.plugin.warn_leftovers = lambda profile: warned.append(profile)
        with mock.patch("os.unlink", unlink):
            self.plugin.clean_settings()

        self.assertEqual(warned, [self.profile])
        self.assertTrue(os.path.isfile(busy))
        self.assertFalse(os.path.exists(os.path.join(self.profile, "qgis.db")))
        self.assertEqual(self.iface.exit_triggered, 1)

    def test_confirm_dialog_defaults_to_cancel(self):
        shown = []
        QMessageBox.exec = lambda box: shown.append(box)
        self.addCleanup(delattr, QMessageBox, "exec")

        self.assertFalse(self.plugin.confirm(self.profile))
        box = shown[0]
        cancel = box.defaultButton()
        self.assertEqual(box.buttonRole(cancel), QMessageBox.ButtonRole.RejectRole)
        self.assertIs(box.escapeButton(), cancel)
        roles = {box.buttonRole(b) for b in box.buttons()}
        self.assertIn(QMessageBox.ButtonRole.DestructiveRole, roles)
        self.assertIn(self.profile, box.informativeText())


if __name__ == "__main__":
    unittest.main()
