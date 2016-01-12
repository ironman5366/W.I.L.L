__author__ = 'willb'
# -*- coding: utf-8 -*-
import wikipedia
import sys
wikiquery=sys.argv[1:]
try:
    print wikipedia.summary(wikiquery,sentences=2).encode("ascii", "ignore")
except wikipedia.exceptions.DisambiguationError as e:
    print wikipedia.summary(e.options[0],sentences=2).encode("ascii", "ignore")
