import unittest
import os
import will.plugins.jsonplugins as jsonplugins
from mock import MagicMock, patch, mock_open
from expects import *


class TestLoadPlugin(unittest.TestCase):
    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch('will.plugins.jsonplugins.json.load')
    @patch('__builtin__.open', mock_open(read_data="data"))
    def test_ShouldReturnJsonDataIfFileExists(self, json_load, isfile, exists):
        exists.return_value = True
        isfile.return_value = True
        json_load.return_value = {
            "key_words":['notify'],
            "command":"notify-send \"{0}\""
        }

        test_data = jsonplugins.load_plugin("plugins/some_plugin.json",
                                            fs_tools=os.path)

        expect(test_data.key_words).to(equal(['notify']))
        expect(test_data.command).to(equal("notify-send \"{0}\""))

    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_ShouldRaiseIOErrorIfFilePathIsDir(self, isfile, exists):
        exists.return_value = True
        isfile.return_value = False

        expect(lambda: jsonplugins.load_plugin(
            "plugins/some_plugin.json",
            fs_tools=os.path
        )).to(
            raise_error(IOError)
        )

    @patch('os.path.exists')
    def test_ShouldRaiseIOErrorIfFileDoesNotExists(self, exists):
        exists.return_value = False

        expect(lambda: jsonplugins.load_plugin(
            "plugins/some_plugin.json",
            fs_tools=os.path
        )).to(
            raise_error(IOError)
        )