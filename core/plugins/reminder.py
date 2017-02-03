# Builtin imports
import logging
import time
# Internal imports
import core
from core.plugin_handler import subscribe
import tools
from dateparser import parse
import datetime

log = logging.getLogger()

def is_reminder(event):
    '''Check to see whether a reminder should be set'''
    event_command = event["command"]
    event_verbs = event["verbs"]
    if "remind" in event_verbs:
        return True
    elif "set a reminder" in event_command.lower():
        return True
    else:
        return False


@subscribe({"name": "reminder", "check": is_reminder})
def main(event):
    '''Set a reminder using the interface scheduler'''
    response = {"type": "success", "text": None, "data": {}}
    event_command = event["command"]
    log.info("In set a reminder with command {0}".format(event_command))
    event_ents = event["ents"]
    log.debug("Event ents are {0}".format(event_ents))
    dates = []
    times = []
    # Look through the recognized entities for dates and times
    for ent_type, ent_word in event_ents.items():
        if ent_type == "DATE":
            dates.append(ent_word)
        elif ent_type == "TIME":
            times.append(ent_word)
    log.debug("Found dates {0} and times {1} in event command {2}".format(
        dates, times, event_command
    ))
    # TODO: ask the user about which time they want to ues
    # TODO: add dates processing

    #Find the alert text
    event_doc = event["doc"]
    time_message = None
    for chunk in event_doc:
        # Use dependency parsing to dermine the object of the command
        if chunk.dep_ == "xcomp":
            lefts = [left.orth_ for left in chunk.lefts]
            rights = [right.orth_ for right in chunk.rights]
            time_message = " ".join(lefts+[chunk.text]+rights)
        elif chunk.dep_ == "pobj":
            lefts = [left.orth_ for left in chunk.lefts]
            rights = [right.orth_ for right in chunk.rights]
            event_time = " ".join(lefts + [chunk.text] + rights)
    if not time_message:
        time_message == "Reminder: {0}".format(event_command)
    #if times:
    #    event_time = times[0]
    #elif dates:
    #    event_time = dates[0]
    #else:
    #    event_time = "1 minute"
    time_in_seconds = (parse("in {0}".format(event_time)) - datetime.datetime.now()).total_seconds()
    log.info("Alert text is {0}".format(time_message))
    #Set the reminder using the events framework
    alert_time = time.time()+time_in_seconds
    log.info("Alert time is {0}, time is {1}, time_in seconds is {2}".format(alert_time, time.time(), time_in_seconds))
    event_id = tools.get_event_uid("notification")
    core.events.append({
        "username": event["session"]["username"],
        "time": time.time()+time_in_seconds,
        "value": time_message,
        "type": "notification",
        "uid": event_id
    })
    response["text"] = "Got it. I'll send you the following reminder: {0}".format(time_message)
    return response
