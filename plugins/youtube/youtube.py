from lxml import etree
import os
import urllib
import urllib2
import os
import re
import webbrowser

def youtube(vidsearch):
    query_string = urllib.urlencode({"search_query": vidsearch})
    html_content = urllib2.urlopen("http://www.youtube.com/results?" + query_string)
    search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content.read().decode('utf-8'))
    vidurl1 = ("http://www.youtube.com/watch?v=" + search_results[0])
    webbrowser.open(vidurl1)


def main(*args):
    q = args[0]
    print q
    youtube(q)
    return "Done"