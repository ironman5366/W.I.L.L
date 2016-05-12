import os
import json
from will.logger import log
from voluptuous import Schema, Required, MultipleInvalid
import API
import subprocess
import threading


def plugin_loader(file_path):
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
            log.info("Loading plugin: {0}".format(self.file_path))
            with open(os.path.abspath(self.file_path), 'r') as file_stream:
                return JsonData(json.load(file_stream))
        raise IOError


class JsonData:
    def __init__(self, json_data):
        self.plugin_data = json_data

    def is_valid(self):
        validation_schema = Schema({
           "key_words": list,
           Required("command"): unicode
        })
        try:
            validation_schema(self.plugin_data)
        except MultipleInvalid as e:
            log.exception("Error parsing plugin: {0}".format(e))
            return False
        return True

    def build_plugin(self):
        if self.is_valid():
            if "key_words" in self.plugin_data:

                # make sure everything in the list is a string
                key_words = map(lambda x: str(x), self.plugin_data["key_words"])

                @API.subscribe_to(key_words)
                def plugin(leader, full_text):

                    def func():
                        subprocess.call(
                            self.plugin_data["command"].format(
                                full_text[len(leader)+1:]
                            ),
                            shell=True
                        )

                    thread = threading.Thread(target=func)
                    thread.daemon = True
                    thread.start()

            else:

                @API.subscribe_to_any
                def plugin(full_text):
                    def func():
                        subprocess.call(
                            self.plugin_data["command"].format(full_text),
                            shell=True
                        )

                    thread = threading.Thread(target=func)
                    thread.daemon = True
                    thread.start()

