from will.unittests import TestCase
from expects import *
from will.plugins.jsonplugins import JsonData


class JsonData_IsValid(TestCase):
    def test_ShouldReturnTrueIfDataIsValid(self):
        valid_data = {
            "with_key_words": {
                "key_words": ['notify'],
                "command": "notify-send \"{0}\""
            },

            "without_key_words": {
                "command": "notify-send \"{0}\""
            }
        }
        json_data = JsonData(valid_data["with_key_words"])
        expect(json_data.is_valid()).to(be_true)

        json_data = JsonData(valid_data["without_key_words"])
        expect(json_data.is_valid()).to(be_true)

    def test_ShouldReturnFalseIfDataIsInvalid(self):
        invalid_data = {
            "gibberish": {
                "some": "random",
                "values": "here"
            },

            "no_command": {
                "key_words": ['notify']
            },

            "key_words_without_list": {
                "key_words": "notify",
                "command": "notify-send \"{0}\""
            }
        }
        json_data = JsonData(invalid_data["gibberish"])
        expect(json_data.is_valid()).to(be_false)

        json_data = JsonData(invalid_data["no_command"])
        expect(json_data.is_valid()).to(be_false)

        json_data = JsonData(invalid_data["key_words_without_list"])
        expect(json_data.is_valid()).to(be_false)
