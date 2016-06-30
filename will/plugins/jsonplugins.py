import os
import json
from will.logger import log
from voluptuous import Schema, Required, MultipleInvalid
import API
import subprocess
import threading

#TODO: get these working

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

    def build_init_callback(self):
        if "init" in self.plugin_data:
            @API.init
            def plugin():
                PluginBuilder.thread_shell_call(
                    self.plugin_data["init"]
                )

    def build_subscribed_callback(self):
        '''Build the api data for the subscribe decorator'''
        data = False
        api_data = {"name" : '',
                    "ents_needed" : {},
                    "structure" : {"needed" : False},
                    "questions_needed" : False,
                    "key_words" : []
                    }
        if "name" in self.plugin_data:
            api_data["name"] = self.plugin_data["name"]
        if "ents_needed" in self.plugin_data:
            plugin_ents = self.plugin_data["ents_needed"]
            if plugin_ents and plugin_ents != {}:
                api_data['ents_needed'].update(plugin_ents)
                data = True
        if "structure" in self.plugin_data:
            struct_needed = self.plugin_data['structure']['needed']
            if struct_needed:
                api_data['structure']['needed'].append(struct_needed)
                data = True
        if "questions_needed" in self.plugin_data:
            q_needed = self.plugin_data["questions_needed"]
            if q_needed:
                api_data["questions_needed"] = q_needed
                data = True
        if "key_words" in self.plugin_data:
            plugin_key_words = self.plugin_data["key_words"]
            if plugin_key_words:
                for key_word in plugin_key_words:
                    api_data["key_words"].append(key_word)
                data = True
        if data:
            @API.subscribe_to(api_data)
            def plugin(*args):
                leader = args[0]
                full_text = args[1]
                arg_data = args[2][0]
                text = full_text.split(" ")[0]
                plugin_data = {"name": arg_data["name"],
                            "ents": arg_data["ents"],
                            "struct_needed" : arg_data["struct_needed"],
                            "full_text" : full_text,
                            "leader" : leader,
                            "headless_text" : text}
                command_str = self.plugin_data["command"]
                for ent in plugin_data["ents"].keys():
                    ent_place = "{%s}" % ent
                    replace_str = plugin_data["ents"][ent]
                    if isinstance(replace_str, list):
                        replace_str = replace_str[0]
                    if ent_place in command_str:
                        command_str = command_str.replace(ent_place, replace_str)
                for word_type in plugin_data["struct_needed"].keys():
                    word_place = "{%s}" % word_type
                    replace_str = plugin_data["struct_needed"][word_type]
                    if isinstance(replace_str, list):
                        replace_str = replace_str[0]
                    if word_place in command_str:
                        command_str = command_str.replace(word_place, replace_str)
                if "{full_text}" in command_str:
                    command_str = command_str.replace("{full_text}", full_text)
                if "{leader}" in command_str:
                    command_str = command_str.replace("{leader}", leader)
                if "{headless_text}" in command_str:
                    command_str = command_str.replace("{headless_text}", full_text)
                PluginBuilder.thread_shell_call(
                    command_str
                )
                return "Done"
        else:
            @API.subscribe_to_any
            def plugin(*args, **kwargs):
                def func():
                    PluginBuilder.thread_shell_call(
                        self.plugin_data["command"].format(args[1])
                    )

    def build_shutdown_callback(self):
        if "shutdown" in self.plugin_data:
            @API.shutdown
            def plugin():
                PluginBuilder.thread_shell_call(
                    self.plugin_data["shutdown"]
                )
class JsonData:

    def __init__(self, json_data):
        self.plugin_data = json_data

    def is_valid(self):
        validation_schema = Schema({
            "name": unicode,
            "init": unicode,
            "shutdown" : unicode,
            "ents_needed": dict,
            "structure" : dict,
            "questions_needed" : bool,
            "key_words" : list,
            Required("command") : unicode
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
