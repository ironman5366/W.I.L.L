import os
from WillPy.unittests import TestCase
from expects import *
from mock import patch, MagicMock, mock_open
from WillPy.plugins.jsonplugins import JsonData, JsonLoader


class JsonData_IsValid(TestCase):
    def test_ShouldReturnTrueIfDataIsValid(self):
        valid_data = {
            "with_key_words": {
                u"key_words": [u"notify"],
                u"command": u"notify-send \"{0}\""
            },

            "without_key_words": {
                u"command": u"notify-send \"{0}\""
            }
        }
        json_data = JsonData(valid_data["with_key_words"])
        expect(json_data.is_valid()).to(be_true)

        json_data = JsonData(valid_data["without_key_words"])
        expect(json_data.is_valid()).to(be_true)

    def test_ShouldReturnFalseIfDataIsInvalid(self):
        invalid_data = {
            "gibberish": {
                u"some": u"random",
                u"values": u"here"
            },

            "no_command": {
                u"key_words": [u"notify"]
            },

            "key_words_without_list": {
                u"key_words": u"notify",
                u"command": u"notify-send \"{0}\""
            }
        }
        json_data = JsonData(invalid_data["gibberish"])
        expect(json_data.is_valid()).to(be_false)

        json_data = JsonData(invalid_data["no_command"])
        expect(json_data.is_valid()).to(be_false)

        json_data = JsonData(invalid_data["key_words_without_list"])
        expect(json_data.is_valid()).to(be_false)


class JsonLoader_IsJsonFile(TestCase):
    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_ShouldReturnTrueIfValidPath(self, isfile, exists):
        isfile.return_value = True
        exists.return_value = True
        json_loader = JsonLoader("plugins/some_plugin.json")

        expect(json_loader.is_json_file(fs_tools=os.path)).to(
            be_true
        )

    def test_ShouldReturnFalseIfNoJsonExtension(self):
        json_loader = JsonLoader("plugins/some_plugin.py")

        expect(json_loader.is_json_file()).to(be_false)

    @patch('os.path.exists')
    def test_ShouldReturnFalseIfPathNotFound(self, exists):
        exists.return_value = False
        json_loader = JsonLoader("plugins/some_plugin.json")

        expect(json_loader.is_json_file()).to(be_false)

    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_ShouldReturnFalseIfPathIsNotFile(self, isfile, exists):
        isfile.return_value = False
        exists.return_value = True
        json_loader = JsonLoader("plugins/some_plugin.json")

        expect(json_loader.is_json_file()).to(be_false)


class JsonLoader_Load(TestCase):
    def test_ShouldReturnJsonDataIfIsJsonFile(self):
        json_loader = JsonLoader("plugins/some_plugin.json")
        json_loader.is_json_file = MagicMock(return_value=True)

        with patch('__builtin__.open',
                   mock_open(read_data="{}"), create=True):
            expect(json_loader.load()).to(be_a(JsonData))

    def test_ShouldRaiseIOErrorIfNotJsonFile(self):
        json_loader = JsonLoader("plugins/some_plugin.json")
        json_loader.is_json_file = MagicMock(return_value=False)

        expect(lambda: json_loader.load()).to(raise_error(IOError))
