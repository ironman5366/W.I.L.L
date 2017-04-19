#Builtin imports
import logging

# Internal imports
from will.core.plugin_handler import *
from will.core import arguments

# External imports
import pyowm

log = logging.getLogger()

class Weather(Plugin):

    name = "weather"
    arguments = [arguments.Location, arguments.TempUnit, arguments.WeatherAPI]

    def exec(self, **kwargs):
        # Execute the location argument
        location = kwargs["Location"]
        api_key = kwargs["WeatherAPI"]
        temp_unit = kwargs["TempUnit"]
        owm = pyowm.OWM(api_key)
        observation = owm.weather_at_place(location)
        w = observation.get_weather()
        status = w.get_detailed_status()
        temperature = w.get_temperature(temp_unit)
        weather_str = "Weather for {0} is {1}, with a temperature of {2} {3}".format(
            location, status, temperature["temp"], temp_unit)
        return weather_str