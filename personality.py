from datetime import datetime
import os
import random
greetfile = open("personality.txt").read()
greetings = greetfile.split('\n')


def get_greet(f):
    '''Fair warning. This module is awful. It's really really messy and has horrible variable names.
    I wrote it awhile ago as a temporary module and since I plan to add a more detailed personality in down the road I've never fixed it. 
    If you plan on reading this I'm sorry.'''
    # Get time and determine environmental variables
    t = str(datetime.now())
    tt = t.split(' ')
    ttt = tt[1].split(':')
    tf = int(ttt[0])
    if tf < 12:
        lt = "Morning"
    elif tf > 17:
        lt = "Night"
    else:
        lt = "Afternoon"

    # Open the file with the string to output
    o = open("output.txt").read()
    ol = o.split('\n')
    olpn = int(ol[0].split('polite=')[1])
    olhn = int(ol[1].split('humor=')[1])
    p = []
    # I have no clue about his section, I really hate myself for writing it.
    # It's awful I know and just the worst. I have no idea why it works.
    for l in greetings:
        try:
            v = l.split(':')[1]
            k = l.split(':')[0]
            vf = v.split(',')
            if vf[0] == lt or vf[0] == 'Neutral':
                vfp = vf[1].split(';')
                vfpn = int(vfp[0].split('polite=')[1])
                if olpn == vfpn or olpn == vfpn - 1 or olpn == vfpn + 1 or olpn == vfpn - 2 or olpn == vfpn + 2:
                    vfh = vfp[1].split('/')
                    vfph = int(vfh[0].split('humor=')[1])
                    if olhn == vfph or olhn == vfph - 1 or olhn == vfhn + 1 or olph == vfhn - 2 or olph == vfph + 2:
                        vfhf = vfh[1].split('f=')[1]
                        if vfhf == f:
                            p.append(k)
                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            else:
                pass
        except IndexError:
            pass
    finalout = random.choice(p)
    return finalout
