import os
import json
from will.logger import log
from voluptuous import Schema, Required, Invalid, MultipleInvalid


def load_plugin(file_path):
    json_loader = JsonLoader(file_path)

    try:
        plugin_data = json_loader.load()
        plugin_data.build_plugin()

    except IOError:
        return


class JsonLoader:
    def __init__(self, file_path):
        self.file_path = file_path

    def is_json_file(self, fs_tools=os.path):
        if self.file_path.endswith('.json'):
            if fs_tools.exists(self.file_path) and fs_tools.isfile(self.file_path):
                return True
        return False

    def load(self):
        if self.is_json_file():
            with open(self.file_path, 'r') as file_stream:
                return JsonData(json.load(file_stream))
        raise IOError


class JsonData:
    def __init__(self, json_data):
        pass

    def is_valid(self):
        pass

    def build_plugin(self):
        pass


def load_plugin(file_path):
    json_loader = JsonLoader(file_path)

    if json_loader.is_json_file():
        with json_loader.open() as file_stream:
            plugin_data = JsonData(file_stream)

        if plugin_data.is_valid():
            plugin_data.build_plugin()


def convert_to_py_plugin(plugin_data):
    pass


def is_valid_plugin(plugin_data):
    validation_schema = Schema({
       "key_words": list,
       Required("command"): str
    })
    try:
        validation_schema(plugin_data)
    except MultipleInvalid as e:
        log.exception("Error parsing plugin: {0}".format(e))
        return False
    return True
