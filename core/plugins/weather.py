#Internal imports
from core.plugin_handler import subscribe
import tools
#External imports
import pyowm

def is_weather(event):
    '''Determine whether to read the news'''
    event_words = [token.orth_.lower() for token in event["doc"]]
    return "weather" in event_words

@subscribe({"name": "weather", "check": is_weather})
def main(event):
    '''Get the users weather from the infromation in the users database'''
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
        return w
    else:
        #TODO: try to use ip data
        return "Can't find location data for user. If you haven't added your location yet, do so now at " \
               "http://willbeddow.com/settings"

