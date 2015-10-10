__author__ = 'willb'
# -*- coding: utf-8 -*-
import wikipedia
import sys
titlequery=sys.argv[1:]
print wikipedia.summary(titlequery,sentences=2).encode("ascii", "ignore")