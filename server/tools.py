import config
import log
from pydispatch import dispatcher
import vars

def get_uid():
    """Generate an incrementing UID for each plugin."""
    #get_uid function written by Max Ertl (https://github.com/Sirs0ri)
    global UID
    uid = "d_{0:04d}".format(UID)
    UID += 1
    return uid

def send_message(message_data):
    assert type(message_data) == dict
    log.info("In send message with message data {0}".format(message_data))

def get_active_devices():
    active_device_names = []
    for device_uid, device_data in vars.ACTIVE_DEVICES:
        log.info("Processing device with uid {0}, data {1}".format(device_uid, device_data))
        device_name = device_data['name']
        assert type(device_name) == str
        log.info("Device name is {0}".format(device_name))
        active_device_names.append(device_name)
    return active_device_names

def activate(device):
    assert type(device) == dict
    log.info("In tools, activating device {0}".format(device))
    device_uid = get_uid()
    #Build a dataset describing the device
    device_name = device["name"]
    log.info("Got uid {0} for device {1}".format(device_uid, device_name))
    device_config = config.load_config("devices", device_name)
    log.info("Device config is {0}".format(device_config))
    device_events = device["events"]
    assert type(device_events) == dict
    log.info("Device events is {0}".format(device_events))
    for event_trigger, event_data in device_events:
        event_uid = get_uid()
        vars.EVENT_HANDLERS.update({event_uid:{"trigger":event_trigger}})
        log.info("Got uid {0} for event trigger {1}".format(event_uid, event_trigger))
        log.info("Processing event trigger {0} for event data {1}".format(event_trigger, event_data))
        assert type(event_data) == dict
        event_data_type = event_data['type']
        log.info("Event data type is {0}".format(event_data_type))
        vars.EVENT_HANDLERS[event_uid].update({"event_type":event_data_type})
        if event_data_type == "message":
            log.info("Event data type is message")
            event_message = event_data["message"]
            vars.EVENT_HANDLERS[event_uid].update({"message":event_message})
            dispatcher.connect(send_message, signal=event_trigger, sender=dispatcher.Any)
        elif event_data_type == "plugin":
            log.info("Event data type is plugin")
            plugins = vars.PLUGINS
            event_params = event_data["parameters"]
            log.info("Event parameters are {0}".format(event_params))
            event_plugin = event_data["plugin"]
            if event_plugin in plugins.keys():
                log.info("Plugin {0} found".format(event_plugin))
                plugin_data = plugins[event_plugin]
                log.info("Processing plugin {0} with plugin data {1}".format(event_plugin,plugin_data))
                vars.EVENT_HANDLERS[event_uid].update({"params":event_params})
                dispatcher.connect(plugin_call, signal=event_trigger, sender=dispatcher.Any)
            else:
                log.info("Error: plugin {0} not found".format(event_plugin))
        vars.ACTIVE_DEVICES.update({device_uid:{"name":device_name,"events":device_events,"config":device_config}})

def register(device):
    pass

def unregister(device):
    device

def plugin_call(**args):
    pass

def deactivate(device):
    pass

def add_command(message):
    pass