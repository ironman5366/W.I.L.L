import config
import log
from pydispatch import dispatcher
import vars

def shutdown():
    pass

def restart():
    pass

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
    '''Use the event handlers and triggers to activate the device dictionary passed'''
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
    vars.EVENT_HANDLERS.update({device_uid:{}})
    for event_trigger, event_data in device_events:
        event_uid = get_uid()
        vars.EVENT_HANDLERS[device_uid].update({event_uid:{"trigger":event_trigger}})
        log.info("Got uid {0} for event trigger {1}".format(event_uid, event_trigger))
        log.info("Processing event trigger {0} for event data {1}".format(event_trigger, event_data))
        assert type(event_data) == dict
        event_data_type = event_data['type']
        log.info("Event data type is {0}".format(event_data_type))
        vars.EVENT_HANDLERS[device_uid][event_uid].update({"event_type":event_data_type})
        if event_data_type == "message":
            log.info("Event data type is message")
            event_message = event_data["message"]
            vars.EVENT_HANDLERS[device_uid][event_uid].update({"message":event_message})
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
                vars.EVENT_HANDLERS[device_uid][event_uid].update({"params":event_params})
                dispatcher.connect(plugin_call, signal=event_trigger, sender=dispatcher.Any)
            else:
                log.info("Error: plugin {0} not found".format(event_plugin))
        elif event_data_type == "action":
            log.info("Event data type is action")
            event_action = event_data["action"]
            log.info("Event action is {0}".format(event_action))
            if event_action == "shutdown":
                log.info("Connecting trigger {0} to shutdown function".format(event_trigger))
                dispatcher.connect(shutdown, signal=event_trigger, sender=dispatcher.Any)
            elif event_action == "restart":
                log.info("Connecting trigger {0} to restart function".format(event_trigger))
                dispatcher.connect(restart, signal=event_trigger, sender=dispatcher.Any)
            #TODO: add more actions, used for things like dumping events or caches
        else:
            log.info("Unhandled event data type {0}".format(event_data_type))
    vars.ACTIVE_DEVICES.update(
        {device_uid: {"name": device_name, "events": device_events, "config": device_config}})

def register(device):
    '''Register a device dictionary in the config'''
    log.info("In register with device dict {0}".format(device))
    assert type(device) == dict
    device_name = device["name"]
    log.info("Device name is {0}".format(device_name))
    log.info("Creating config entry for device {0}".format(device_name))
    config.add_entry("devices", device_name)
    log.info("Created config entry. Filling with requisite values")
    for device_key, device_value in device:
        log.info("Processing device key {0}, value {1}".format(device_key, device_value))
        config.add_item("devices", device_name, {device_key:device_value})
        log.info("Added config entry")
    device_config = config.load_config("devices", device_name)
    log.info("Finished registering device {0}, final config entry is {1}".format(device_name, device_config))


def unregister(device_name, backup=False):
    '''Remove the device dictionary from the config'''
    assert type(device_name) == str
    log.info("In unregister with device name {0}".format(device_name))
    device_config = config.load_config("devices", device_name)
    log.info("Loaded device config {0}".format(device_config))
    log.info("Device config exists")
    if backup:
        config.add_entry("backups", device_name)
        for device_key, device_value in device_config:
            config.add_item("backups", device_name, {device_key:device_value})
    config.remove_entry("devices", device_name)
    log.info("Unregistered device {0}".format(device_name))

def plugin_call(**args):
    '''Call a plugin registered to an event'''
    pass
    #TODO: use getattr to complete the call

def deactivate(device_uid):
    '''Deactivate a device and remove the event triggers'''
    log.info("In deactivate with device {0}".format(device_uid))
    assert type(device_uid) == str
    if device_uid in vars.ACTIVE_DEVICES.keys():
        log.info("Removing event triggers associated with device {0}".format(device_uid))
        device = vars.ACTIVE_DEVICES[device_uid]
        device_name = device["name"]
        log.info("Name for device uid {0} is {1}".format(device_uid, device_name))
        event_thread = vars.EVENT_HANDLERS[device_uid]
        log.info("Found event thread {0} for device".format(event_thread))
        log.info("Removing device thread {0} from event handlers".format(device_uid))
        del vars.EVENT_HANDLERS[device_uid]
        log.info("Deleted device thread from event handlers")
    else:
        log.info("Can't deactivate device {0}, already in active devices".format(device_uid))

def add_command(message):
    pass