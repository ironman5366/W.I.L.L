#Internal modules
import will.plugins.API as API
import will.config as config
from will.logger import log

#External modules
import requests
import wolframalpha
import wikipedia
import google as g_search
from bs4 import BeautifulSoup

#Internal modules
import threading
import time

#TODO: document this more


search_threads_done = {
    "wolfram" : False,
    "wiki" : False,
    "google" : False,
}

g_threads_done = {}

def parser(first_word, full_text, args, dispatcher_args):
    '''Function to determine which of the results to return'''
    log.info("In parser")
    similarities = {}
    parsing_done = {
        "wolfram" : False,
        "wiki" : False,
        "google" : False
    }
    ents = args['ents']
    struct = args['struct']
    signal = dispatcher_args['signal']
    t_lower = full_text.lower()
    words = full_text.split(' ')
    def sim_check(check_str, service):
        '''Check for similarities'''
        global full_text
        log.info("Signal is {0}, first_word is {1}".format(signal, first_word))
        if signal.lower() == first_word.lower():
            full_text = full_text.replace(first_word, '')
        sim_n = 0
        # Check to see if the user explicitly requested one of the services
        if service.lower() in signal.lower():
            sim_n += 2
        for ent_word,ent_type in ents:
            #Filter out the entity types that I don't want
            unwanted_ents = [
                "DATE",
                "TIME",
                "PERCENT",
                "QUANTITY",
                "ORDINAL",
                "CARDINAL",
                "MONEY",
                "LANGUAGE"
            ]
            if ent_type not in unwanted_ents:
                log.info("Looking at word {0}".format(str(ent_word)))
                if ent_word in words[-1]:
                    if ent_word.lower() in check_str.lower():
                        sim_n+=4
                else:
                    if ent_word.lower() in check_str.lower():
                        sim_n+=2

        return sim_n

    while False in parsing_done.values():
        if search_threads_done["wolfram"]:
            wolfram_results = search_threads_done["wolfram"]
            similarities.update({wolfram_results:0})
            sim_n = sim_check(wolfram_results,"wolfram")
            similarities[wolfram_results]+=sim_n
        if search_threads_done["wiki"]:
            wiki_results = search_threads_done["wiki"]
            similarities.update({wiki_results:0})
            sim_n = sim_check(wiki_results,"wiki")
            similarities[wiki_results]+=sim_n
        if search_threads_done["google"]:
            google_results = search_threads_done["google"]
            for result in google_results:
                similarities.update({result:0})
                sim_n = sim_check(result, "google")
                similarities[result]+=sim_n
    log.info("Similarities is {0}".format(str(similarities)))
    sim_highest = max(similarities.values())
    log.info("Sim highest is {0}".format(sim_highest))
    for result, num in similarities:
        if num == sim_highest:
            log.info("Returning result {0}".format(str(result)))
            return result

class search():
    '''Contains functions for all of the various types of searches'''

    def wiki(self, search_item):
        '''Search wikipedia'''
        global search_threads_done
        log.info("In wiki with search_item {0}".format(str(search_item)))
        log.info("Suggesting article")
        suggested_article = wikipedia.suggest(search_item)
        if suggested_article:
            title = suggested_article
        else:
            log.info("No suggestion was found")
            title_items = wikipedia.search(search_item)
            log.info("Searched wikipedia for {0}, found articles {1}".format(search_item, title_items))
            if len (title_items) > 0:
                #TODO: possibly, in the future, ask the user which of these they want or do manual parsing
                title = title_items[0]
        log.info("Loading summary of article {0}".format(str(title)))
        summary = wikipedia.summary(title, sentences=2)
        log.info("Got summary {0}".format(str(summary)))
        if summary:
            search_threads_done["wiki"] = summary
        else:
            search_threads_done["wiki"] = None

    def wolfram(self, search_item):
        '''Search wolframalpha using the keys in the config file'''
        global search_threads_done
        log.info("In wolfram with search_item {0}".format(str(search_item)))
        wolfram_config = config.load_config("wolfram")
        if wolfram_config:
            key_list = wolfram_config['keys']
            for key in key_list:
                try:
                    client = wolframalpha.Client(key)
                    client.query("test")
                    break
                except Exception as key_exception:
                    log.info("Can not use key {0}".format(key))
                    search_threads_done["wolfram"] = None
            if client:
                log.info("Starting wolfram search")
                try:
                    query = client.query(search_item)
                    query_results = query.results
                    if next(query_results) != "None":
                        assert isinstance(next(query_results).text, object)
                        search_threads_done['wolfram'] = next(query_results).text
                    else:
                        log.info("No usable results")
                        search_threads_done["wolfram"] = None
                except StopIteration as stop_iter_error:
                    log.info("Hit StopIteration in wolfram_search")
                    search_threads_done["wolfram"] = None
            else:
                log.info("Error: could not start client with any of the keys in config file")
                search_threads_done["wolfram"] = None
        else:
            log.info("Wolfram configuration could not be loaded")
            search_threads_done["wolfram"] = None

    def google(self, search_item, nlp_data):
        '''Search google'''
        global g_threads_done
        log.info("In google with search item {0}, and nlp args {1}".format(search_item, str(nlp_args)))
        search_results = g_search.search(query=search_item, stop=20)
        log.info("Did google search. Search results are {0}".format(str(search_results)))
        return_results = []
        def check_url(url):
            '''Check the url for similarities with the search term'''
            log.info("In check_url with url {0}".format(url))
            try:
                page = requests.open(url)
                page_html = page.html
                #Parse the page with bs4
                log.info("Loading the html of {0} into bs4".format(url))
                s_page = BeautifulSoup(page_html)
                s_lower = search_item.lower()
                ents = nlp_data['ents']
                struct = nlp_data['struct']
                words = search_item.split(' ')
                punctuation = ['.',';','?','!']
                #Very basic parsing. More comprehensive parsing will be done later
                for word in words:
                    if punctuation in word:
                        word = word.replace(word[-1],'')
                for p in s_page.find_all('p'):
                    p_str = p.string
                    if "{0} is".format(words[-1].lower()) in p_str.lower():
                        return_results.append(p_str)
                        break
                    for e in ents.keys():
                        if e.lower() in p_str.lower():
                            return_results.append(p_str)
                            break
                    for w,t in struct:
                        if t == "NN":
                            if w.lower() in p_str.lower():
                                return_results.append(p)
                                break
            except Exception as request_exception:
                log.info("Could not connect to url {0}".format(str(url)))
            finally:
                global g_threads_done
                g_threads_done[url] = True
        for result in search_results:
            g_threads_done.update({result : False})
            r_thread = threading.Thread(target=check_url(result))
            r_thread.start()
        while True:
            if False in g_threads_done.values():
                time.sleep(0.001)
            else:
                break
        search_threads_done['google'] = return_results

@API.subscribe_to(
    {
        "name" : "search",
        "structure" : {"needed" : False},
        "ents_needed" : False,
        "questions_needed" : True,
        "key_words" : ["google", "search", "wikipedia", "wiki", "wolframalpha", "wolfram"]
    }
)
def search_main(first_word, sentence, *args, **kwargs):
    log.info("In search module")
    global search_threads_done
    search_threads_done = {
        "wolfram" : False,
        "google" : False,
        "wiki" : False
    }
    wolfram_thread = threading.Thread(target=search().wolfram(sentence))
    wiki_thread = threading.Thread(target=search().wiki(sentence))
    google_thread = threading.Thread(target=search().google(sentence,args))
    wolfram_thread.start()
    wiki_thread.start()
    google_thread.start()
    result = parser(first_word,sentence,args,kwargs)
    log.info("Finishing search module with result {0}".format(str(result)))
    return result