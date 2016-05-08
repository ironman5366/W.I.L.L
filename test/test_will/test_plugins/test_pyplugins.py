import unittest
import os
from expects import *
from mock import MagicMock, patch

import will.plugins.pyplugins as pyplugins


class GetImportName(unittest.TestCase):
    @patch('os.path.exists')
    def test_ShouldReturnBasenameIfPyExists(self, exists):
        """Should return the basename of the python python file if the file exists"""
        exists.return_value = True

        expect(pyplugins.get_import_name(
            'plugins/my_plugin.py', fs_tools=os.path
        )).to(equal("my_plugin"))

    @patch('os.path.exists')
    @patch('os.path.isdir')
    def test_ShouldReturnBasenameIfPyModuleExists(self, exists, isdir):
        """
        Should return the basename of the python module if the directory exists
        and if there is an '__init__.py' in the directory.
        """
        exists.return_value = True
        isdir.return_value = True

        expect(pyplugins.get_import_name(
            'plugins/my_plugin', fs_tools=os.path
        )).to(equal("my_plugin"))

    @patch('os.path.exists')
    def test_ShouldRaiseIOERRorIfPyDoesNotExist(self, exists):
        """
        Should raise IOError if plugin python file does not exist.
        """
        exists.return_value = False

        expect(lambda: pyplugins.get_import_name(
            'plugins/my_plugin.py', fs_tools=os.path
        )).to(raise_error(IOError))

    @patch('os.path.isdir')
    @patch('os.path.exists')
    def test_ShouldRaiseIOErrorIfInitPyDoesNotExist(self, isdir, exists):
        """
        Should raise IOError if __init__.py does not exist in plugin directory.
        """
        isdir.return_value = True
        exists.return_value = False

        expect(lambda: pyplugins.get_import_name(
            'plugins/my_plugin', fs_tools=os.path
        )).to(raise_error(IOError))

    @patch('os.path.isdir')
    def test_ShouldRaiseIOErrorIfAnythingButPythonPluginIsPassedIn(self, isdir):
        """
        Should raise IOError if anything but a python plugin in passed in.
        """
        isdir.return_value = False

        expect(lambda: pyplugins.get_import_name(
            'plugins/my_plugin.json', fs_tools=os.path
        )).to(raise_error(IOError))


class TestGetLibPath(unittest.TestCase):
    @staticmethod
    def test_ShouldReturnBasePath():
        """
        Should return the base directory path of the python plugin
        """
        import os.path

        expect(pyplugins.get_lib_path('plugins/my_plugin.py')).to(
            equal(os.path.normpath('plugins'))
        )


class TestLoadPluginMetaData(unittest.TestCase):
    @staticmethod
    def test_ShouldReturnDictObjectWithIsPluginAsFalse():
        """
        Should return a DictObject with it's 'is_plugin' member var as False
        """
        meta_data = pyplugins.load_plugin_meta_data('plugins/what/my_plugin.py')

        expect(len(meta_data)).to(be(3))
        expect(meta_data.is_plugin).to(be_false)

    @patch('will.plugins.pyplugins.get_import_name')
    def test_ShouldReturnDictObjectWithIsPluginIsTrue(self, get_import_name):
        """
        Should return a DictObject with it's 'is_plugin' member var as True
        """
        get_import_name.return_value = "my_plugin"
        meta_data = pyplugins.load_plugin_meta_data('plugins/my_plugin.py')

        expect(meta_data.is_plugin).to(be_true)
        expect(meta_data.import_name).to(equal("my_plugin"))
        expect(meta_data.lib_path).to(equal('plugins'))
