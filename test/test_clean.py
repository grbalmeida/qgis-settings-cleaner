"""Runs the plugin inside the QGIS Python, without a QGIS window, on a throwaway profile.

QGIS_CUSTOM_CONFIG_PATH must be set before QgsApplication starts, so it is set here,
on import, and the profiles live under a temporary folder for the whole process.
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
    """The part of QgisInterface the plugin touches, recording what happens when."""

    def __init__(self, profile):
        super().__init__()
        self.profile = profile
        self.close_project = True
        self.events = []
        self._main = QMainWindow()
        self.exit_action = QAction(self._main)
        self.exit_action.triggered.connect(self._exit)
        self.menus = []

    def _contents(self):
        return sorted(os.listdir(self.profile)) if os.path.isdir(self.profile) else None

    def _exit(self):
        self.events.append(("exit", self._contents()))

    def mainWindow(self):
        return self._main

    def newProject(self, prompt):
        self.events.append(("newProject", prompt, self._contents()))
        return self.close_project

    def actionExit(self):
        return self.exit_action

    def addPluginToMenu(self, menu, action):
        self.menus.append((menu, action))

    def removePluginMenu(self, menu, action):
        self.menus.remove((menu, action))


def fill(profile):
    os.makedirs(os.path.join(profile, "python", "plugins"))
    os.makedirs(os.path.join(profile, "QGIS"))
    for name in ("QGIS/QGIS3.ini", "bookmarks.xml", "qgis.db"):
        with open(os.path.join(profile, name), "w") as f:
            f.write("x")


class CleanTest(unittest.TestCase):
    def setUp(self):
        self.profile = QGISSettingsCleaner.profile_path()
        self.assertEqual(self.profile, os.path.join(CONFIG_ROOT, "profiles", "default"))
        self.other = os.path.join(CONFIG_ROOT, "profiles", "other")
        for folder in (self.profile, self.other):
            shutil.rmtree(folder, ignore_errors=True)
            fill(folder)
        QSettings().setValue("locale/userLocale", "pt_BR")
        QSettings().sync()
        self.before = sorted(os.listdir(self.profile))

        self.iface = FakeIface(self.profile)
        self.plugin = QGISSettingsCleaner(self.iface)
        self.plugin.initGui()

    def tearDown(self):
        self.plugin.unload()

    def test_portuguese_translation_is_loaded(self):
        self.assertEqual(
            self.plugin.action.text(),
            "Excluir o Perfil de Usuário e Fechar o QGIS...",
        )

    def test_cancel_keeps_everything(self):
        self.plugin.confirm = lambda profile: False
        self.plugin.clean_settings()
        self.assertEqual(sorted(os.listdir(self.profile)), self.before)
        self.assertEqual(self.iface.events, [])

    def test_keeping_an_unsaved_project_keeps_everything(self):
        self.plugin.confirm = lambda profile: True
        self.iface.close_project = False
        self.plugin.clean_settings()
        self.assertEqual(sorted(os.listdir(self.profile)), self.before)
        self.assertEqual(self.iface.events, [("newProject", True, mock.ANY)])

    def test_confirm_closes_the_project_then_empties_the_profile_then_exits(self):
        self.plugin.confirm = lambda profile: True
        self.plugin.clean_settings()
        self.assertEqual(
            self.iface.events,
            [("newProject", True, self.before), ("exit", [])],
        )
        self.assertEqual(
            sorted(os.listdir(self.other)),
            ["QGIS", "bookmarks.xml", "python", "qgis.db"],
        )

    def test_symlinked_profile_is_emptied_too(self):
        target = os.path.join(CONFIG_ROOT, "elsewhere")
        shutil.rmtree(target, ignore_errors=True)
        shutil.move(self.profile, target)
        os.symlink(target, self.profile)
        self.plugin.confirm = lambda profile: True
        self.plugin.clean_settings()
        self.assertTrue(os.path.islink(self.profile))
        self.assertEqual(os.listdir(target), [])
        self.assertEqual(self.iface.events[-1], ("exit", []))

    def test_leftovers_are_reported_and_qgis_still_closes(self):
        # Stands in for a file QGIS still has open.
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
        self.plugin.warn_leftovers = lambda profile, leftovers: warned.append(
            (profile, leftovers)
        )
        with mock.patch("os.unlink", unlink):
            self.plugin.clean_settings()

        reason = str(PermissionError(13, "in use", busy))
        self.assertEqual(warned, [(self.profile, [(busy, reason)])])
        self.assertEqual(self.iface.events[-1], ("exit", ["busy.db"]))

    def test_confirm_dialog_defaults_to_cancel(self):
        shown = []
        QMessageBox.exec = lambda box: shown.append(box)
        self.addCleanup(delattr, QMessageBox, "exec")

        self.assertFalse(self.plugin.confirm(self.profile))
        box = shown[0]
        cancel = box.defaultButton()
        self.assertEqual(box.buttonRole(cancel), QMessageBox.ButtonRole.RejectRole)
        roles = {box.buttonRole(b) for b in box.buttons()}
        self.assertIn(QMessageBox.ButtonRole.DestructiveRole, roles)
        self.assertIn(self.profile, box.informativeText())

    def test_leftovers_dialog_lists_the_files(self):
        shown = []
        QMessageBox.exec = lambda box: shown.append(box)
        self.addCleanup(delattr, QMessageBox, "exec")

        busy = os.path.join(self.profile, "busy.db")
        self.plugin.warn_leftovers(self.profile, [(busy, "in use")])
        self.assertIn(self.profile, shown[0].informativeText())
        self.assertIn(busy + ": in use", shown[0].detailedText())


if __name__ == "__main__":
    unittest.main()
