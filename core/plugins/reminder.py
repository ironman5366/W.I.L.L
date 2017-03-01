# Builtin imports
import logging
import time

# Internal imports
import core
from core.plugin_handler import subscribe
import tools
import datetime
import traceback
import sys

#External imports
from dateparser import parse
from pytz import timezone

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
    event_time = None
    for chunk in event_doc:
        # Use dependency parsing to dermine the object of the command
        if chunk.dep_ == "xcomp" or chunk.dep_ == "advcl":
            lefts = [left.orth_ for left in chunk.lefts]
            rights = [right.orth_ for right in chunk.rights]
            time_message = " ".join(lefts+[chunk.text]+rights)
        elif chunk.dep_ == "pobj" or chunk.dep_ == "npadvmod":
            lefts = [left.orth_ for left in chunk.lefts]
            rights = [right.orth_ for right in chunk.rights]
            event_time = " ".join(lefts + [chunk.text] + rights)
            #Break out of the loop so the event time is the first matching word
            if time_message:
                break
    if not time_message:
        time_message == "Reminder: {0}".format(event_command)
    if not event_time:
        if times:
            event_time = times[0]
        elif dates:
            event_time = dates[0]
        else:
            event_time = "1 minute"
    try:
        user_timezone = event["user_table"]["timezone"]
        log.debug("User timezone is {0}".format(user_timezone))
    except:
        response["text"] = "Error: wasn't able to parse a timezone for the user"
        response["type"] = "error"
        return response
    tz = timezone(user_timezone)
    datetime_tz = datetime.datetime.now(tz)
    tzname = datetime_tz.tzinfo._tzname
    time_word = "in"
    for word in event["doc"]:
        if word.tag_ == "IN":
            time_word = word.orth_
            log.debug("using time word {0}".format(time_word))
    try:
        #If the event time looks like a numerical time (ex: 1:00), and it's in 12 hour format w/o AM or PM, check whether noon or midnight is closer
        if ":" in event_time and len(event_time)<5:
            col_split = event_time.split(":")
            col_split_pre = col_split[0]
            #If it's a number
            log.debug("Checking for 12 hour time")
            if col_split_pre.isdigit():
                hour_num = int(col_split_pre)
                log.debug("Checking hour {0}".format(hour_num))
                if hour_num < 12:
                    event_time+=" PM"
        parse_time_str = "{0} {1} {2}".format(time_word, event_time, tzname)
        log.debug("Parse time str is {0}".format(parse_time_str))
        time_in_seconds = (
            parse(
                parse_time_str,
                settings={
                    "RETURN_AS_TIMEZONE_AWARE": True
                }
            )
            - datetime_tz).total_seconds()
    except:
        traceback.print_exc(sys.stdout)
        response["text"] = "Couldn't parse a time from {0}".format(event_time)
        response["type"] = "error"
        return response
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
    response["text"] = "Got it. I'll send you the following reminder: {0} {1} {2}".format(time_message, time_word,  event_time)
    return response
