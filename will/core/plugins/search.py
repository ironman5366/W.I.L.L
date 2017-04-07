# Internal imports
# Builtin imports
import logging

import google
import requests
import wikipedia
# External imports
import wolframalpha
from bs4 import BeautifulSoup
from core.plugin_handler import subscribe
from newspaper import Article

from will import tools

log = logging.getLogger()

def search_google(query):
    '''Search google and determine if wikipedia is in it'''
    search_object = google.search(query)
    #Determine if a wikipedia url is in the first 5 searches
    urls = []
    for i in range(0, 4):
        url = search_object.__next__()
        urls.append(url)
        if "wikipedia.org/wiki" in url:
            wikipedia_search = wikipedia.search(query)[0]
            url = wikipedia.page(wikipedia_search).url
            response = wikipedia.summary(wikipedia_search) + " ({0})".format(url)
            return response
    #If there were no wikipedia pages
    first_url = urls[0]
    try:
        article = Article(first_url)
        article.download()
        article.parse()
        article.nlp()
        article_summary = article.summary
        article_title = article.title
        return "{0}\n{1} - ({2})".format(
            article_summary, article_title, first_url
        )

    except Exception as article_exception:
        try:
            log.debug("Got error {0}, {1} while using newspaper, switching to bs4".format(
            article_exception.message,article_exception.args
            ))
            html = requests.get(first_url).text
            #Parse the html using bs4
            soup = BeautifulSoup(html, "html.parser")
            [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
            text = soup.getText()
         # break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # drop blank lines
            soup_text = '\n'.join(chunk for chunk in chunks if " " in chunk)
            response = format(soup_text) + " ({0})".format(first_url)
            return response
        except Exception as search_exception:
            log.info("Error {0},{1} occurred while searching query {2}".format(
                search_exception.message, search_exception.args, query
            ))
            return "Error encountered on query {0}".format(query)
def search_wolfram(query, api_key):
    '''Search wolframalpha'''
    client = wolframalpha.Client(api_key)
    # Santize query
    res = client.query(query)
    try:
        next_result = next(res.results).text
        if next_result:
            # Sanitze result
            log.debug("Sanitized wolfram result is {0}".format(next_result))
            return next_result
        else:
            return False
    except StopIteration:
        log.error("StopIteration raised with wolfram query {0}".format(
            query
        ))
        return False
    except AttributeError:
        return False


def is_search(event):
    '''Determine whether it's a search command'''
    command = event["command"]
    if "search" in event["verbs"]:
        return True
    question_words = [
        "what",
        "when",
        "why",
        "how",
        "who",
        "are",
        "is"
    ]
    first_word = command.split(" ")[0].lower()
    log.debug("First word in command is {0}".format(first_word))
    if first_word in question_words:
        return True
    return False


@subscribe(name="search", check=is_search)
def main(data):
    '''Start the search'''
    response = {"text": None, "data":{}, "type": "success"}
    query = data["command"]
    log.info("In main search function with query {0}".format(query))
    db = data["db"]
    answer = False
    wolfram_key = tools.load_key("wolfram", db)
    wolfram_response = search_wolfram(query, wolfram_key)
    # If it found an answer answer will be set to that, if not it'll still be false
    answer = wolfram_response
    if answer:
        response["text"] = answer
    else:
        response["text"]=search_google(query)
    return response
