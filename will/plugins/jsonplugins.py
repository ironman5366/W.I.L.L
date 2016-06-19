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
            if fs_tools.exists(self.file_path) and fs_tools.isfile(self.file_path):  # noqa
                return True
        return False

    def load(self):
        if self.is_json_file():
            log.info("Loading plugin: {0}".format(self.file_path))
            with open(os.path.abspath(self.file_path), 'r') as file_stream:
                return JsonData(json.load(file_stream))
        raise IOError


class PluginBuilder:

    def __init__(self, plugin_data):
        self.plugin_data = plugin_data

    @staticmethod
    def thread_shell_call(command):
        thread = threading.Thread(target=lambda: subprocess.call(
            command, shell=True
        ))
        thread.daemon = True
        thread.start()

    def build(self):
        self.build_init_callback()
        self.build_subscribed_callback()
        self.build_shutdown_callback()
        self.build_nlp_req_add()

    def build_init_callback(self):
        if "init" in self.plugin_data:
            @API.init
            def plugin():
                PluginBuilder.thread_shell_call(
                    self.plugin_data["init"]
                )

    def build_subscribed_callback(self):
        if "key_words" in self.plugin_data:
            # make sure everything in the list is a string
            key_words = map(lambda x: str(x),
                self.plugin_data["key_words"]  # noqa
            )  # noqa

            @API.subscribe_to(key_words)
            def plugin(leader, full_text):
                PluginBuilder.thread_shell_call(
                    self.plugin_data["command"].format(full_text)
                )
        else:
            @API.subscribe_to_any
            def plugin(full_text):
                def func():
                    PluginBuilder.thread_shell_call(
                        self.plugin_data["command"].format(full_text)
                    )

    def build_shutdown_callback(self):
        if "shutdown" in self.plugin_data:
            @API.shutdown
            def plugin():
                PluginBuilder.thread_shell_call(
                    self.plugin_data["shutdown"]
                )
    #TODO: test this and make sure I can access it properly
    def build_nlp_req_add(self):
        if "nlp_reqs" in self.plugin_data:
            @API.require
            def plugin(nlp_req_data):
                PluginBuilder.thread_shell_call(
                    self.plugin_data_data["nlp_reqs"].format(nlp_req_data)
                )

class JsonData:

    def __init__(self, json_data):
        self.plugin_data = json_data

    def is_valid(self):
        validation_schema = Schema({
            "key_words": list,
            "init": unicode,
            "shutdown" : unicode,
            "require" : dict,
            Required("command"): unicode,
        })
        try:
            validation_schema(self.plugin_data)
        except MultipleInvalid as e:
            log.exception("Error parsing plugin: {0}".format(e))
            return False
        return True

    def build_plugin(self):
        if self.is_valid():
            PluginBuilder(self.plugin_data).build()
