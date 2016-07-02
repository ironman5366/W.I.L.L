import os
from will.unittests import TestCase
from expects import *  # noqa
from mock import patch
from will.plugins.pyplugins import PythonLoader


class PythonLoader_ImportName(TestCase):
    def test_ShouldReturnModuleNameSutableForImport(self):
        plugin_file = PythonLoader("plugin/my_plugin.py")
        plugin_module = PythonLoader("plugin/my_plugin")  # Module dir

        expect(plugin_file.import_name()).to(equal("my_plugin"))
        expect(plugin_module.import_name()).to(equal("my_plugin"))


class PythonLoader_IsPlugin(TestCase):
    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_ShouldReturnTrueIfPluginIsFileAndExists(self, isfile, exists):
        plugin_file = PythonLoader("plugin/my_plugin.py")
        isfile.return_value = True
        exists.return_value = True

        expect(plugin_file.is_plugin(fs_tools=os.path)).to(be_true)

    @patch('os.path.isfile')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_ShouldReturnTrueifPluginIsDirAndExists(self, isdir, exists,
                                                    isfile):
        isfile.side_effect = [False, True]
        exists.return_value = True
        isdir.return_value = True
        plugin_module = PythonLoader("plugin/my_plugin")

        expect(plugin_module.is_plugin(fs_tools=os.path)).to(be_true)

    @patch('os.path.exists')
    def test_ShouldReturnFalseIfPluginDoesNotExist(self, exists):
        exists.return_value = False
        plugin_file = PythonLoader("plugins/my_plugin.py")

        expect(plugin_file.is_plugin(fs_tools=os.path)).to(be_false)

    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.path.isdir')
    def test_ShouldReturnFalseIfInitFileDoesNotExistInDir(self, isdir, isfile,
                                                          exists):
        exists.side_effect = [True, False]
        isfile.side_effect = [False, True]
        isdir.return_value = True
        plugin_file = PythonLoader("plugins/my_plugin")

        expect(plugin_file.is_plugin(fs_tools=os.path)).to(be_false)

    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('os.path.isdir')
    def test_ShouldReturnFalseIfInitIsNotAFile(self, isdir, isfile, exists):
        exists.return_value = True
        isfile.return_value = False
        isdir.return_value = True
        plugin_file = PythonLoader("plugins/my_plugin")

        expect(plugin_file.is_plugin(fs_tools=os.path)).to(be_false)
