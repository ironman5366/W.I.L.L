#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib2
import urllib
import re
import os
import wolframalpha
# import TTS_Talk
import json as m_json
import builtins.search.wcycle as wcycle


# app_id number 2 : TWH856-2RPQQX96K
def wlfram_search(user_query, appid):
    print "in wolfram search"
    print user_query
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
        print "Hit stop iteration, going into google search"
        return google_search(user_query)


def skwiki(titlequery):
    print "in skwiki"
    print titlequery
    assert isinstance(titlequery, object)
    path = os.getcwd()
    path += ("/builtins/search/")
    oscmd = "python " + path + "getsummary.py %s" % titlequery
    print oscmd
    # I don't know why I had to do it like this but theres a dictionary in the
    # wikipedia module that the summary cannot be extracted from in an import
    resultvar = os.popen(oscmd).read()
    print "result fetched"
    print str(resultvar)
    #	phrase = "According to wikipedia " + wikipedia.summary(titlequery, sentences=1)
    #	pattern = re.compile('/.*?/')
    #	phrase = re.sub(pattern,'',phrase)
    #	pattern = re.compile('\(.*?\)')
    #	phrase = re.sub(pattern,'',phrase)
    #    	TTS_Talk.tts_talk(phrase)
    return resultvar.decode('utf8')


def print_gsearch(results):
    phrase = "I was unable to find an answer. Here are some links on the subject"
    # TTS_Talk.tts_talk(phrase)
    for result in results:
        title = result['title']
        url = result['url']
        pattern = re.compile('<.*?>')
        title = re.sub(pattern, '', title)
        return (title).decode('utf8')


def google_search(user_query):
    print "In google search with query: " + str(user_query)
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
            print "wiki_bool is true"
            titlelst = title.split('-')
            titlequery = titlelst[0].strip()
            return skwiki(titlequery)
            wiki_bool = True
            break

    if wiki_bool == False:
        print "wiki_bool is false"
        print_gsearch(results)


def main(query):
    query = query[0]
    print "In main, query is:" + str(query)
    wcycle.main()
    appid = open('builtins/search/appidfinal.txt').read().rstrip()
    print "going into wolfram search"
    answer = wlfram_search(query, appid)
    return "answer:;:;:" + answer
