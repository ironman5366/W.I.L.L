import json
import os
import sys
from termcolor import colored


CONFIG_FILE_PATH = os.path.abspath("config.json")


class HeaderNotFound(Exception):
    pass


def config_cache(pass_func):
    try:
        with open(CONFIG_FILE_PATH, 'r') as config:
            c_cache = json.load(config)
    except IOError:
        sys.stderr.write(
            colored("ERROR: Couldn't load config file.  Exiting.", 'red')
        )
        sys.stderr.flush()
        os.exit(1)
    except ValueError:  # Error on loading the json itself.
        sys.stderr.write(
            colored(
                "ERROR: Couldn't load config file JSON. Formatting error?",
                'red'
            )
        )
        sys.stderr.flush()
        os.exit(1)

    def dummy_config(header):
        if header in c_cache:
            return c_cache[header]
        raise HeaderNotFound

    return dummy_config


@config_cache
def load_config():
    pass
