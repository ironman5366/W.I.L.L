import config
import random


def app_id():
    app_ids = config.load_config("wolfram")["keys"]
    return random.choice(app_ids)
