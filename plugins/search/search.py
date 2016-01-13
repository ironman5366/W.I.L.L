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
from logs import logs as log
logs=log()
# app_id number 2 : TWH856-2RPQQX96K
def wlfram_search(user_query,appid):
    logs.write("in wolfram search",'working')
    logs.write(user_query,'working')
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
        logs.write("Hit stop iteration, going into google search", 'working')
        return google_search(user_query)


def skwiki(titlequery):
    logs.write("in skwiki", 'working')
    logs.write(titlequery, 'working')
    assert isinstance(titlequery, object)
    path=os.getcwd()
    path+= ("/plugins/search/")
    oscmd="python "+path+"getsummary.py %s" %titlequery
    resultvar=os.popen(oscmd).read()  #I don't know why I had to do it like this but theres a dictionary in the wikipedia module that the summary cannot be extracted from in an import
    logs.write("result fetched", 'success')
    logs.write(str(resultvar), 'success')
    #	phrase = "According to wikipedia " + wikipedia.summary(titlequery, sentences=1)
    #	pattern = re.compile('/.*?/')
    #	phrase = re.sub(pattern,'',phrase)
    #	pattern = re.compile('\(.*?\)')
    #	phrase = re.sub(pattern,'',phrase)
    #    	TTS_Talk.tts_talk(phrase)
    return resultvar.decode('utf8')


def print_gsearch(results):
    import requests
    logs.write("In print_gsearch", 'working')
    for result in results:
        title = result['title']
        logs.write(title, 'working')
        url = result['url']
        logs.write(url, 'working')
        r=requests.get(url).text
        logs.write("Got html from {0}".format(url),'success')
        textresult=None
        for line in r.split('\n'):
            line=line.encode('ascii','ignore')
            line=str(line.decode('utf8'))
            logs.write("Analyzing line {0}".format(line), 'trying')
            if "h1" not in line:
                if "<p>" in line and "</p>" in line:
                    textresult=line.split("<p>")[1].split("</p>")[0]
                    pattern = re.compile('<.*?>')
                    textresult = re.sub(pattern,'',textresult)
                    logs.write("Text result is {0}".format(textresult), 'success')
                    break
        if textresult!=None:
            phrase="According to {0}, {1}".format(url,textresult)
            return (phrase).decode('utf8')
        #pattern = re.compile('<.*?>')
        #title = re.sub(pattern, '', title)
        #logs.write(title, 'working')
        


def google_search(user_query):
    logs.write("In google search with query: "+str(user_query), 'working')
    query = user_query
    query = urllib.urlencode({'q': query})
    response = urllib2.urlopen('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&' + query).read()
    json = m_json.loads(response)
    results = json['responseData']['results']
    wiki_bool = False
    for result in results:
        title = result['title']
        url = result['url']
        pattern = re.compile('<.*?>')
        title = re.sub(pattern, '', title)
        if "Wikipedia, the free encyclopedia" in title:
            logs.write("wiki_bool is true", 'working')
            titlelst = title.split('-')
            titlequery = titlelst[0].strip()
            return skwiki(titlequery)
            wiki_bool = True
            break

    if wiki_bool == False:
        logs.write("wiki_bool is false", 'working')
        return print_gsearch(results)


def main(query):
    query=query[0]
    firstword=query.split(' ')[0]
    firstlower=firstword.lower()
    if firstlower=="search" or firstlower=="google":
        query=query.split(firstword+" ")[1]
    logs.write("In main, query is:"+str(query), 'working')
    wcycle.main()
    appid = open('builtins/search/appidfinal.txt').read().rstrip()
    print "going into wolfram search"
    answer= wlfram_search(query,appid)
    return answer
