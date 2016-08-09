#Internal imports
import config
import log
import devices
import vars
import eventbuilder

#Builtin imports
import socket, traceback
import json

host = ''
port = 5366
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.bind((host, port))
while True:
    try:
        return_message={
            "type":None,
            "text":None,
            "data":{}
        }
        raw_message, address = s.recvfrom(8192)
        log.info("Got message {0} from {1}".format(raw_message,address))
        try:
            message = json.loads(message)
            log.info("Loaded message json is {0}".format(message))
            message_type = message["type"]
            log.info("Message type is {0}".format(message_type))
            if message_type == "register":
                log.info("Message type is register")
                device_name = message["device_name"]
                log.info("Device name is {0}".format(device_name))
                known_devices = config.load_config("data","known_devices")
                log.info("Retrieved known devices list from config. Is as follows:\n {0}".format(known_devices))
                if device_name in known_devices:
                    return_message['type'] = "error"
                    return_message['text'] = "Attempted registry of device {0} failed because there is already a device with that name".format(device_name)
                    return_message["data"].update({"code":"DEVICE_ALREADY_REGISTERED"})
                else:
                    log.info("Registering device {0}".format(device_name))
                    config.add_item("data","known_devices",device_name)
                    log.info("Added device {0} to config list of known devices".format(device_name))
                    config.add_header("devices",device_name)
                    device_data = message["data"]
                    for data_dict in device_data:
                        log.info("Adding data item {0} to config".format(data_dict))
                        config.add_item("devices",device_name,data_dict)
                    return_message["type"] = "success"
                    return_message["text"] = "Device {0} was successfully registered, and it's data stored.".format(device_name)
            elif message_type == "activate":
                log.info("Message type is activate")
                device_name = message["device_name"]
                log.info("Checking for device name in list of active devices")
                active_device_names = vars.ACTIVE_DEVICES.keys()
                log.info("Active devices are {0}".format(active_device_names))
                if device_name in active_device_names:
                    log.info("Device {0} was already registered as active".format(device_name ))
                    return_message["type"] = "error"
                    return_message["text"] = "Device {0} was already registered as active".format(device_name)
                    return_message["data"].update({"code":"DEVICE_ALREADY_ACTIVE"})
                else:
                    log.info("Device {0} not in list of already active devices".format(device_name))
                    log.info("Checking to see if device is registered")
                    known_devices = config.load_config("data","known_devices")
                    log.info("Loaded list of known devices from config")
                    if device_name in known_devices:
                        log.info("Device {0} is in known devices".format(device_name))
                        vars.ACTIVE_DEVICES.update({device_name:message})
                        try:
                            # TODO: Make this callout valid
                            eventbuilder.process(message)
                            log.info("Activated device")
                            return_message["type"] = "success"
                            return_message["text"] = "Device {0} was activated successfully, and it's events processed.".format(device_name)
                        except Exception as process_exception:
                            p_message = process_exception.message
                            p_args = process_exception.args
                            log.info("Exception {0},{1} occurred while trying to activate device {2} and process it's events. Device data is {3}"
                                     .format(p_message,p_args,device_name,message))
                            return_message["type"] = "error"
                            return_message["text"] = "Exception {0},{1} occurred while trying to activate device {2} and process it's events.".format(p_message,p_args)
                            return_message["data"].update({"code":"EVENT_PROCESS_ERROR"})
                    else:
                        log.info("Device {0} wasn't found in the list of known devices".format(device_name))
                        return_message["type"] = "error"
                        return_message["text"] = "Couldn't activate device {0} because it isn't in the list of known devices. Please make sure that the device is registered".format(device_name)
                        return_message["data"].update({"code":"DEVICE_NOT_KNOWN"})
        except Exception as parse_exception:
            e_message = parse_exception.message
            e_args = parse_exception.args
            log.info("Error {0}, {1} occurred while trying to load message {2}".format(e_message,e_args,raw_message))
            return_message["type"] = "error"
            return_message["text"] = "{0},{1}".format(e_message,e_args)
            return_message["data"].update({"code":False})
        finally:
            log.info("Sending return message {0} to address {1}".format(return_message,address))
            log.info("Converting the return message to json")
            return_json = json.dumps(return_message)
            s.sendto(return_json,address)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        traceback.print_exc()