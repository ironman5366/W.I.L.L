import config
import log
def get_uid():
    """Generate an incrementing UID for each plugin."""
    #Written by Max Ertl (https://github.com/Sirs0ri)
    global UID
    uid = "d_{0:04d}".format(UID)
    UID += 1
    return uid

def activate(device):
    assert type(device) == dict
    log.info("In tools, activating device {0}".format(device))
    #Build a dataset describing the device
    device_name = device["name"]
    device_config = config.load_config("devices", device_name)
    log.info("Device config is {0}".format(device_config)


def deactivate(device):
    pass

def add_command(message):
    pass