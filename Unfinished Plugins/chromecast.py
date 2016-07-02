from __future__ import print_function
import time
import pychromecast
from will import config
#TODO: remove this eventually
import easygui

from splinter import Browser

#TODO: eventually do this as part of the framework insetad of a standalone ui

#@API.subscribe_to({
#"name": "cast",
#"ents_needed" : ["ORG"],
#"structure" : {"needed":["VERB"]},
#"questions_needed" : False,
#"key_words" : ["cast", "netflix", "hulu", "hbo"]})
#TODO: Finish the cast function and add netflix support via splinter
def main(leader, sentence, *args, **kwargs):
    def cast(chromecast):
        cast = pychromecast.get_chromecast(friendly_name=chromecast)
        cast.wait()
        if leader == "netflix" or sentence.split(" ")[1] == "netflix" or "netflix" in args["ents"].keys().lower():
            pass
            #TODO: add netflix code here
    known_chromecasts = config.load_config("chromecasts")
    chromecasts_available = pychromecast.get_chromecasts_as_dict().keys()
    chromecast_name = None
    for chromecast in chromecasts_available:
        if isinstance(known_chromecasts, list):
            if chromecast in known_chromecasts:
                chromecast_name = chromecast
        elif isinstance(known_chromecasts, str):
            if chromecast == known_chromecast:
                chromecast_name = chromecast
        else:
            return "Error: unrecognized chromecast conifg {0}".format(str(known_chromecasts))
    if chromecast_name:
        cast(chromecast_name)
    else:
        chromecast_choice = easygui.buttonbox(title="Chromecasts Found", msg="Please choose a chromecast", choices=chromecasts_available)
        if chromecast_choice:
            if easygui.ynbox("Would you like to save this chromecast in your W.I.L.L config?"):
                config.add_config({"known_chromecasts":[chromecast_choice]})
        cast(chromecast_choice)
        else:
            return "Error: No chromecast chosen"
    cast.wait()
    print(cast.device)

    print(cast.status)

    mc = cast.media_controller
    mc.play_media('http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', 'video/mp4')
    print(mc.status)

    mc.pause()
    time.sleep(5)
    mc.play()