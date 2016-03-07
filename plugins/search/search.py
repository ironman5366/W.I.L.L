#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2
import urllib
import re
import os
import wolframalpha
import config
# import TTS_Talk
import json as m_json
import builtins.search.wcycle as wcycle
from logger import log
# app_id number 2 : TWH856-2RPQQX96K


def wlfram_search(user_query, appid):
    log.info("in wolfram search")
    log.info(user_query)
    try:
        client = wolframalpha.Client(appid)
        res = client.query(user_query)
        if next(res.results).text != 'None':
            # for i in res.pods:
            # print "\n"
            # print i.text
            #			phrase = str(next(res.results).text)
            #			TTS_Talk.tts_talk(phrase)
            print next(res.results).text
            assert isinstance(next(res.results).text, object)
            return next(res.results).text
        else:
            google_search(user_query)
    except StopIteration:
        log.info("Hit stop iteration, going into google search")
        return google_search(user_query)


def skwiki(titlequery):
    log.info("in skwiki")
    log.info(titlequery)
    assert isinstance(titlequery, object)
    path = os.getcwd()
    path += ("/plugins/search/")
    oscmd = "python " + path + "getsummary.py %s" % titlequery
    # I don't know why I had to do it like this but theres a dictionary in the
    # wikipedia module that the summary cannot be extracted from in an import
    resultvar = os.popen(oscmd).read()
    log.info("result fetched")
    log.info(str(resultvar))
    #	phrase = "According to wikipedia " + wikipedia.summary(titlequery, sentences=1)
    #	pattern = re.compile('/.*?/')
    #	phrase = re.sub(pattern,'',phrase)
    #	pattern = re.compile('\(.*?\)')
    #	phrase = re.sub(pattern,'',phrase)
    #    	TTS_Talk.tts_talk(phrase)
    return resultvar.decode('utf8')


def print_gsearch(results):
    import requests
    log.info("In print_gsearch")
    for result in results:
        title = result['title']
        log.info(title)
        url = result['url']
        log.info(url)
        r = requests.get(url).text
        log.info("Got html from {0}".format(url))
        textresult = None
        for line in r.split('\n'):
            line = line.encode('ascii', 'ignore')
            line = str(line.decode('utf8'))
            log.info("Analyzing line {0}".format(line))
            if "h1" not in line:
                if "<p>" in line and "</p>" in line:
                    textresult = line.split("<p>")[1].split("</p>")[0]
                    pattern = re.compile('<.*?>')
                    textresult = re.sub(pattern, '', textresult)
                    log.info("Text result is {0}".format(
                        textresult))
                    break
        if textresult != None:
            phrase = "According to {0}, {1}".format(url, textresult)
            return (phrase).decode('utf8')
        else:
            return ("Could not successfully extract information from {0}".format(url))
        #pattern = re.compile('<.*?>')
        #title = re.sub(pattern, '', title)
        #logs.write(title, 'working')


def google_search(user_query):
    log.info("In google search with query: " + str(user_query))
    query = user_query
    query = urllib.urlencode({'q': query})
    response = urllib2.urlopen(
        'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&' + query).read()
    json = m_json.loads(response)
    results = json['responseData']['results']
    wiki_bool = False
    for result in results:
        title = result['title']
        url = result['url']
        pattern = re.compile('<.*?>')
        title = re.sub(pattern, '', title)
        if "Wikipedia, the free encyclopedia" in title:
            log.info("wiki_bool is true")
            titlelst = title.split('-')
            titlequery = titlelst[0].strip()
            return skwiki(titlequery)
            wiki_bool = True
            break

    if wiki_bool == False:
        log.info("wiki_bool is false")
        return print_gsearch(results)


def main(query):
    query = query[0]
    firstword = query.split(' ')[0]
    firstlower = firstword.lower()
    if firstlower == "search" or firstlower == "google":
        query = query.split(firstword + " ")[1]
    log.info("In main, query is:" + str(query))
    appid = config.load_config()["wolfram"]["keys"][0]
    print "going into wolfram search"
    answer = wlfram_search(query, appid)
    return answer
