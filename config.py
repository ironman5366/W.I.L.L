import json
import logs
import os


CONFIG_FILE_PATH = os.path.abspath("config.json")


def config_cache(pass_func):
    try:
        with open(CONFIG_FILE_PATH, 'r') as config:
            c_cache = json.load(config)
    except IOError:
        log = logs.logs()
        log.write("Couldn't load config file. Exiting.", 'error')
        os.exit(1)
    except ValueError:  # Error on loading the json itself.
        log = logs.logs()
        log.write("Couldn't load config file JSON. Formatting error?", 'error')
        os.exit(1)

    def dummy_config():
        return c_cache

    return dummy_config


@config_cache
def load_config():
    pass
