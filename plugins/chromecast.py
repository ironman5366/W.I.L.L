from __future__ import print_function
import time
import pychromecast
from will import config
#TODO: remove this eventually
import easygui
import keyring
from will.logger import log
import will.plugins.API as API

from splinter import Browser

#TODO: eventually do this as part of the framework insetad of a standalone ui

def get_shows(ents):
    works_of_art = []
    for e_name, e_type in ents:
        if e_type == "WORK_OF_ART":
            log.info("Appending {0} to works of art".format(e_name))
            works_of_art.append(e_name)
    return works_of_art

#TODO: Finish the cast function and add netflix support via splinter
#TODO: Eventually ask for netflix credentials when they aren't found
def netflix(sentence, args):
    netflix_config = config.load_config("netflix")
    if netflix_config:
        username = netflix_config['username']
        password = keyring.get_password("netflix", username)
        profile_name = netflix_config["profile_name"]
        if username and password:
            #TODO: change this to zope.testbrowser once it's working in the frontend
            chrome_path = config.load_config("chrome_path")
            executable_path = {'executable_path': chrome_path}
            browser = Browser("Chrome")
            browser.visit("https:///netflix.com/Login")
            email_field = browser.find_by_name("email")
            password_field = browser.find_by_name("password")
            sign_in_xpath = '//*[@id="appMountPoint"]/div/div[2]/div/form[1]/button'
            sign_in_button = browser.find_by_xpath(sign_in_xpath)
            email_field.fill(username)
            password_field.fill(password)
            sign_in_button.click()
            if browser.is_text_present(profile_name):
                profile_button = browser.find_by_text(profile_name)
                profile_button.click()
                #Use ent code to find out if there's a named work of art that was detected
                #search_tab_xpath = '//*[@id="hdPinTarget"]/div/div[1]/div/button'
                #search_tab_xpath = '//*[@id="hdPinTarget"]/div/div[1]/div/button/span[1]'
                search_tab_xpath = '//*[@id="hdPinTarget"]/div/div[1]/div/button'
                search_tab = browser.find_by_xpath(search_tab_xpath)
                search_tab.click()
                if "netflix" in sentence:
                    if "netflix play "in sentence:
                        show = sentence.split("netflix play ")[1]
                    else:
                        show = sentence.split("netflix ")[1]
                    #search_field = browser.find_by_text("Titles, people, genres")[0]
                    search_field_xpath = '//*[@id="hdPinTarget"]/div/div[1]/div/div/input'
                    search_field = browser.find_by_xpath(search_field_xpath)
                    search_field.fill(show)
                    show_card_xpath = '//*[@id="title-card-undefined-0"]'
                    show_card = browser.find_by_xpath(show_card_xpath)
                    show_card.click()
                    play_icon_xpath = '//*[@id="title-card-undefined-0"]/div[2]/a/div/div'
                    play_icon = browser.find_by_xpath(play_icon_xpath)
                    play_icon.click()
                    play_button_xpath = '//*[@id="70279852"]/div[2]/a/div/div'
                    play_button = browser.find_by_xpath(play_button_xpath)
                    play_button.click()
                    #chromecast_button_xpath = '//*[@id="netflix-player"]/div[4]/section[2]/div[7]/div[2]/button'
                    #chromecast_button = browser.find_by_xpath(chromecast_button_xpath)
                    #chromecast_button.click()
                    return "Done"
            else:
                return "Profile {0} could not be found on the netflix page".format(str(profile_name))
        else:
            return "Netflix username and password could not be retrieved from config and keyring"
    else:
        return "Netflix config not found"
@API.subscribe_to({
"name": "cast",
"ents_needed" : False,
"structure" : {"needed":[]},
"questions_needed" : False,
"key_words" : ["cast", "netflix", "hulu", "hbo"]})
def cast_main(leader, sentence, *args, **kwargs):
    log.info("In cast")
    def cast(chromecast):
        #cast = pychromecast.get_chromecast(friendly_name=chromecast)
        #cast.wait()
        if leader == "netflix" or sentence.split(" ")[1] == "netflix" or "netflix" in args["ents"].keys().lower():
            log.info("Sentence is {0}".format(sentence))
            netflix(sentence, args)
    known_chromecasts = config.load_config("chromecasts")
    log.info("Known chromecasts are {0}".format(str(known_chromecasts)))
    chromecasts_available = pychromecast.get_chromecasts_as_dict().keys()
    chromecast_name = None
    for chromecast in chromecasts_available:
        if isinstance(known_chromecasts, list):
            if chromecast in known_chromecasts:
                chromecast_name = chromecast
        elif isinstance(known_chromecasts, str):
            if chromecast == known_chromecasts:
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
    # cast.wait()
    # print(cast.device)
    #
    # print(cast.status)
    #
    # mc = cast.media_controller
    # mc.play_media('http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', 'video/mp4')
    # print(mc.status)
    #
    # mc.pause()
    # time.sleep(5)
    # mc.play()