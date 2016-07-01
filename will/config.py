import json
import os
import sys
from will.logger.fallback import error
from will.ftools import memoize


CONFIG_FILE_PATH = os.path.abspath("config.json")


class HeaderNotFound(Exception):
    pass


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


def add_config(config_item):
    config = _load_config_json
    config.update(config_item)
    config_file = open("config.json", 'w')
    config_file.write(json.dump(config))
    config.close()