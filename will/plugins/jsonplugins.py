import os
import json
from will.collections import DictObject
from will.logger import log


def load_plugin(file_path, fs_tools=os.path):
    if fs_tools.exists(file_path) and fs_tools.isfile(file_path):
        try:
            with open(file_path, 'r') as json_plugin:
                return DictObject(**json.load(json_plugin))
        except Exception as e:
            log.exception("Error loading json plugin: {0}".format(e))
            raise IOError
    raise IOError
