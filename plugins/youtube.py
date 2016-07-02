import urllib
import urllib2
import re
import webbrowser
import will.plugins.API as API


@API.subscribe_to({
"name": "youtube",
"ents_needed" : False,
"structure" : {"needed":False},
"questions_needed" : False,
"key_words" : ["youtube"]})
def youtube(key_word, search_string):
    query_string = urllib.urlencode({"search_query": search_string})
    html_content = urllib2.urlopen(
        "http://www.youtube.com/results?" + query_string)
    search_results = re.findall(
        r'href=\"\/watch\?v=(.{11})', html_content.read().decode('utf-8'))
    vidurl1 = ("http://www.youtube.com/watch?v=" + search_results[0])
    webbrowser.open(vidurl1)
