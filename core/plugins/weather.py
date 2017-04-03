# Internal imports
from core.plugin_handler import subscribe
import tools

#Builtin imports
import logging
import traceback
import sys

# External imports
import pyowm

log = logging.getLogger()

def is_weather(event):
    '''Determine whether to read the news'''
    event_words = [token.orth_.lower() for token in event["doc"]]
    return "weather" in event_words

def set_country(response_value, event):
    """
    Set the user country and rerun the main weather function with the event

    :param response_value:
    :param event:
    :return:
    """
    response = {"text": None, "type": None, "data": {}}
    session_id = event["session"]["id"]
    log.info(":{0}:Got country {1}, rerunning main weather function".format(session_id, response_value))
    db = event["db"]
    db.begin()
    try:
        if tools.check_string(response_value):
            user_table = event["user_table"]
            username = user_table["username"]
            db["users"].update({"country": response_value, "username": username}, ["username"])
            db.commit()
            log.info(":{0}:Country {1} set succesfully".format(session_id, response_value))
            #Rerun the weather function
            weather_response = weather_main(event)
            return weather_response
        else:
            db.rollback()
            response["text"] = "Country {0} failed string validation".format(response_value)
            response["type"] = "error"
    except:
        db.rollback()
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_string = repr(traceback.format_exception(exc_type, exc_value,
                                                       exc_traceback))
        is_admin = user_table["admin"]
        # If the user is an admin, give them the full error string
        if is_admin:
            response["text"] = error_string
        else:
            response["text"] = "An error occurred while trying to set your country. Please contact me at " \
                                   "will@willbeddow.com to notify me of the issue."
    return response

def ask_country(response_value, event):
    """
    The object of a response listener, set the city that the user specified and set another response listener for the country

    :param response_value:
    :param event:
    :return response listender object:
    """
    response = {"type": None, "text": None, "data": {}}
    session_id = event["session"]["id"]
    log.info(":{0}:Setting city to {1}, asking country".format(session_id, response_value))
    #Set the city in the database
    if tools.check_string(response_value):
        db = event["db"]
        db.begin()
        try:
            db["users"].update({"city": response_value, "username": event["user_table"]["username"]}, ["username"])
            db.commit()
            #Now that the city is set, ask the user for their country and create another response listener
            response["type"] = "success"
            response["text"] = "What country are you in?"
            command_id = event["command_id"]
            tools.set_response(session_id, command_id, event, set_country)
            response["data"] = {"response": command_id}
        except:
            db.rollback()
            user_table = event["user_table"]
            is_admin = user_table["admin"]
            response["type"] = "error"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error_string = repr(traceback.format_exception(exc_type, exc_value,
                                                           exc_traceback))
            #If the user is an admin, give them the full error. Otherwise, just log the error and tell the user that an error occurred
            if is_admin:
                response["text"] = error_string
            else:
                response["text"] = "An error occurred while trying to set your city. Please contact me at " \
                                   "will@willbeddow.com to notify me of the issue."
            log.debug(":{0}:Error occurred while setting city. Error traceback: {1}".format(session_id, error_string))
    else:
        response["type"] = "error"
        response["text"] = "City {0} failed string validation".format(response_value)
    return response

@subscribe(name="weather", check=is_weather)
def weather_main(event):
    '''Get the users weather from the infromation in the users database'''
    log.info("This function is {0}".format(weather_main))
    response = {"type": "success", "text": None, "data": {}}
    db = event["db"]
    username = event["username"]
    user_table = db["users"].find_one(username=username)
    if (user_table["city"] and user_table["country"]):
        if user_table["state"]:
            fetch_str = "{0}, {1}".format(user_table["city"], user_table["state"])
        else:
            fetch_str = "{0}, {1}".format(user_table["city"], user_table["country"])
        pyowm_key = tools.load_key("pyowm", db)
        owm = pyowm.OWM(pyowm_key)
        observation = owm.weather_at_place(fetch_str)
        w = observation.get_weather()
        status = w.get_detailed_status()
        temp_sym = "F"
        if "temp_unit" in user_table.keys():
            user_temp_unit = user_table["temp_unit"]
            temperature = w.get_temperature(user_temp_unit)
            if user_temp_unit == "celsius":
                temp_sym = "C"
        else:
            temperature = w.get_temperature('fahrenheit')

        weather_str = "Weather for {0} is {1}, with a temperature of {2} {3}".format(
            fetch_str, status, temperature["temp"], temp_sym)
        response["text"] = weather_str
    else:
        response["type"] = "success"
        command_id = event["command_id"]
        session_id = event["session"]["id"]
        response["text"] = "What city are you in?"
        #Add a pointer to this function to the event, because for some reason the code in the above function can't find it
        tools.set_response(session_id, command_id, event, ask_country)
        response["data"] = {"response": command_id}
    return response