"""Runs the plugin inside the QGIS Python, without a QGIS window, on a throwaway profile.

QGIS_CUSTOM_CONFIG_PATH must be set before QgsApplication starts, so it is set here,
on import, and the profiles live under a temporary folder for the whole process.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CONFIG_ROOT = tempfile.mkdtemp(prefix="qgis-settings-cleaner-test-")
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = CONFIG_ROOT
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qgis.core import QgsApplication, QgsTask  # noqa: E402
from qgis.PyQt.QtCore import QObject, QSettings, QTimer  # noqa: E402
from qgis.PyQt.QtWidgets import QAction, QMainWindow, QMessageBox  # noqa: E402

from qgis_settings_cleaner import HINT_SETTING, QGISSettingsCleaner  # noqa: E402

# The plugin waits before pushing the message; the tests push it themselves.


APP = QgsApplication([], True)
APP.initQgis()


class FakeIface(QObject):
    """The part of QgisInterface the plugin touches, recording what happens when."""

    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self.close_project = True
        self.events = []
        self._main = QMainWindow()
        self.exit_action = QAction(self._main)
        self.exit_action.triggered.connect(self._exit)
        self.menus = []
        self.toolbar = []
        self.messages = []

    def _contents(self):
        return sorted(os.listdir(self.folder)) if os.path.isdir(self.folder) else None

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

    def addToolBarIcon(self, action):
        self.toolbar.append(action)

    def removeToolBarIcon(self, action):
        self.toolbar.remove(action)

    def messageBar(self):
        return self

    def pushMessage(self, title, text, level, duration):
        self.messages.append(text)


def fill(folder):
    os.makedirs(os.path.join(folder, "python", "plugins"))
    os.makedirs(os.path.join(folder, "QGIS"))
    for name in ("QGIS/QGIS3.ini", "bookmarks.xml", "qgis.db"):
        with open(os.path.join(folder, name), "w") as f:
            f.write("x")


class CleanTest(unittest.TestCase):
    def setUp(self):
        self.folder = QGISSettingsCleaner.settings_path()
        self.assertEqual(self.folder, os.path.join(CONFIG_ROOT, "profiles", "default"))
        self.other = os.path.join(CONFIG_ROOT, "profiles", "other")
        for folder in (self.folder, self.other):
            # A previous test may have left a symbolic link here, which
            # rmtree refuses to follow.
            if os.path.islink(folder):
                os.unlink(folder)
            shutil.rmtree(folder, ignore_errors=True)
            fill(folder)
        QSettings().setValue("locale/userLocale", "pt_BR")
        QSettings().remove(HINT_SETTING)
        QSettings().sync()
        self.before = sorted(os.listdir(self.folder))

        self.iface = FakeIface(self.folder)
        self.plugin = QGISSettingsCleaner(self.iface)
        self.plugin.initGui()

    def tearDown(self):
        self.plugin.unload()

    def test_portuguese_translation_is_loaded(self):
        self.assertEqual(
            self.plugin.action.text(),
            "Apagar Todas as Configurações do QGIS e Fechar...",
        )

    def test_the_action_is_in_the_menu_and_on_the_toolbar(self):
        self.assertEqual(
            self.iface.menus, [("&QGIS Settings Cleaner", self.plugin.action)]
        )
        self.assertEqual(self.iface.toolbar, [self.plugin.action])
        self.plugin.unload()
        self.assertEqual(self.iface.menus, [])
        self.assertEqual(self.iface.toolbar, [])
        self.plugin.initGui()

    def test_where_to_find_the_plugin_is_said_once(self):
        self.assertEqual(self.iface.messages, [])
        self.plugin.push_where_to_find()
        [message] = self.iface.messages
        self.assertEqual(
            message,
            "Instalado. É a vassoura na barra de ferramentas Complementos, e está"
            " no menu Complementos.",
        )

        # Said already: a later start says nothing, and pushes no timer.
        timers = []
        with mock.patch.object(QTimer, "singleShot", lambda ms, f: timers.append(f)):
            self.plugin.unload()
            self.plugin.initGui()
        self.assertEqual(timers, [])
        self.assertEqual(len(self.iface.messages), 1)

    def test_the_message_waits_for_the_startup_messages(self):
        timers = []
        self.plugin.unload()
        with mock.patch.object(
            QTimer, "singleShot", lambda ms, f: timers.append((ms, f))
        ):
            self.plugin.initGui()
        [(delay, push)] = timers
        self.assertGreaterEqual(delay, 1000)
        self.assertEqual(self.iface.messages, [])
        push()
        self.assertEqual(len(self.iface.messages), 1)

    def run_task(self, flags):
        task = QgsTask.fromFunction("busy", lambda task: time.sleep(0.5), flags=flags)
        QgsApplication.taskManager().addTask(task)
        self.addCleanup(task.waitForFinished)

    def test_running_tasks_stop_it_before_the_confirmation(self):
        self.run_task(QgsTask.Flag.CanCancel)
        warned = []
        self.plugin.confirm = lambda folder: self.fail("asked to confirm")
        self.plugin.warn = lambda text, informative, details="": warned.append(text)
        self.plugin.clean_settings()
        self.assertEqual(
            warned, ["O QGIS ainda está executando tarefas em segundo plano."]
        )
        self.assertEqual(sorted(os.listdir(self.folder)), self.before)
        self.assertEqual(self.iface.events, [])

    def test_tasks_qgis_cancels_by_itself_do_not_stop_it(self):
        self.run_task(QgsTask.Flag.CancelWithoutPrompt)
        self.plugin.warn = lambda *args: self.fail("refused")
        self.plugin.confirm = lambda folder: True
        self.plugin.clean_settings()
        self.assertEqual(self.iface.events[-1], ("exit", []))

    def test_cancel_keeps_everything(self):
        self.plugin.confirm = lambda folder: False
        self.plugin.clean_settings()
        self.assertEqual(sorted(os.listdir(self.folder)), self.before)
        self.assertEqual(self.iface.events, [])

    def test_keeping_an_unsaved_project_keeps_everything(self):
        self.plugin.confirm = lambda folder: True
        self.iface.close_project = False
        self.plugin.clean_settings()
        self.assertEqual(sorted(os.listdir(self.folder)), self.before)
        self.assertEqual(self.iface.events, [("newProject", True, mock.ANY)])

    def test_confirm_closes_the_project_then_empties_the_folder_then_exits(self):
        self.plugin.confirm = lambda folder: True
        self.plugin.clean_settings()
        self.assertEqual(
            self.iface.events,
            [("newProject", True, self.before), ("exit", [])],
        )
        self.assertEqual(
            sorted(os.listdir(self.other)),
            ["QGIS", "bookmarks.xml", "python", "qgis.db"],
        )

    def test_symlinked_folder_is_emptied_too(self):
        target = os.path.join(CONFIG_ROOT, "elsewhere")
        shutil.rmtree(target, ignore_errors=True)
        shutil.move(self.folder, target)
        os.symlink(target, self.folder)
        self.plugin.confirm = lambda folder: True
        self.plugin.clean_settings()
        self.assertTrue(os.path.islink(self.folder))
        self.assertEqual(os.listdir(target), [])
        self.assertEqual(self.iface.events[-1], ("exit", []))

    def test_leftovers_are_reported_and_qgis_still_closes(self):
        # Stand-ins for a file and a folder QGIS still has open.
        busy = os.path.join(self.folder, "busy.db")
        with open(busy, "w") as f:
            f.write("x")
        held = os.path.join(self.folder, "python")
        real_unlink, real_rmdir = os.unlink, os.rmdir

        def unlink(path, *args, **kwargs):
            if os.path.basename(path) == "busy.db":
                raise PermissionError(13, "in use", path)
            return real_unlink(path, *args, **kwargs)

        def rmdir(path, *args, **kwargs):
            if path == held:
                raise PermissionError(13, "held", path)
            return real_rmdir(path, *args, **kwargs)

        warned = []
        self.plugin.confirm = lambda folder: True
        self.plugin.warn_leftovers = lambda folder, leftovers: warned.append(
            (folder, sorted(leftovers))
        )
        with mock.patch("os.unlink", unlink), mock.patch("os.rmdir", rmdir):
            self.plugin.clean_settings()

        self.assertEqual(warned, [(self.folder, [(busy, "in use"), (held, "held")])])
        self.assertEqual(self.iface.events[-1], ("exit", ["busy.db", "python"]))

    def test_confirm_answers_as_the_buttons_say(self):
        boxes = []

        def press(role):
            def exec_(box):
                boxes.append(box)
                [button] = [b for b in box.buttons() if box.buttonRole(b) == role]
                button.click()
                return 0

            return exec_

        self.addCleanup(delattr, QMessageBox, "exec")
        QMessageBox.exec = press(QMessageBox.ButtonRole.RejectRole)
        self.assertFalse(self.plugin.confirm(self.folder))
        QMessageBox.exec = press(QMessageBox.ButtonRole.DestructiveRole)
        self.assertTrue(self.plugin.confirm(self.folder))

        box = boxes[0]
        self.assertEqual(
            box.buttonRole(box.defaultButton()), QMessageBox.ButtonRole.RejectRole
        )
        self.assertIn(self.folder, box.informativeText())

    def test_leftovers_dialog_lists_the_files(self):
        shown = []
        QMessageBox.exec = lambda box: shown.append(box)
        self.addCleanup(delattr, QMessageBox, "exec")

        busy = os.path.join(self.folder, "busy.db")
        self.plugin.warn_leftovers(self.folder, [(busy, "in use")])
        self.assertIn(self.folder, shown[0].informativeText())
        self.assertIn(busy + ": in use", shown[0].detailedText())


if __name__ == "__main__":
    unittest.main()
