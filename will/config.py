import json
import os
import sys
from will.logger.fallback import error
from will.ftools import memoize


CONFIG_FILE_PATH = os.path.abspath("config.json")


class HeaderNotFound(Exception):
    pass


class FilePath:
    def __init__(self, file_path):
        self.file_path = os.path.normpath(file_path)

    def __str__(self):
        return self.file_path

    def get_path(self):
        return str(self)

    def exists(self):
        return os.path.exists(self.file_path)

    def base_name(self):
        return os.path.basename(self.file_path)

    def is_directory(self):
        return os.path.isdir(self.file_path)

    def is_file(self):
        return not self.is_directory()

    def abs_path(self):
        return FilePath(os.path.abspath(str(self)))

    def join(self, secondary_path):
        return FilePath((os.path.join(self.file_path, str(secondary_path))))


@memoize
def _load_config_json():
    try:
        with open(CONFIG_FILE_PATH, 'r') as config:
            return json.load(config)
    except IOError:
        error("Couldn't load config file. Exiting.")
        sys.stderr.flush()
        sys.exit(1)
    except ValueError:  # Error on loading the json itself.
        error("Couldn't load config file JSON.  Formatting error?")
        error("system shutting down.")
        sys.stderr.flush()
        sys.exit(1)


@memoize
def load_config(header):
    config = _load_config_json()
    if header in config:
        return config[header]
    raise HeaderNotFound
